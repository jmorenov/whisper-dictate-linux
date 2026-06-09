#!/usr/bin/env python3
"""Push-to-talk dictation for Linux (Wayland/COSMIC) using whisper.cpp.

Hold the configured key, speak, release: the transcription is typed at the
cursor in the focused application. 100% offline, powered by your local
whisper-cli + ggml model.

Pipeline: evdev (hold key) -> arecord -> whisper-cli -> wtype / clipboard.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

import selectors

import evdev
from evdev import ecodes


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DEFAULTS = {
    "ptt_key": "KEY_RIGHTCTRL",          # key to hold while speaking
    "model": "",                          # empty -> auto-detect (see below)
    "language": "auto",                   # whisper language code or "auto"
    "threads": 0,                          # 0 -> let whisper-cli decide
    "beam_size": 0,                        # 0 -> greedy (faster)
    "min_record_secs": 0.3,                # ignore accidental taps
    "notify": True,                        # desktop notifications
    "type_delay_ms": 0,                    # wtype keystroke delay
}

MODEL_CANDIDATES = [
    Path.home() / ".cache/whisper/ggml-large-v3-turbo.bin",
    Path.home() / ".local/share/whisper/ggml-large-v3-turbo.bin",
]

CONFIG_PATH = Path(
    os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
) / "whisper-dictate-linux" / "config.toml"


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.is_file():
        with open(CONFIG_PATH, "rb") as fh:
            cfg.update(tomllib.load(fh))
    return cfg


def resolve_model(cfg: dict) -> Path:
    if cfg["model"]:
        p = Path(cfg["model"]).expanduser()
        if not p.is_file():
            sys.exit(f"[whisper-dictate-linux] model not found: {p}")
        return p
    for cand in MODEL_CANDIDATES:
        if cand.is_file():
            return cand
    sys.exit(
        "[whisper-dictate-linux] no ggml model found. Searched:\n  "
        + "\n  ".join(str(c) for c in MODEL_CANDIDATES)
    )


# --------------------------------------------------------------------------- #
# Feedback
# --------------------------------------------------------------------------- #

_NOTIFY = shutil.which("notify-send")


def notify(cfg: dict, summary: str, body: str = "", *, urgency: str = "low") -> None:
    if not cfg["notify"] or not _NOTIFY:
        return
    subprocess.run(
        [_NOTIFY, "-u", urgency, "-t", "1500", "-a", "whisper-dictate-linux", summary, body],
        check=False,
    )


# --------------------------------------------------------------------------- #
# Recording
# --------------------------------------------------------------------------- #

def start_recording(wav_path: str) -> subprocess.Popen:
    """Start arecord into a 16kHz mono wav (whisper's expected format)."""
    return subprocess.Popen(
        [
            "arecord",
            "-q",
            "-f", "S16_LE",
            "-c", "1",
            "-r", "16000",
            "-t", "wav",
            wav_path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_recording(proc: subprocess.Popen) -> None:
    """SIGINT lets arecord finalize the wav header cleanly."""
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


# --------------------------------------------------------------------------- #
# Transcription
# --------------------------------------------------------------------------- #

_ARTIFACT = re.compile(r"^\s*[\[\(].*[\]\)]\s*$")  # [BLANK_AUDIO], (silence), ...


def transcribe(cfg: dict, model: Path, wav_path: str) -> str:
    cmd = [
        "whisper-cli",
        "-m", str(model),
        "-f", wav_path,
        "--no-timestamps",
    ]
    if cfg["language"]:
        if cfg["language"] != "auto":
            cmd += ["-l", cfg["language"]]
        else:
            cmd += ["-l", "auto"]
    if cfg["threads"]:
        cmd += ["-t", str(cfg["threads"])]
    if cfg["beam_size"]:
        cmd += ["-bs", str(cfg["beam_size"])]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return ""

    lines = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line or _ARTIFACT.match(line):
            continue
        lines.append(line)
    return " ".join(lines).strip()


# --------------------------------------------------------------------------- #
# Text injection
# --------------------------------------------------------------------------- #

def _guess_wayland_display() -> str | None:
    """Try to find the active Wayland socket when WAYLAND_DISPLAY is missing."""
    import re as _re
    run_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    if not os.path.isdir(run_dir):
        return None
    # Only sockets named exactly wayland-<number> (ignore .lock, -render, etc.).
    _wl_re = _re.compile(r"^wayland-\d+$")
    candidates = sorted(
        (
            p for p in Path(run_dir).glob("wayland-*")
            if p.is_socket() and _wl_re.match(p.name)
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0].name if candidates else None


def inject(cfg: dict, text: str) -> str:
    """Type the text at the cursor. Returns the method used."""
    env = os.environ.copy()
    if not env.get("WAYLAND_DISPLAY"):
        guess = _guess_wayland_display()
        if guess:
            env["WAYLAND_DISPLAY"] = guess
            print(f"[inject] guessed WAYLAND_DISPLAY={guess}", file=sys.stderr)
    if not env.get("XDG_RUNTIME_DIR"):
        env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"

    wtype = shutil.which("wtype")
    if wtype:
        cmd = [wtype]
        if cfg["type_delay_ms"]:
            cmd += ["-d", str(cfg["type_delay_ms"])]
        cmd += ["--", text]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
        if res.returncode == 0:
            return "wtype"
        print(f"[wtype error] {res.stderr.strip()}", file=sys.stderr)

    # Fallback 1: ydotool (works on any compositor via /dev/uinput)
    ydotool = shutil.which("ydotool")
    if ydotool:
        cmd = [ydotool, "type", text]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
        if res.returncode == 0:
            return "ydotool"
        print(f"[ydotool error] {res.stderr.strip()}", file=sys.stderr)

    # Fallback 2: dotool
    dotool = shutil.which("dotool")
    if dotool:
        cmd = ["sh", "-c", f"echo type '{text}' | dotool"]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
        if res.returncode == 0:
            return "dotool"
        print(f"[dotool error] {res.stderr.strip()}", file=sys.stderr)

    # Fallback 3: clipboard + Ctrl+V
    wl_copy = shutil.which("wl-copy")
    if wl_copy:
        subprocess.run([wl_copy], input=text.encode(), check=False, env=env)
        if wtype:
            res = subprocess.run(
                [wtype, "-M", "ctrl", "-k", "v", "-m", "ctrl"],
                capture_output=True, text=True, env=env, check=False,
            )
            if res.returncode == 0:
                return "clipboard+paste"
            print(f"[wtype paste error] {res.stderr.strip()}", file=sys.stderr)
        if ydotool:
            res = subprocess.run(
                [ydotool, "key", "ctrl+v"],
                capture_output=True, text=True, env=env, check=False,
            )
            if res.returncode == 0:
                return "clipboard+ydotool"
            print(f"[ydotool paste error] {res.stderr.strip()}", file=sys.stderr)
            return "clipboard"
        return "clipboard"

    return "none"


# --------------------------------------------------------------------------- #
# Keyboard discovery
# --------------------------------------------------------------------------- #

def find_keyboards() -> list[evdev.InputDevice]:
    devices = []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except (PermissionError, OSError):
            continue
        caps = dev.capabilities()
        keys = caps.get(ecodes.EV_KEY, [])
        # A real keyboard exposes letter keys.
        if ecodes.KEY_A in keys and ecodes.KEY_Z in keys:
            devices.append(dev)
    return devices


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #

def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    cfg = load_config()
    model = resolve_model(cfg)

    ptt_code = getattr(ecodes, cfg["ptt_key"], None)
    if ptt_code is None:
        sys.exit(f"[whisper-dictate-linux] unknown key: {cfg['ptt_key']}")

    keyboards = find_keyboards()
    if not keyboards:
        sys.exit(
            "[whisper-dictate-linux] no readable keyboard in /dev/input.\n"
            "Are you in the 'input' group?  sudo usermod -aG input $USER  (then re-login)"
        )

    print(f"[whisper-dictate-linux] model: {model}")
    print(f"[whisper-dictate-linux] hold {cfg['ptt_key']} to dictate "
          f"({len(keyboards)} keyboard(s) watched)")
    notify(cfg, "whisper-dictate-linux listo", f"Mantén {cfg['ptt_key']} para dictar")

    sel = selectors.DefaultSelector()
    for dev in keyboards:
        sel.register(dev, selectors.EVENT_READ)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = tmp.name
    tmp.close()

    recording = False
    rec_proc: subprocess.Popen | None = None
    start_ts = 0.0

    try:
        while True:
            for key, _ in sel.select():
                dev = key.fileobj
                try:
                    events = list(dev.read())
                except OSError:
                    continue
                for event in events:
                    if event.type != ecodes.EV_KEY or event.code != ptt_code:
                        continue
                    if event.value == 1 and not recording:  # key down
                        recording = True
                        start_ts = time.monotonic()
                        rec_proc = start_recording(wav_path)
                        notify(cfg, "Grabando…", urgency="normal")
                    elif event.value == 0 and recording:  # key up
                        recording = False
                        duration = time.monotonic() - start_ts
                        if rec_proc:
                            stop_recording(rec_proc)
                            rec_proc = None
                        if duration < cfg["min_record_secs"]:
                            continue
                        notify(cfg, "Transcribiendo…")
                        text = transcribe(cfg, model, wav_path)
                        if not text:
                            notify(cfg, "Sin texto", "No se detectó voz")
                            continue
                        method = inject(cfg, text)
                        if method == "none":
                            notify(cfg, "No se pudo escribir",
                                   "Instala wtype o wl-clipboard", urgency="critical")
                        print(f"[{method}] {text}")
    except KeyboardInterrupt:
        pass
    finally:
        if rec_proc:
            stop_recording(rec_proc)
        try:
            os.unlink(wav_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
