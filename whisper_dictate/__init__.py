"""whisper_dictate - Core package for push-to-talk voice dictation on Linux."""

__version__ = "1.0.0"

from .audio import start_recording, stop_recording
from .keyboard import find_keyboards
from .config import load_config, resolve_model, DEFAULTS, CONFIG_PATH
from .whisper import transcribe
from .notify import notify
from .inject import inject

__all__ = [
    "start_recording",
    "stop_recording",
    "find_keyboards",
    "load_config",
    "DEFAULTS",
    "CONFIG_PATH",
    "transcribe",
    "notify",
    "inject",
    "__version__",
]
