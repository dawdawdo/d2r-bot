"""Withdraw gold from the shared stash and resurrect the merc at Asheara now (dev helper).

  python tools/revive_now.py

New Hell game -> Act 3 -> town walk to the stash -> withdraw `stash.withdraw_gold` -> save & exit -> new game -> Asheara:
Resurrect -> save & exit. For when runs keep failing the revive because she carries no gold (deaths drop it) and the
run loop's withdrawal comes after its revive try (2026-11-22: "Resurrect Waheed: 50000" with 0 gold, all evening).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import state  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import (leave_other_act, merc_alive, restart_in_act3, revive_merc, spawn_act, walk_chain,  # noqa: E402
                      walk_route, withdraw_gold)
from bot.vision.screen import ScreenClassifier  # noqa: E402


def to_act3(bot, cfg) -> None:
    ensure_main_menu(bot)
    create_game(bot, cfg["game"]["difficulty"])
    bot.wait_for("in_game", 10)
    act = spawn_act(bot)
    if act == 4:
        restart_in_act3(bot)
    elif act != 3:
        leave_other_act(bot, act)


def main() -> int:
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    ok = False
    try:
        to_act3(bot, cfg)
        if merc_alive(bot):
            print("merc already alive", flush=True)
            return 0
        state.save({**state.load(), "gold_needed": True})
        tcfg = cfg["town"]
        gave_up = walk_chain(bot, tcfg["route"], tcfg["route_disp"]) if tcfg.get("route_disp") else 0
        if gave_up is not None:
            walk_route(bot, tcfg["route"][gave_up:] if tcfg.get("route_disp") else tcfg["route"])
        print("withdrew" if withdraw_gold(bot) else "withdraw FAILED", flush=True)
        save_and_exit(bot)
        for attempt in range(3):
            to_act3(bot, cfg)
            ok = revive_merc(bot) or merc_alive(bot)
            save_and_exit(bot)
            print(f"revive attempt {attempt + 1}: {'alive' if ok else 'still dead'}", flush=True)
            if ok:
                break
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
