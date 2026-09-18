from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

import requests

from . import NAME
from .config import groq_key, ollama_model, openai_key, openai_model
from .memory import Memory
from .personality import SYSTEM_PROMPT, style
from .skills import apps, blender, coding, files, media, phone, system, web
from .skills.base import Result
from .stt import is_stop_listen


@dataclass
class Reply:
    text: str
    stop_listen: bool = False
    client_action: dict[str, Any] | None = None

TOOLS: dict[str, Callable[..., Result]] = {}


def _register(name: str, fn: Callable[..., Result]) -> None:
    TOOLS[name] = fn


_register("open_app", lambda name, extra_args=None: apps.open_app(name, extra_args))
_register("close_app", lambda name: apps.close_app(name))
_register("open_vscode", lambda path=None: coding.open_vscode(path))
_register(
    "write_code",
    lambda language="python", filename=None, content=None, project_name="jd60_project": coding.write_and_open(
        language, filename, content, project_name
    ),
)
_register("run_python", lambda path: coding.run_python(path))
_register(
    "open_blender",
    lambda scene_intent=None, background=False: blender.open_blender(scene_intent, background),
)
_register("blender_python", lambda code: blender.run_blender_python(code))
_register("set_volume", lambda percent: system.set_volume(int(percent)))
_register("change_volume", lambda delta: system.change_volume(int(delta)))
_register("mute", lambda state=None: system.mute(state))
_register("screenshot", lambda folder=None: system.screenshot(folder))
_register("lock_pc", lambda: system.lock_pc())
_register("shutdown", lambda kind="shutdown": system.shutdown(kind))
_register("type_text", lambda text: system.type_text(text))
_register("hotkey", lambda keys: system.hotkey(*keys))
_register("system_info", lambda: system.system_info())
_register("open_path", lambda path: files.open_path(path))
_register("search_files", lambda query: files.search_files(query))
_register("list_dir", lambda path=None: files.list_dir(path))
_register("open_url", lambda url: web.open_url(url))
_register("search_web", lambda query, engine="google": web.search_web(query, engine))
_register("wiki", lambda topic: web.wiki_summary(topic))
_register("time_now", lambda: web.now())
_register("media", lambda action: media.media(action))
_register("phone_open", lambda name: phone.adb_open(name))
_register("phone_close", lambda name: phone.adb_close(name))
_register("phone_home", lambda: phone.adb_home())

TOOL_SPEC = [
    {"name": "open_app", "args": {"name": "vscode|blender|chrome|..."}},
    {"name": "close_app", "args": {"name": "app"}},
    {"name": "open_vscode", "args": {"path": "optional folder or file"}},
    {"name": "write_code", "args": {"language": "python|html|js", "filename": "", "content": "", "project_name": ""}},
    {"name": "open_blender", "args": {"scene_intent": "cube|sphere|monkey|render ...", "background": False}},
    {"name": "blender_python", "args": {"code": "bpy script"}},
    {"name": "set_volume", "args": {"percent": 0}},
    {"name": "change_volume", "args": {"delta": 10}},
    {"name": "mute", "args": {"state": True}},
    {"name": "screenshot", "args": {}},
    {"name": "lock_pc", "args": {}},
    {"name": "shutdown", "args": {"kind": "shutdown|restart|sleep"}},
    {"name": "type_text", "args": {"text": ""}},
    {"name": "hotkey", "args": {"keys": ["ctrl", "c"]}},
    {"name": "system_info", "args": {}},
    {"name": "open_path", "args": {"path": ""}},
    {"name": "search_files", "args": {"query": ""}},
    {"name": "list_dir", "args": {"path": ""}},
    {"name": "open_url", "args": {"url": ""}},
    {"name": "search_web", "args": {"query": "", "engine": "google|youtube|github|images|wikipedia"}},
    {"name": "wiki", "args": {"topic": ""}},
    {"name": "time_now", "args": {}},
    {"name": "media", "args": {"action": "play|pause|next|previous"}},
    {"name": "remember", "args": {"key": "", "value": ""}},
    {"name": "recall", "args": {"key": ""}},
]


