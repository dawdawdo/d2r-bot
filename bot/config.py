"""Load config.yaml into a plain dict with expanded paths."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.yaml"


_WIN_VAR = re.compile(r"%([^%]+)%")


def _expand(value: str) -> str:
    """Expand ~, $VAR and Windows-style %VAR% on any OS."""
    value = _WIN_VAR.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    return os.path.expandvars(os.path.expanduser(value))


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    paths = cfg.setdefault("paths", {})
    for key, value in paths.items():
        if isinstance(value, dict):  # per-platform value, keyed by sys.platform ("win32", "linux")
            value = value[sys.platform]
        p = Path(_expand(str(value)))
        paths[key] = p if p.is_absolute() else ROOT / p
    return cfg
