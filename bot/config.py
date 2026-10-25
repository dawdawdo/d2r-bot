"""Load config.yaml into a plain dict with expanded paths."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    paths = cfg.setdefault("paths", {})
    for key, value in paths.items():
        p = Path(os.path.expandvars(os.path.expanduser(str(value))))
        paths[key] = p if p.is_absolute() else ROOT / p
    return cfg
