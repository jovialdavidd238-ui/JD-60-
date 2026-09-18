from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .config import MEMORY_PATH


class Memory:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {
            "facts": {},
            "history": [],
            "last_app": None,
            "last_project": None,
        }
        self._load()

    def _load(self) -> None:
        if MEMORY_PATH.exists():
            try:
                loaded = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
                self.data.update(loaded)
            except json.JSONDecodeError:
                pass

    def save(self) -> None:
        MEMORY_PATH.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def remember(self, key: str, value: str) -> None:
        self.data["facts"][key] = value
        self.save()

    def recall(self, key: str | None = None) -> str:
        facts = self.data.get("facts", {})
        if key:
            return str(facts.get(key, f"I have nothing stored for {key}."))
        if not facts:
            return "My long-term memory is empty so far."
        lines = [f"- {k}: {v}" for k, v in facts.items()]
        return "Stored facts:\n" + "\n".join(lines)

    def add_turn(self, role: str, text: str) -> None:
        self.data.setdefault("history", []).append(
            {"role": role, "text": text, "at": datetime.now().isoformat(timespec="seconds")}
        )
        self.data["history"] = self.data["history"][-40:]
        self.save()

    def recent(self, n: int = 8) -> list[dict]:
        return list(self.data.get("history", [])[-n:])
