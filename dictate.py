#!/usr/bin/env python3
"""Push-to-talk dictation for Linux (Wayland/COSMIC) using whisper.cpp.

Hold the configured key, speak, release: the transcription is typed at the
cursor in the focused application. 100% offline, powered by your local
whisper-cli + ggml model.

Pipeline: evdev (hold key) -> arecord -> whisper-cli -> wtype / clipboard.
"""

from __future__ import annotations

import os
import selectors
import sys
import tempfile
import time

from evdev import ecodes

from whisper_dictate import (
    find_keyboards,
    inject,
    load_config,
    notify,
    resolve_model,
    start_recording,
    stop_recording,
    transcribe,
)


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
    rec_proc = None
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
