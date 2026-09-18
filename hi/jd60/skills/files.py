from __future__ import annotations

import os
from pathlib import Path

from .base import Result

SEARCH_ROOTS = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "OneDrive" / "Desktop",
]


def open_path(path: str) -> Result:
    target = Path(os.path.expandvars(os.path.expanduser(path)))
    if not target.exists():
        return Result(False, f"I cannot find {target}.")
    os.startfile(str(target))  # type: ignore[attr-defined]
    return Result(True, f"Opened {target}.")


def search_files(query: str, limit: int = 12) -> Result:
    q = query.lower()
    hits: list[str] = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "__pycache__"}]
            for name in filenames:
                if q in name.lower():
                    hits.append(str(Path(dirpath) / name))
                    if len(hits) >= limit:
                        listing = "\n".join(hits)
                        return Result(True, f"Found {len(hits)} matches:\n{listing}", {"files": hits})
    if not hits:
        return Result(False, f"No files matching '{query}' in Desktop, Documents, or Downloads.")
    listing = "\n".join(hits)
    return Result(True, f"Found {len(hits)} matches:\n{listing}", {"files": hits})


def list_dir(path: str | None = None) -> Result:
    target = Path(path) if path else Path.home() / "Desktop"
    if not target.exists():
        return Result(False, f"{target} does not exist.")
    names = sorted(os.listdir(target))[:40]
    return Result(True, f"{target}:\n" + "\n".join(names), {"entries": names})
