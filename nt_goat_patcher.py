#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NT GOAT PATCHER
===============
Turns every CPU opponent of
    "Yu-Gi-Oh! Nightmare Troubadour (Europe) (En,Fr,De,Es,It).nds"
into a GOAT Format (April 2005 Forbidden & Limited list) duelist:
Yugi, Kaiba, Pegasus and the rest of the cast play Goat Control, Chaos
(Return / Control / Recruiter), Reasoning Gate and the other 2005 meta decks,
rebuilt from the cards that actually exist in Nightmare Troubadour.

* No dependencies: Python 3.8+ only (Tkinter for the GUI, which ships with
  the standard Windows / macOS Python installers).
* Run without arguments for the GUI, or see `python nt_goat_patcher.py -h`.
* The original ROM is never modified; a new .nds file is written.

How it works
------------
The ROM's file system (NitroFS) is parsed, the card database is read from the
ROM itself (bin/CARD_*.bin) so every card name is checked against the game's
real card pool, and each opponent deck file (deck/*.ydc) is replaced with a
Goat deck. Deck names (GAME_Text_*.bin) are renamed in all 5 languages.
Every deck is validated against the April 2005 TCG Forbidden & Limited list
before anything is written. The game's own built-in banlist is also checked
(it already matches Goat for every Goat-legal card).
"""
import argparse
import json
import os
import re
import struct
import sys

VERSION = "1.0"

# ════════════════════════════════════════════════════════════════════════════
#  Low level helpers
# ════════════════════════════════════════════════════════════════════════════

def crc16(data, crc=0xFFFF):
    """CRC-16 used by the Nintendo DS header (poly 0xA001, init 0xFFFF)."""
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def blz_decompress(data):
    """Decompress Nintendo 'backwards LZ' (used for arm9 / overlays)."""
    data = bytearray(data)
    enc_hdr, inc_len = struct.unpack_from('<II', data, len(data) - 8)
    if inc_len == 0:
        return bytes(data)
    hdr_len, enc_len = enc_hdr >> 24, enc_hdr & 0xFFFFFF
    dec_len = len(data) + inc_len
    out = bytearray(dec_len)
    out[:len(data)] = data
    start, src, dst = len(data) - enc_len, len(data) - hdr_len, dec_len
    while src > start:
        src -= 1
        flags = data[src]
        for _ in range(8):
            if src <= start:
                break
            if flags & 0x80:
                src -= 2
                v = data[src] | (data[src + 1] << 8)
                ln, disp = (v >> 12) + 3, (v & 0xFFF) + 3
                for _ in range(ln):
                    dst -= 1
                    out[dst] = out[dst + disp]
            else:
                src -= 1
                dst -= 1
                out[dst] = data[src]
            flags = (flags << 1) & 0xFF
    return bytes(out)


def align(x, a):
    return (x + a - 1) // a * a


# ════════════════════════════════════════════════════════════════════════════
#  Nintendo DS ROM / NitroFS
# ════════════════════════════════════════════════════════════════════════════

class NDSRom:
    def __init__(self, data):
        self.data = bytearray(data)
        h = self.data
        if len(h) < 0x200:
            raise ValueError("File is too small to be a Nintendo DS ROM.")
        self.game_title = h[0:12].rstrip(b'\0').decode('ascii', 'replace')
        self.game_code = h[12:16].decode('ascii', 'replace')
        (self.fnt_off, self.fnt_size, self.fat_off, self.fat_size) = struct.unpack_from('<IIII', h, 0x40)
        if crc16(h[:0x15E]) != struct.unpack_from('<H', h, 0x15E)[0]:
            raise ValueError("Header checksum mismatch: this does not look like a valid .nds ROM.")
        self.nfiles = self.fat_size // 8
        self.fat = [list(struct.unpack_from('<II', h, self.fat_off + 8 * i)) for i in range(self.nfiles)]
        self.paths = {}
        self._parse_fnt()
        self._grow_ptr = None

    # -- file name table -----------------------------------------------------
    def _parse_fnt(self):
        base = self.fnt_off

        def walk(dir_id, prefix):
            off = base + (dir_id & 0xFFF) * 8
            sub_off, first_id = struct.unpack_from('<IH', self.data, off)
            p = base + sub_off
            fid = first_id
            while True:
                t = self.data[p]; p += 1
                if t == 0:
                    break
                ln = t & 0x7F
                name = self.data[p:p + ln].decode('latin-1'); p += ln
                if t & 0x80:
                    sub_id = struct.unpack_from('<H', self.data, p)[0]; p += 2
                    walk(sub_id, prefix + name + '/')
                else:
                    self.paths[prefix + name] = fid
                    fid += 1
        walk(0xF000, '')

    def exists(self, path):
        return path in self.paths

    def read(self, path):
        s, e = self.fat[self.paths[path]]
        return bytes(self.data[s:e])

    def list(self, prefix=''):
        return sorted(p for p in self.paths if p.startswith(prefix))

    # -- writing ----------------------------------------------------------------
    def _shared(self, fid):
        s, e = self.fat[fid]
        for i, (s2, e2) in enumerate(self.fat):
            if i != fid and s2 < e and s < e2 and e2 > s2:
                return True
        return False

    def _end_of_data(self):
        used = struct.unpack_from('<I', self.data, 0x80)[0]
        return max([used] + [e for s, e in self.fat])

    def _slack_end(self, fid):
        """End of the free space after a file (its size plus the alignment
        padding up to the next file / ROM region)."""
        s, e = self.fat[fid]
        h = self.data
        bounds = [st for st, en in self.fat if st >= e and (st, en) != (s, e)]
        for o in (0x20, 0x30, 0x40, 0x48, 0x50, 0x58, 0x68):
            v = struct.unpack_from('<I', h, o)[0]
            if v >= e:
                bounds.append(v)
        bounds.append(max(e, struct.unpack_from('<I', h, 0x80)[0]))
        return max(e, min(bounds))

    def replace(self, path, new):
        """Replace a file. Written in place when it fits (file size + padding)
        and the space is not shared with another FAT entry; otherwise appended
        after the last file."""
        fid = self.paths[path]
        s, e = self.fat[fid]
        if not self._shared(fid):
            e = self._slack_end(fid)
        if len(new) <= e - s and not self._shared(fid):
            self.data[s:s + len(new)] = new
            self.data[s + len(new):e] = b'\xFF' * (e - s - len(new))
            self.fat[fid] = [s, s + len(new)]
        else:
            if self._grow_ptr is None:
                self._grow_ptr = align(self._end_of_data(), 0x200)
            start = self._grow_ptr
            end = start + len(new)
            if len(self.data) < end:
                self.data.extend(b'\xFF' * (end - len(self.data)))
            self.data[start:end] = new
            self.fat[fid] = [start, end]
            self._grow_ptr = align(end, 0x200)
        struct.pack_into('<II', self.data, self.fat_off + 8 * fid, *self.fat[fid])

    def finalize(self):
        used = struct.unpack_from('<I', self.data, 0x80)[0]
        end = self._end_of_data()
        if end > used:
            struct.pack_into('<I', self.data, 0x80, end)
            if len(self.data) < end:
                self.data.extend(b'\xFF' * (end - len(self.data)))
        cap = self.data[0x14]
        while (0x20000 << cap) < len(self.data):
            cap += 1
        self.data[0x14] = cap
        struct.pack_into('<H', self.data, 0x15E, crc16(self.data[:0x15E]))
        return bytes(self.data)

    # -- arm9 -------------------------------------------------------------------
    def arm9_decompressed(self):
        off, entry, ram, size = struct.unpack_from('<IIII', self.data, 0x20)
        body = bytes(self.data[off:off + size])
        footer = self.data[off + size:off + size + 12]
        if len(footer) == 12 and struct.unpack_from('<I', footer, 0)[0] == 0xDEC00621:
            mp = struct.unpack_from('<I', footer, 4)[0]
            comp_end = struct.unpack_from('<I', body, mp + 0x14)[0]
            if comp_end:
                ce = comp_end - ram
                return blz_decompress(body[:ce]) + body[ce:]
        return body


# ════════════════════════════════════════════════════════════════════════════
#  Card database (read from the ROM itself)
# ════════════════════════════════════════════════════════════════════════════

def norm(name):
    """Loose key for card names: 'D.D. Warrior Lady' == 'D. D. Warrior Lady'."""
    return re.sub(r'[^a-z0-9]', '', name.lower())


class CardDB:
    def __init__(self, rom, lang='E'):
        prop = rom.read('bin/CARD_Prop.bin')
        intid = rom.read('bin/CARD_IntID.bin')
        idx = rom.read('bin/CARD_Indx_%s.bin' % lang)
        names = rom.read('bin/CARD_Name_%s.bin' % lang)
        ids = struct.unpack('<%dH' % (len(intid) // 2), intid)
        inv = {v: k + 4000 for k, v in enumerate(ids) if v}
        self.by_id, self.by_key = {}, {}
        for i in range(1, len(prop) // 8):
            if i not in inv:
                continue
            a, b = struct.unpack_from('<II', prop, i * 8)
            o = struct.unpack_from('<I', idx, i * 8)[0]
            name = names[o:names.find(b'\0', o)].decode('latin-1')
            cid = inv[i]
            self.by_id[cid] = dict(id=cid, name=name, kind=b & 0xF, attr=(b >> 4) & 0xF,
                                   level=(b >> 8) & 0xF, atk=((a >> 13) & 0x1FF) * 10,
                                   df=((a >> 22) & 0x1FF) * 10)
            self.by_key.setdefault(norm(name), cid)
        self.desc_src = None
        try:
            self.desc_src = (idx, rom.read('bin/CARD_Desc_%s.bin' % lang), inv)
        except Exception:
            pass
        self._inv_idx = {v: k for k, v in inv.items()}

    def desc(self, cid):
        if not self.desc_src:
            return ''
        idx, d, inv = self.desc_src
        i = self._inv_idx.get(cid)
        if i is None:
            return ''
        o = struct.unpack_from('<I', idx, i * 8 + 4)[0]
        return d[o:d.find(b'\0', o)].decode('latin-1').replace('\r', ' ').replace('\n', ' ')

    def lookup(self, name):
        return self.by_key.get(norm(name))

    def name(self, cid):
        c = self.by_id.get(cid)
        return c['name'] if c else '#%d' % cid

    def is_extra(self, cid):
        return self.by_id[cid]['kind'] in (2, 3)


# ════════════════════════════════════════════════════════════════════════════
#  .ydc deck files
# ════════════════════════════════════════════════════════════════════════════

DEFAULT_YDC_HEADER = bytes.fromhex('01fc12004f57443f')


def read_ydc(data):
    p, lists = 8, []
    for _ in range(3):  # main, extra (fusion), side
        n = struct.unpack_from('<H', data, p)[0]; p += 2
        lists.append(list(struct.unpack_from('<%dH' % n, data, p))); p += 2 * n
    return data[:8], lists[0], lists[1], lists[2]


def write_ydc(header, main, extra, side=()):
    out = bytearray(header[:8].ljust(8, b'\0'))
    for lst in (main, extra, side):
        out += struct.pack('<H', len(lst)) + struct.pack('<%dH' % len(lst), *lst)
    return bytes(out)


# ════════════════════════════════════════════════════════════════════════════
#  GOAT FORMAT  -  April 2005 TCG Forbidden & Limited list
# ════════════════════════════════════════════════════════════════════════════

GOAT_FORBIDDEN = [
    "Chaos Emperor Dragon - Envoy of the End", "Fiber Jar", "Magical Scientist",
    "Makyura the Destructor", "Witch of the Black Forest", "Yata-Garasu",
    "Butterfly Dagger - Elma", "Change of Heart", "Confiscation", "Dark Hole",
    "Harpie's Feather Duster", "Mirage of Nightmare", "Monster Reborn",
    "Painful Choice", "Raigeki", "The Forceful Sentry", "Imperial Order",
]
GOAT_LIMITED = [
    "Black Luster Soldier - Envoy of the Beginning", "Breaker the Magical Warrior",
    "Cyber Jar", "Dark Magician of Chaos", "D.D. Warrior Lady", "Exodia the Forbidden One",
    "Exiled Force", "Injection Fairy Lily", "Jinzo", "Left Arm of the Forbidden One",
    "Left Leg of the Forbidden One", "Morphing Jar", "Protector of the Sanctuary",
    "Reflect Bounder", "Right Arm of the Forbidden One", "Right Leg of the Forbidden One",
    "Sacred Phoenix of Nephthys", "Sangan", "Sinister Serpent", "Tribe-Infecting Virus",
    "Twin-Headed Behemoth", "Card Destruction", "Delinquent Duo", "Graceful Charity",
    "Heavy Storm", "Lightning Vortex", "Mage Power", "Mystical Space Typhoon", "Pot of Greed",
    "Premature Burial", "Snatch Steal", "Swords of Revealing Light", "United We Stand",
    "Call of the Haunted", "Ceasefire", "Deck Devastation Virus", "Magic Cylinder",
    "Mirror Force", "Reckless Greed", "Ring of Destruction", "Torrential Tribute",
]
GOAT_SEMI = [
    "Abyss Soldier", "Dark Scorpion - Chick the Yellow", "Manticore of Darkness",
    "Marauding Captain", "Night Assailant", "Vampire Lord", "Creature Swap",
    "Emergency Provisions", "Level Limit - Area B", "Nobleman of Crossout",
    "Reinforcement of the Army", "Upstart Goblin", "Good Goblin Housekeeping",
    "Gravity Bind", "Last Turn",
]
# Cards present in Nightmare Troubadour (an OCG-based 2005 game) that were NOT
# released in the TCG during Goat format, plus the God cards. Never used here.
NOT_IN_GOAT_POOL = [
    "Marshmallon", "Sixth Sense", "Reversal of Graves", "Crush Card", "Exarion Universe",
    "Card of Sanctity", "Obelisk the Tormentor", "Slifer the Sky Dragon",
    "The Winged Dragon of Ra", "Master of Dragon Soldier",
]


def goat_limit(name):
    k = norm(name)
    if k in {norm(n) for n in GOAT_FORBIDDEN + NOT_IN_GOAT_POOL}:
        return 0
    if k in {norm(n) for n in GOAT_LIMITED}:
        return 1
    if k in {norm(n) for n in GOAT_SEMI}:
        return 2
    return 3


# ════════════════════════════════════════════════════════════════════════════
#  DECKLISTS  (Goat Format, adapted to the Nightmare Troubadour card pool)
#
#  Not in NT, so replaced: Chaos Sorcerer, Gravekeeper's Spy/Guard, Asura
#  Priest, Blade Knight, Dekoichi, Sacred Crane, Mobius, Pitch-Black Warwolf,
#  Gyaku-Gire Panda and the level-4/5 Metamorphosis fusions (Ryu Senshi,
#  Dark Balter, Reaper on the Nightmare, Fiend Skull Dragon...).
# ════════════════════════════════════════════════════════════════════════════

GOAT_EXTRA = """
3 Thousand-Eyes Restrict
1 Zombie Warrior
1 Alligator's Sword Dragon
1 Ojama King
1 Dark Paladin
"""

DECKS = {
    # ── GOAT CONTROL ─────────────────────────────────────────────────────────
    "Goat Control A": dict(name="Goat Control", note="2005 U.S. Nationals style (Suffridge)", main="""
2 Magician of Faith
1 Sangan
1 Sinister Serpent
1 Tribe-Infecting Virus
1 D.D. Warrior Lady
2 Tsukuyomi
1 Black Luster Soldier - Envoy of the Beginning
1 Jinzo
2 Airknight Parshath
1 Breaker the Magical Warrior
1 Morphing Jar
1 Spirit Reaper
1 Exiled Force
3 Scapegoat
2 Metamorphosis
2 Book of Moon
2 Nobleman of Crossout
1 Delinquent Duo
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
1 Snatch Steal
1 Pot of Greed
1 Graceful Charity
2 Sakuretsu Armor
1 Ring of Destruction
1 Torrential Tribute
1 Mirror Force
1 Call of the Haunted
1 Ceasefire
""", extra=GOAT_EXTRA),

    "Goat Control B": dict(name="Goat Control", note="SJC style, more aggressive (Long)", main="""
2 Airknight Parshath
2 Magician of Faith
1 Black Luster Soldier - Envoy of the Beginning
1 Breaker the Magical Warrior
1 D.D. Warrior Lady
1 D.D. Assailant
1 Injection Fairy Lily
1 Sangan
1 Sinister Serpent
1 Spirit Reaper
1 Tribe-Infecting Virus
2 Tsukuyomi
1 Jinzo
2 Scapegoat
2 Metamorphosis
2 Nobleman of Crossout
1 Book of Moon
1 Brain Control
1 Snatch Steal
1 Delinquent Duo
1 Different Dimension Capsule
1 Pot of Greed
1 Graceful Charity
1 Heavy Storm
1 Mystical Space Typhoon
1 Lightning Vortex
1 Premature Burial
3 Sakuretsu Armor
1 Call of the Haunted
1 Ring of Destruction
1 Torrential Tribute
1 Mirror Force
""", extra=GOAT_EXTRA),

    # ── CHAOS ────────────────────────────────────────────────────────────────
    "Chaos Return A": dict(name="Chaos Return", note="Return from the D.D. + BLS + DMoC, recruiters", main="""
1 Black Luster Soldier - Envoy of the Beginning
1 Dark Magician of Chaos
2 Thunder Dragon
1 Breaker the Magical Warrior
1 D.D. Warrior Lady
2 D.D. Assailant
1 Kycoo the Ghost Destroyer
1 Exiled Force
2 Magician of Faith
1 Sangan
1 Sinister Serpent
2 Mystic Tomato
2 Shining Angel
1 Jinzo
2 Book of Moon
1 Delinquent Duo
1 Graceful Charity
1 Heavy Storm
2 Nobleman of Crossout
1 Pot of Greed
1 Snatch Steal
1 Premature Burial
1 Mystical Space Typhoon
3 Return from the Different Dimension
1 Ceasefire
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
2 Solemn Judgment
""", extra=""),

    "Chaos Return B": dict(name="Chaos Return", note="Thunder Dragon engine, Night Assailant", main="""
1 Black Luster Soldier - Envoy of the Beginning
1 Dark Magician of Chaos
3 Thunder Dragon
1 D.D. Warrior Lady
2 D.D. Assailant
2 Kycoo the Ghost Destroyer
1 Exiled Force
1 Breaker the Magical Warrior
2 Magician of Faith
1 Sangan
1 Sinister Serpent
1 Night Assailant
1 Jinzo
3 Book of Moon
2 Nobleman of Crossout
1 Delinquent Duo
1 Graceful Charity
1 Pot of Greed
1 Heavy Storm
1 Snatch Steal
1 Premature Burial
1 Swords of Revealing Light
3 Return from the Different Dimension
2 Solemn Judgment
1 Ceasefire
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
""", extra=""),

    "Chaos Control": dict(name="Chaos Control", note="Thunder Dragon Chaos + Scapegoat/Metamorphosis", main="""
1 Black Luster Soldier - Envoy of the Beginning
1 Dark Magician of Chaos
3 Thunder Dragon
2 Magician of Faith
1 Sangan
1 Sinister Serpent
1 Tribe-Infecting Virus
1 D.D. Warrior Lady
2 Tsukuyomi
1 Airknight Parshath
1 Breaker the Magical Warrior
1 Jinzo
3 Scapegoat
2 Metamorphosis
2 Book of Moon
1 Nobleman of Crossout
1 Delinquent Duo
1 Graceful Charity
1 Pot of Greed
1 Heavy Storm
1 Mystical Space Typhoon
1 Snatch Steal
1 Premature Burial
1 Card Destruction
2 Sakuretsu Armor
1 Ring of Destruction
1 Torrential Tribute
1 Mirror Force
1 Call of the Haunted
1 Ceasefire
1 Solemn Judgment
""", extra=GOAT_EXTRA),

    "Chaos Recruiter": dict(name="Chaos Recruiter", note="Mystic Tomato / Shining Angel Chaos", main="""
1 Black Luster Soldier - Envoy of the Beginning
1 Dark Magician of Chaos
3 Mystic Tomato
3 Shining Angel
1 D.D. Warrior Lady
1 D.D. Assailant
2 Kycoo the Ghost Destroyer
1 Breaker the Magical Warrior
1 Exiled Force
1 Sangan
1 Sinister Serpent
1 Night Assailant
1 Jinzo
1 Airknight Parshath
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
2 Nobleman of Crossout
2 Book of Moon
1 Swords of Revealing Light
1 Creature Swap
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
1 Bottomless Trap Hole
""", extra=""),

    # ── REASONING GATE ───────────────────────────────────────────────────────
    "Reasoning Gate A": dict(name="Reasoning Gate", note="Reasoning / Monster Gate / Dimension Fusion combo", main="""
1 Dark Magician of Chaos
1 Black Luster Soldier - Envoy of the Beginning
1 Jinzo
1 Sacred Phoenix of Nephthys
2 Airknight Parshath
3 Thunder Dragon
1 Twin-Headed Behemoth
3 Reasoning
3 Monster Gate
2 Dimension Fusion
1 Pot of Greed
1 Graceful Charity
1 Card Destruction
2 Upstart Goblin
1 Heavy Storm
1 Giant Trunade
1 Premature Burial
2 Scapegoat
1 Snatch Steal
1 Delinquent Duo
1 Swords of Revealing Light
1 Mystical Space Typhoon
1 Brain Control
1 Nobleman of Crossout
1 Book of Moon
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra=""),

    "Reasoning Gate B": dict(name="Reasoning Gate", note="Thunder Gate: Scapegoat tokens as Gate tributes", main="""
1 Dark Magician of Chaos
1 Black Luster Soldier - Envoy of the Beginning
1 Jinzo
3 Thunder Dragon
1 Sacred Phoenix of Nephthys
2 Airknight Parshath
1 Twin-Headed Behemoth
1 Breaker the Magical Warrior
3 Reasoning
3 Monster Gate
1 Dimension Fusion
1 Card Destruction
2 Upstart Goblin
1 Pot of Greed
1 Graceful Charity
1 Heavy Storm
1 Giant Trunade
1 Premature Burial
3 Scapegoat
1 Snatch Steal
1 Delinquent Duo
1 Swords of Revealing Light
1 Mystical Space Typhoon
1 Book of Moon
1 Nobleman of Crossout
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra=""),

    "Machine Gate": dict(name="Machine Gate", note="Reasoning Gate with Cyber-Stein into Blue-Eyes Ultimate", main="""
1 Jinzo
1 Cyber-Stein
1 Barrel Dragon
1 Reflect Bounder
2 Cannon Soldier
1 Dark Magician of Chaos
1 Black Luster Soldier - Envoy of the Beginning
2 Thunder Dragon
3 Reasoning
3 Monster Gate
1 Dimension Fusion
1 Pot of Greed
1 Graceful Charity
1 Card Destruction
2 Upstart Goblin
1 Heavy Storm
1 Giant Trunade
1 Premature Burial
3 Scapegoat
1 Snatch Steal
1 Delinquent Duo
1 Swords of Revealing Light
1 Mystical Space Typhoon
1 Brain Control
1 Nobleman of Crossout
1 Book of Moon
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra="""
1 Blue-Eyes Ultimate Dragon
1 Master of Oz
1 Dark Paladin
"""),

    # ── OTHER 2005 META DECKS ────────────────────────────────────────────────
    "Warrior Toolbox": dict(name="Warrior Toolbox", note="Pre-June 2005 Warriors (Reinforcement toolbox)", main="""
1 D.D. Warrior Lady
2 D.D. Assailant
1 Exiled Force
2 Marauding Captain
2 Don Zaloog
2 Goblin Attack Force
2 Zombyra the Dark
2 Gearfried the Iron Knight
1 Breaker the Magical Warrior
1 Command Knight
1 Sangan
1 Sinister Serpent
2 Reinforcement of the Army
2 Nobleman of Crossout
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
1 Book of Moon
1 Axe of Despair
2 Sakuretsu Armor
1 Bottomless Trap Hole
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra=""),

    "Warrior Beat": dict(name="Warrior Beat", note="Anti-flip Warriors with Jinzo", main="""
1 D.D. Warrior Lady
2 D.D. Assailant
1 Exiled Force
2 Marauding Captain
1 Don Zaloog
2 Goblin Attack Force
3 Zombyra the Dark
1 Gearfried the Iron Knight
1 Breaker the Magical Warrior
2 Command Knight
1 Jinzo
1 Sangan
2 Reinforcement of the Army
2 Nobleman of Crossout
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
2 Book of Moon
1 Lightning Vortex
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Bottomless Trap Hole
""", extra=""),

    "Zombies A": dict(name="Zombie Goat", note="Pyramid Turtle / Vampire Lord / Book of Life", main="""
3 Pyramid Turtle
2 Vampire Lord
2 Spirit Reaper
2 Despair from the Dark
1 Patrician of Darkness
1 Double Coston
1 Sangan
1 Sinister Serpent
1 Tribe-Infecting Virus
1 D.D. Warrior Lady
1 Exiled Force
1 Breaker the Magical Warrior
1 Kycoo the Ghost Destroyer
2 Book of Life
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
2 Nobleman of Crossout
1 Swords of Revealing Light
1 Book of Moon
1 Creature Swap
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
1 Bottomless Trap Hole
""", extra=""),

    "Zombies B": dict(name="Zombie Goat", note="Spirit Reaper x3, Call of the Mummy", main="""
3 Pyramid Turtle
2 Vampire Lord
3 Spirit Reaper
1 Despair from the Dark
1 Double Coston
1 Sangan
1 Sinister Serpent
1 Tribe-Infecting Virus
2 Kycoo the Ghost Destroyer
1 D.D. Warrior Lady
1 Exiled Force
1 Night Assailant
2 Book of Life
1 Call of the Mummy
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
2 Nobleman of Crossout
2 Book of Moon
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
1 Solemn Judgment
""", extra=""),

    "Zoo": dict(name="Zoo Beatdown", note="Beast beatdown with Gaia Power", main="""
3 Berserk Gorilla
2 Enraged Battle Ox
2 Manticore of Darkness
2 King Tiger Wanghu
2 Giant Rat
1 Chiron the Mage
1 Breaker the Magical Warrior
1 Exiled Force
1 Injection Fairy Lily
1 Sangan
1 Sinister Serpent
1 Mystical Space Typhoon
2 Book of Moon
1 Heavy Storm
1 Beast Soul Swap
1 Delinquent Duo
1 Snatch Steal
1 Pot of Greed
2 Gaia Power
1 Premature Burial
2 Nobleman of Crossout
1 Terraforming
1 Graceful Charity
2 Solemn Judgment
2 Sakuretsu Armor
1 Mirror Force
1 Torrential Tribute
1 Ring of Destruction
1 Call of the Haunted
""", extra=""),

    "Flip Control": dict(name="Flip Control", note="Flip-flop stall (PACMAN style)", main="""
1 Morphing Jar
2 Morphing Jar #2
2 Needle Worm
2 Magician of Faith
3 Nimble Momonga
2 Penguin Soldier
2 Spirit Reaper
1 Cyber Jar
1 Sangan
1 Sinister Serpent
3 Book of Moon
2 Book of Taiyou
1 Swords of Revealing Light
1 Pot of Greed
1 Graceful Charity
1 Heavy Storm
1 Mystical Space Typhoon
1 Messenger of Peace
2 Level Limit - Area B
2 Gravity Bind
2 Wall of Revealing Light
2 Compulsory Evacuation Device
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
""", extra=""),

    "Burn": dict(name="Burn", note="Stall & burn (Stealth Bird, Cannon Soldier, Wave-Motion)", main="""
3 Stealth Bird
2 Cannon Soldier
1 Lava Golem
1 Des Koala
2 Nimble Momonga
2 Magician of Faith
1 Sangan
1 Sinister Serpent
1 Morphing Jar
2 Messenger of Peace
2 Level Limit - Area B
1 Swords of Revealing Light
2 Wave-Motion Cannon
1 Pot of Greed
1 Graceful Charity
1 Heavy Storm
1 Mystical Space Typhoon
1 Ojama Trio
2 Scapegoat
2 Gravity Bind
1 Ceasefire
1 Magic Cylinder
1 Ring of Destruction
2 Just Desserts
2 Secret Barrel
1 Poison of the Old Man
2 Wall of Revealing Light
""", extra=""),

    "Exodia Library": dict(name="Exodia Library", note="Royal Magical Library stall into Exodia", main="""
3 Royal Magical Library
1 Exodia the Forbidden One
1 Left Arm of the Forbidden One
1 Left Leg of the Forbidden One
1 Right Arm of the Forbidden One
1 Right Leg of the Forbidden One
1 Sangan
2 Magician of Faith
1 Spirit Reaper
2 Upstart Goblin
1 Pot of Greed
1 Graceful Charity
3 Scapegoat
1 Swords of Revealing Light
2 Messenger of Peace
2 Level Limit - Area B
1 Heavy Storm
1 Mystical Space Typhoon
2 Book of Moon
1 Delinquent Duo
1 Premature Burial
3 Jar of Greed
2 Gravity Bind
2 Waboku
1 Mirror Force
1 Magic Cylinder
1 Call of the Haunted
""", extra=""),
}

# ════════════════════════════════════════════════════════════════════════════
#  WHO PLAYS WHAT   (deck file → deck)
#  File numbers: first two digits = duelist, last digit = deck variant.
# ════════════════════════════════════════════════════════════════════════════

ASSIGN = {
    # 01 Yami Yugi
    "011.ydc": "Chaos Return A", "012.ydc": "Goat Control A", "013.ydc": "Reasoning Gate A",
    "014obe.ydc": "Chaos Control", "014osi.ydc": "Goat Control B", "015obe.ydc": "Chaos Return B",
    "015osi.ydc": "Reasoning Gate B", "016.ydc": "Goat Control A",
    # 02 Yugi Muto
    "021.ydc": "Goat Control B", "022.ydc": "Chaos Control", "023.ydc": "Reasoning Gate A",
    "024.ydc": "Warrior Toolbox", "026.ydc": "Chaos Return A",
    # 03 Seto Kaiba
    "031.ydc": "Chaos Return A", "032.ydc": "Machine Gate", "033.ydc": "Reasoning Gate B",
    "034.ydc": "Chaos Control", "034obe.ydc": "Goat Control B", "036.ydc": "Goat Control A",
    # 04 Joey Wheeler
    "041.ydc": "Warrior Toolbox", "042.ydc": "Warrior Beat", "043.ydc": "Chaos Recruiter",
    "044.ydc": "Warrior Toolbox", "045.ydc": "Goat Control B", "046.ydc": "Warrior Beat",
    # 05 Mai Valentine
    "051.ydc": "Chaos Recruiter", "052.ydc": "Flip Control", "056.ydc": "Goat Control B",
    # 06 Yami Bakura
    "061.ydc": "Chaos Return B", "062.ydc": "Zombies A", "063.ydc": "Goat Control A",
    # 07 Yami Marik
    "071.ydc": "Goat Control A",
    # 08 Marik Ishtar
    "081.ydc": "Reasoning Gate B", "081ra.ydc": "Chaos Control", "086.ydc": "Zombies B",
    # 09 Odion
    "091.ydc": "Flip Control", "092.ydc": "Goat Control B",
    # 10 Ishizu Ishtar
    "101.ydc": "Goat Control A", "106.ydc": "Flip Control",
    # 11 Pegasus
    "111.ydc": "Goat Control A", "112.ydc": "Reasoning Gate A", "116.ydc": "Chaos Return B",
    # 12 Bandit Keith
    "121.ydc": "Machine Gate", "122.ydc": "Burn",
    # 13 Strings
    "131.ydc": "Zombies B", "132.ydc": "Flip Control",
    # 14 Arkana
    "141.ydc": "Chaos Return B",
    # 15 Rare Hunter
    "151.ydc": "Exodia Library",
    # 17 Solomon
    "171.ydc": "Exodia Library", "172.ydc": "Goat Control B", "173.ydc": "Exodia Library",
    # 19 Tea Gardner
    "191.ydc": "Burn", "192.ydc": "Flip Control",
    # 20 Serenity
    "201.ydc": "Chaos Recruiter", "202.ydc": "Goat Control B",
    # 21 Rex Raptor
    "211.ydc": "Zoo", "212.ydc": "Zoo",
    # 22 Espa Roba
    "221.ydc": "Reasoning Gate B", "222.ydc": "Reasoning Gate A",
    # 23 Weevil
    "231.ydc": "Flip Control", "232.ydc": "Burn", "236.ydc": "Goat Control B",
    # 24 Mako
    "241.ydc": "Zoo", "242.ydc": "Warrior Beat", "246.ydc": "Chaos Recruiter",
    # 25 Mokuba
    "251.ydc": "Burn", "252.ydc": "Machine Gate",
    # 26 Gozaburo
    "261.ydc": "Exodia Library",
    # 27 Noah
    "271.ydc": "Goat Control A",
    # 28 Rebecca
    "281.ydc": "Burn", "282.ydc": "Chaos Control",
    # 29 Lumis / 30 Umbra
    "291.ydc": "Goat Control B", "301.ydc": "Zombies A",
    # 31 PaniK
    "311.ydc": "Zombies B", "312.ydc": "Chaos Return A",
    # 32 Para / 33 Dox
    "321.ydc": "Warrior Toolbox", "322.ydc": "Flip Control",
    "331.ydc": "Warrior Beat", "332.ydc": "Burn",
    # 34 Bonz
    "341.ydc": "Zombies A", "342.ydc": "Zombies B",
    # 35-39 Big Five
    "351.ydc": "Goat Control B", "361.ydc": "Flip Control", "371.ydc": "Reasoning Gate A",
    "381.ydc": "Machine Gate", "391.ydc": "Chaos Control",
    # 40 Bakura
    "401.ydc": "Zombies A", "402.ydc": "Chaos Return B",
    # special / tournament decks
    "bc1.ydc": "Warrior Toolbox", "bc2.ydc": "Chaos Return A", "ec1.ydc": "Goat Control A",
    "ec2.ydc": "Zombies A", "yasei.ydc": "Zoo",
}

# Order of the 88 story decks in the game (deck index → GAME_Text entry 0x66+index)
DECK_ORDER = [
    "011", "012", "013", "014obe", "014osi", "015obe", "015osi", "016", "021", "022", "023", "024",
    "026", "031", "032", "033", "034", "034obe", "036", "041", "042", "043", "044", "045", "046",
    "051", "052", "056", "061", "062", "063", "071", "081", "081ra", "086", "091", "092", "101",
    "106", "111", "112", "116", "121", "122", "131", "132", "141", "151", "171", "172", "173",
    "191", "192", "201", "202", "211", "212", "221", "222", "231", "232", "236", "241", "242",
    "246", "251", "252", "261", "271", "281", "282", "291", "301", "311", "312", "321", "322",
    "331", "332", "341", "342", "351", "361", "371", "381", "391", "401", "402",
]
DECK_NAME_TEXT_BASE = 0x66

DUELISTS = {
    "01": "Yami Yugi", "02": "Yugi Muto", "03": "Seto Kaiba", "04": "Joey Wheeler",
    "05": "Mai Valentine", "06": "Yami Bakura", "07": "Yami Marik", "08": "Marik Ishtar",
    "09": "Odion", "10": "Ishizu Ishtar", "11": "Pegasus", "12": "Bandit Keith", "13": "Strings",
    "14": "Arkana", "15": "Rare Hunter", "17": "Solomon", "19": "Tea Gardner", "20": "Serenity",
    "21": "Rex Raptor", "22": "Espa Roba", "23": "Weevil", "24": "Mako", "25": "Mokuba",
    "26": "Gozaburo", "27": "Noah", "28": "Rebecca", "29": "Lumis", "30": "Umbra", "31": "PaniK",
    "32": "Para", "33": "Dox", "34": "Bonz", "35": "Gansley (Big 1)", "36": "Crump (Big 2)",
    "37": "Johnson (Big 3)", "38": "Nesbitt (Big 4)", "39": "Leichter (Big 5)", "40": "Bakura",
}


def duelist_of(fname):
    stem = fname.split('.')[0]
    return DUELISTS.get(stem[:2], {"bc": "Special", "ec": "Special", "ya": "Special"}.get(stem[:2], "?"))


# ════════════════════════════════════════════════════════════════════════════
#  Deck building / validation
# ════════════════════════════════════════════════════════════════════════════

def parse_list(text):
    out = []
    for line in (text or "").strip().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^(\d+)\s*x?\s+(.+)$', line)
        if not m:
            raise ValueError("Bad deck line: %r (expected '<count> <card name>')" % line)
        out.append((int(m.group(1)), m.group(2).strip()))
    return out


class DeckError(Exception):
    pass


def build_deck(key, spec, db):
    """Return (main_ids, extra_ids) after full validation."""
    errors = []
    main, extra = [], []
    totals = {}
    for section, target in (("main", main), ("extra", extra)):
        entries = spec.get(section) or ""
        if isinstance(entries, str):
            entries = parse_list(entries)
        for count, name in entries:
            cid = db.lookup(name)
            if cid is None:
                errors.append("'%s' is not in Nightmare Troubadour's card pool" % name)
                continue
            real = db.name(cid)
            if section == "main" and db.is_extra(cid):
                errors.append("'%s' is a Fusion monster (belongs in the extra deck)" % real)
            if section == "extra" and not db.is_extra(cid):
                errors.append("'%s' is not a Fusion monster" % real)
            totals[real] = totals.get(real, 0) + count
            target.extend([cid] * count)
    for real, n in totals.items():
        lim = goat_limit(real)
        if n > lim:
            what = {0: "Forbidden / not Goat-legal", 1: "Limited", 2: "Semi-Limited"}.get(lim, "max 3")
            errors.append("%d x '%s' (%s in Goat format)" % (n, real, what))
    if not 40 <= len(main) <= 60:
        errors.append("main deck has %d cards (must be 40-60)" % len(main))
    if len(extra) > 15:
        errors.append("extra deck has %d cards (max 15)" % len(extra))
    if errors:
        raise DeckError("Deck '%s':\n  - " % key + "\n  - ".join(errors))
    return main, extra


def format_deck(key, spec, db):
    main, extra = build_deck(key, spec, db)
    groups = {"Monsters": [], "Spells": [], "Traps": []}
    seen = []
    for cid in main:
        if cid not in seen:
            seen.append(cid)
    for cid in seen:
        k = db.by_id[cid]['kind']
        grp = "Spells" if k == 0xD else "Traps" if k == 0xE else "Monsters"
        groups[grp].append("%dx %s" % (main.count(cid), db.name(cid)))
    lines = ["%s  [%s]  -  %s" % (key, spec.get('name', key), spec.get('note', '')),
             "  Main deck: %d cards" % len(main)]
    for g, items in groups.items():
        n = sum(int(i.split('x')[0]) for i in items)
        lines.append("  %s (%d): %s" % (g, n, ", ".join(items)))
    if extra:
        ex = []
        for cid in dict.fromkeys(extra):
            ex.append("%dx %s" % (extra.count(cid), db.name(cid)))
        lines.append("  Extra (%d): %s" % (len(extra), ", ".join(ex)))
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
#  In-game banlist check (read-only)
# ════════════════════════════════════════════════════════════════════════════

def read_game_banlist(rom, db):
    """Find the game's Forbidden/Limited table in arm9 (pairs of u16 id, u16 status)."""
    arm9 = rom.arm9_decompressed()
    obelisk = db.lookup("Obelisk the Tormentor")
    if obelisk is None:
        return None
    needle = struct.pack('<HH', obelisk, 0)
    pos = arm9.find(needle)
    while pos >= 0:
        table, p = {}, pos
        while p + 4 <= len(arm9):
            cid, st = struct.unpack_from('<HH', arm9, p)
            if cid not in db.by_id or st > 2:
                break
            table[db.name(cid)] = st
            p += 4
        if len(table) > 30:
            return table
        pos = arm9.find(needle, pos + 2)
    return None


def compare_banlist(table, db):
    goat = {}
    for lst, st in ((GOAT_FORBIDDEN, 0), (GOAT_LIMITED, 1), (GOAT_SEMI, 2)):
        for n in lst:
            cid = db.lookup(n)
            if cid is not None:
                goat[db.name(cid)] = st
    diffs = [(n, st, table.get(n, 3)) for n, st in goat.items() if table.get(n, 3) != st]
    extra = [(n, st) for n, st in table.items() if n not in goat]
    return diffs, extra


# ════════════════════════════════════════════════════════════════════════════
#  Text (deck names)
# ════════════════════════════════════════════════════════════════════════════

TEXT_LANGS = "EFGIS"


def patch_text(idx_data, txt_data, changes):
    """changes: {entry_index: new_string}. In place when it fits, else appended."""
    n = len(idx_data) // 4
    offs = list(struct.unpack('<%dI' % n, idx_data))
    txt = bytearray(txt_data)
    starts = sorted(set(offs))
    for i, s in changes.items():
        raw = s.encode('latin-1', 'replace') + b'\0'
        o = offs[i]
        nxt = next((x for x in starts if x > o), len(txt))
        shared = offs.count(o) > 1
        if not shared and len(raw) <= nxt - o:
            txt[o:o + len(raw)] = raw
            txt[o + len(raw):nxt] = b'\0' * (nxt - o - len(raw))
        else:
            o2 = align(len(txt), 4)
            txt.extend(b'\0' * (o2 - len(txt)))
            txt.extend(raw)
            offs[i] = o2
    txt.extend(b'\0' * (align(len(txt), 4) - len(txt)))
    return struct.pack('<%dI' % n, *offs), bytes(txt)


# ════════════════════════════════════════════════════════════════════════════
#  Main patch routine
# ════════════════════════════════════════════════════════════════════════════

def load_config(path):
    decks, assign = dict(DECKS), dict(ASSIGN)
    if path:
        with open(path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        for k, v in cfg.get('decks', {}).items():
            decks[k] = v
        for k, v in cfg.get('assign', {}).items():
            assign[k if k.endswith('.ydc') else k + '.ydc'] = v
    return decks, assign


def patch_rom(in_path, out_path, config=None, rename=True, log=print):
    with open(in_path, 'rb') as f:
        rom = NDSRom(f.read())
    log("ROM: %s [%s], %d files, %.1f MB" % (rom.game_title, rom.game_code, len(rom.paths), len(rom.data) / 1048576))
    if not rom.exists('bin/CARD_Prop.bin') or not rom.exists('deck/011.ydc'):
        raise ValueError("This ROM does not look like Yu-Gi-Oh! Nightmare Troubadour.")
    if rom.game_code[:3] != 'AYG' and not rom.game_title.startswith('YU-GI-OH'):
        log("WARNING: unexpected game code %s - continuing anyway." % rom.game_code)

    db = CardDB(rom)
    log("Card pool read from ROM: %d cards" % len(db.by_id))

    decks, assign = load_config(config)

    # 1) validate everything before touching the ROM
    built, problems = {}, []
    for fname, key in assign.items():
        if key not in decks:
            problems.append("%s is assigned to unknown deck '%s'" % (fname, key))
            continue
        if key not in built:
            try:
                built[key] = build_deck(key, decks[key], db)
            except DeckError as ex:
                built[key] = None
                problems.append(str(ex))
    if problems:
        raise DeckError("Nothing was written. Fix these problems first:\n" + "\n".join(problems))
    log("All %d decklists are legal under the April 2005 Goat list." % len(built))

    # 2) banlist check
    table = read_game_banlist(rom, db)
    if table:
        diffs, extra = compare_banlist(table, db)
        if not diffs:
            log("In-game Forbidden/Limited list already matches Goat format "
                "(extra entries: %s)." % ", ".join(n for n, s in extra))
        else:
            log("NOTE: in-game list differs from Goat on: " +
                ", ".join("%s (goat %d / game %d)" % d for d in diffs))
    else:
        log("NOTE: could not locate the in-game banlist (not needed for the patch).")

    # 3) decks
    replaced = 0
    for fname, key in sorted(assign.items()):
        path = 'deck/' + fname
        if not rom.exists(path):
            log("  skip %s (not in ROM)" % fname)
            continue
        hdr = rom.read(path)[:8] or DEFAULT_YDC_HEADER
        main, extra = built[key]
        rom.replace(path, write_ydc(hdr, main, extra, []))
        replaced += 1
    log("Replaced %d opponent decks." % replaced)

    # 4) deck names in every language
    if rename:
        changes = {}
        for i, stem in enumerate(DECK_ORDER):
            key = assign.get(stem + '.ydc')
            if key:
                changes[DECK_NAME_TEXT_BASE + i] = decks[key].get('name', key)[:20]
        done = []
        for L in TEXT_LANGS:
            ip, tp = 'bin/GAME_Indx_%s.bin' % L, 'bin/GAME_Text_%s.bin' % L
            if not (rom.exists(ip) and rom.exists(tp)):
                continue
            idx, txt = rom.read(ip), rom.read(tp)
            if len(idx) // 4 < DECK_NAME_TEXT_BASE + len(DECK_ORDER) + 1:
                log("  skip deck names (%s): unexpected text table" % L)
                continue
            if L == 'E':
                o = struct.unpack_from('<I', idx, 4 * (DECK_NAME_TEXT_BASE - 1))[0]
                if not txt[o:].startswith(b'Auto Generated'):
                    log("  skip deck names: text table layout not recognised")
                    break
            idx2, txt2 = patch_text(idx, txt, changes)
            rom.replace(ip, idx2)
            rom.replace(tp, txt2)
            done.append(L)
        if done:
            log("Deck names updated in languages: %s" % ", ".join(done))

    out = rom.finalize()
    with open(out_path, 'wb') as f:
        f.write(out)
    log("Wrote %s (%.1f MB)." % (out_path, len(out) / 1048576))
    return out


def export_report(in_path, out_txt, config=None):
    with open(in_path, 'rb') as f:
        rom = NDSRom(f.read())
    db = CardDB(rom)
    decks, assign = load_config(config)
    lines = ["NT GOAT PATCHER %s - decklists (April 2005 Goat format)" % VERSION, ""]
    lines.append("WHO PLAYS WHAT")
    for fname in sorted(assign):
        lines.append("  %-11s %-18s %s" % (fname, duelist_of(fname), assign[fname]))
    lines.append("")
    for key in dict.fromkeys(assign.values()):
        lines.append(format_deck(key, decks[key], db))
        lines.append("")
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    return "\n".join(lines)


def export_ydc(in_path, out_dir, config=None):
    with open(in_path, 'rb') as f:
        rom = NDSRom(f.read())
    db = CardDB(rom)
    decks, assign = load_config(config)
    os.makedirs(out_dir, exist_ok=True)
    for fname, key in assign.items():
        path = 'deck/' + fname
        hdr = rom.read(path)[:8] if rom.exists(path) else DEFAULT_YDC_HEADER
        main, extra = build_deck(key, decks[key], db)
        with open(os.path.join(out_dir, fname), 'wb') as f:
            f.write(write_ydc(hdr, main, extra, []))
    return len(assign)


def dump_config(out_json):
    cfg = {"decks": {k: {"name": v["name"], "note": v.get("note", ""),
                         "main": [[c, n] for c, n in parse_list(v["main"])],
                         "extra": [[c, n] for c, n in parse_list(v.get("extra", ""))]}
                     for k, v in DECKS.items()},
           "assign": ASSIGN}
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=1, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════════════
#  GUI
# ════════════════════════════════════════════════════════════════════════════

def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    root = tk.Tk()
    root.title("NT Goat Patcher %s - Yu-Gi-Oh! Nightmare Troubadour" % VERSION)
    root.geometry("760x560")

    v_in, v_out, v_cfg = tk.StringVar(), tk.StringVar(), tk.StringVar()
    v_rename = tk.BooleanVar(value=True)

    frm = tk.Frame(root, padx=10, pady=8)
    frm.pack(fill='x')

    def row(r, label, var, cmd):
        tk.Label(frm, text=label, anchor='w', width=16).grid(row=r, column=0, sticky='w')
        tk.Entry(frm, textvariable=var, width=70).grid(row=r, column=1, sticky='we', padx=4)
        tk.Button(frm, text="Browse...", command=cmd).grid(row=r, column=2)

    def pick_in():
        p = filedialog.askopenfilename(title="Nightmare Troubadour ROM",
                                       filetypes=[("Nintendo DS ROM", "*.nds"), ("All files", "*.*")])
        if p:
            v_in.set(p)
            if not v_out.get():
                b, e = os.path.splitext(p)
                v_out.set(b + " (GOAT)" + e)

    def pick_out():
        p = filedialog.asksaveasfilename(title="Save patched ROM as", defaultextension=".nds",
                                         filetypes=[("Nintendo DS ROM", "*.nds")])
        if p:
            v_out.set(p)

    def pick_cfg():
        p = filedialog.askopenfilename(title="Custom deck config (optional)",
                                       filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if p:
            v_cfg.set(p)

    row(0, "Original ROM (.nds)", v_in, pick_in)
    row(1, "Patched ROM (.nds)", v_out, pick_out)
    row(2, "Custom config", v_cfg, pick_cfg)
    tk.Checkbutton(frm, text="Rename opponent decks (Goat Control, Chaos Return, Reasoning Gate...)",
                   variable=v_rename).grid(row=3, column=1, sticky='w')

    logbox = scrolledtext.ScrolledText(root, height=22, font=("Consolas", 9))
    logbox.pack(fill='both', expand=True, padx=10, pady=4)

    def log(msg):
        logbox.insert('end', msg + "\n")
        logbox.see('end')
        root.update_idletasks()

    def do_patch():
        if not v_in.get() or not v_out.get():
            messagebox.showwarning("NT Goat Patcher", "Choose the original ROM and the output file.")
            return
        if os.path.abspath(v_in.get()) == os.path.abspath(v_out.get()):
            messagebox.showwarning("NT Goat Patcher", "Output must be a different file than the original.")
            return
        try:
            patch_rom(v_in.get(), v_out.get(), v_cfg.get() or None, v_rename.get(), log)
            messagebox.showinfo("NT Goat Patcher", "Done! Patched ROM written to:\n" + v_out.get())
        except Exception as e:  # noqa
            log("ERROR: %s" % e)
            messagebox.showerror("NT Goat Patcher", str(e))

    def do_report():
        if not v_in.get():
            messagebox.showwarning("NT Goat Patcher", "Choose the original ROM first.")
            return
        p = filedialog.asksaveasfilename(title="Save decklists", defaultextension=".txt",
                                         initialfile="NT_Goat_decklists.txt")
        if p:
            try:
                export_report(v_in.get(), p, v_cfg.get() or None)
                log("Decklists written to %s" % p)
            except Exception as e:  # noqa
                log("ERROR: %s" % e)

    def do_dump():
        p = filedialog.asksaveasfilename(title="Save editable config", defaultextension=".json",
                                         initialfile="nt_goat_config.json")
        if p:
            dump_config(p)
            log("Editable config written to %s (edit decks/assignments, then load it above)." % p)

    bar = tk.Frame(root, pady=6)
    bar.pack()
    tk.Button(bar, text="PATCH ROM", width=18, command=do_patch, bg="#2d6a2d", fg="white").pack(side='left', padx=6)
    tk.Button(bar, text="Export decklists (.txt)", width=22, command=do_report).pack(side='left', padx=6)
    tk.Button(bar, text="Export editable config", width=22, command=do_dump).pack(side='left', padx=6)

    log("NT Goat Patcher %s" % VERSION)
    log("1) Pick your 'Yu-Gi-Oh! - Nightmare Troubadour (Europe)' .nds  2) PATCH ROM")
    log("Your original ROM is never modified.\n")
    root.mainloop()


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        try:
            return run_gui()
        except ImportError:
            print("Tkinter is not available; use the command line (see -h).")
            return 1
    ap = argparse.ArgumentParser(description="Goat Format patcher for Yu-Gi-Oh! Nightmare Troubadour")
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('patch', help="write a patched ROM")
    p.add_argument('rom'); p.add_argument('out')
    p.add_argument('--config', help="custom JSON config (see dump-config)")
    p.add_argument('--no-rename', action='store_true', help="keep the original deck names")
    r = sub.add_parser('report', help="write all decklists + who-plays-what to a text file")
    r.add_argument('rom'); r.add_argument('out'); r.add_argument('--config')
    e = sub.add_parser('export-ydc', help="write the new .ydc files to a folder (for manual ROM tools)")
    e.add_argument('rom'); e.add_argument('outdir'); e.add_argument('--config')
    d = sub.add_parser('dump-config', help="write the built-in decks/assignments as editable JSON")
    d.add_argument('out')
    sub.add_parser('gui', help="open the graphical interface")
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'patch':
            if os.path.abspath(a.rom) == os.path.abspath(a.out):
                raise ValueError("Output must be a different file than the input ROM.")
            patch_rom(a.rom, a.out, a.config, not a.no_rename)
        elif a.cmd == 'report':
            export_report(a.rom, a.out, a.config); print("Wrote", a.out)
        elif a.cmd == 'export-ydc':
            print("Wrote %d deck files to %s" % (export_ydc(a.rom, a.outdir, a.config), a.outdir))
        elif a.cmd == 'dump-config':
            dump_config(a.out); print("Wrote", a.out)
        elif a.cmd == 'gui':
            run_gui()
    except (DeckError, ValueError, OSError) as ex:
        print("ERROR:", ex)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
