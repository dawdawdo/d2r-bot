"""Promote raw frames into labeled fixtures (committed to git).

  python tools/label.py town fixtures/raw/town_*_003.png [--hp 100 --mp 80] [--labels rune,unique]

Copies to fixtures/labeled/<state>/<name>.png and writes <name>.json with the expected
values that tests/test_vision_fixtures.py checks. Omitted fields are not checked.
"""
from __future__ import annotations

import argparse
import glob
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("state")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--hp", type=float)
    ap.add_argument("--mp", type=float)
    ap.add_argument("--labels", help="comma list of expected label kinds, e.g. rune,unique ('' = none)")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    dest = ROOT / "fixtures" / "labeled" / args.state
    dest.mkdir(parents=True, exist_ok=True)
    for pat in args.files:
        for src in map(Path, glob.glob(pat)):
            out = dest / src.name
            shutil.copy2(src, out)
            meta = {"state": args.state}
            if args.hp is not None:
                meta["hp"] = args.hp
            if args.mp is not None:
                meta["mp"] = args.mp
            if args.labels is not None:
                meta["labels"] = sorted(k for k in args.labels.split(",") if k)
            if args.note:
                meta["note"] = args.note
            out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
            print("labeled", out.relative_to(ROOT), meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
