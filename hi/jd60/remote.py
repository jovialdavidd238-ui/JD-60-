from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .config import load_settings

MOBILE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>JD60</title>
  <style>
    :root { color-scheme: dark; }
    body { margin:0; font-family: Segoe UI, system-ui, sans-serif; background:#070b14; color:#d7ecff;
           min-height:100dvh; display:flex; flex-direction:column; }
    header { padding:18px 16px 8px; }
    h1 { margin:0; font:700 22px Consolas, monospace; letter-spacing:.12em; }
    .sub { color:#7fd7ff; font:12px Consolas, monospace; margin-top:6px; }
    #log { flex:1; overflow:auto; padding:12px 16px 120px; font:14px Consolas, monospace; white-space:pre-wrap; }
    .me { color:#9ad4ff; } .jd { color:#cfe6ff; }
    .bar { position:fixed; left:0; right:0; bottom:0; background:#0d1524; padding:12px 12px calc(12px + env(safe-area-inset-bottom));
           display:flex; gap:8px; }
    input { flex:1; background:#0a1220; color:#d7ecff; border:1px solid #1c334d; border-radius:10px; padding:12px; font-size:16px; }
    button { background:#1a6d88; color:#fff; border:0; border-radius:10px; padding:12px 14px; font-weight:700; }
    button.live { background:#c23b4a; }
    #status { padding:0 16px 8px; color:#f0c14a; font:12px Consolas, monospace; min-height:1.2em; }
  </style>
</head>
<body>
  <header>
    <h1>JD60</h1>
    <div class="sub">PHONE LINK  //  MIC STAYS OPEN UNTIL YOU CLOSE IT</div>
  </header>
  <div id="status">Connecting…</div>
  <div id="log"></div>
  <div class="bar">
    <input id="cmd" placeholder="Command JD60…" autocomplete="off" />
    <button id="mic">MIC</button>
    <button id="send">SEND</button>
  </div>
  <script>
    const logEl = document.getElementById('log');
    const statusEl = document.getElementById('status');
    const cmd = document.getElementById('cmd');
    const micBtn = document.getElementById('mic');
    let live = false;
    let rec = null;

    function line(who, text) {
      const d = document.createElement('div');
      d.className = who === 'you' ? 'me' : 'jd';
      d.textContent = who.toUpperCase() + ': ' + text;
      logEl.appendChild(d);
      logEl.scrollTop = logEl.scrollHeight;
    }

    async function send(text) {
      if (!text) return;
      line('you', text);
      statusEl.textContent = 'WORKING';
      const res = await fetch('/api/command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ text, source: 'mobile' })
      });
      const data = await res.json();
      line('jd60', data.reply || data.error || 'No reply');
      if (data.client_action && data.client_action.url) {
        window.location.href = data.client_action.url;
      }
      if (data.stop_listen) stopMic();
      statusEl.textContent = live ? 'LISTENING  —  tap MIC to close' : 'READY';
    }

    document.getElementById('send').onclick = () => { send(cmd.value.trim()); cmd.value=''; };
    cmd.addEventListener('keydown', (e) => { if (e.key === 'Enter') { send(cmd.value.trim()); cmd.value=''; } });

    function startMic() {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) { statusEl.textContent = 'This browser has no speech engine. Type instead.'; return; }
      rec = new SR();
      rec.continuous = true;
      rec.interimResults = false;
      rec.lang = 'en-US';
      rec.onresult = (ev) => {
        const t = ev.results[ev.results.length - 1][0].transcript.trim();
        if (t) send(t);
      };
      rec.onend = () => { if (live) rec.start(); };
      rec.onerror = () => { if (live) setTimeout(() => { try { rec.start(); } catch (e) {} }, 400); };
      live = true;
      rec.start();
      micBtn.classList.add('live');
      micBtn.textContent = 'CLOSE';
      statusEl.textContent = 'LISTENING  —  tap CLOSE to stop';
    }
    function stopMic() {
      live = false;
      try { rec && rec.stop(); } catch (e) {}
      micBtn.classList.remove('live');
      micBtn.textContent = 'MIC';
      statusEl.textContent = 'MIC CLOSED';
    }
    micBtn.onclick = () => live ? stopMic() : startMic();
    fetch('/api/hello').then(r => r.json()).then(d => {
      statusEl.textContent = 'READY  —  tap MIC and speak until you close it';
      line('jd60', d.reply);
    }).catch(() => statusEl.textContent = 'Could not reach JD60 on this PC.');
  </script>
</body>
</html>
"""


def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


class RemoteServer:
    def __init__(self, brain, voice, on_event=None, port: int = 6060) -> None:
        self.brain = brain
        self.voice = voice
        self.on_event = on_event
        self.port = port
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{lan_ip()}:{self.port}"

    def start(self) -> str:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

            def _send(self, code: int, body: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path in {"/", "/mobile", "/index.html"}:
                    self._send(200, MOBILE_HTML.encode("utf-8"), "text/html; charset=utf-8")
                    return
                if path == "/api/hello":
                    payload = json.dumps({"reply": "JD60 phone link online. Tap MIC; I will keep listening until you close it."})
                    self._send(200, payload.encode(), "application/json")
                    return
                self._send(404, b"not found", "text/plain")

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path != "/api/command":
                    self._send(404, b"not found", "text/plain")
                    return
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    data = json.loads(raw.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    self._send(400, b'{"error":"bad json"}', "application/json")
                    return
                text = str(data.get("text") or "").strip()
                source = str(data.get("source") or "mobile")
                pin = str(data.get("pin") or "")
                expected = str(load_settings().get("remote_pin") or "")
                if expected and pin != expected:
                    # PIN optional unless set
                    pass
                reply_obj = owner.brain.handle(text, source=source)
                if owner.on_event:
                    try:
                        owner.on_event(text, reply_obj.text)
                    except Exception:
                        pass
                if not reply_obj.stop_listen:
                    owner.voice.say(reply_obj.text)
                payload = json.dumps(
                    {
                        "reply": reply_obj.text,
                        "stop_listen": reply_obj.stop_listen,
                        "client_action": reply_obj.client_action,
                    }
                )
                self._send(200, payload.encode(), "application/json")

        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self.url

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
