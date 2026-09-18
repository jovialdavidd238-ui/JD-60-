from __future__ import annotations

import argparse
import sys

from .brain import Brain
from .config import load_settings
from .memory import Memory
from .personality import greet
from .stt import Ears
from .tts import Voice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jd60", description="JD60 personal operator")
    parser.add_argument("--cli", action="store_true", help="Terminal mode instead of HUD")
    parser.add_argument("--silent", action="store_true", help="Disable spoken replies")
    parser.add_argument("--voice", action="store_true", help="CLI: listen after each prompt")
    args = parser.parse_args(argv)

    settings = load_settings()
    user = settings.get("user_name", "sir")
    memory = Memory()
    brain = Brain(memory, user)
    voice = Voice()
    if args.silent:
        voice.enabled = False

    if not args.cli:
        from .hud import HUD

        app = HUD(brain, voice, user)
        app.mainloop()
        return 0

    hello = greet(user)
    print(f"JD60: {hello}")
    voice.say(hello, block=False)
    ears = Ears() if args.voice else None
    while True:
        try:
            if ears:
                print("JD60: listening…")
                line = ears.listen()
                print(f"You: {line}")
            else:
                line = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJD60: Offline.")
            return 0
        if not line:
            continue
        if line.lower() in {"exit", "quit", "offline"}:
            print("JD60: Shutting the interface.")
            return 0
        reply = brain.handle(line)
        print(f"JD60: {reply}")
        voice.say(reply, block=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
