from __future__ import annotations

import urllib.parse
import webbrowser
from datetime import datetime

import requests

from .base import Result


def open_url(url: str) -> Result:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return Result(True, f"Opening {url}.")


def search_web(query: str, engine: str = "google") -> Result:
    engines = {
        "google": "https://www.google.com/search?q=",
        "youtube": "https://www.youtube.com/results?search_query=",
        "github": "https://github.com/search?q=",
        "images": "https://www.google.com/search?tbm=isch&q=",
        "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search=",
    }
    base = engines.get(engine, engines["google"])
    webbrowser.open(base + urllib.parse.quote(query))
    return Result(True, f"Searching {engine} for {query}.")


def wiki_summary(topic: str) -> Result:
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(topic)
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "JD60/1.0"})
        if resp.status_code != 200:
            return search_web(topic, "wikipedia")
        data = resp.json()
        extract = data.get("extract") or "No summary available."
        title = data.get("title", topic)
        return Result(True, f"{title}: {extract}", data)
    except requests.RequestException:
        return search_web(topic, "wikipedia")


def now() -> Result:
    stamp = datetime.now().strftime("%A, %B %d %Y — %I:%M %p")
    return Result(True, f"It is {stamp}.")
