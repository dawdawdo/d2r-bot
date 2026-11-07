from pathlib import Path

import cv2

from bot.vision import stack_count as sc

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "stash"

# 2026-11-07 12:30, read by eye from crops magnified 6x
GEMS = [[12, 13, 19, 14, 2, 11, 6], [20, 16, 20, 17, 12, 17, 15], [22, 29, 27, 17, 19, 26, 24],
        [62, 59, 57, 52, 58, 53, 46], [1, 0, 2, 1, 18, 3, 54]]  # skulls: the picture hides the tens
RUNES = [6, 7, 20, 5, 28, 21, 31, 17, 33,  # El..Ort
         13, 34, 28, 18, 34, 17, 18, 14, 8,  # Thul..Ko; a rune's 1 is dim, magnify to see it
         4, 5, 8]  # Fal, Lem, Pul
# Ith, Tal, Ral, Hel checked live: 9 of each moved into the cube (Lem: 5). runes_counts2: after Tir -> Nef once and
# Eth -> Ith 3 times
RUNES2 = [6, 7, 17, 6, 19, 24, 31, 17, 33, 13, 34, 28, 18, 34, 17, 18, 14, 8, 4, 5, 8]


def test_gem_counts():
    got = sc.read_tab(cv2.imread(str(FIX / "gems_counts.png")), "gems")
    want = {(r, c): n for r, row in enumerate(GEMS) for c, n in enumerate(row)}
    assert {k: v for k, v in got.items() if v != want[k]} == {}


def test_rune_counts_up_to_pul():
    got = sc.rune_counts(cv2.imread(str(FIX / "runes_counts.png")))
    from bot.cube import RUNES as NAMES
    wrong = {n: (got[n], w) for n, w in zip(NAMES, RUNES) if got[n] != w}
    assert wrong == {}


def test_rune_counts_after_cubing():
    got = sc.rune_counts(cv2.imread(str(FIX / "runes_counts2.png")))
    from bot.cube import RUNES as NAMES
    wrong = {n: (got[n], w) for n, w in zip(NAMES, RUNES2) if got[n] != w}
    assert wrong == {}