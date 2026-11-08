"""Make a template mask (white = compare) from bright pixels, for text drawn over scenery.

    python tools/make_mask.py difficulty.png --above 110 --rows-from 32
--rows-from N also keeps every row from N down (e.g. a dialog frame under the text).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

T = Path(__file__).resolve().parent.parent / "bot" / "assets" / "templates"

ap = argparse.ArgumentParser()
ap.add_argument("template")
ap.add_argument("--above", type=int, default=110, help="gray level counted as text")
ap.add_argument("--rows-from", type=int, help="also keep all rows from this one down")
a = ap.parse_args()
src = T / a.template
g = cv2.cvtColor(cv2.imread(str(src)), cv2.COLOR_BGR2GRAY)
m = cv2.dilate((g > a.above).astype(np.uint8), np.ones((3, 3), np.uint8))
if a.rows_from is not None:
    m[a.rows_from:] = 1
out = src.with_name(src.stem + "_mask.png")
cv2.imwrite(str(out), m * 255)
print(f"{out.name}: {m.mean():.0%} of pixels compared")
