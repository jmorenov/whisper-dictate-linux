from __future__ import annotations

import re
import subprocess
from pathlib import Path

_ARTIFACT = re.compile(r"^\s*[\[\(].*[\]\)]\s*$")  # [BLANK_AUDIO], (silence), ...


def transcribe(cfg: dict, model: Path, wav_path: str) -> str:
    """Transcribe audio using whisper-cli."""
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
