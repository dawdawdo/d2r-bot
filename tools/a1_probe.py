"""Hand-walk the Rogue Encampment step by step and save frames (to build Act 1 town services: stash, Akara, Kashya,
Charsi; Stephen 2026-11-23: Andariel runs should never go to Act 3).

  python tools/a1_probe.py game map:spawn wp map:wp click:300,200 map:nw esc exit

Steps (in order, one game per command):
  game           new Hell game; must spawn in Act 1
  wp             walk to the Act 1 waypoint (open_a1_wp), close its panel
  map:NAME       automap on, frame scratch/a1/NAME.png (automap stays on)
  shot:NAME      automap off, frame scratch/a1/NAME.png
  click:X,Y[,S]  left click (walk / talk), wait S seconds (default 1.5)
  hover:X,Y,NAME move the mouse there, frame NAME.png (automap off)
  goto:NAME[,N]  walk to the automap label NAME (akara, kashya, charsi, stash) until within N px
  poke:NAME      click where goto found NAME, frame poke_NAME.png (no dialog check)
  talk:NAME      click that NPC (after goto), frame talk_NAME.png (its dialog)
  line:N         click the Nth line below TALK in the open NPC menu (1 = the line after Talk)
  stash / akara[:buy] / kashya / charsi   the real Act 1 services (bot/a1town.py)
  esc            close an NPC menu if one is up (a1town.close_npc)
  escx           press Esc (a trade window or the stash)
  exit           save & exit (also done at the end if still in game)
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.a1town import (BODY_UP, akara_stop, charsi_repair, close_npc, npc_menu, open_stash_a1,  # noqa: E402
                        revive_merc_a1, talk, town_automap, town_map_off, walk_to)
from bot.nav import CENTER  # noqa: E402
from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import close_dialog, close_stash, open_a1_wp, spawn_act  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

OUT = ROOT / "scratch" / "a1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    s = start_session(backup=False)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()

    def map_off() -> None:
        town_map_off(bot)

    last_off: dict = {}
    try:
        for step in sys.argv[1:]:
            name, _, arg = step.partition(":")
            print(step, flush=True)
            if name == "game":
                ensure_main_menu(bot)
                create_game(bot, cfg["game"]["difficulty"])
                bot.wait_for("in_game", 10)
                bot.kill.sleep(1.0)
                act = spawn_act(bot)
                if act != 1:
                    raise BotError(f"spawned in Act {act}, not Act 1")
            elif name == "wp":
                map_off()
                open_a1_wp(bot)
                bot.kill.sleep(1.5)  # the panel opens late: an early Esc missed it (2026-11-23 probe)
                close_dialog(bot)
            elif name == "map":
                town_automap(bot)
                bot.kill.sleep(0.3)
                cv2.imwrite(str(OUT / f"{arg}.png"), bot.capture.grab())
            elif name == "shot":
                map_off()
                bot.input.move(640, 650)
                bot.kill.sleep(0.3)
                cv2.imwrite(str(OUT / f"{arg}.png"), bot.capture.grab())
            elif name == "click":
                v = [float(x) for x in arg.split(",")]
                bot.click(int(v[0]), int(v[1]))
                bot.kill.sleep(v[2] if len(v) > 2 else 1.5)
            elif name == "hover":
                x, y, n = arg.split(",")
                map_off()
                bot.input.move(int(x), int(y))
                bot.kill.sleep(0.4)
                cv2.imwrite(str(OUT / f"{n}.png"), bot.capture.grab())
            elif name == "goto":  # goto:NAME[,near]  walk to an automap label (bot/a1town.py)
                n, _, near = arg.partition(",")
                off = walk_to(bot, n, float(near or 150))
                print(f"  {n}: {off}", flush=True)
                last_off[n] = off
            elif name == "talk":  # talk:NAME  click the NPC found by goto, frame talk_NAME.png
                off = last_off.get(arg)
                if off is None:
                    raise BotError(f"no goto:{arg} before talk")
                bot.input.move(640, 650)
                loc = talk(bot, arg, off)
                bot.kill.sleep(0.3)
                cv2.imwrite(str(OUT / f"talk_{arg}.png"), bot.capture.grab())
                print(f"  dialog: {loc}", flush=True)
            elif name == "poke":  # poke:NAME  click where goto found NAME (no dialog check), frame poke_NAME.png
                off = last_off.get(arg)
                if off is None:
                    raise BotError(f"no goto:{arg} before poke")
                map_off()
                x, y = int(CENTER[0] + off[0]), int(CENTER[1] + off[1] - BODY_UP)
                print(f"  click ({x}, {y})", flush=True)
                bot.click(x, y)
                bot.kill.sleep(1.8)
                cv2.imwrite(str(OUT / f"poke_{arg}.png"), bot.capture.grab())
            elif name == "line":  # line:N  click the Nth menu line below TALK (24 px apart; Kashya's menu 2026-11-23)
                m = npc_menu(bot)
                if m is None:
                    raise BotError("no NPC menu up")
                x, y = m[0] + 20, m[1] + 6 + 24 * int(arg)
                print(f"  click line {arg} at ({x}, {y})", flush=True)
                bot.click(x, y)
                bot.kill.sleep(1.5)
            elif name == "stash":  # the real Act 1 stash opener, frame, close
                bot.act = 1
                ok = open_stash_a1(bot)
                print(f"  stash open: {ok}", flush=True)
                cv2.imwrite(str(OUT / "stash_open.png"), bot.capture.grab())
                close_stash(bot)
            elif name == "akara":  # akara:buy  the real Akara stop (heal; buy potions with :buy)
                ok = akara_stop(bot, buy=arg == "buy")
                print(f"  akara: {ok}", flush=True)
                cv2.imwrite(str(OUT / "akara_done.png"), bot.capture.grab())
            elif name == "kashya":  # the real revive (only acts if the merc is dead)
                print(f"  revive: {revive_merc_a1(bot)}", flush=True)
            elif name == "charsi":  # the real repair (needs npc_charsi.png)
                print(f"  repair: {charsi_repair(bot)}", flush=True)
            elif name == "esc":  # only when an NPC menu is up (a1town.close_npc); escx: any panel (trade, stash)
                close_npc(bot)
            elif name == "escx":
                bot.press("esc")
                bot.kill.sleep(0.4)
            elif name == "exit":
                save_and_exit(bot)
            else:
                raise BotError(f"unknown step {step}")
        print(f"frames in {OUT}", flush=True)
    except BotError as e:
        print(f"error: {e}", flush=True)
        bot.save_failure("a1_probe")
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
