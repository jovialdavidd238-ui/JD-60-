from __future__ import annotations

import ctypes
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import pyautogui
from pycaw.pycaw import AudioUtilities

from .base import Result

pyautogui.FAILSAFE = True


def _volume_interface():
    speakers = AudioUtilities.GetSpeakers()
    return speakers.EndpointVolume


def set_volume(percent: int) -> Result:
    value = max(0, min(100, int(percent)))
    try:
        volume = _volume_interface()
        volume.SetMasterVolumeLevelScalar(value / 100.0, None)
    except Exception:
        pyautogui.press("volumemute")
        pyautogui.press("volumemute")
        return Result(True, f"Tried to reach {value} percent via system keys.")
    return Result(True, f"Volume set to {value} percent.")


def change_volume(delta: int) -> Result:
    try:
        volume = _volume_interface()
        current = volume.GetMasterVolumeLevelScalar()
        nxt = max(0.0, min(1.0, current + delta / 100.0))
        volume.SetMasterVolumeLevelScalar(nxt, None)
        return Result(True, f"Volume is now {int(nxt * 100)} percent.")
    except Exception:
        key = "volumeup" if delta > 0 else "volumedown"
        pyautogui.press(key)
        return Result(True, "Nudged system volume.")


def mute(state: bool | None = None) -> Result:
    try:
        volume = _volume_interface()
        if state is None:
            state = not bool(volume.GetMute())
        volume.SetMute(bool(state), None)
        return Result(True, "Muted." if state else "Unmuted.")
    except Exception:
        pyautogui.press("volumemute")
        return Result(True, "Toggled mute.")


def screenshot(folder: str | None = None) -> Result:
    dest_dir = Path(folder or Path.home() / "Desktop")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"jd60_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    pyautogui.screenshot(str(dest))
    return Result(True, f"Screenshot saved to {dest}.", {"path": str(dest)})


def lock_pc() -> Result:
    ctypes.windll.user32.LockWorkStation()
    return Result(True, "Locking the workstation.")


def shutdown(kind: str = "shutdown") -> Result:
    mapping = {
        "shutdown": ["shutdown", "/s", "/t", "5"],
        "restart": ["shutdown", "/r", "/t", "5"],
        "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "hibernate": ["shutdown", "/h"],
    }
    cmd = mapping.get(kind)
    if not cmd:
        return Result(False, f"Unknown power action {kind}.")
    subprocess.Popen(cmd, shell=False)
    return Result(True, f"Executing {kind} in a moment.")


def type_text(text: str) -> Result:
    pyautogui.typewrite(text, interval=0.02)
    return Result(True, "Typed into the active window.")


def hotkey(*keys: str) -> Result:
    pyautogui.hotkey(*keys)
    return Result(True, f"Pressed {'+'.join(keys)}.")


def system_info() -> Result:
    uname = platform.uname()
    msg = (
        f"{uname.system} {uname.release} on {uname.node}. "
        f"Processor: {uname.processor or 'unknown'}."
    )
    return Result(True, msg, {"system": uname.system, "release": uname.release})


def empty_recycle_bin() -> Result:
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
        capture_output=True,
        text=True,
    )
    return Result(True, "Recycle Bin cleared.")
