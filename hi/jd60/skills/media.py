from __future__ import annotations

import pyautogui

from .base import Result


def media(action: str) -> Result:
    mapping = {
        "play": "playpause",
        "pause": "playpause",
        "playpause": "playpause",
        "next": "nexttrack",
        "previous": "prevtrack",
        "prev": "prevtrack",
        "stop": "stop",
        "volup": "volumeup",
        "voldown": "volumedown",
        "mute": "volumemute",
    }
    key = mapping.get(action.lower())
    if not key:
        return Result(False, f"Unknown media action {action}.")
    pyautogui.press(key)
    return Result(True, f"Media: {action}.")
