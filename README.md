# WinLossOverlay

Real-time win/loss and rank overlays for OBS with a local launcher, GUI controls, hotkeys, and support for Overwatch and Valorant.

## Features

- Two separate OBS browser overlays:
  - **Stats Overlay** (wins, losses, draws, ratio)
  - **Rank Overlay** (rank icon + rank/category display)
- Per-overlay opacity controls (stats and rank independently)
- Session stats and persistent total stats
- Multi-category rank support for Overwatch (Open Queue, Support, Tank, Damage, Stadium)
- Rank cycling in overlay display
- Local GUI for controls, hotkeys, resets, and OBS URL copy buttons
- Local HTTP server for OBS browser sources

## Requirements

- Python 3.10+ (recommended)
- OBS Studio
- Optional hotkey support package:

```bash
pip install keyboard
```

If `keyboard` is not installed, overlays and GUI still work, but global hotkey listeners are disabled.

## Release Build (No Python Required)

Releases are distributed as a `.rar` archive that contains:

- `WinLossOverlay.exe`
- `_internal/` (required runtime files)

### Important

- Keep `WinLossOverlay.exe` and the `_internal` folder together.
- Do **not** move the `.exe` out of that folder structure.
- Extract the full `.rar` before running.

### Run Release Build

1. Download and extract the release `.rar`.
2. Open the extracted folder.
3. Run `WinLossOverlay.exe`.
4. Add the OBS Browser Sources (URLs below).

## Quick Start

1. Clone this repository.
2. Open the project folder.
3. Run the launcher:

```bash
python launcher.py
```

The launcher will:

- Initialize overlay state
- Start a local web server on `127.0.0.1:17357`
- Open the control GUI
- Print OBS browser source URLs in the terminal

## OBS Setup

Add **two Browser Source** entries in OBS:

- Stats source:
  - `http://127.0.0.1:17357/overlay/stats/index.html`
- Rank source:
  - `http://127.0.0.1:17357/overlay/rank/index.html`

Tip: You can also copy these URLs directly from the GUI (`Settings` tab).

## How It Works

- `main.py` manages app state, stats, rank logic, and writes `overlay_state.json`.
- `launcher.py` runs a local HTTP server and starts the GUI.
- `gui.py` provides controls for game selection, recording results, rank updates, opacity, and hotkeys.
- Overlay pages (`overlay/stats`, `overlay/rank`) poll state and render in OBS.

## Data Files

Runtime data is stored in `data/` and is intentionally gitignored:

- `data/settings.json`
- `data/saved_data.json`
- `data/overlay_state.json`

These files are generated automatically at runtime.

## Default Supported Games

- Overwatch
- Valorant

## Controls Overview

- Record Win / Loss / Draw
- Reset current session stats
- Reset total stats for active game
- Set, increase, decrease rank
- Edit and save hotkeys
- Set independent opacity for stats and rank overlays

## Project Structure

```text
main.py
launcher.py
gui.py
overlay/
  stats/
    index.html
    script.js
  rank/
    index.html
    script.js
  assets/
    Logos/
    Ranks/
  fonts/
data/               (generated at runtime)
```

## Notes

- Keep `launcher.py` running while OBS uses the browser sources.
- For release builds, keep `WinLossOverlay.exe` and `_internal/` in the same folder.
- If another app is using port `17357`, update the launcher port and OBS URLs accordingly.
- Rank and logo assets are served locally from `overlay/assets/`.
