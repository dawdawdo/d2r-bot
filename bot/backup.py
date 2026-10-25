"""Copy the D2R save folder to backups/<timestamp>/. Read-only on the source."""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

log = logging.getLogger(__name__)


def backup_saves(save_dir: str | Path, backup_root: str | Path) -> Path:
    save_dir = Path(save_dir)
    if not save_dir.is_dir():
        raise FileNotFoundError(f"save dir not found: {save_dir}")
    dest = Path(backup_root) / time.strftime("%Y%m%d-%H%M%S")
    n = 1
    while dest.exists():
        dest = dest.with_name(f"{dest.name.split('_')[0]}_{n}")
        n += 1
    shutil.copytree(save_dir, dest)
    count = sum(1 for p in dest.rglob("*") if p.is_file())
    log.info("backed up %d files from %s to %s", count, save_dir, dest)
    return dest
