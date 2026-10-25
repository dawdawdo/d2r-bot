"""Logging setup: console + timestamped file in logs/."""
from __future__ import annotations

import logging
import time
from pathlib import Path

_FMT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(log_dir: str | Path | None = None, level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FMT))
    root.addHandler(console)
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / time.strftime("bot-%Y%m%d-%H%M%S.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(_FMT))
        root.addHandler(fh)
    return logging.getLogger("bot")
