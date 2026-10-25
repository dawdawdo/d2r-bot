"""Bot entry point.

  python -m bot.run --runs 20          # M2: create game -> save & exit, N times

Backs up saves first, arms F12, logs to logs/, appends one row per run to runs.csv.
"""
from __future__ import annotations

import argparse
import csv
import logging
import time

from .config import ROOT
from .controller import BotError, Controller
from .io import open_backend
from .killswitch import KillSwitchTripped
from .lifecycle import create_game, save_and_exit
from .session import start_session
from .vision.screen import ScreenClassifier

log = logging.getLogger("bot.run")
RUNS_CSV = ROOT / "runs.csv"
FIELDS = ["start", "duration_s", "result", "error"]


def one_run(bot: Controller, cfg: dict) -> None:
    create_game(bot, cfg["game"]["difficulty"])
    bot.kill.sleep(1.0)
    save_and_exit(bot)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--max-fail-streak", type=int, default=3)
    args = ap.parse_args()

    session = start_session()
    cfg = session.cfg
    backend = open_backend(cfg["game"]["window_title"])
    bot = Controller(backend.window, backend.capture, backend.input,
                     ScreenClassifier.from_config(cfg["vision"]["states"]), session.kill, cfg)
    backend.window.focus()
    new_file = not RUNS_CSV.exists()
    ok = streak = 0
    try:
        with open(RUNS_CSV, "a", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            if new_file:
                w.writeheader()
            for i in range(args.runs):
                t0 = time.time()
                row = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "result": "ok", "error": ""}
                try:
                    one_run(bot, cfg)
                    ok += 1
                    streak = 0
                except BotError as e:
                    row.update(result="fail", error=str(e))
                    streak += 1
                    log.error("run %d failed: %s", i + 1, e)
                row["duration_s"] = round(time.time() - t0, 1)
                w.writerow(row)
                f.flush()
                log.info("run %d/%d %s in %.1fs", i + 1, args.runs, row["result"], row["duration_s"])
                if streak >= args.max_fail_streak:
                    log.error("%d failures in a row; stopping", streak)
                    break
    except KillSwitchTripped as e:
        log.warning("stopped by kill switch: %s", e)
    finally:
        bot.release_all()
        backend.capture.close()
        session.close()
    log.info("%d/%d runs ok", ok, args.runs)
    return 0 if ok == args.runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
