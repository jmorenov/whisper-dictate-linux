#!/usr/bin/env bash
# One-shot setup for whisper-dictate-linux.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$HERE"

echo "==> System packages (sudo)"
sudo apt-get install -y wtype wl-clipboard libnotify-bin alsa-utils ydotool

echo "==> Add user to 'input' group (needed to read the keyboard via evdev)"
if ! id -nG "$USER" | tr ' ' '\n' | grep -qx input; then
  sudo usermod -aG input "$USER"
  echo "   -> added. You must LOG OUT and back in for this to take effect."
fi

echo "==> Python virtualenv"
python3 -m venv .venv
.venv/bin/pip -q install --upgrade pip
.venv/bin/pip -q install -r requirements.txt

echo "==> Config"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/whisper-dictate-linux"
mkdir -p "$CFG"
[ -f "$CFG/config.toml" ] || cp config.example.toml "$CFG/config.toml"
echo "   config: $CFG/config.toml"

chmod +x whisper-dictate-linux dictate.py

echo
echo "Done. Make sure the ggml model exists at:"
echo "   ~/.cache/whisper/ggml-large-v3-turbo.bin"
echo
echo "Run it with:  ./whisper-dictate-linux"
echo "Or install the user service:"
echo "   mkdir -p ~/.config/systemd/user"
echo "   cp whisper-dictate-linux.service ~/.config/systemd/user/"
echo "   systemctl --user daemon-reload"
echo "   systemctl --user import-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR"
echo "   systemctl --user enable --now whisper-dictate-linux"
