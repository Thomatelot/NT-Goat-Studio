# Technical notes

How Yu-Gi-Oh! Nightmare Troubadour (Europe, game code `AYGP`) stores the data this tool changes. Everything here was found by reading the ROM and its code, and checked by booting the game in an emulator. Addresses are RAM addresses after the main program (arm9) has decompressed itself. The offset inside the decompressed arm9 is the address minus `0x02000000`.

## ROM layout
- Standard Nintendo DS ROM, 64 MB. The arm9 is BLZ-compressed ("backwards LZ"), and so are all 23 overlays.
- The file system (NitroFS) has 5,193 files. Several FAT entries point to the same data, so a file can't be rewritten in place blindly. The tool checks for shared data before writing.
- The arm9 sits at ROM offset `0x4000` and the overlay table starts 20 bytes after it, so **the compressed arm9 can't grow**.

## Card database (`bin/`)
| File | Content |
|---|---|
| `CARD_Prop.bin` | 8 bytes per card. Word 0: ATK/10 in bits 13–21, DEF/10 in bits 22–30. Word 1: kind in bits 0–3 (0 Normal, 1 Effect, 2/3 Fusion, 4/5 Ritual, 0xD Spell, 0xE Trap), attribute in bits 4–7, level in bits 8–11, spell/trap subtype in bits 12–15 |
| `CARD_IntID.bin` | u16 table: Konami card ID − 4000 → internal card index |
| `CARD_Indx_<lang>.bin` | Per card: name offset, description offset |
| `CARD_Name_<lang>.bin`, `CARD_Desc_<lang>.bin` | Null-terminated strings |

The game has 1,075 cards.

## Deck files (`deck/*.ydc`)
```
8 bytes   header (ignored by the loader)
u16 n     main deck count, then n × u16 card IDs (max 80)
u16 n     extra (fusion) deck count, then n × u16 (max 15)
u16 n     side deck count, then n × u16 (max 15)
```
The loader (`0x02012B20`) does no bounds checking, so the tool enforces the limits itself.

- **File names:** `DDV[suffix].ydc`, where `DD` is the duelist (01–40) and `V` the variant. The suffix `obe`, `osi` or `ra` means the deck is only used while that duelist holds Obelisk, Slifer or Ra (save flags, function `0x02007704`, only for duelists 01, 03 and 08).
- **Deck table:** 88 pointers at `0x02068D4C`, one per story deck. A second list at `0x02068C44` is used by the tournaments (`bc` = Beginner's Cup, `ec` = Expert Cup, `yasei`).
- **Deck names:** `bin/GAME_Text_<lang>.bin` entry `0x66 + deck index`, in all five languages.
- **Unused decks:** `ojama`, `countdown`, `ganseki`, `default_test`, `default_plus`, `e3_013`, `e3_033`, `e3_043` and `e3_player` aren't referenced by any code.

## Story progression
- The save holds the **story stage** at `[0x02096FA8 + 0x4B8]`, from 0 to 10. 10 is the post-game.
- **Duelist table** at `0x02060D1C`: 16 bytes per duelist (01–40). Bytes 4–14 are the duelist's level at stages 0–10; 0 means the duelist isn't available at that stage. The level only feeds the EXP / DP rewards (`level × 50`, table at `0x020609C0`).
- **Deck selection** (`0x02012C0C`): at stage *s*, the variant is the number of distinct non-zero levels in stages 0..*s* (at least 1). At stage 10, variant 6 is also a candidate. When several files match, the game picks one at random.
- **AI:** no per-duelist or global AI difficulty value was found. The `.ydc` header is ignored, and the duelist table only holds levels. Every opponent uses the same CPU logic.

### The "post-game decks for every duelist" option
- **Duelists with a variant 6 file:** stage 10 is given a new, distinct level. That makes the current variant number one that has no file, so only the variant 6 deck remains.
- **Duelists whose last deck covers mid-game and post-game:** the stages before 10 are set to the previous variant's level, so the last deck is only used at stage 10.

## Same-size patching of the compressed arm9 (`blz_patch.py`)
- The BLZ stream is parsed into tokens (literals and matches), each with the output position it produces.
- Around each changed byte, the tokens from `change − 4,120` to `change` are re-encoded with an optimal parse. 4,120 bytes covers the maximum match distance plus length, so no untouched token can copy from changed data.
- All other tokens are kept as they are and re-packed into flag groups.
- The stream is padded back to its original length with the header's padding field. The ROM layout, the module parameters and the secure area stay untouched.
- **Verification:** the result is decompressed and compared with the intended bytes, and the in-place decompression is simulated to check it never overwrites unread input.

## Banlist
The Forbidden / Limited list is a table of `u16 card ID, u16 status` pairs (0 forbidden, 1 limited, 2 semi-limited) at `0x020631D8`. It matches the April 2005 TCG list for every Goat-legal card. The only extras are the three God cards and Sixth Sense, Marshmallon, Reversal of Graves and Crush Card, none of which were in the TCG at the time.

## Scenes and developer tools
- **Scene table** at `0x02067F38`: 16 bytes per scene: function, overlay, parameter, Japanese name.
- **Boot flow** at `0x0206812C`: the entry at `0x02068134` is the title screen (scene `0x10`). Developer ROM builds change only this value.

| Scene | Name | Notes |
|---|---|---|
| `0x00` | Script Test | |
| `0x01` | Duelist Info | |
| `0x17` | 3D Script | |
| `0x18` | Card Gallery | |
| `0x19` | Bust-up & Background | |
| `0x1C` | Card Get | |
| `0x1D` | Duel (B select) | Opponent slot set by `mov r0,#2` at `0x02010EC8` |
| `0x1E` | Duel Only | |

**Debug duel:** only slot 2 (deck index 1) works. Other slots crash in the text renderer around `0x020019E0`. The Duel Arena build writes the chosen deck into `deck/012.ydc` instead of changing the slot.

## Tools used during research
- A capstone-based ARM/Thumb disassembler and cross-reference script.
- A headless melonDS core driven by a small C++ harness, used to boot ROMs, press buttons, read RAM and take screenshots.

These aren't part of the repository.
