"""Probe which model IDs the configured DeepSeek endpoint accepts.

    .venv\\Scripts\\python.exe repro\\probe_models.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://api.deepseek.com"
CANDIDATES = ["deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash", "deepseek-v4-pro",
              "deepseek-flash", "1017flash", "1017-flash"]


def key() -> str:
    for line in (os.path.join(os.path.dirname(__file__), ".env"),):
        if not os.path.exists(line):
            continue
        for ln in open(line, encoding="utf-8"):
            ln = ln.strip()
            if ln.startswith("DEEPSEEK_API_KEY="):
                return ln.split("=", 1)[1].strip()
    return os.environ.get("DEEPSEEK_API_KEY", "")


def call(k: str, path: str, payload: dict | None = None, timeout: int = 60):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
        method="POST" if payload else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def main() -> int:
    k = key()
    print("key length:", len(k), "prefix:", k[:6] if k else "-")
    st, body = call(k, "/models")
    print("[models]", st, body[:800])
    for m in CANDIDATES:
        st, body = call(k, "/chat/completions", {
            "model": m,
            "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            "max_tokens": 8,
            "temperature": 0,
            "stream": False,
        })
        preview = body.replace("\n", " ")[:200]
        print(f"[{m}] {st} {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
