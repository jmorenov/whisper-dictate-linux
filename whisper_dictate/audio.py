from __future__ import annotations

import signal
import subprocess


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
