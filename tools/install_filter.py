"""Install filters/LK Bot.fltr into D2R's saves folder (only while D2R is closed: the game keeps .fltr files in
memory and rewrites them on exit, so a copy made while it runs is lost).

  python tools/install_filter.py            # refuses if D2R.exe is running
  python tools/install_filter.py --dry-run  # show the rules that would change

The live copy is backed up to backups/filter-<timestamp>/ first.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.config import load_config  # noqa: E402
from bot.io import game_running  # noqa: E402


def d2r_running() -> bool:
    return game_running("D2R.exe")


def rule_names(p: Path) -> list[str]:
    return [r["name"] for r in json.loads(p.read_text(encoding="utf-8-sig"))["rules"]] if p.exists() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    name = cfg["loot"]["filter_name"]
    src = ROOT / "filters" / f"{name}.fltr"
    dst = Path(os.path.expandvars(cfg["paths"]["save_dir"])) / f"{name}.fltr"
    new, old = rule_names(src), rule_names(dst)
    print(f"{src} -> {dst}")
    print("rules added:", [n for n in new if n not in old] or "-")
    print("rules removed:", [n for n in old if n not in new] or "-")
    if args.dry_run:
        return 0
    if d2r_running():
        print("D2R is running: close it first (it would overwrite the filter on exit)")
        return 1
    if dst.exists():
        bak = ROOT / "backups" / f"filter-{time.strftime('%Y%m%d-%H%M%S')}"
        bak.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, bak / dst.name)
        print(f"backed up the live filter to {bak}")
    shutil.copy2(src, dst)
    print("installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
