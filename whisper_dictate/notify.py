from __future__ import annotations

import shutil
import subprocess

_NOTIFY = shutil.which("notify-send")


def notify(cfg: dict, summary: str, body: str = "", *, urgency: str = "low") -> None:
    """Show a desktop notification if enabled and notify-send is available."""
    if not cfg.get("notify", True) or not _NOTIFY:
        return
    subprocess.run(
        [_NOTIFY, "-u", urgency, "-t", "1500", "-a", "whisper-dictate-linux", summary, body],
        check=False,
    )
