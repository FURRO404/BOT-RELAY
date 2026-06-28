# BOT-RELAY Scoreboard Assets

This directory is the default asset root for the scoreboard renderer, but the
game-data files (char.vromfs.bin, lang.vromfs.bin, map images, vehicle icons,
fonts) are **not included** in this repository.

## What you need

The renderer expects the following layout under `$BOT_RELAY_SCOREBOARD_ASSETS_DIR`
(or this directory):

- `MAPS/*.jpg` — map background images, keyed by map internal name
- `ICONS/VEHICLES/*.png` — per-vehicle icons, keyed by vehicle internal name
- `FONTS/arial_unicode_ms.otf` — Unicode font used by the renderer
- `FONTS/symbols_skyquake.ttf` — symbol font
- `char.vromfs.bin` — game character/vehicle name data (from War Thunder)
- `lang.vromfs.bin` — game language data (from War Thunder)
- `DAGOR_FILES/` — Dagor asset files (included)

## How to get them

1. **char.vromfs.bin / lang.vromfs.bin**: Copy from your local War Thunder
   installation, or use `python update_game_files.py` from the repo root.

2. **MAPS/ and ICONS/VEHICLES/**: These are extracted from the game files.
   Use the included `update_game_files.py` script to populate them.

3. **FONTS/**: `arial_unicode_ms.otf` is a Windows system font; you can
   supply your own Unicode font. `symbols_skyquake.ttf` is bundled with the
   game files.

4. **DAGOR_FILES/**: Already included — these are vendored utilities.

## Custom path

If you keep the assets elsewhere, point the renderer at them:

```bash
export BOT_RELAY_SCOREBOARD_ASSETS_DIR=/path/to/your/assets
```
