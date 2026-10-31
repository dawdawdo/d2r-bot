"""Game settings the bot depends on, set through the game's own menus (never by writing files).

Stephen plays Blizzaga by hand too and changes options (2026-10-31: automap "Mini Map Right" + no fade,
his own "Looting" filter, difficulty scaling 3). At session start the bot reads Settings.json and
lootfilter.json (read only) and puts back what it needs:
- automap Full Screen (AutoMapMode 0) with Center opacity (AutoMapFade 1): Durance odometry reads its lines;
- the loot filter profile `loot.filter_name` for the character (labels = what the bot picks up);
- /players (Settings "Offline Difficulty Scaling"): typed only when the setting differs.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)

TEMPLATES = Path(__file__).parent / "assets" / "templates"
CHAT_REGION = (0, 530, 220, 90)  # full-res (x, y, w, h) around the "[Game]" chat input line

# Main menu -> Options -> Gameplay, paged down once (click on the scrollbar track). Client coords, live
# 2026-10-31. The arrows cycle (wrapping) in an order that isn't the stored number, and the Opacity choices
# depend on the Size (Center only with Full Screen; minimaps offer No/Custom/Auto). So: Size first, then
# Opacity, one left-arrow click at a time, Apply (the menu stays open) and re-read Settings.json.
OPTIONS_BUTTON = (132, 292)
GAMEPLAY_TAB = (730, 110)
PAGE_DOWN = (927, 480)
APPLY = (472, 618)
ARROW_LEFT_X = 706
OPTION_ROWS = {"AutoMapMode": 300, "AutoMapFade": 334}  # y of "Automap Size" / "Automap Opacity"
WANT = {"AutoMapMode": 0, "AutoMapFade": 1}  # Full Screen, Center (in this order)

# In game: Esc -> Loot Filter -> profile dropdown. Entries: "Select a Profile", then the .fltr names
# sorted (live 2026-10-31: LK Bot at y 134, Looting at y 148).
LOOT_FILTER_CLOSE = (950, 56)
PROFILE_DROPDOWN = (540, 108)
PROFILE_ROW0_Y, PROFILE_ROW_H = 121, 13.3


def save_dir(cfg: dict) -> Path:
    return Path(os.path.expandvars(cfg["paths"]["save_dir"]))


def read_settings(cfg: dict) -> dict:
    try:
        return json.loads((save_dir(cfg) / "Settings.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        log.warning("Settings.json unreadable: %s", e)
        return {}


def loot_profile(cfg: dict) -> str | None:
    try:
        d = json.loads((save_dir(cfg) / "lootfilter.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return d.get("Profiles", {}).get(cfg["game"]["character"])


def profiles(cfg: dict) -> list[str]:
    return sorted(p.stem for p in save_dir(cfg).glob("*.fltr"))


def players_setting(cfg: dict) -> int | None:
    v = read_settings(cfg).get("Offline Difficulty Scaling")
    return int(v) if v is not None else None


_CHAT: list = []


def chat_open(frame: np.ndarray) -> bool:
    if not _CHAT:
        _CHAT.append(cv2.imread(str(TEMPLATES / "chat_input.png")))
    x, y, w, h = CHAT_REGION
    return float(cv2.matchTemplate(frame[y : y + h, x : x + w], _CHAT[0], cv2.TM_CCOEFF_NORMED).max()) >= 0.8


def ensure_options(bot) -> bool:
    """At the main menu: automap Full Screen + Center opacity. True if they're right (now or already)."""
    cfg = bot.cfg
    cur = read_settings(cfg)
    if all(cur.get(k) == v for k, v in WANT.items()):
        return True
    log.info("game options: setting %s (was %s)", WANT, {k: cur.get(k) for k in WANT})
    bot.click(*OPTIONS_BUTTON)
    bot.kill.sleep(1.5)
    bot.click(*GAMEPLAY_TAB)
    bot.kill.sleep(1.0)
    bot.click(*PAGE_DOWN)
    bot.kill.sleep(0.6)
    for k, v in WANT.items():
        for _ in range(6):
            if read_settings(cfg).get(k) == v:
                break
            bot.click(ARROW_LEFT_X, OPTION_ROWS[k])
            bot.kill.sleep(0.4)
            bot.click(*APPLY)
            bot.kill.sleep(1.2)
    bot.press("esc")
    bot.kill.sleep(1.0)
    now = read_settings(cfg)
    ok = all(int(now.get(k, -1)) == v for k, v in WANT.items())
    if not ok:
        bot.save_failure("options_not_set")
        log.warning("game options still %s", {k: now.get(k) for k in WANT})
    return ok


def ensure_loot_filter(bot) -> bool:
    """In game (no menu open): select the bot's loot filter profile if another one is active."""
    cfg = bot.cfg
    want = cfg["loot"]["filter_name"]
    have = loot_profile(cfg)
    if have == want:
        return True
    names = profiles(cfg)
    if want not in names:
        log.warning("loot filter %r not found in %s", want, names)
        return False
    log.info("loot filter: %s -> %s", have, want)
    bot.press("esc")
    bot.kill.sleep(1.0)
    bot.click(*bot.cfg["ui"]["esc_loot_filter"])
    bot.kill.sleep(1.5)
    bot.click(*PROFILE_DROPDOWN)
    bot.kill.sleep(1.0)
    bot.click(PROFILE_DROPDOWN[0], round(PROFILE_ROW0_Y + PROFILE_ROW_H * (names.index(want) + 1)))
    bot.kill.sleep(1.0)
    bot.click(*LOOT_FILTER_CLOSE)  # closes the filter window; the Paused menu stays
    bot.kill.sleep(0.8)
    bot.press("esc")
    bot.kill.sleep(0.8)
    ok = loot_profile(cfg) == want
    if not ok:
        bot.save_failure("loot_filter_not_set")
        log.warning("loot filter still %s", loot_profile(cfg))
    return ok
