"""Keeps the bot running unattended: sessions back to back, backoff on trouble, remote control.

  python -m bot.supervisor            # runs until Ctrl+C; the bot itself still stops on F12

What should run lives in logs/desired.json ({"run": true, "tasks": "meph"}), written by `--start/--stop`, the local
web page, or the remote hook. The supervisor only ever starts `python -m bot.run`; everything in-game stays there.

- A session that ends on its own (150 runs done) starts again right away.
- F12 (or a stop request) sets run=false: a person asked for it, so stay stopped until told otherwise.
- Failure streaks / quick deaths (D2R won't start: an update or login prompt) back off 5 min, doubling to 1 h.
- A bot whose status.json hasn't moved for HANG_S is killed; the next session's start recovers the game.

Remote hook (optional, `remote.url` in config.local.yaml): every REMOTE_EVERY_S, POST status JSON to the URL with
`Authorization: Bearer <token>` (token in `remote.token_file`); the reply may carry {"desired": {...}} and/or
{"command": "stop_now" | "stop_after_run"}. Outbound HTTPS only: nothing listens on GLaDOS.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import platform
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import control
from .config import ROOT, load_config

log = logging.getLogger("bot.supervisor")
DESIRED = ROOT / "logs" / "desired.json"
SUP_STATUS = ROOT / "logs" / "supervisor.json"
BOT_OUT = ROOT / "logs" / "supervisor_bot.out"
RUNS_CSV = ROOT / "runs.csv"
LOOT_CSV = ROOT / "logs" / "loot.csv"
TICK_S = 5
HANG_S = 20 * 60          # a Meph run times out at 7 min; 20 min without a status update = stuck
QUICK_S = 180             # a session shorter than this with no run done counts as "didn't start"
BACKOFF_S = (300, 600, 1200, 2400, 3600)
REMOTE_EVERY_S = 30
SESSION_RUNS = 150
DEFAULT = {"run": False, "tasks": "meph", "mode": "chests", "max_fail_streak": 4}


def read_desired() -> dict:
    try:
        return {**DEFAULT, **json.loads(DESIRED.read_text())}
    except (OSError, ValueError):
        return dict(DEFAULT)


def write_desired(**changes) -> dict:
    d = {**read_desired(), **changes, "updated": time.time()}
    DESIRED.parent.mkdir(exist_ok=True)
    tmp = DESIRED.with_suffix(".tmp")
    tmp.write_text(json.dumps(d))
    os.replace(tmp, DESIRED)
    return d


def tail_csv(path: Path, n: int) -> list[dict]:
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))[-n:]
    except OSError:
        return []


def tail_lines(path: Path, n: int) -> list[str]:
    try:
        return path.read_text(errors="replace").splitlines()[-n:]
    except OSError:
        return []


class Supervisor:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.proc: subprocess.Popen | None = None
        self.started = 0.0
        self.out_offset = 0
        self.fails = 0              # sessions in a row that ended badly
        self.backoff_until = 0.0
        self.state = "idle"
        self.last_end = ""
        self.remote_at = 0.0
        r = (cfg.get("remote") or {})
        self.remote_url = r.get("url")
        self.remote_synced = False
        tf = r.get("token_file")
        self.remote_token = Path(tf).expanduser().read_text().strip() if tf and Path(tf).expanduser().exists() else ""

    # -- sessions -------------------------------------------------------------------------------------
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def other_bot(self) -> bool:
        """A bot this supervisor didn't start (a terminal, the local web page) is running: never start a second."""
        st = control.read_status()
        mine = self.proc.pid if self.running() else None
        return (st.get("state") == "running" and st.get("pid") != mine
                and time.time() - float(st.get("updated", 0) or 0) < HANG_S)

    def start(self, d: dict) -> None:
        cmd = [sys.executable, "-m", "bot.run", "--mode", d["mode"], "--tasks", d["tasks"],
               "--runs", str(SESSION_RUNS), "--max-fail-streak", str(d["max_fail_streak"])]
        BOT_OUT.parent.mkdir(exist_ok=True)
        self.out_offset = BOT_OUT.stat().st_size if BOT_OUT.exists() else 0
        self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=open(BOT_OUT, "ab"), stderr=subprocess.STDOUT)
        self.started = time.time()
        self.state = "running"
        log.info("session started: %s (pid %d)", " ".join(cmd[3:]), self.proc.pid)

    def session_output(self) -> str:
        try:
            with open(BOT_OUT, "rb") as f:
                f.seek(self.out_offset)
                return f.read().decode(errors="replace")
        except OSError:
            return ""

    def ended(self) -> None:
        """The bot process exited: decide what comes next."""
        code = self.proc.returncode if self.proc else None
        out = self.session_output()
        took = time.time() - self.started
        runs_done = len(re.findall(r"run \d+/\d+ (?:ok|fail|chicken)", out))
        self.proc = None
        if "stopped by kill switch" in out or "stop requested" in out:
            why = "F12" if "stopped by kill switch" in out else "stop request"  # every session logs "kill switch armed"
            log.info("session stopped on purpose (%s): staying stopped", why)
            write_desired(run=False, stopped_by=why)
            self.fails, self.last_end = 0, f"stopped ({why})"
            self.state = "stopped"
            return
        bad = code != 0 and ("failures in a row" in out or (took < QUICK_S and not runs_done) or "Traceback" in out)
        if bad:
            self.fails += 1
            wait = BACKOFF_S[min(self.fails, len(BACKOFF_S)) - 1]
            self.backoff_until = time.time() + wait
            last = [ln for ln in out.splitlines() if "ERROR" in ln or "Error" in ln][-1:] or ["(no error line)"]
            self.last_end = f"failed ({self.fails} in a row): {last[0][-160:]}"
            self.state = "backoff"
            log.warning("session ended badly after %.0f s (%s); next try in %d min", took, self.last_end, wait // 60)
        else:
            self.fails, self.last_end = 0, f"ended normally after {took / 60:.0f} min"
            self.state = "idle"
            log.info("session ended normally after %.0f min", took / 60)

    def stop(self, now: bool) -> None:
        if self.running():
            control.request("now" if now else "after_run")
            log.info("asked the bot to stop %s", "now" if now else "after this run")

    def check_hang(self) -> None:
        st = control.read_status()
        upd = float(st.get("updated", 0) or 0)
        if self.running() and upd and time.time() - max(upd, self.started) > HANG_S:
            log.error("no status update for %d min: killing the bot (pid %d)", HANG_S // 60, self.proc.pid)
            self.proc.kill()
            self.proc.wait(timeout=30)
            self.ended()

    # -- remote ---------------------------------------------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "machine": platform.node(), "ts": time.time(),
            "supervisor": {"state": self.state, "fails": self.fails, "backoff_until": self.backoff_until,
                           "last_end": self.last_end, "pid": self.proc.pid if self.running() else None},
            "desired": read_desired(), "bot": control.read_status(),
            "runs": tail_csv(RUNS_CSV, 30 if self.remote_synced or not self.remote_url else 1000),  # 1st: backfill
            "loot": [ln for ln in tail_lines(LOOT_CSV, 40)],
        }

    def remote(self) -> None:
        if not self.remote_url or time.time() - self.remote_at < REMOTE_EVERY_S:
            return
        self.remote_at = time.time()
        req = urllib.request.Request(self.remote_url, data=json.dumps(self.snapshot(), default=str).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "d2r-bot-supervisor/1",
                                              "Authorization": f"Bearer {self.remote_token}"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                reply = json.loads(resp.read() or b"{}")
        except Exception as e:  # the site being down must never stop the bot
            log.debug("remote check-in failed: %s", e)
            return
        self.remote_synced = True
        want = reply.get("desired")
        if isinstance(want, dict):
            keep = {k: want[k] for k in ("run", "tasks", "mode", "max_fail_streak") if k in want}
            cur = read_desired()
            if keep.get("run"):
                keep["stopped_by"] = None  # started from the site: an old F12 no longer applies
            if any(cur.get(k) != v for k, v in keep.items()):
                log.info("remote: desired %s", keep)
                write_desired(**keep, set_by="remote")
        cmd = reply.get("command")
        if cmd in ("stop_now", "stop_after_run"):
            log.info("remote: %s", cmd)
            write_desired(run=False, set_by="remote")
            self.stop(now=cmd == "stop_now")

    # -- loop -----------------------------------------------------------------------------------------
    def write_status(self) -> None:
        tmp = SUP_STATUS.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.snapshot()["supervisor"] | {"updated": time.time()}))
        os.replace(tmp, SUP_STATUS)

    def f12_seen(self, d: dict) -> bool:
        """F12 ended a session (ours or one started elsewhere) after the last desired change: stay stopped."""
        st = control.read_status()
        upd = float(st.get("updated", 0) or 0)
        return (st.get("state") == "idle" and "kill switch" in (st.get("tally") or {})
                and upd > float(d.get("updated", 0) or 0))

    def tick(self) -> None:
        d = read_desired()
        if self.proc is not None and self.proc.poll() is not None:
            self.ended()
            d = read_desired()
        if d["run"] and not self.running() and self.f12_seen(d):
            log.info("F12 ended the last session: staying stopped")
            d = write_desired(run=False, stopped_by="F12")
        self.check_hang()
        if d["run"] and not self.running():
            if self.other_bot():
                self.state = "busy (another bot is running)"
            elif time.time() >= self.backoff_until:
                self.start(d)
            else:
                self.state = "backoff"
        elif not d["run"] and self.running() and control.read() is None:
            self.stop(now=False)
        elif not d["run"] and not self.running():
            self.state = "stopped" if d.get("stopped_by") else "idle"
        self.remote()
        self.write_status()

    def loop(self) -> None:
        log.info("supervisor up (remote %s)", self.remote_url or "off")
        while True:
            try:
                self.tick()
            except Exception:
                log.exception("supervisor tick failed")
            time.sleep(TICK_S)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", metavar="TASKS", help="set desired: run these tasks (e.g. meph, lk, lk,meph) and exit")
    ap.add_argument("--stop", action="store_true", help="set desired: stop after the current run, and exit")
    a = ap.parse_args(argv)
    if a.start:
        print(write_desired(run=True, tasks=a.start, stopped_by=None, set_by="cli"))
        return 0
    if a.stop:
        print(write_desired(run=False, set_by="cli"))
        return 0
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(ROOT / "logs" / "supervisor.log"), logging.StreamHandler()])
    Supervisor(load_config()).loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
