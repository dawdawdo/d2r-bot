"""Cube planning: which upgrades to transmute, given stash counts. Pure: no game, no pixels.

Stephen 2026-11-07: cube gems and runes, keep 5 of each lower gem and rune for odds and ends, runes up through
Fal; rune recipes take gems, so those come first. Recipes (offline D2R, all of them available):
  3 runes -> next rune, El..Ort; from Thul to Ko each also takes a gem (RUNE_GEM)
  3 gems -> next grade, chipped..flawless -> perfect, skulls too; up to TOP_GRADE
"""
from __future__ import annotations

RUNES = ["El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul", "Amn", "Sol", "Shael", "Dol",
         "Hel", "Io", "Lum", "Ko", "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur",
         "Ber", "Jah", "Cham", "Zod"]
COLORS = ["Amethyst", "Topaz", "Sapphire", "Emerald", "Ruby", "Diamond", "Skull"]
GRADES = ["Chipped", "Flawed", "", "Flawless", "Perfect"]


def gem(grade: str, color: str) -> str:
    return f"{grade} {color}".strip()


GEM_LADDERS = [[gem(g, c) for g in GRADES] for c in COLORS]
RUNE_GEM = {  # rune -> the gem its upgrade also takes
    "Thul": gem("Chipped", "Topaz"), "Amn": gem("Chipped", "Amethyst"), "Sol": gem("Chipped", "Sapphire"),
    "Shael": gem("Chipped", "Ruby"), "Dol": gem("Chipped", "Emerald"), "Hel": gem("Chipped", "Diamond"),
    "Io": gem("Flawed", "Topaz"), "Lum": gem("Flawed", "Amethyst"), "Ko": gem("Flawed", "Sapphire"),
}
# the gems rune recipes take: saved for them, never cubed up (the filter hides chipped and flawed gems now, so
# the stash can't get more)
FOR_RUNES = set(RUNE_GEM.values())
KEEP = 5
STACK_MAX = 99  # a stash stack holds 99 (Stephen 2026-10-31); a result past that stays in the cube and stops cubing
TOP_RUNE = "Fal"  # the highest rune cubing makes
TOP_GRADE = "Flawless"  # the highest gem grade cubing makes (Stephen keeps flawless gems: Lo+ upgrades take them)


def plan(counts: dict[str, int], keep: int = KEEP, top: str = TOP_RUNE,
         top_grade: str = TOP_GRADE, stack_max: int = STACK_MAX) -> list[tuple[dict[str, int], str]]:
    """Transmutes in order, each ({input: n}, output). `counts` names runes and gems as in RUNES / gem();
    missing names count 0. Runes first, bottom up, so what one step makes feeds the next; gems after, with
    whatever the runes left, except gems saved for runes (FOR_RUNES); repeated until nothing changes."""
    have = dict(counts)
    steps: list[tuple[dict[str, int], str]] = []

    def n(name: str) -> int:
        return have.get(name, 0)

    def do(inputs: dict[str, int], out: str) -> None:
        for k, v in inputs.items():
            have[k] = n(k) - v
        have[out] = n(out) + 1
        steps.append((inputs, out))

    last = RUNES.index(top)
    grades = GRADES.index("" if top_grade == "Normal" else top_grade) + 1
    while True:
        before = len(steps)
        for i in range(last):
            rune, nxt = RUNES[i], RUNES[i + 1]
            g = RUNE_GEM.get(rune)
            while n(rune) - 3 >= keep and (g is None or n(g) - 1 >= keep) and n(nxt) < stack_max:
                do({rune: 3, g: 1} if g else {rune: 3}, nxt)
        for ladder in GEM_LADDERS:
            for low, high in zip(ladder[:grades], ladder[1:grades]):
                while low not in FOR_RUNES and n(low) - 3 >= keep and n(high) < stack_max:
                    do({low: 3}, high)
        if len(steps) == before:
            return steps