class Brain:
    def __init__(self, memory: Memory, user_name: str) -> None:
        self.memory = memory
        self.user_name = user_name
        self.pending_danger: dict[str, Any] | None = None

    def handle(self, utterance: str, source: str = "pc") -> Reply:
        text = (utterance or "").strip()
        if not text:
            return Reply("I did not catch that.")
        self.memory.add_turn("user", text)

        stripped = self._strip_wake(text)
        if is_stop_listen(stripped):
            return self._out("Mic closed. I will wait until you open it again.", stop_listen=True)
        if self._is_confirm(stripped) and self.pending_danger:
            result = self._run(self.pending_danger["name"], self.pending_danger.get("args") or {})
            self.pending_danger = None
            return self._out(result.message)
        if self.pending_danger and self._is_cancel(stripped):
            self.pending_danger = None
            return self._out("Cancelled.")

        local = self._rule_route(stripped, source)
        if isinstance(local, Result):
            action = (local.data or {}).get("client_action")
            return self._out(local.message, client_action=action)
        if local is not None:
            return self._out(local)

        llm = self._llm_route(stripped)
        return self._out(llm)

    def _out(
        self,
        text: str,
        stop_listen: bool = False,
        client_action: dict[str, Any] | None = None,
    ) -> Reply:
        reply = style(text, self.user_name)
        self.memory.add_turn("jd60", reply)
        return Reply(reply, stop_listen=stop_listen, client_action=client_action)

    def _strip_wake(self, text: str) -> str:
        t = text.strip()
        for wake in ["hey jd60", "ok jd60", "jd60", "hey jd", "jarvis", "hey jarvis"]:
            if t.lower().startswith(wake):
                return t[len(wake) :].strip(" ,.-")
        return t

    def _is_confirm(self, text: str) -> bool:
        return text.lower() in {"yes", "yeah", "yep", "confirm", "do it", "proceed", "affirmative"}

    def _is_cancel(self, text: str) -> bool:
        return text.lower() in {"no", "cancel", "stop", "never mind", "nevermind"}

    def _run(self, name: str, args: dict[str, Any]) -> Result:
        if name == "remember":
            self.memory.remember(str(args.get("key")), str(args.get("value")))
            return Result(True, f"I will remember {args.get('key')}.")
        if name == "recall":
            return Result(True, self.memory.recall(args.get("key")))
        fn = TOOLS.get(name)
        if not fn:
            return Result(False, f"I do not have a tool named {name}.")
        try:
            return fn(**{k: v for k, v in args.items() if v is not None})
        except TypeError:
            return fn()
        except Exception as exc:
            return Result(False, f"Tool {name} failed: {exc}")

    def _danger(self, name: str, args: dict) -> str:
        self.pending_danger = {"name": name, "args": args}
        return f"That will {name.replace('_', ' ')}. Say confirm to proceed."

    def _rule_route(self, text: str) -> str | None:
        q = text.lower().strip()

        if re.search(r"\b(hello|hi|hey|good (morning|evening|afternoon))\b", q) and len(q.split()) <= 4:
            return f"Online and listening, {self.user_name}."
        if re.search(r"\b(who are you|your name|what are you)\b", q):
            return (
                f"I am {NAME}, your personal operator. I run this machine — "
                "applications, files, Blender, VS Code, media, and research."
            )
        if re.search(r"\b(help|what can you do|capabilities)\b", q):
            return (
                "I can open VS Code and scaffold code, launch Blender and build a basic scene, "
                "control volume, take screenshots, lock the PC, search the web, find files, "
                "and remember facts. Speak naturally: 'open blender and make a monkey', "
                "'open vscode and start a python project'."
            )
        if re.search(r"\b(time|date|day is it)\b", q):
            return self._run("time_now", {}).message
        if "who am i" in q or "my name" in q:
            return f"You are {self.user_name}."

        m = re.search(r"remember (?:that )?(.+?) (?:is|=) (.+)", q)
        if m:
            self.memory.remember(m.group(1).strip(), m.group(2).strip())
            return f"Logged. {m.group(1).strip()} is {m.group(2).strip()}."
        if q.startswith("recall") or q.startswith("what do you remember"):
            key = q.replace("recall", "").replace("what do you remember about", "").replace("what do you remember", "").strip()
            return self.memory.recall(key or None)

        if re.search(r"\block\b.*(pc|computer|workstation)|lock (the )?pc", q):
            return self._run("lock_pc", {}).message
        if re.search(r"\bshut ?down\b", q):
            return self._danger("shutdown", {"kind": "shutdown"})
        if re.search(r"\b(restart|reboot)\b", q):
            return self._danger("shutdown", {"kind": "restart"})
        if q in {"sleep", "go to sleep"} or re.search(
            r"\b(sleep the (pc|computer)|put (the )?(pc|computer) to sleep|hibernate)\b", q
        ):
            return self._danger("shutdown", {"kind": "sleep"})

        if "screenshot" in q or "screen shot" in q:
            return self._run("screenshot", {}).message
        if re.search(r"\bsystem (info|information|status)\b", q) or q in {"status", "diagnostics"}:
            return self._run("system_info", {}).message

        if re.search(r"\bmute\b", q):
            return self._run("mute", {"state": True}).message
        if re.search(r"\bunmute\b", q):
            return self._run("mute", {"state": False}).message
        m = re.search(r"volume (?:to |at )?(\d{1,3})", q)
        if m:
            return self._run("set_volume", {"percent": int(m.group(1))}).message
        if re.search(r"(volume|sound).*(up|increase|raise)|turn it up", q):
            return self._run("change_volume", {"delta": 10}).message
        if re.search(r"(volume|sound).*(down|decrease|lower)|turn it down", q):
            return self._run("change_volume", {"delta": -10}).message

        if re.search(r"\b(play|pause|resume)\b.*(music|song|media)?", q) and "play" in q:
            if "youtube" not in q:
                return self._run("media", {"action": "play"}).message
        if re.search(r"\bnext (track|song)\b", q):
            return self._run("media", {"action": "next"}).message
        if re.search(r"\b(previous|last) (track|song)\b", q):
            return self._run("media", {"action": "previous"}).message

        if "youtube" in q:
            topic = re.sub(r".*(youtube|search youtube for|on youtube)\s*", "", q).strip()
            topic = topic or text
            return self._run("search_web", {"query": topic, "engine": "youtube"}).message
        if re.search(r"\b(google|search the web|search for)\b", q):
            topic = re.sub(r".*(google|search the web for|search for|search)\s*", "", q).strip()
            return self._run("search_web", {"query": topic or text, "engine": "google"}).message
        if q.startswith("wiki") or "wikipedia" in q:
            topic = re.sub(r".*(wikipedia|wiki)\s*(for )?", "", q).strip()
            return self._run("wiki", {"topic": topic or text}).message
        m = re.search(r"open (https?://\S+|www\.\S+)", q)
        if m:
            return self._run("open_url", {"url": m.group(1)}).message

        if re.search(r"\b(find|search) (file|files)\b", q) or q.startswith("find file"):
            topic = re.sub(r".*(files? (named |called )?|find file |search files? for )", "", q).strip()
            return self._run("search_files", {"query": topic or text}).message
        if q.startswith("open folder") or q.startswith("open path"):
            path = text.split(" ", 2)[-1]
            return self._run("open_path", {"path": path}).message

        # Blender first (before generic open)
        if "blender" in q:
            if re.search(r"\b(close|kill|quit)\b", q):
                return self._run("close_app", {"name": "blender"}).message
            intent = None
            if re.search(r"(make|create|add|do|build|scene|cube|sphere|monkey|render|torus)", q):
                intent = text
            return self._run("open_blender", {"scene_intent": intent}).message

        # VS Code / coding
        if re.search(r"(vs ?code|visual studio code|\bcode\b)", q) and "barcode" not in q:
            if re.search(r"\b(close|kill|quit)\b", q) and "vscode" in q.replace(" ", ""):
                return self._run("close_app", {"name": "vscode"}).message
            lang = None
            for candidate in ("python", "html", "javascript", "js", "website", "web", "c "):
                if candidate.strip() in q:
                    lang = "html" if candidate in {"website", "web"} else candidate.strip()
                    break
            if lang or re.search(r"(write|scaffold|create|new project|start).*code", q) or "and code" in q:
                language = lang or "python"
                return self._run("write_code", {"language": language, "project_name": "jd60_project"}).message
            return self._run("open_vscode", {}).message

        m = re.search(r"\b(open|launch|start|run)\s+(.+)", q)
        if m:
            target = m.group(2).strip()
            target = re.sub(r"\s+for me$", "", target)
            if target:
                key, meta = apps.resolve_app(target)
                if meta or len(target.split()) <= 3:
                    return self._run("open_app", {"name": key or target}).message

        m = re.search(r"\b(close|quit|kill|exit)\s+(.+)", q)
        if m:
            target = m.group(2).strip()
            return self._run("close_app", {"name": target}).message

        return None

    def _llm_route(self, text: str) -> str:
        plan = self._ask_llm(text)
        if not plan:
            guess = self._heuristic_open(text)
            return guess or (
                "I can handle that if you phrase it as an action: open blender, "
                "open vscode and make a python file, search youtube for X, lock pc, volume 30."
            )
        if plan.get("reply") and not plan.get("tool"):
            return str(plan["reply"])
        tool = plan.get("tool")
        args = plan.get("args") or {}
        if tool == "shutdown" or (tool == "close_app" and str(args.get("name", "")).lower() in {"explorer"}):
            return self._danger(tool, args)
        if tool:
            result = self._run(str(tool), args)
            spoken = plan.get("reply")
            if spoken:
                return f"{spoken} {result.message}".strip()
            return result.message
        return str(plan.get("reply") or "Standing by.")

    def _heuristic_open(self, text: str) -> str | None:
        key, meta = apps.resolve_app(text.lower())
        if meta:
            return self._run("open_app", {"name": key}).message
        return None

    def _ask_llm(self, text: str) -> dict[str, Any] | None:
        history = self.memory.recent(6)
        user_blob = json.dumps(history, indent=2)
        prompt = (
            SYSTEM_PROMPT
            + f"\nUser name: {self.user_name}\n"
            + "Return ONLY JSON: {\"tool\": string|null, \"args\": object, \"reply\": string}\n"
            + "Available tools:\n"
            + json.dumps(TOOL_SPEC)
            + "\nRecent history:\n"
            + user_blob
            + "\nCurrent request:\n"
            + text
        )
        content = self._complete(prompt)
        if not content:
            return None
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content).rstrip("`").strip()
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return {"tool": None, "args": {}, "reply": content}
        return {"tool": None, "args": {}, "reply": content}

    def _complete(self, prompt: str) -> str | None:
        if groq_key():
            return self._chat(
                "https://api.groq.com/openai/v1/chat/completions",
                groq_key(),
                "llama-3.3-70b-versatile",
                prompt,
            )
        if openai_key():
            return self._chat(
                "https://api.openai.com/v1/chat/completions",
                openai_key(),
                openai_model(),
                prompt,
            )
        try:
            resp = requests.post(
                "http://127.0.0.1:11434/api/chat",
                json={
                    "model": ollama_model(),
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": "Return JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=8,
            )
            if resp.ok:
                return resp.json().get("message", {}).get("content")
        except requests.RequestException:
            return None
        return None

    def _chat(self, url: str, key: str, model: str, prompt: str) -> str | None:
        try:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": "Return JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return None
