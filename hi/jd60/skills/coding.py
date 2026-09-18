from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ..config import PROJECTS_DIR
from .apps import find_executable, resolve_app
from .base import Result

TEMPLATES: dict[str, tuple[str, str]] = {
    "python": (
        "main.py",
        'def main() -> None:\n    print("Hello from JD60")\n\n\nif __name__ == "__main__":\n    main()\n',
    ),
    "html": (
        "index.html",
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"UTF-8\" />\n  <title>JD60 Project</title>\n  <style>body{font-family:Segoe UI,sans-serif;background:#0b1220;color:#d7e7ff;display:grid;place-items:center;height:100vh;margin:0}h1{letter-spacing:.2em}</style>\n</head>\n<body>\n  <h1>JD60 ONLINE</h1>\n</body>\n</html>\n",
    ),
    "javascript": (
        "app.js",
        "console.log('JD60 project ready');\n",
    ),
    "c": (
        "main.c",
        '#include <stdio.h>\nint main(void) {\n    printf("Hello from JD60\\n");\n    return 0;\n}\n',
    ),
}


def _code_exe() -> str | None:
    _, meta = resolve_app("vscode")
    if not meta:
        return shutil.which("code")
    return find_executable(meta) or shutil.which("code")


def open_vscode(path: str | None = None) -> Result:
    exe = _code_exe()
    target = path or str(PROJECTS_DIR)
    if not exe:
        return Result(False, "VS Code was not found on this PC.")
    subprocess.Popen([exe, target], shell=False)
    return Result(True, f"Opening VS Code at {target}.", {"path": target})


def write_and_open(
    language: str,
    filename: str | None = None,
    content: str | None = None,
    project_name: str = "jd60_project",
) -> Result:
    lang = language.lower().strip()
    if lang in {"js", "node"}:
        lang = "javascript"
    if lang in {"web", "website", "html5"}:
        lang = "html"
    if lang in {"py", "python3"}:
        lang = "python"

    folder = PROJECTS_DIR / project_name
    folder.mkdir(parents=True, exist_ok=True)

    if content and filename:
        dest = folder / filename
        dest.write_text(content, encoding="utf-8")
    else:
        default_name, default_body = TEMPLATES.get(lang, TEMPLATES["python"])
        dest = folder / (filename or default_name)
        dest.write_text(content or default_body, encoding="utf-8")

    opened = open_vscode(str(dest))
    if not opened.ok:
        os.startfile(str(dest))  # type: ignore[attr-defined]
        return Result(True, f"Created {dest} and opened it.")
    return Result(True, f"Scaffolded {dest} and opened it in VS Code.", {"file": str(dest)})


def run_python(path: str) -> Result:
    target = Path(path)
    if not target.exists():
        return Result(False, f"{path} does not exist.")
    completed = subprocess.run(["python", str(target)], capture_output=True, text=True)
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return Result(False, f"Python exited with an error:\n{output[-1500:]}")
    return Result(True, output or "Script finished with no output.")
