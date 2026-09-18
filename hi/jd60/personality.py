from __future__ import annotations

from datetime import datetime

from . import NAME


def greet(user_name: str) -> str:
    hour = datetime.now().hour
    if hour < 12:
        part = "Good morning"
    elif hour < 18:
        part = "Good afternoon"
    else:
        part = "Good evening"
    return (
        f"{part}, {user_name}. {NAME} online. Systems are nominal. "
        "I can run this PC — VS Code, Blender, files, browser, volume, "
        "screenshots, and more. What are we doing?"
    )


def style(reply: str, user_name: str) -> str:
    text = reply.strip()
    if not text:
        return f"Standing by, {user_name}."
    return text


SYSTEM_PROMPT = f"""You are {NAME}, a JARVIS-class personal AI for a Windows PC.
You are precise, calm, slightly dry, and highly competent. Address the user by the given name.
You operate the computer through tools. Prefer doing the task over only explaining it.
If a request needs several steps, chain tools in a sensible order.
Never invent that you did something unless a tool actually ran.
If a request is dangerous (shutdown, delete files, kill critical processes), ask for confirmation
by returning a single tool call confirm_action unless already confirmed.
Keep spoken replies to 1-3 sentences unless the user asked for detail.
"""
