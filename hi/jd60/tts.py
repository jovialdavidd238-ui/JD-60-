from __future__ import annotations

import threading

import pyttsx3

from .config import load_settings


class Voice:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.enabled = True
        self.idle = threading.Event()
        self.idle.set()
        self._engine = pyttsx3.init()
        settings = load_settings()
        self._engine.setProperty("rate", settings.get("voice_rate", 175))
        prefer = [p.lower() for p in settings.get("voice_prefer", [])]
        for voice in self._engine.getProperty("voices"):
            name = (voice.name or "").lower()
            if any(p in name for p in prefer) and "female" not in name:
                self._engine.setProperty("voice", voice.id)
                break

    def wait_idle(self, timeout: float = 60.0) -> None:
        self.idle.wait(timeout=timeout)

    def say(self, text: str, block: bool = False) -> None:
        if not self.enabled or not text:
            return

        def _run() -> None:
            self.idle.clear()
            try:
                with self._lock:
                    self._engine.say(text)
                    self._engine.runAndWait()
            finally:
                self.idle.set()

        if block:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        try:
            self._engine.stop()
        except Exception:
            pass
        self.idle.set()
