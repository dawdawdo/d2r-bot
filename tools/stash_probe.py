"""Dev helper: stash actions one at a time, a screenshot after each. Stays in the game (in town) between calls.

  python tools/stash_probe.py enter                 # new game, walk to the stash, open it
  python tools/stash_probe.py shot NAME             # save scratch/probe/NAME.png
  python tools/stash_probe.py click X Y [mod] NAME  # mod: none|shift|ctrl|right
  python tools/stash_probe.py exit                  # esc, save & exit
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import open_stash, walk_chain, walk_route  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "scratch" / "probe"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cmd, args = sys.argv[1], sys.argv[2:]
    s = start_session(backup=cmd == "enter")
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    name = args[-1] if args else cmd
    try:
        if cmd == "enter":
            ensure_main_menu(bot)
            create_game(bot, cfg["game"]["difficulty"])
            bot.wait_for("in_game", 10)
            tcfg = cfg["town"]
            gave_up = walk_chain(bot, tcfg["route"], tcfg["route_disp"]) if tcfg.get("route_disp") else 0
            if gave_up is not None:
                walk_route(bot, tcfg["route"][gave_up:] if tcfg.get("route_disp") else tcfg["route"])
            if not open_stash(bot):
                return 1
        elif cmd == "click":
            x, y = int(args[0]), int(args[1])
            mod = args[2] if len(args) > 3 else "none"
            if mod == "right":
                bot.click(x, y, button="right")
            else:
                keys = [] if mod == "none" else mod.split("+")
                for k in keys:
                    bot.input.key_down(k)
                    bot.kill.sleep(0.05)
                bot.click(x, y)
                for k in reversed(keys):
                    bot.kill.sleep(0.05)
                    bot.input.key_up(k)
        elif cmd == "cube":  # cube N: at most N transmutes, with the stash open
            from bot.cubing import cube_stash
            cfg.setdefault("cube", {})["max_transmutes"] = int(args[0])
            print("transmutes:", cube_stash(bot))
        elif cmd == "hover":
            bot.input.move(int(args[0]), int(args[1]))
        elif cmd == "exit":
            bot.press("esc")
            bot.kill.sleep(0.4)
            save_and_exit(bot)
            return 0
        bot.kill.sleep(0.6)
        cv2.imwrite(str(OUT / f"{name}.png"), b.capture.grab())
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
