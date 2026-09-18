from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Result:
    ok: bool
    message: str
    data: dict[str, Any] | None = None


SkillFn = Callable[..., Result]
