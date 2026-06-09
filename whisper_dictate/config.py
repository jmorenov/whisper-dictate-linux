from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import tomllib

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
            raise FileNotFoundError(f"[whisper-dictate-linux] model not found: {p}")
        return p
    for cand in MODEL_CANDIDATES:
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        "[whisper-dictate-linux] no ggml model found. Searched:\n  "
        + "\n  ".join(str(c) for c in MODEL_CANDIDATES)
    )
