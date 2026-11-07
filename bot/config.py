"""Load config.yaml, plus this machine's config.local.yaml if it has one, into a plain dict with expanded paths."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.yaml"


def _merge(base: dict, over: dict) -> dict:
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    """config.local.yaml sits beside `path` and isn't in git: what differs per machine (game and save paths)."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    local = path.with_name(f"{path.stem}.local{path.suffix}")
    if local.exists():
        _merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    if "risk" in cfg:  # one switch for what trades her safety for speed (config.yaml risk_levels)
        _merge(cfg, cfg["risk_levels"][cfg["risk"]])
    paths = cfg.setdefault("paths", {})
    for key, value in paths.items():
        p = Path(os.path.expandvars(os.path.expanduser(str(value))))
        paths[key] = p if p.is_absolute() else ROOT / p
    return cfg
