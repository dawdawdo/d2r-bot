"""Regenerate the Chronicle part of the loot filter (bot/chronicle.py). The web page's button runs this too.

  python tools/chronicle_filter.py              # print the missing list, write filters/LK Bot.fltr
  python tools/chronicle_filter.py --dry-run    # print only
  python tools/chronicle_filter.py --install    # also install it (refused while D2R runs)

Starts from the live filter, so changes made in the game's editor stay.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot import chronicle as cf  # noqa: E402
from bot.config import load_config  # noqa: E402


def main() -> int:
    from install_filter import d2r_running

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--stash", type=Path)
    ap.add_argument("--tables", type=Path)
    args = ap.parse_args()
    cfg = load_config()
    if args.install and d2r_running():
        print("D2R is running: close it first (it would overwrite the filter on exit)")
        return 1
    rep = cf.report(cfg, args.stash, args.tables)
    print(f"Chronicle: uniques {rep['uniques']['found']}/{rep['uniques']['total']}, "
          f"sets {rep['sets']['found']}/{rep['sets']['total']}, runewords {rep['runewords']}")
    print(f"\n== missing sets ({len(rep['missing_sets'])}) ==")
    for r in rep["missing_sets"]:
        print(f"  {r['name']} [{r['code']}]")
    print(f"\n== missing uniques ({len(rep['missing_uniques'])}) ==")
    for r in rep["missing_uniques"]:
        print(f"  {r['name']} [{r['code']}]")
    print(f"\nbase codes: {rep['uniques']['codes']} unique, {rep['sets']['codes']} set")
    if args.dry_run:
        return 0
    src, live = cf.repo_filter(cfg), cf.live_filter(cfg)
    bak = ROOT / "backups" / f"filter-repo-{time.strftime('%Y%m%d-%H%M%S')}"
    bak.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, bak / src.name)
    new = cf.build_filter(cf.read_filter(live if live.exists() else src),
                          set(rep["unique_codes"]), set(rep["set_codes"]))
    src.write_text(json.dumps(new, indent=4) + "\n", encoding="utf-8")
    print(f"wrote {src} (old copy in {bak})")
    if args.install:
        sys.stdout.flush()
        return subprocess.call([sys.executable, str(ROOT / "tools" / "install_filter.py")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
