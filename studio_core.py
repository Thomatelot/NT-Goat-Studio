# -*- coding: utf-8 -*-
"""NT Goat Studio - core logic (no UI).

Story progression facts (reverse-engineered from the European ROM):
* The save file holds a story STAGE 0..10. Stage 10 = post-game (after Yami Marik).
* arm9 table @0x02060D1C: 16 bytes per duelist (01..40); bytes 4..14 = the
  duelist's level at stages 0..10 (0 = not available at that stage).
* Deck variant used at stage s = number of distinct non-zero levels in stages
  0..s. File "deck/DDV.ydc": DD = duelist, V = variant. At stage 10 the game
  also allows variant 6 (random pick between candidates).
* Suffixes obe/osi/ra: only if that duelist currently holds Obelisk / Slifer / Ra.
"""
import copy
import re
import struct

import blz_patch
import nt_goat_patcher as core
import profiles as PR

LEVEL_TABLE = 0x60D1C          # offset in decompressed arm9
FLOW_TITLE = 0x68134           # boot flow entry (title screen scene id)
ARENA_OPP_IMM = 0x10EC8        # 'mov r0,#2' : debug duel opponent slot (deck index + 1)
DECK_TABLE = 0x68D4C           # 88 pointers to "deck/xxx.ydc"
EXPECTED_ROW_IDS = [0x01, 0x02, 0x04, 0x03, 0x09, 0x06]

DEV_SCENES = {
    "gallery": (0x18, "Card Gallery - every card in the game"),
    "bustup": (0x19, "Bust-up & Background viewer (developer)"),
    "script": (0x00, "Script Test - plays story event scripts"),
    "arena": (0x1D, "Duel Arena - debug quick duel against a chosen deck"),
    "duelonly": (0x1E, "Duel Only - quick duel against a test opponent"),
    "cardget": (0x1C, "Card Get (developer)"),
}

PRESETS = {
    "gentle": "Gentle: one tier easier until the final stretch",
    "standard": "Standard: Rookie -> Duelist -> Expert -> Goat Max",
    "hard": "Hard: one tier harder from stage 3",
    "goat": "Goat everywhere: every opponent plays Goat Max decks",
}


def parse_file(fname):
    m = re.match(r'^(\d\d)(\d)(obe|osi|ra)?\.ydc$', fname)
    if not m:
        return None
    return m.group(1), int(m.group(2)), m.group(3)


