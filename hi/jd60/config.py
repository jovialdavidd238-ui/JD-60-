from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / ".jd60"
DATA_DIR.mkdir(exist_ok=True)
MEMORY_PATH = DATA_DIR / "memory.json"
CONFIG_PATH = DATA_DIR / "settings.json"
PROJECTS_DIR = ROOT / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)
JOBS_DIR = ROOT / "blender_jobs"
JOBS_DIR.mkdir(exist_ok=True)

DEFAULTS = {
    "user_name": os.getenv("JD60_NAME", "sir"),
    "wake_words": ["jd60", "jd 60", "hey jd", "jarvis", "jay dee"],
    "voice_rate": 175,
    "voice_prefer": ["David", "Guy", "Ryan", "James", "Mark"],
    "listen_seconds": 6,
    "confirm_dangerous": True,
    "app_aliases": {},
}


def load_settings() -> dict:
    data = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            data.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return data


def save_settings(settings: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def groq_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def openai_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()


def ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.1").strip()
