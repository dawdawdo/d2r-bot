"""Make a tooltip-text template: crop the bright text of a saved tooltip crop.

  python tools/make_tt_template.py fixtures/raw/tooltip_x.png tt_chest.png
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
src, name = sys.argv[1], sys.argv[2]
im = cv2.imread(src)
g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
ys, xs = np.where(g > 130)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
# keep only the text columns that sit on the dark box (ignore sprite bleed at the edges)
dark_cols = (g < 25).mean(axis=0) > 0.3
cols = np.where(dark_cols)[0]
x0, x1 = max(x0, cols.min()), min(x1, cols.max())
t = im[max(0, y0 - 2) : y1 + 3, max(0, x0 - 2) : x1 + 3]
cv2.imwrite(str(ROOT / "bot" / "assets" / "templates" / name), t)
print(name, t.shape)
