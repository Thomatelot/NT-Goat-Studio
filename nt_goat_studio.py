#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NT Goat Studio 2.0 - web interface for the Nightmare Troubadour Goat patcher.

Run:  python nt_goat_studio.py            (opens http://127.0.0.1:8765 in your browser)
      python nt_goat_studio.py --port 9000 --no-browser
      python nt_goat_studio.py build ROM.nds OUT.nds [--preset standard|gentle|hard|goat] [--no-postgame]

Everything runs locally; nothing is sent anywhere.
"""
import argparse
import json
import os
import secrets
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import nt_goat_patcher as core  # noqa: E402
import profiles as PR            # noqa: E402
import studio_core as SC         # noqa: E402

VERSION = "2.1"

# Security: the server only listens on 127.0.0.1, only answers requests whose Host
# header is this machine (blocks DNS-rebinding), and every API call must carry a
# random per-session token that only the Studio page knows (blocks other web sites
# open in your browser from talking to it).
TOKEN = secrets.token_urlsafe(24)
ALLOWED_HOSTS = ("127.0.0.1", "localhost")
MAX_UPLOAD = 256 * 1024 * 1024

KIND_NAME = {0: "Normal", 1: "Effect", 2: "Fusion", 3: "Fusion", 4: "Ritual", 5: "Ritual", 0xD: "Spell", 0xE: "Trap"}

HIDDEN = [
    dict(title="Card Gallery", status="Works", how="Developer ROM: 'Card Gallery'",
         text="A developer card viewer that shows every one of the 1,075 cards with art and text, "
              "whether you own them or not. It is scene 24 in the game's scene table and nothing in "
              "the menus leads to it."),
    dict(title="Bust-up & Background viewer", status="Works", how="Developer ROM: 'Bust-up viewer'",
         text="A tool the artists used to check character portraits on every location background. "
              "Its Japanese debug labels show as garbled text because the European font has no Japanese characters."),
    dict(title="Debug quick duel (Duel B-select)", status="Works with one opponent slot",
         how="Developer ROM: 'Duel Arena' (put any deck in it)",
         text="Starts a duel immediately against deck slot 2 (Yami Yugi). Other slots crash in the "
              "game's own text code, so the Studio swaps the deck file behind slot 2 instead: you "
              "can fight any deck, shown with Yami Yugi's portrait."),
    dict(title="Script Test / 3D Script", status="Works", how="Developer ROM: 'Script Test'",
         text="Plays story event scripts directly (the KaibaCorp opening by default)."),
    dict(title="Duel Only / Card Get", status="Works", how="Developer ROM",
         text="'Duel Only' starts a duel against a faceless test opponent; 'Card Get' is the debug "
              "screen that awards cards."),
    dict(title="Developer scene list", status="Text only",
         text="31 internal scene names in Japanese (Logo, Map, Mail, Trunk, Kiosk, Story, Side "
              "Exchange, Gallery, Satellite, Recipe Viewer, Script Test, Duelist Info...) and debug duel "
              "options: Match / Single / 20-turn duel / Shadow Game / Noah & Gozaburo."),
    dict(title="Unused decks", status="Selectable in the Studio",
         text="Decks the game never loads: Ojama Lock (with 3 Ojama King), Final Countdown stall, "
              "Stone wall, a developer test deck, and the E3 2005 demo decks for Yami Yugi, Kaiba, "
              "Joey and the player. Assign any of them to a duelist from a deck drawer."),
    dict(title="Sound test lists", status="Text only",
         text="Every BGM title in Japanese and English (\"Melancholy Dream\", \"Duel of Destiny\", "
              "\"Rise from Darkness\"...) plus a location list including Pandora (Arkana's Japanese "
              "name) and the Big Five's Japanese names."),
    dict(title="Unused graphics", status="Files only",
         text="A US title logo (NT_USA_Logo), extra map backgrounds (map02_07e1, map03_09a/b), kiosk "
              "room variants, a ritual star effect and build files (makelist.inc) listing Photoshop "
              "sources and a Thumbs.db."),
    dict(title="Unused characters", status="No duel data",
         text="Clerk and Roland have names and story roles but no duelist data; nine name slots "
              "after Bakura are empty."),
]


class App:
    def __init__(self):
        self.st = None
        self.rom_name = None
        self.built = None
        self.built_name = None
        self.lock = threading.Lock()

    # ── helpers ─────────────────────────────────────────────────────────────
    def need(self):
        if not self.st:
            raise ValueError("Load your Nightmare Troubadour ROM first.")
        return self.st

    def card_json(self, cid, count=None):
        c = self.st.db.by_id[cid]
        name = c["name"]
        d = dict(id=cid, name=name, kind=KIND_NAME.get(c["kind"], "?"), level=c["level"],
                 atk=c["atk"], df=c["df"], limit=core.goat_limit(name))
        if count is not None:
            d["count"] = count
        return d

    def deck_json(self, main, extra):
        def group(ids):
            out, seen = [], {}
            for cid in ids:
                seen[cid] = seen.get(cid, 0) + 1
            for cid, n in seen.items():
                out.append(self.card_json(cid, n))
            return out
        return dict(main=group(main), extra=group(extra), size=len(main))

    def load(self, data, name):
        st = SC.Studio(data)
        with self.lock:
            self.st, self.rom_name, self.built = st, name, None

    def state(self):
        out = dict(version=VERSION, loaded=bool(self.st), presets=SC.PRESETS,
                   hidden=HIDDEN, dev_scenes={k: v[1] for k, v in SC.DEV_SCENES.items()})
        if not self.st:
            return out
        st = self.st
        table = SC.core and core
        bl = core.compare_banlist(core.read_game_banlist(st.rom, st.db) or {}, st.db)
        out.update(
            rom=dict(name=self.rom_name, title=st.rom.game_title, code=st.rom.game_code,
                     size=len(st.rom.data), cards=len(st.db.by_id), timeline=st.timeline_ok),
            banlist_ok=not bl[0],
            options=st.options,
            profiles={dd: dict(name=p["name"], boost=st.boost(dd), default_boost=p.get("boost", 0))
                      for dd, p in PR.PROFILES.items()},
            decks=[dict(key=k, name=v.get("name") or k, note=v.get("note", ""), custom=k in st.custom_decks)
                   for k, v in st.all_decks().items()],
            dev_decks=[dict(key="dev:" + f, name=n) for f, n in PR.DEV_DECKS.items() if st.rom.exists('deck/' + f)],
            built=self.built_name)
        return out

    def plan(self):
        st = self.need()
        plan, rows = st.plan()
        duelists = []
        groups = {}
        for f, e in plan.items():
            groups.setdefault(e.get("duelist") or "zz", []).append((f, e))
        for dd in sorted(groups):
            prof = PR.PROFILES.get(dd)
            items = []
            for f, e in groups[dd]:
                spec = e["spec"]
                err = None
                try:
                    main, extra = st.build(spec, f)
                    size = len(main)
                except core.DeckError as ex:
                    err, size = str(ex), 0
                items.append(dict(file=f, kind=e["kind"], tier=e.get("tier"), stages=e.get("stages", []),
                                  name=spec.get("name") or spec.get("label") or spec.get("note") or e.get("key"),
                                  note=spec.get("note", ""), override=st.overrides.get(f), error=err, size=size))
            duelists.append(dict(id=dd, name=prof["name"] if prof else "Tournament & special",
                                 levels=rows.get(dd), original=st.levels.get(dd), decks=items))
        return dict(duelists=duelists)

    def deck(self, f=None, key=None):
        st = self.need()
        if f:
            plan, _ = st.plan()
            e = plan[f]
            spec = e["spec"]
            title = spec.get("name") or spec.get("label") or spec.get("note")
        else:
            spec = st.deck_spec(key)
            title = spec.get("name") or key
        try:
            main, extra = st.build(spec, f or key)
            d = self.deck_json(main, extra)
            d["error"] = None
        except core.DeckError as ex:
            d = dict(main=[], extra=[], size=0, error=str(ex))
        d.update(title=title, note=spec.get("note", ""), file=f, key=key)
        return d

    def cards(self, q, kind):
        st = self.need()
        q = (q or "").lower()
        res = []
        for cid, c in st.db.by_id.items():
            if q and q not in c["name"].lower():
                continue
            k = KIND_NAME.get(c["kind"], "?")
            if kind and kind != "all" and k.lower() != kind:
                continue
            if core.goat_limit(c["name"]) == 0:
                continue
            res.append(self.card_json(cid))
        res.sort(key=lambda x: x["name"])
        return res[:200]

    def card(self, cid):
        st = self.need()
        d = self.card_json(cid)
        d["desc"] = st.db.desc(cid)
        return d

    def validate(self, body):
        st = self.need()
        spec = dict(main="\n".join("%d %s" % (n, c) for n, c in body.get("main", [])),
                    extra="\n".join("%d %s" % (n, c) for n, c in body.get("extra", [])))
        try:
            core.build_deck(body.get("name") or "deck", spec, st.db)
            return dict(ok=True, errors=[])
        except core.DeckError as ex:
            return dict(ok=False, errors=str(ex).splitlines()[1:])

    def save_custom(self, body):
        st = self.need()
        name = (body.get("name") or "").strip() or "My deck"
        key = body.get("key") or ("custom:" + name)
        spec = dict(name=name[:20], note=body.get("note") or "Custom deck",
                    main="\n".join("%d %s" % (n, c) for n, c in body.get("main", [])),
                    extra="\n".join("%d %s" % (n, c) for n, c in body.get("extra", [])))
        core.build_deck(name, spec, st.db)
        st.custom_decks[key] = spec
        return dict(key=key)

    def build(self, body):
        st = self.need()
        logs = []
        dev = body.get("dev_scene") or None
        out, plan = st.apply(log=logs.append, dev_scene=dev)
        if dev == "arena" and body.get("arena_key"):
            k = body["arena_key"]
            if k.startswith("file:"):
                spec = plan[k[5:]]["spec"]
            else:
                spec = st.deck_spec(k)
            main, extra = st.build(spec, "arena")
            rom = core.NDSRom(out)
            rom.replace('deck/012.ydc', core.write_ydc(rom.read('deck/012.ydc')[:8], main, extra))
            out = rom.finalize()
            logs.append("Duel Arena opponent deck: %s" % (spec.get("name") or spec.get("note")))
        base = os.path.splitext(self.rom_name or "Nightmare Troubadour.nds")[0]
        suffix = " (GOAT)" if not dev else " (DEV - %s)" % dev
        self.built, self.built_name = out, base + suffix + ".nds"
        logs.append("Ready: %s (%.1f MB)" % (self.built_name, len(out) / 1048576))
        return dict(log=logs, name=self.built_name)

    def resolve_save_path(self, path):
        """Accept a folder or a file path. A folder (existing, or ending with a slash,
        or without .nds extension) gets the built ROM's file name appended."""
        if not path:
            raise ValueError("Type a folder or a file path, e.g. D:\\TELECHARGEMENTS")
        is_dir = os.path.isdir(path) or path.endswith(("/", "\\")) or not path.lower().endswith(".nds")
        if is_dir:
            os.makedirs(path, exist_ok=True)
            path = os.path.join(path, self.built_name)
        else:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        return path

    def export_config(self):
        st = self.need()
        return dict(options=st.options, overrides=st.overrides, custom_decks=st.custom_decks)

    def import_config(self, cfg):
        st = self.need()
        st.options.update(cfg.get("options", {}))
        st.custom_decks.update(cfg.get("custom_decks", {}))
        st.overrides.update(cfg.get("overrides", {}))
        return dict(ok=True)


APP = App()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            raise ValueError("File too large (max 256 MB).")
        return self.rfile.read(n) if n else b""

    def host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return host in ALLOWED_HOSTS

    def token_ok(self):
        q = parse_qs(urlparse(self.path).query)
        tok = self.headers.get("X-Studio-Token") or (q.get("t") or [""])[0]
        return secrets.compare_digest(tok, TOKEN)

    def guard(self, api):
        if not self.host_ok():
            self.send(403, {"error": "Forbidden host."})
            return False
        if api and not self.token_ok():
            self.send(403, {"error": "Missing or wrong session token. Reload the Studio page."})
            return False
        return True

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if not self.guard(u.path.startswith("/api/")):
            return
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "web", "index.html"), "rb") as f:
                    page = f.read().replace(b"__STUDIO_TOKEN__", TOKEN.encode())
                return self.send(200, page, "text/html; charset=utf-8",
                                 {"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                                  "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'"})
            if u.path == "/api/state":
                return self.send(200, APP.state())
            if u.path == "/api/plan":
                return self.send(200, APP.plan())
            if u.path == "/api/deck":
                return self.send(200, APP.deck(q.get("file"), q.get("key")))
            if u.path == "/api/cards":
                return self.send(200, APP.cards(q.get("q"), q.get("kind")))
            if u.path == "/api/card":
                return self.send(200, APP.card(int(q["id"])))
            if u.path == "/api/report":
                return self.send(200, APP.need().report(), "text/plain; charset=utf-8",
                                 {"Content-Disposition": 'attachment; filename="NT_Goat_plan.txt"'})
            if u.path == "/api/config":
                return self.send(200, APP.export_config(), headers={"Content-Disposition": 'attachment; filename="nt_goat_studio.json"'})
            if u.path == "/api/download":
                if not APP.built:
                    return self.send(404, {"error": "Build a ROM first."})
                return self.send(200, APP.built, "application/octet-stream",
                                 {"Content-Disposition": 'attachment; filename="%s"' % APP.built_name.replace('"', '')})
            return self.send(404, {"error": "not found"})
        except Exception as ex:  # noqa
            traceback.print_exc()
            return self.send(400, {"error": str(ex)})

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if not self.guard(True):
            return
        try:
            if u.path == "/api/upload":
                APP.load(self.body(), q.get("name") or "rom.nds")
                return self.send(200, APP.state())
            body = json.loads(self.body() or b"{}")
            if u.path == "/api/open":
                path = os.path.expanduser(body["path"].strip().strip('"'))
                with open(path, "rb") as f:
                    APP.load(f.read(), os.path.basename(path))
                return self.send(200, APP.state())
            st = APP.need()
            if u.path == "/api/options":
                for k in ("preset", "postgame", "rename"):
                    if k in body:
                        st.options[k] = body[k]
                if "boosts" in body:
                    st.options["boosts"] = {k: int(v) for k, v in body["boosts"].items()}
                return self.send(200, APP.state())
            if u.path == "/api/override":
                if body.get("key"):
                    st.overrides[body["file"]] = body["key"]
                else:
                    st.overrides.pop(body["file"], None)
                return self.send(200, {"ok": True})
            if u.path == "/api/validate":
                return self.send(200, APP.validate(body))
            if u.path == "/api/custom":
                return self.send(200, APP.save_custom(body))
            if u.path == "/api/build":
                return self.send(200, APP.build(body))
            if u.path == "/api/config":
                return self.send(200, APP.import_config(body))
            if u.path == "/api/save":
                path = os.path.expanduser(body["path"].strip().strip('"'))
                if not APP.built:
                    raise ValueError("Build a ROM first.")
                path = APP.resolve_save_path(path)
                with open(path, "wb") as f:
                    f.write(APP.built)
                return self.send(200, {"ok": True, "path": path})
            return self.send(404, {"error": "not found"})
        except Exception as ex:  # noqa
            traceback.print_exc()
            return self.send(400, {"error": str(ex)})


def serve(port, open_browser):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://127.0.0.1:%d/" % port
    print("NT Goat Studio %s running at %s  (Ctrl+C to stop)" % (VERSION, url))
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(description="NT Goat Studio")
    ap.add_argument("cmd", nargs="?", default="serve", choices=["serve", "build", "report"])
    ap.add_argument("rom", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--preset", default="standard", choices=list(SC.PRESETS))
    ap.add_argument("--no-postgame", action="store_true")
    ap.add_argument("--dev", choices=list(SC.DEV_SCENES), help="build a developer ROM instead")
    a = ap.parse_args()
    if a.cmd == "serve":
        return serve(a.port, not a.no_browser)
    with open(a.rom, "rb") as f:
        st = SC.Studio(f.read())
    st.options.update(preset=a.preset, postgame=not a.no_postgame)
    if a.cmd == "report":
        text = st.report()
        if a.out:
            open(a.out, "w", encoding="utf-8").write(text)
        print(text)
        return
    out, _ = st.apply(dev_scene=a.dev)
    with open(a.out, "wb") as f:
        f.write(out)
    print("Wrote", a.out)


if __name__ == "__main__":
    main()