class Studio:
    def __init__(self, rom_bytes):
        self.rom = core.NDSRom(rom_bytes)
        if not self.rom.exists('bin/CARD_Prop.bin') or not self.rom.exists('deck/011.ydc'):
            raise ValueError("This ROM does not look like Yu-Gi-Oh! Nightmare Troubadour.")
        self.db = core.CardDB(self.rom)
        a9 = self.rom.data
        off, _, ram, size = struct.unpack_from('<IIII', a9, 0x20)
        self.arm9_off, self.arm9_size = off, size
        self.arm9_comp = bytes(a9[off:off + size])
        _, self.arm9 = blz_patch.tokens(self.arm9_comp)
        self.timeline_ok = all(self.arm9[LEVEL_TABLE + 16 * i] == v for i, v in enumerate(EXPECTED_ROW_IDS))
        self.levels = {}
        if self.timeline_ok:
            for dd in range(1, 41):
                o = LEVEL_TABLE + 16 * (dd - 1) + 4
                self.levels["%02d" % dd] = list(self.arm9[o:o + 11])
        self.orig_names = {}
        try:
            idx, txt = self.rom.read('bin/GAME_Indx_E.bin'), self.rom.read('bin/GAME_Text_E.bin')
            for i, stem in enumerate(core.DECK_ORDER):
                o = struct.unpack_from('<I', idx, 4 * (core.DECK_NAME_TEXT_BASE + i))[0]
                self.orig_names[stem + '.ydc'] = txt[o:txt.find(b'\0', o)].decode('latin-1')
        except Exception:
            pass
        self.deck_files = sorted(p[5:] for p in self.rom.list('deck/') if p.endswith('.ydc'))
        self.archetypes = dict(core.DECKS)
        self.archetypes.update(PR.EXTRA_ARCHETYPES)
        self.custom_decks = {}       # user-made decks {key: spec}
        self.overrides = {}          # file -> deck key
        self.options = dict(preset="standard", postgame=True, rename=True, boosts={})

    # ── timeline ───────────────────────────────────────────────────────────
    def files_of(self, dd):
        out = []
        for f in self.deck_files:
            p = parse_file(f)
            if p and p[0] == dd:
                out.append((f, p[1], p[2]))
        return out

    @staticmethod
    def variant_at(row, s):
        seen, prev, var = 0, 0, 0
        for i in range(s + 1):
            if row[i] and row[i] != prev:
                var += 1
                prev = row[i]
        return max(var, 1)

    def new_levels(self):
        rows = copy.deepcopy(self.levels)
        if not self.options.get("postgame"):
            return rows
        for dd, row in rows.items():
            if not row[10]:
                continue
            files = self.files_of(dd)
            variants = {v for f, v, suf in files}
            if 6 in variants:
                # make stage 10 a new variant with no file -> only the variant-6 deck remains
                if row[9] and row[10] == row[9]:
                    row[10] = min(255, max(row) + 2)
                continue
            plain = sorted({v for f, v, suf in files if not suf})
            if len(plain) < 2:
                continue
            k = max(plain)
            if self.variant_at(row, 10) != k:
                continue
            first_k = next(s for s in range(11) if row[s] and self.variant_at(row, s) == k)
            if first_k == 10:
                continue  # already post-game exclusive
            prev_val = row[first_k - 1] if first_k > 0 and row[first_k - 1] else None
            if prev_val is None:
                continue
            final = row[10]
            for s in range(first_k, 10):
                row[s] = prev_val
            row[10] = final if final != prev_val else min(255, prev_val + 2)
        return rows

    def stages_of(self, rows):
        """file -> sorted list of stages where the file can be picked."""
        res = {}
        for dd, row in rows.items():
            for f, v, suf in self.files_of(dd):
                st = []
                for s in range(11):
                    if not row[s]:
                        continue
                    if self.variant_at(row, s) == v or (s == 10 and v == 6):
                        st.append(s)
                res[f] = st
        return res

    # ── tiers ────────────────────────────────────────────────────────────────
    def boost(self, dd):
        b = self.options.get("boosts", {}).get(dd)
        if b is None:
            b = PR.PROFILES.get(dd, {}).get("boost", 0)
        return int(b)

    def tier_for(self, dd, stages):
        preset = self.options.get("preset", "standard")
        if preset == "goat":
            return 4
        if not stages:
            return 3
        first = min(stages)
        if stages == [10]:
            return 4
        boost = self.boost(dd)
        base = 1 if first <= 2 else 2 if first <= 5 else 3
        if preset == "gentle" and first < 8:
            base = max(1, base - 1)
        if preset == "hard" and first >= 3:
            base = min(4, base + 1)
        if 10 in stages and first >= 8:
            return 4                      # late single-deck duelists: post-game max
        if boost and 10 in stages and len(self.files_of(dd)) == 1:
            return 4                      # single-deck bosses (Noah, Gozaburo)
        if boost and first >= 8:
            return 4
        if first < 6:
            boost = 0                     # bosses only step up from stage 6
        return min(3 if preset != "hard" else 4, base + boost)

    # ── deck generation ─────────────────────────────────────────────────────
    def theme_deck(self, dd, tier):
        prof = PR.PROFILES[dd]
        counts, order = {}, []

        def add(name, n, respect_gate=True):
            cid = self.db.lookup(name)
            if cid is None:
                return 0
            real = self.db.name(cid)
            lim = core.goat_limit(real)
            room = min(n, lim - counts.get(real, 0), 40 - sum(counts.values()))
            if room <= 0 or self.db.is_extra(cid):
                return 0
            if real not in counts:
                order.append(real)
            counts[real] = counts.get(real, 0) + room
            return room

        for n, name in core.parse_list(PR.STAPLES[tier]):
            add(name, n)
        for line in prof["theme"].strip().splitlines():
            m = re.match(r'^(\d+)\s+(.+?)(?:\s+@(\d))?$', line.strip())
            if not m:
                continue
            gate = int(m.group(3) or 1)
            if gate > tier:
                continue
            add(m.group(2), int(m.group(1)))
        for n, name in core.parse_list(PR.FILLER):
            if sum(counts.values()) >= 40:
                break
            add(name, n)
        main = "\n".join("%d %s" % (counts[n], n) for n in order)
        return dict(name=None, note="%s - %s tier" % (prof["name"], PR.TIER_NAMES[tier]),
                    main=main, extra=prof.get("extra", ""))

    def max_deck(self, dd, idx):
        prof = PR.PROFILES[dd]
        spec = prof["max"][idx % len(prof["max"])]
        base_key = spec.get("deck") or spec.get("base")
        base = self.all_decks()[base_key]
        main = core.parse_list(base["main"])
        if spec.get("swap"):
            cnt = {}
            order = []
            for n, c in main:
                if c not in cnt:
                    order.append(c)
                cnt[c] = cnt.get(c, 0) + n
            for line in spec["swap"].strip().splitlines():
                m = re.match(r'^([+-])(\d+)\s+(.+)$', line.strip())
                sign, n, c = m.group(1), int(m.group(2)), m.group(3).strip()
                if sign == '-':
                    cnt[c] = cnt.get(c, 0) - n
                else:
                    if c not in cnt:
                        order.append(c)
                    cnt[c] = cnt.get(c, 0) + n
            main = [(cnt[c], c) for c in order if cnt.get(c, 0) > 0]
        name = spec.get("name") or base.get("name") or base_key
        return dict(name=name, note="%s - Goat Max (%s)" % (prof["name"], base_key),
                    main="\n".join("%d %s" % x for x in main), extra=base.get("extra", ""))

    def all_decks(self):
        d = dict(self.archetypes)
        d.update(self.custom_decks)
        return d

    # ── plan ─────────────────────────────────────────────────────────────────
    def plan(self):
        rows = self.new_levels() if self.timeline_ok else {}
        stages = self.stages_of(rows) if self.timeline_ok else {}
        plan = {}
        max_counter = {}
        for f in self.deck_files:
            p = parse_file(f)
            entry = None
            if f in self.overrides:
                key = self.overrides[f]
                entry = dict(kind="custom", key=key, spec=self.deck_spec(key))
            elif p and p[0] in PR.PROFILES:
                dd = p[0]
                st = stages.get(f, [])
                tier = self.tier_for(dd, st)
                if tier == 4:
                    i = max_counter.get(dd, 0)
                    max_counter[dd] = i + 1
                    spec = self.max_deck(dd, i)
                else:
                    spec = self.theme_deck(dd, tier)
                    spec["label"] = self.orig_names.get(f) or "%s deck" % PR.PROFILES[dd]["name"]
                entry = dict(kind="profile", duelist=dd, tier=tier, stages=st, spec=spec)
            elif f in PR.SPECIAL:
                dd, tier = PR.SPECIAL[f]
                if self.options.get("preset") == "goat":
                    tier = 4
                spec = self.max_deck(dd, 0) if tier == 4 else self.theme_deck(dd, tier)
                spec.setdefault("label", "%s (tournament)" % PR.PROFILES[dd]["name"])
                entry = dict(kind="special", duelist=dd, tier=tier, stages=[], spec=spec)
            if entry:
                plan[f] = entry
        return plan, rows

    def deck_spec(self, key):
        if key.startswith("dev:"):
            f = key[4:]
            hdr, m, e, s = core.read_ydc(self.rom.read('deck/' + f))
            return dict(name=None, note=PR.DEV_DECKS.get(f, f), raw=(m, e))
        return self.all_decks()[key]

    def build(self, spec, label):
        if "raw" in spec:
            return spec["raw"]
        return core.build_deck(label, spec, self.db)

    # ── arm9 edits ───────────────────────────────────────────────────────────
    def arm9_changes(self, rows, dev_scene=None, arena_deck=None):
        ch = {}
        if rows and self.options.get("postgame"):
            for dd, row in rows.items():
                o = LEVEL_TABLE + 16 * (int(dd) - 1) + 4
                for s, v in enumerate(row):
                    if self.arm9[o + s] != v:
                        ch[o + s] = v
        if dev_scene:
            ch[FLOW_TITLE] = DEV_SCENES[dev_scene][0]
            if dev_scene == "arena" and arena_deck is not None:
                ch[ARENA_OPP_IMM] = arena_deck + 1
        return ch

    def deck_index(self, fname):
        stem = fname[:-4]
        idx = core.DECK_ORDER.index(stem) if stem in core.DECK_ORDER else None
        return idx

    # ── apply ────────────────────────────────────────────────────────────────
    def apply(self, log=print, dev_scene=None, arena_deck=None):
        rom = core.NDSRom(bytes(self.rom.data))
        plan, rows = self.plan()
        problems, built = [], {}
        for f, e in plan.items():
            try:
                built[f] = self.build(e["spec"], f)
            except core.DeckError as ex:
                problems.append(str(ex))
        if problems:
            raise core.DeckError("Nothing was written. Fix these problems first:\n" + "\n".join(problems))
        for f, (main, extra) in sorted(built.items()):
            hdr = rom.read('deck/' + f)[:8]
            rom.replace('deck/' + f, core.write_ydc(hdr, main, extra, []))
        log("Wrote %d opponent decks." % len(built))
        # deck names
        if self.options.get("rename", True):
            changes = {}
            for i, stem in enumerate(core.DECK_ORDER):
                e = plan.get(stem + '.ydc')
                if e and e["spec"].get("name"):
                    changes[core.DECK_NAME_TEXT_BASE + i] = e["spec"]["name"][:20]
            for L in core.TEXT_LANGS:
                ip, tp = 'bin/GAME_Indx_%s.bin' % L, 'bin/GAME_Text_%s.bin' % L
                if rom.exists(ip) and rom.exists(tp) and changes:
                    i2, t2 = core.patch_text(rom.read(ip), rom.read(tp), changes)
                    rom.replace(ip, i2)
                    rom.replace(tp, t2)
            log("Renamed %d Goat Max decks (5 languages)." % len(changes))
        # arm9
        ch = self.arm9_changes(rows, dev_scene, arena_deck)
        if ch:
            new_comp = blz_patch.patch(self.arm9_comp, ch)
            rom.data[self.arm9_off:self.arm9_off + self.arm9_size] = new_comp
            log("Game code: %d bytes changed (re-encoded in place, same size, verified)." % len(ch))
        return rom.finalize(), plan

    # ── report ───────────────────────────────────────────────────────────────
    def report(self):
        plan, rows = self.plan()
        lines = ["NT GOAT STUDIO - plan (%s preset, post-game decks for all: %s)" %
                 (self.options["preset"], self.options["postgame"]), ""]
        by = {}
        for f, e in plan.items():
            by.setdefault(e.get("duelist", "zz"), []).append((f, e))
        for dd in sorted(by):
            name = PR.PROFILES.get(dd, {}).get("name", "Special")
            lines.append("== %s" % name)
            for f, e in by[dd]:
                st = e.get("stages") or []
                stx = ("stages %d-%d" % (min(st), max(st))) if st else "tournament"
                lines.append("  %-11s %-14s %-9s %s" % (f, stx, PR.TIER_NAMES.get(e.get("tier"), "custom"),
                                                       e["spec"].get("name") or e["spec"].get("label") or e["spec"].get("note")))
            lines.append("")
        return "\n".join(lines)
