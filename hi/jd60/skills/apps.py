from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .base import Result

COMMON_APPS: dict[str, dict] = {
    "vscode": {
        "names": ["vscode", "vs code", "visual studio code", "code"],
        "bins": ["code", "code.cmd"],
        "exes": [
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES(X86)%\Microsoft VS Code\Code.exe",
        ],
        "process": "Code.exe",
    },
    "blender": {
        "names": ["blender"],
        "bins": ["blender"],
        "exes": [
            r"%PROGRAMFILES%\Blender Foundation\Blender 4.5\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender 4.4\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender 4.3\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender 4.2\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender 4.1\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender 4.0\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender 3.6\blender.exe",
        ],
        "process": "blender.exe",
    },
    "chrome": {
        "names": ["chrome", "google chrome"],
        "bins": ["chrome"],
        "exes": [
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        ],
        "process": "chrome.exe",
    },
    "edge": {
        "names": ["edge", "microsoft edge"],
        "bins": ["msedge"],
        "exes": [r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"],
        "process": "msedge.exe",
    },
    "firefox": {
        "names": ["firefox"],
        "bins": ["firefox"],
        "exes": [r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"],
        "process": "firefox.exe",
    },
    "notepad": {
        "names": ["notepad"],
        "bins": ["notepad"],
        "exes": [r"%WINDIR%\notepad.exe"],
        "process": "notepad.exe",
    },
    "calculator": {
        "names": ["calculator", "calc"],
        "bins": ["calc"],
        "exes": [],
        "process": "CalculatorApp.exe",
    },
    "explorer": {
        "names": ["explorer", "files", "file explorer"],
        "bins": ["explorer"],
        "exes": [r"%WINDIR%\explorer.exe"],
        "process": "explorer.exe",
    },
    "spotify": {
        "names": ["spotify"],
        "bins": ["spotify"],
        "exes": [r"%APPDATA%\Spotify\Spotify.exe"],
        "process": "Spotify.exe",
    },
    "discord": {
        "names": ["discord"],
        "bins": ["discord"],
        "exes": [r"%LOCALAPPDATA%\Discord\Update.exe"],
        "process": "Discord.exe",
        "args": ["--processStart", "Discord.exe"],
    },
    "steam": {
        "names": ["steam"],
        "bins": ["steam"],
        "exes": [r"%PROGRAMFILES(X86)%\Steam\steam.exe"],
        "process": "steam.exe",
    },
    "word": {
        "names": ["word", "microsoft word"],
        "bins": ["winword"],
        "exes": [
            r"%PROGRAMFILES%\Microsoft Office\root\Office16\WINWORD.EXE",
        ],
        "process": "WINWORD.EXE",
    },
    "excel": {
        "names": ["excel", "microsoft excel"],
        "bins": ["excel"],
        "exes": [r"%PROGRAMFILES%\Microsoft Office\root\Office16\EXCEL.EXE"],
        "process": "EXCEL.EXE",
    },
    "powerpoint": {
        "names": ["powerpoint", "power point"],
        "bins": ["powerpnt"],
        "exes": [r"%PROGRAMFILES%\Microsoft Office\root\Office16\POWERPNT.EXE"],
        "process": "POWERPNT.EXE",
    },
    "cmd": {
        "names": ["cmd", "command prompt", "terminal cmd"],
        "bins": ["cmd"],
        "exes": [r"%WINDIR%\System32\cmd.exe"],
        "process": "cmd.exe",
    },
    "powershell": {
        "names": ["powershell", "terminal", "windows terminal"],
        "bins": ["wt", "pwsh", "powershell"],
        "exes": [
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe",
        ],
        "process": "WindowsTerminal.exe",
    },
    "paint": {
        "names": ["paint", "mspaint"],
        "bins": ["mspaint"],
        "exes": [r"%WINDIR%\System32\mspaint.exe"],
        "process": "mspaint.exe",
    },
    "settings": {
        "names": ["settings", "windows settings"],
        "bins": [],
        "exes": [],
        "uri": "ms-settings:",
        "process": "SystemSettings.exe",
    },
}


def _expand(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))


def resolve_app(query: str) -> tuple[str | None, dict | None]:
    q = query.lower().strip()
    for key, meta in COMMON_APPS.items():
        if q == key or q in meta["names"] or any(n in q for n in meta["names"]):
            return key, meta
    for key, meta in COMMON_APPS.items():
        if key in q:
            return key, meta
    return None, None


def find_executable(meta: dict) -> str | None:
    for bin_name in meta.get("bins", []):
        found = shutil.which(bin_name)
        if found:
            return found
    for exe in meta.get("exes", []):
        path = Path(_expand(exe))
        if path.exists():
            return str(path)
    if meta.get("key") == "blender" or True:
        foundation = Path(_expand(r"%PROGRAMFILES%\Blender Foundation"))
        if foundation.exists():
            matches = sorted(foundation.glob("*/blender.exe"), reverse=True)
            if matches:
                return str(matches[0])
    return None


def open_app(name: str, extra_args: list[str] | None = None) -> Result:
    key, meta = resolve_app(name)
    if not meta:
        # last resort: start command
        try:
            subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
            return Result(True, f"Asked Windows to start {name}.")
        except Exception as exc:
            return Result(False, f"I could not identify an app named {name}. {exc}")

    if meta.get("uri"):
        os.startfile(meta["uri"])  # type: ignore[attr-defined]
        return Result(True, f"Opening {key}.")

    exe = find_executable(meta)
    if not exe:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", key], shell=False)
            return Result(True, f"Asked Windows to start {key}.")
        except Exception as exc:
            return Result(False, f"{key} does not appear to be installed. {exc}")

    args = [exe]
    args += meta.get("args", [])
    if extra_args:
        args += extra_args
    subprocess.Popen(args, shell=False)
    return Result(True, f"Launching {key}.", {"app": key, "exe": exe})


def close_app(name: str) -> Result:
    key, meta = resolve_app(name)
    process = (meta or {}).get("process")
    if not process:
        process = name if name.lower().endswith(".exe") else f"{name}.exe"
    completed = subprocess.run(
        ["taskkill", "/IM", process, "/F"],
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return Result(True, f"Closed {key or name}.")
    return Result(False, f"Could not close {key or name}. It may not be running.")
