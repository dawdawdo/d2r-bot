"""Classify frames and compare to the label in their filename (<label>_<stamp>.png).

  python tools/state_check.py "fixtures/raw/*.png" [--scores]

Labels that aren't screen states (e.g. town -> in_game) are mapped via ALIASES.
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.vision.screen import ScreenClassifier, match_score  # noqa: E402

ALIASES = {"town": "in_game", "lk": "in_game", "after_exit": None, "opt": None, "dropdown": None,
           "lootfilter_ui": None, "lootfilter_lkbot": None, "lootfilter_newrule": None,
           "lootfilter_items": None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern")
    ap.add_argument("--scores", action="store_true")
    args = ap.parse_args()
    clf = ScreenClassifier.from_config(load_config()["vision"]["states"])
    bad = 0
    for p in sorted(glob.glob(args.pattern)):
        f = cv2.imread(p)
        label = Path(p).stem.rsplit("_", 1)[0]
        if label.startswith("lootfilter"):
            label = "after_exit"  # panel over the game; not a distinct state yet
        want = ALIASES.get(label, label)
        got = clf.classify(f)
        ok = want is None or got == want
        bad += not ok
        line = f"{'  ' if ok else 'XX'} {Path(p).name:45s} want={want} got={got}"
        if args.scores:
            line += "  " + " ".join(f"{n}={max(match_score(f, c.template, c.region)[0] for c in cs):.2f}"
                                    for n, cs in clf.states.items())
        print(line)
    print(f"{bad} mismatches")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
