# whisper-dictate-linux

> **Push-to-talk voice dictation for Linux.** Hold a key, speak, release — the transcription is typed at your cursor in any focused application. 100% offline, powered by [whisper.cpp](https://github.com/ggerganov/whisper.cpp).

<p align="center">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Wayland%20%7C%20X11-success?style=flat-square&logo=linux" alt="Platform: Linux">
  <img src="https://img.shields.io/badge/offline-100%25-blue?style=flat-square" alt="Offline">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License: MIT">
</p>

Like **Amal**, **Wispr Flow**, or **Superwhisper**, but **local, private, and Linux-native**. No cloud, no subscription, no data leaves your machine.

---

## Table of Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Supported Platforms](#supported-platforms)
- [Requirements](#requirements)
- [Install](#install)
- [Configuration](#configuration)
- [Run as a background service](#run-as-a-background-service)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Push-to-talk** — Hold a key while speaking, release to transcribe. No accidental triggers.
- **100% offline** — Runs entirely on your machine with [whisper.cpp](https://github.com/ggerganov/whisper.cpp).
- **Universal text injection** — Works on **Wayland**, **X11**, and any compositor (COSMIC, Sway, Hyprland, GNOME, KDE, etc.) via multiple fallback strategies.
- **GPU/CPU accelerated** — whisper-cli can use Vulkan, CUDA, or CPU.
- **Configurable** — Choose key, language, model, beam size, and more.
- **Desktop notifications** — Visual feedback for recording and transcription states.
- **Systemd service** — Run as a background user service.

---

## How it works

```
hold key ──▶ evdev (read /dev/input) ──▶ arecord (16kHz mono WAV)
release ──▶ whisper-cli (GPU/CPU) ──▶ [wtype → ydotool → dotool → clipboard]
                                            ↓
                                      typed at cursor
```

The pipeline is simple and transparent:
1. **Capture** — `evdev` reads the keyboard at the kernel level to detect the hold key.
2. **Record** — `arecord` captures 16kHz mono audio to a temporary WAV.
3. **Transcribe** — `whisper-cli` converts speech to text using your local ggml model.
4. **Inject** — The text is typed at your cursor using the best available method for your session.

---

## Supported Platforms

| Platform / Compositor | Text Injection | Status |
|---|---|---|
| **Wayland** (Sway, Hyprland, GNOME, KDE, etc.) | `wtype` | ✅ |
| **COSMIC** (Pop!_OS, System76) | `ydotool` | ✅ |
| **X11** | `xdotool` (not included yet, PRs welcome) | ⚠️ |
| **Any session** | `wl-copy` + paste | ✅ (fallback) |

> **Note:** `ydotool` works universally on any compositor because it uses `/dev/uinput` at the kernel level, bypassing Wayland protocol limitations.

---

## Requirements

### System packages

- `whisper-cli` — Install via [Homebrew](https://brew.sh) (`brew install whisper-cpp`) or build from [source](https://github.com/ggerganov/whisper.cpp).
- `arecord` — `alsa-utils`
- `wtype` — For Wayland text injection (optional, but recommended)
- `ydotool` — For COSMIC / universal injection (optional, but recommended for COSMIC)
- `wl-clipboard` — `wl-copy` / `wl-paste` for clipboard fallback
- `libnotify-bin` — Desktop notifications (`notify-send`)

### GGML Model

Download a Whisper model (e.g., `large-v3-turbo`) and place it at:

```
~/.cache/whisper/ggml-large-v3-turbo.bin
```

You can download it with:

```bash
# Using Homebrew whisper-cli
whisper-cli --download-model large-v3-turbo

# Or manually
mkdir -p ~/.cache/whisper
curl -L -o ~/.cache/whisper/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

### Permissions

You must be in the `input` group to read the keyboard via `evdev`:

```bash
sudo usermod -aG input $USER
# Log out and back in for the change to take effect
```

---

## Install

### Quick install (recommended)

```bash
git clone https://github.com/yourusername/whisper-dictate-linux.git
cd whisper-dictate-linux
./install.sh
```

This will:
- Install system dependencies
- Add you to the `input` group
- Create a Python virtual environment
- Copy the example configuration to `~/.config/whisper-dictate-linux/config.toml`

> **Important:** After running `install.sh`, **log out and back in** so the `input` group membership takes effect.

### Manual install

```bash
# 1. Install dependencies
sudo apt-get install -y wtype wl-clipboard libnotify-bin alsa-utils ydotool

# 2. Add yourself to the input group
sudo usermod -aG input $USER
# Log out and back in

# 3. Create virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4. Create config
mkdir -p ~/.config/whisper-dictate-linux
cp config.example.toml ~/.config/whisper-dictate-linux/config.toml

# 5. Make executable
chmod +x whisper-dictate-linux dictate.py
```

### Run

```bash
./whisper-dictate-linux
```

Hold **Right Ctrl** (default), speak, release. The text appears at your cursor.

---

## Configuration

Edit `~/.config/whisper-dictate-linux/config.toml` (created automatically by `install.sh`):

```toml
# Key to HOLD while speaking (evdev KEY_* name).
# Examples: KEY_RIGHTCTRL, KEY_RIGHTALT, KEY_CAPSLOCK, KEY_F12, KEY_SCROLLLOCK
ptt_key = "KEY_RIGHTCTRL"

# Path to the ggml model. Empty = auto-detect.
model = ""

# Whisper language code: "auto", "es", "en", "de", "fr", ...
# NOTE: "auto" often defaults to English. Set explicitly for your language.
language = "es"

# 0 = let whisper-cli decide thread count.
threads = 0

# 0 = greedy decoding (fastest). 2+ = beam search (slower, more accurate).
beam_size = 0

# Ignore key taps shorter than this (seconds) to avoid empty recordings.
min_record_secs = 0.3

# Desktop notifications for state (recording / transcribing).
notify = true

# Per-keystroke delay for wtype in ms (0 = as fast as possible).
type_delay_ms = 0
```

See `config.example.toml` for all options.

---

## Run as a background service

```bash
mkdir -p ~/.config/systemd/user
cp whisper-dictate-linux.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user import-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR
systemctl --user enable --now whisper-dictate-linux
```

View logs:

```bash
journalctl --user -u whisper-dictate-linux -f
```

Stop the service:

```bash
systemctl --user stop whisper-dictate-linux
```

---

## Troubleshooting

### "no readable keyboard in /dev/input"

You are not in the `input` group, or you haven't logged out/in since joining it.

```bash
# Verify
id | grep input
# If empty, add yourself and re-login
sudo usermod -aG input $USER
```

### Text doesn't appear

Check which text injection method is available:

```bash
wtype -- hola       # For Wayland compositors with virtual-keyboard support
ydotool type hola   # For any compositor (COSMIC, etc.)
wl-copy <<< "hola" && ydotool key ctrl+v  # Clipboard fallback
```

If `wtype` fails on COSMIC, that's expected — `ydotool` will be used automatically.

### No audio / empty transcription

Test your microphone:

```bash
arecord -d 3 test.wav && aplay test.wav
```

If silent, select the correct input in your sound settings (pavucontrol, COSMIC Settings, etc.).

### Service fails with "No such file or directory: 'whisper-cli'"

Ensure `whisper-cli` is in your PATH. If installed via Homebrew:

```bash
export PATH="$HOME/linuxbrew/.linuxbrew/bin:$PATH"
```

The `whisper-dictate-linux` launcher already includes common Homebrew paths.

### Spanish transcription defaults to English

Set `language = "es"` explicitly in your config. `"auto"` often fails for Spanish.

---

## Contributing

Pull requests are welcome! Some ideas:

- **X11 support** — Add `xdotool` fallback.
- **GUI config** — A simple GTK or COSMIC settings panel.
- **Model downloader** — Auto-download models on first run.
- **Other languages** — Test and document support for more languages.
- **Performance** — Support for faster models (tiny, base, small) for low-end hardware.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ for the Linux community.
</p>
