from __future__ import annotations

import evdev
from evdev import ecodes


def find_keyboards() -> list[evdev.InputDevice]:
    """Find all keyboard input devices via evdev."""
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
