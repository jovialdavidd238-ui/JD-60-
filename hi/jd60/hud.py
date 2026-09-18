from __future__ import annotations

import threading
from datetime import datetime

import customtkinter as ctk

from . import NAME, __version__
from .brain import Brain
from .personality import greet
from .stt import Ears
from .tts import Voice


class HUD(ctk.CTk):
    def __init__(self, brain: Brain, voice: Voice, user_name: str) -> None:
        super().__init__()
        self.brain = brain
        self.voice = voice
        self.user_name = user_name
        self.ears = Ears()
        self.listening = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title(f"{NAME}  ·  personal operator")
        self.geometry("980x640")
        self.minsize(820, 540)
        self.configure(fg_color="#070b14")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="#0d1524", corner_radius=0, height=78)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        self.orb = ctk.CTkLabel(header, text="●", text_color="#3de0ff", font=("Segoe UI", 28))
        self.orb.grid(row=0, column=0, padx=(22, 8), pady=18)
        title = ctk.CTkLabel(
            header,
            text=f"{NAME}  //  JARVIS-CLASS INTERFACE",
            font=("Consolas", 20, "bold"),
            text_color="#d4ecff",
        )
        title.grid(row=0, column=1, sticky="w")
        self.status = ctk.CTkLabel(
            header,
            text="SYSTEMS NOMINAL",
            font=("Consolas", 12),
            text_color="#7fd7ff",
        )
        self.status.grid(row=0, column=2, padx=22)

        chips = ctk.CTkFrame(self, fg_color="transparent")
        chips.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 0))
        for i, (label, cmd) in enumerate(
            [
                ("VS Code", "open vscode and start a python project"),
                ("Blender cube", "open blender and make a cube"),
                ("Screenshot", "take a screenshot"),
                ("Volume 40", "set volume to 40"),
                ("Lock PC", "lock the pc"),
            ]
        ):
            btn = ctk.CTkButton(
                chips,
                text=label,
                width=140,
                height=32,
                fg_color="#132033",
                hover_color="#1c334d",
                text_color="#b9dcff",
                command=lambda c=cmd: self.submit(c),
            )
            btn.grid(row=0, column=i, padx=6)

        self.log = ctk.CTkTextbox(
            self,
            font=("Consolas", 14),
            fg_color="#0a1220",
            text_color="#cfe6ff",
            wrap="word",
        )
        self.log.grid(row=2, column=0, sticky="nsew", padx=16, pady=12)
        self.log.configure(state="disabled")

        bar = ctk.CTkFrame(self, fg_color="#0d1524")
        bar.grid(row=3, column=0, sticky="ew", padx=0, pady=0)
        bar.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            bar,
            placeholder_text="Command JD60…  e.g. open blender and make a monkey",
            height=42,
            font=("Segoe UI", 14),
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=14)
        self.entry.bind("<Return>", lambda _e: self.submit())

        self.mic = ctk.CTkButton(
            bar,
            text="MIC",
            width=80,
            height=42,
            fg_color="#123348",
            command=self.toggle_listen,
        )
        self.mic.grid(row=0, column=1, pady=14)
        send = ctk.CTkButton(
            bar,
            text="SEND",
            width=90,
            height=42,
            fg_color="#1a6d88",
            command=self.submit,
        )
        send.grid(row=0, column=2, padx=(8, 16), pady=14)

        self.after(200, self._boot)

    def _boot(self) -> None:
        hello = greet(self.user_name)
        self._write("JD60", hello)
        self.voice.say(hello)

    def _write(self, who: str, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"[{stamp}] {who}: {text}\n\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_status(self, text: str, color: str = "#7fd7ff") -> None:
        self.status.configure(text=text, text_color=color)
        self.orb.configure(text_color=color)

    def submit(self, preset: str | None = None) -> None:
        text = preset if preset is not None else self.entry.get().strip()
        if not text:
            return
        if preset is None:
            self.entry.delete(0, "end")
        self._write(self.user_name.upper(), text)
        self.set_status("THINKING", "#f0c14a")
        threading.Thread(target=self._work, args=(text,), daemon=True).start()

    def _work(self, text: str) -> None:
        try:
            reply = self.brain.handle(text)
        except Exception as exc:
            reply = f"Internal fault: {exc}"
        self.after(0, lambda: self._finish(reply))

    def _finish(self, reply: str) -> None:
        self._write("JD60", reply)
        self.set_status("SYSTEMS NOMINAL", "#7fd7ff")
        self.voice.say(reply)

    def toggle_listen(self) -> None:
        if self.listening:
            return
        self.listening = True
        self.set_status("LISTENING", "#3de0ff")
        self.mic.configure(fg_color="#1a6d88")
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            heard = self.ears.listen()
        except Exception as exc:
            heard = ""
            err = str(exc)
            self.after(0, lambda: self._write("JD60", err))
        self.listening = False
        self.after(0, lambda: self.mic.configure(fg_color="#123348"))
        if heard:
            self.after(0, lambda: self.submit(heard))
        else:
            self.after(0, lambda: self.set_status("SYSTEMS NOMINAL", "#7fd7ff"))
