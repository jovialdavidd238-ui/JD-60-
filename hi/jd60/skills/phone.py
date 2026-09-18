from __future__ import annotations

import shutil
import subprocess

from .base import Result

PACKAGES: dict[str, dict[str, str]] = {
    "instagram": {"package": "com.instagram.android", "intent": "https://www.instagram.com"},
    "whatsapp": {"package": "com.whatsapp", "intent": "https://wa.me/"},
    "youtube": {"package": "com.google.android.youtube", "intent": "https://www.youtube.com"},
    "chrome": {"package": "com.android.chrome", "intent": "https://www.google.com"},
    "gmail": {"package": "com.google.android.gm", "intent": "https://mail.google.com"},
    "maps": {"package": "com.google.android.apps.maps", "intent": "https://maps.google.com"},
    "spotify": {"package": "com.spotify.music", "intent": "https://open.spotify.com"},
    "camera": {"package": "com.android.camera2", "intent": ""},
    "settings": {"package": "com.android.settings", "intent": ""},
    "phone": {"package": "com.android.dialer", "intent": "tel:"},
    "messages": {"package": "com.google.android.apps.messaging", "intent": "sms:"},
    "photos": {"package": "com.google.android.apps.photos", "intent": ""},
    "gallery": {"package": "com.google.android.apps.photos", "intent": ""},
    "facebook": {"package": "com.facebook.katana", "intent": "https://www.facebook.com"},
    "twitter": {"package": "com.twitter.android", "intent": "https://x.com"},
    "x": {"package": "com.twitter.android", "intent": "https://x.com"},
    "snapchat": {"package": "com.snapchat.android", "intent": "https://www.snapchat.com"},
    "telegram": {"package": "org.telegram.messenger", "intent": "https://t.me"},
    "netflix": {"package": "com.netflix.mediaclient", "intent": "https://www.netflix.com"},
    "clock": {"package": "com.google.android.deskclock", "intent": ""},
    "calculator": {"package": "com.google.android.calculator", "intent": ""},
}


def resolve_mobile(name: str) -> tuple[str, dict[str, str]] | None:
    q = name.lower().strip()
    if q in PACKAGES:
        return q, PACKAGES[q]
    for key, meta in PACKAGES.items():
        if key in q:
            return key, meta
    return None


def adb_available() -> bool:
    return shutil.which("adb") is not None


def adb_open(name: str) -> Result:
    found = resolve_mobile(name)
    if not found:
        return Result(False, f"I do not have a phone app mapping for {name}.")
    key, meta = found
    if not adb_available():
        url = _intent_url(meta)
        return Result(
            True,
            f"Open {key} on the phone from the JD60 mobile page.",
            {"client_action": {"type": "open", "url": url, "app": key}},
        )
    pkg = meta["package"]
    completed = subprocess.run(
        ["adb", "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        subprocess.run(
            ["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", meta.get("intent") or f"package:{pkg}"],
            capture_output=True,
            text=True,
        )
    return Result(True, f"Opening {key} on the phone.")


def adb_close(name: str) -> Result:
    found = resolve_mobile(name)
    if not found:
        return Result(False, f"I do not have a phone app mapping for {name}.")
    key, meta = found
    if not adb_available():
        return Result(
            False,
            f"To close {key} on the phone, connect it with USB debugging (adb) or use the mobile page.",
        )
    subprocess.run(["adb", "shell", "am", "force-stop", meta["package"]], capture_output=True, text=True)
    return Result(True, f"Closed {key} on the phone.")


def adb_home() -> Result:
    if not adb_available():
        return Result(True, "Go home on the phone.", {"client_action": {"type": "home"}})
    subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_HOME"], capture_output=True, text=True)
    return Result(True, "Sent the phone to the home screen.")


def _intent_url(meta: dict[str, str]) -> str:
    if meta.get("intent"):
        return meta["intent"]
    pkg = meta["package"]
    return f"intent:#Intent;action=android.intent.action.MAIN;category=android.intent.category.LAUNCHER;package={pkg};end"
