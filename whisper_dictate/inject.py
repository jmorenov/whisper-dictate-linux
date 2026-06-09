from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


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
        if cfg.get("type_delay_ms"):
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
