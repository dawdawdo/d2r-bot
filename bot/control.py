"""Bot <-> web page plumbing through two small files in logs/ (the bot runs as its own process):

- logs/control.txt: a stop request, "after_run" (finish the current run) or "now" (save & exit now).
- logs/status.json: what the bot is doing, rewritten at every run start and end.
"""
from __future__ import annotations

import json
import os
import time

from .config import ROOT
from .controller import BotError

CONTROL = ROOT / "logs" / "control.txt"
STATUS = ROOT / "logs" / "status.json"


class StopNow(BotError):
    """The web page asked to stop now: leave the game (save & exit) and end the session."""


def request(what: str) -> None:
    if what not in ("after_run", "now"):
        raise ValueError(what)
    CONTROL.parent.mkdir(exist_ok=True)
    CONTROL.write_text(what)


def read() -> str | None:
    try:
        return CONTROL.read_text().strip() or None
    except OSError:
        return None


def clear() -> None:
    try:
        CONTROL.unlink()
    except OSError:
        pass


def write_status(**fields) -> None:
    STATUS.parent.mkdir(exist_ok=True)
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps({**fields, "pid": os.getpid(), "updated": time.time()}, default=str))
    os.replace(tmp, STATUS)  # the page never reads a half-written file


def read_status() -> dict:
    try:
        return json.loads(STATUS.read_text())
    except (OSError, ValueError):
        return {"state": "idle"}
