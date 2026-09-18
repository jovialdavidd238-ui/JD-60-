from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np
import sounddevice as sd
import speech_recognition as sr

from .config import load_settings

STOP_LISTEN = {
    "stop listening",
    "close the mic",
    "close mic",
    "mic off",
    "stop the mic",
    "turn off the mic",
    "that's enough",
    "thats enough",
    "stand down",
    "stop listening jd60",
    "go idle",
}


def is_stop_listen(text: str) -> bool:
    q = (text or "").strip().lower().strip(" .!")
    return q in STOP_LISTEN or q.startswith("stop listening") or q.startswith("close the mic")


class Ears:
    def __init__(self) -> None:
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.sample_rate = 16000

    def listen(self, seconds: float | None = None) -> str:
        settings = load_settings()
        duration = seconds or float(settings.get("listen_seconds", 6))
        frames = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        return self._decode(np.ascontiguousarray(frames))

    def listen_utterance(self, alive: Callable[[], bool], wait_for_speech: float = 90.0) -> str:
        """Keep the mic open until speech, then stop after trailing silence."""
        rate = self.sample_rate
        hop = int(0.12 * rate)
        noise: list[float] = []
        for _ in range(8):
            if not alive():
                return ""
            chunk = sd.rec(hop, samplerate=rate, channels=1, dtype="float32")
            sd.wait()
            noise.append(float(np.sqrt(np.mean(np.square(chunk)) + 1e-12)))
        floor = max(0.012, (sum(noise) / max(len(noise), 1)) * 3.2)

        voiced = False
        silence_hops = 0
        buf: list[np.ndarray] = []
        started = time.time()
        while alive():
            chunk = sd.rec(hop, samplerate=rate, channels=1, dtype="float32")
            sd.wait()
            rms = float(np.sqrt(np.mean(np.square(chunk)) + 1e-12))
            if rms >= floor:
                voiced = True
                silence_hops = 0
                buf.append(chunk.copy())
            elif voiced:
                buf.append(chunk.copy())
                silence_hops += 1
                if silence_hops >= 10:
                    break
            elif time.time() - started > wait_for_speech:
                return ""
        if not buf:
            return ""
        audio = np.concatenate(buf, axis=0)
        pcm = np.clip(audio, -1.0, 1.0)
        frames = (pcm * 32767.0).astype(np.int16)
        return self._decode(frames)

    def _decode(self, frames: np.ndarray) -> str:
        audio = sr.AudioData(np.ascontiguousarray(frames).tobytes(), self.sample_rate, 2)
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            raise RuntimeError(f"Speech service unavailable: {exc}") from exc
