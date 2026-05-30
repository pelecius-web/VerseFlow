# VerseFlow

A dual-monitor Bible verse display system for churches. Built with Python and PyQt6.

## Features

- **Dual-Monitor Display** — Operator control panel on one screen, congregation view on the other
- **Verse Lookup & Navigation** — Chapter navigator with highlight + arrow-key navigation
- **Keyword Search** — Flat result list across multiple Bible translations
- **Translation Selector** — Switch between translations (AMP, ESV, MSG, NKJV, NLT, KJB)
- **NDI Output** — Send congregation display to streaming / broadcast systems
- **Theme Engine** — 10+ built-in themes (light, dark, amber, purple, green, etc.)
- **Theme Designer** — Custom UI theme builder
- **Playlist Management** — Organize and queue verses for service
- **Hotkey System** — Keyboard shortcuts for common actions
- **Settings Panel** — Persistent configuration
- **Contact Sheet / Thumbnail Generator** — Visual previews

## Requirements

- Python 3.12+
- PyQt6
- platformdirs
- NDI SDK (included — `src/ndi/Processing.NDI.Lib.x64.dll`)

## Quick Start

```bash
# Install dependencies
pip install PyQt6 platformdirs

# Run VerseFlow
python src/main.py
```

> **Note:** The Bible database (`3. Database/verseflow.db`) is required. It's built from XML translations in `4. Translations/` using `src/db/build_db.py`.

## Project Structure

```
VerseFlow/
├── src/                    # Source code (modular)
│   ├── main.py            # Entry point
│   ├── core/              # Core logic (channels, navigation, hotkeys, models)
│   ├── db/                # Database layer
│   ├── display/           # Display system (dual-monitor, widgets, NDI)
│   ├── ndi/               # NDI output bridge
│   ├── ui/                # UI panels (home, playlist, queue, settings, theme designer)
│   └── utils/             # Utilities (constants, icons, theme engine, settings)
├── 3. Database/           # Bible database (verseflow.db)
├── 4. Translations/       # Bible XML source files (Zefania format)
├── docs/                  # Implementation plans
├── scripts/              # Utility scripts
├── tests/                # Test suite
└── samples/              # Sample playlists
```

## Credits

Created by Pelecius.
