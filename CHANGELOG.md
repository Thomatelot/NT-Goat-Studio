# Changelog

## v2.1.0 — first public release

### Added
- **Web interface (NT Goat Studio)**: story decks map, deck drawer with card text, difficulty settings, deck builder with a live Goat banlist check, hidden content page, build and download.
- **Decks that fit each duelist**: a profile for each of the 37 duelists, built from the signature cards Konami gave them.
- **Story progression**: Rookie → Duelist → Expert → Goat Max tiers, based on the game's own story stages (0–10). Presets Gentle, Standard, Hard and Goat everywhere. Boss duelists can be configured.
- **Post-game decks for every duelist** (option): the game's stage table is edited inside the compressed game code, re-encoded at the same size and verified.
- New Goat archetypes: Harpie Control, Water Goat, Insect Lock, Blue-Eyes Gate, Lava Control, Gate Guardian Gate, plus themed variants (Fairy Goat, Angel Chaos, Dino Zoo, Koala Zoo).
- **Developer ROM builds** for the hidden tools: Card Gallery, Bust-up & Background viewer, Script Test, Duel Arena (any deck), Duel Only, Card Get.
- Unused developer decks (Ojama Lock, Final Countdown, Stone wall, E3 2005 demo decks) selectable for any duelist.
- Export / import of settings as JSON; full plan as text.
- Command line: `build`, `report`, `--preset`, `--no-postgame`, `--dev`.

### Security
- The server listens on 127.0.0.1 only, checks the Host header and requires a per-session token on every request. Uploads are limited to 256 MB.

### Fixed
- Saving to a folder path (instead of a full file name) caused "Permission denied". Folders are now accepted and created if needed.
- Short themed decks could end up with fewer than 40 cards on the Gentle preset.

## v1.0 — private version
- Every CPU opponent (93 decks) gets a Goat Format deck: Goat Control, Chaos Return / Control / Recruiter, Reasoning Gate, Machine Gate, Warriors, Zombies, Zoo, Flip Control, Burn, Exodia Library.
- Decks validated against the April 2005 TCG Forbidden & Limited list and the game's card pool.
- Deck names renamed in all five languages.
- Tkinter window and command line (`nt_goat_patcher.py`).
