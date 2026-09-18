# JD60

Personal JARVIS-class operator for this Windows PC. Talk or type; JD60 opens apps, drives VS Code and Blender, controls volume, finds files, and searches the web.

## Start

```powershell
cd "C:\Users\JOVIAL DAVID\OneDrive\Desktop\cursor\hi"
python -m pip install -r requirements.txt
python -m jd60
```

Or double-click `run_jd60.bat`.

- HUD (default): type in the bar or press **MIC** (needs internet for speech-to-text).
- Terminal: `python -m jd60 --cli`
- Voice in terminal: `python -m jd60 --cli --voice`
- Silent: `python -m jd60 --silent`

## What to say

- `open vscode and start a python project`
- `open blender and make a monkey`
- `open blender and render a cube`
- `open chrome` / `open discord` / `open spotify`
- `set volume to 30` / `mute` / `take a screenshot` / `lock the pc`
- `search youtube for blender donut tutorial`
- `find files named resume`
- `remember that project folder is C:\work` then `recall project folder`

Shutdown and restart ask for **confirm**.

## Make him smarter

Copy `.env.example` to `.env` and add a **Groq** or **OpenAI** key. Without a key, built-in skills still run; conversation on unknown requests is more limited unless [Ollama](https://ollama.com) is running locally.

Change how he addresses you in `.jd60/settings.json`:

```json
{ "user_name": "David" }
```
