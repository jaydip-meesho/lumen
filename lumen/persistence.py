"""Local session persistence — history stays on your machine.

Sessions are saved as JSON under ~/.lumen/sessions/ and can be resumed with
`lumen --continue` (latest for this directory) or `lumen --resume <id>`.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from lumen.config import CONFIG_DIR

SESSIONS_DIR = CONFIG_DIR / "sessions"


def new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(2).hex()


def save(session, provider: str, model: str, cwd: str) -> None:
    if not session.messages:
        return
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "id": session.id,
        "created": session.created,
        "updated": time.time(),
        "provider": provider,
        "model": model,
        "cwd": cwd,
        "prompt_tokens": session.prompt_tokens,
        "completion_tokens": session.completion_tokens,
        "cost": session.cost,
        "messages": session.messages,
    }
    (SESSIONS_DIR / f"{session.id}.json").write_text(json.dumps(data))


def load(session_id: str) -> dict | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        # allow a prefix match for convenience
        matches = sorted(SESSIONS_DIR.glob(f"{session_id}*.json"))
        if not matches:
            return None
        path = matches[-1]
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def list_recent(limit: int = 20, cwd: str | None = None) -> list[dict]:
    if not SESSIONS_DIR.exists():
        return []
    rows: list[dict] = []
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if cwd and d.get("cwd") != cwd:
            continue
        rows.append(d)
    rows.sort(key=lambda d: d.get("updated", 0), reverse=True)
    return rows[:limit]


def latest(cwd: str | None = None) -> dict | None:
    rows = list_recent(limit=1, cwd=cwd)
    return rows[0] if rows else None
