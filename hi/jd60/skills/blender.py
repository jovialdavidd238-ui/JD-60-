from __future__ import annotations

import subprocess
import time

from ..config import JOBS_DIR
from .apps import find_executable, resolve_app
from .base import Result


def _blender() -> str | None:
    _, meta = resolve_app("blender")
    return find_executable(meta) if meta else None


def _script_for(intent: str) -> str:
    q = intent.lower()
    extras = ""
    if "sphere" in q:
        extras = "bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0))\n"
    elif "monkey" in q or "suzanne" in q:
        extras = "bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 0))\n"
    elif "torus" in q:
        extras = "bpy.ops.mesh.primitive_torus_add(location=(0, 0, 0))\n"
    elif "plane" in q:
        extras = "bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0))\n"
    else:
        extras = "bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))\n"

    light = ""
    if "light" in q or "render" in q:
        light = "bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))\n"

    camera = ""
    if "camera" in q or "render" in q:
        camera = (
            "bpy.ops.object.camera_add(location=(7, -7, 5))\n"
            "cam = bpy.context.object\n"
            "cam.rotation_euler = (1.1, 0, 0.8)\n"
            "bpy.context.scene.camera = cam\n"
        )

    render = ""
    if "render" in q:
        out = (JOBS_DIR / "render.png").as_posix()
        render = (
            f"bpy.context.scene.render.filepath = r'{out}'\n"
            "bpy.ops.render.render(write_still=True)\n"
        )

    return (
        "import bpy\n"
        "bpy.ops.object.select_all(action='SELECT')\n"
        "bpy.ops.object.delete(use_global=False)\n"
        + extras
        + light
        + camera
        + render
    )


def open_blender(scene_intent: str | None = None, background: bool = False) -> Result:
    exe = _blender()
    if not exe:
        return Result(False, "Blender was not found. Install it and I can drive it.")

    args = [exe]
    if scene_intent:
        script = JOBS_DIR / f"job_{int(time.time())}.py"
        script.write_text(_script_for(scene_intent), encoding="utf-8")
        if background:
            args += ["--background", "--python", str(script)]
        else:
            args += ["--python", str(script)]
        subprocess.Popen(args, shell=False)
        return Result(
            True,
            f"Opening Blender and applying: {scene_intent}.",
            {"script": str(script)},
        )

    subprocess.Popen(args, shell=False)
    return Result(True, "Launching Blender.")


def run_blender_python(code: str) -> Result:
    exe = _blender()
    if not exe:
        return Result(False, "Blender was not found.")
    script = JOBS_DIR / f"custom_{int(time.time())}.py"
    script.write_text(code, encoding="utf-8")
    subprocess.Popen([exe, "--python", str(script)], shell=False)
    return Result(True, "Sent a custom Python job into Blender.", {"script": str(script)})
