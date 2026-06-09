# Agent Guide for whisper-dictate-linux

This document contains instructions, context, and conventions for AI agents (like Cursor, Claude, Copilot, etc.) working on this codebase.

## Project Overview

- **Name:** whisper-dictate-linux
- **Purpose:** Push-to-talk voice dictation for Linux, 100% offline, powered by whisper.cpp
- **Architecture:** Python 3 daemon that reads keyboard events via evdev, records audio via arecord, transcribes via whisper-cli, and injects text via wtype/ydotool/clipboard
- **Target Platforms:** Linux (Wayland, X11, COSMIC, Sway, Hyprland, GNOME, KDE, etc.)
- **License:** MIT

## Repository Structure

```
.
├── AGENTS.md              # This file
├── README.md              # User-facing documentation
├── LICENSE                # MIT license
├── config.example.toml    # Example configuration file
├── dictate.py             # Main application (entry point)
├── install.sh             # One-shot installation script
├── requirements.txt       # Python dependencies (evdev)
├── whisper-dictate-linux        # Bash launcher (creates venv, sets PATH)
└── whisper-dictate-linux.service # systemd user service template
```

## Code Conventions

### Python
- **Style:** PEP 8, 4-space indentation
- **Typing:** Use type hints (`from __future__ import annotations` for Python 3.9+)
- **Error handling:** Use `subprocess.run(..., check=False)` and check return codes manually for non-fatal operations
- **Logging:** Print to stderr for diagnostics; use `sys.stdout.reconfigure(line_buffering=True)` for systemd compatibility
- **Shebang:** `#!/usr/bin/env python3`

### Bash
- **Style:** `set -euo pipefail` in all scripts
- **Paths:** Use `readlink -f` to resolve script location
- **Compatibility:** Target bash 4.2+ (Debian/Ubuntu default)

## Key Design Decisions

1. **No GUI** — This is a daemon/tool, not a desktop app. Configuration is via TOML.
2. **Multiple text injection fallbacks** — `wtype` (Wayland) → `ydotool` (universal) → `dotool` → `wl-copy` + paste. This ensures compatibility across all compositors.
3. **Kernel-level keyboard reading** — Uses `evdev` to read `/dev/input` directly. This is required because Wayland compositors only report key *press* events, not *hold* duration.
4. **Environment variable handling** — `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR` must be passed correctly to child processes. The script auto-detects the Wayland socket if the variable is missing.
5. **PATH handling** — The `whisper-dictate-linux` launcher sets PATH to include Homebrew and local directories, because systemd services don't inherit the user's shell environment.

## Common Tasks for Agents

### Adding a new text injection method

Edit `inject()` in `dictate.py`:
1. Check if the binary exists with `shutil.which()`
2. Run it with the full `env` dict
3. Capture `stderr` and print it on failure
4. Return the method name as a string on success

### Adding a new configuration option

1. Add the default to `DEFAULTS` dict in `dictate.py`
2. Add documentation to `config.example.toml`
3. Document it in `README.md`
4. If the option affects behavior, update `AGENTS.md` Key Design Decisions

### Modifying the install script

- Keep it idempotent (safe to run multiple times)
- Use `sudo` only for system packages and `usermod`
- Don't install models automatically (they're large)
- Print clear next steps after installation

### Modifying the systemd service

- Use `PassEnvironment` for Wayland variables, don't hardcode them
- Don't hardcode `ExecStart` paths; use `%h` for home directory
- Remember that systemd services don't inherit shell PATH

## Testing Checklist

Before submitting changes:

- [ ] `python3 -m py_compile dictate.py` passes
- [ ] `./install.sh` syntax is valid (`bash -n install.sh`)
- [ ] `config.example.toml` is valid TOML
- [ ] README.md reflects all changes
- [ ] AGENTS.md is updated if design decisions changed

## External Dependencies

- `whisper-cli` (Homebrew or compiled from source)
- `arecord` (alsa-utils)
- `wtype` (Wayland virtual keyboard)
- `ydotool` (universal input via /dev/uinput)
- `wl-clipboard` (wl-copy, wl-paste)
- `libnotify-bin` (notify-send)

Python packages (in venv):
- `evdev>=1.9`

## Important Notes

- **COSMIC compatibility:** COSMIC does not support the `virtual-keyboard` Wayland extension, so `wtype` will fail. `ydotool` is the primary method there.
- **Group requirement:** The user MUST be in the `input` group. There's no workaround — this is a kernel-level requirement for evdev.
- **Model location:** The script searches `~/.cache/whisper/` and `~/.local/share/whisper/` for ggml models.
- **Language setting:** `language = "auto"` often defaults to English. For non-English dictation, always set the language explicitly.
