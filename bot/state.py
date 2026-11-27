"""Small persistent bot state (logs/state.json): things we track but can't cheaply read off the screen."""
from __future__ import annotations

import json

from .config import ROOT

PATH = ROOT / "logs" / "state.json"


def use(character: str, default: str) -> None:
    """Per-character state: the default character (Blizzaga) keeps logs/state.json, others logs/state_<name>.json (a
    corpse flag, key count or inventory baseline belongs to whoever is playing)."""
    global PATH
    PATH = ROOT / "logs" / ("state.json" if character == default else f"state_{character}.json")


def load() -> dict:
    try:
        return json.loads(PATH.read_text())
    except (OSError, ValueError):
        return {}


def save(state: dict) -> None:
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(state, indent=1))
