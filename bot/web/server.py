"""Web page for the bot: pick tasks, start, stop, watch. Standard library only.

  python -m bot.web            # then open http://127.0.0.1:8765 (user: any, password: logs/web_password.txt)

The bot itself runs as a separate process (python -m bot.run ...), so the page stays responsive and a
crash on either side doesn't take the other down. They talk through logs/control.txt and
logs/status.json (bot/control.py). F12 is still the emergency stop.
"""
from __future__ import annotations

import base64
import csv
import hmac
import json
import logging
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .. import chronicle, control
from ..config import ROOT, load_config
from ..io import window_info
from ..tasks import catalog

log = logging.getLogger("bot.web")
PAGE = Path(__file__).with_name("index.html")
PASSWORD_FILE = ROOT / "logs" / "web_password.txt"
BOT_OUT = ROOT / "logs" / "web_bot.out"
RUNS_CSV = ROOT / "runs.csv"
LOOT_CSV = ROOT / "logs" / "loot.csv"
STALE_S = 300  # a "running" status older than this (and no process of ours) means the bot died
FILTER_TOOL = ROOT / "tools" / "chronicle_filter.py"
STOPPED = (b"stopped by kill switch", b"stop requested")  # the session was ended on purpose: no LK afterwards


def password() -> str:
    if not PASSWORD_FILE.exists():
        PASSWORD_FILE.parent.mkdir(exist_ok=True)
        PASSWORD_FILE.write_text(secrets.token_urlsafe(9))
    return PASSWORD_FILE.read_text().strip()


def recent_runs(n: int = 25) -> list[dict]:
    from ..run import FIELDS

    try:
        with open(RUNS_CSV, newline="") as f:
            next(f)
            rows = list(csv.DictReader(f, FIELDS))
    except (OSError, StopIteration):
        return []
    return rows[-n:][::-1]


def recent_loot(n: int = 25) -> list[dict]:
    try:
        lines = LOOT_CSV.read_text().splitlines()
    except OSError:
        return []
    out = []
    for ln in lines[-n:][::-1]:
        when, _, item = ln.partition(",")
        out.append({"time": when, "item": item})
    return out


class BotProcess:
    """The one bot process this server may run."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.chain: threading.Thread | None = None  # "then LK" watcher: between its two processes neither runs
        self.lock = threading.Lock()

    def running(self) -> bool:
        if self.proc is not None and self.proc.poll() is None:
            return True
        if self.chain is not None and self.chain.is_alive():
            return True
        st = control.read_status()  # started by an earlier server, or from a terminal
        return st.get("state") == "running" and time.time() - float(st.get("updated", 0)) < STALE_S

    def _spawn(self, cmd: list[str]) -> subprocess.Popen:
        BOT_OUT.parent.mkdir(exist_ok=True)
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=open(BOT_OUT, "ab"), stderr=subprocess.STDOUT)
        log.info("started bot: %s (pid %d)", " ".join(cmd[1:]), proc.pid)
        return proc

    def _then_lk(self, first: subprocess.Popen, offset: int) -> None:
        """When the first stage ends by itself (full stash, too many failures), run LK. F12, the mouse or a stop
        from this page end everything. Same rule as scratch/meph_then_lk.ps1."""
        first.wait()
        try:
            with open(BOT_OUT, "rb") as f:
                f.seek(offset)
                out = f.read()
        except OSError:
            out = b""
        if any(s in out for s in STOPPED):
            log.info("session stopped on purpose: no LK")
            return
        log.info("first stage over: LK with a full stash allowed")
        self.proc = self._spawn([sys.executable, "-m", "bot.run", "--mode", "chests", "--tasks", "lk",
                                 "--runs", "9000", "--stash-full-ok"])

    def start(self, tasks: list[str], runs: int, minutes: float | None, then_lk: bool = False) -> None:
        ready = {t["name"] for t in catalog(load_config()) if t["ready"]}
        if not tasks or any(t not in ready for t in tasks):
            raise ValueError(f"pick tasks from: {', '.join(sorted(ready))}")
        if not 1 <= runs <= 10000:
            raise ValueError("runs must be 1-10000")
        with self.lock:
            if self.running():
                raise RuntimeError("the bot is already running")
            control.clear()
            cmd = [sys.executable, "-m", "bot.run", "--mode", "chests", "--tasks", ",".join(tasks), "--runs", str(runs)]
            if minutes:
                cmd += ["--max-minutes", str(minutes)]
            if then_lk:
                cmd += ["--max-fail-streak", "6"]
            offset = BOT_OUT.stat().st_size if BOT_OUT.exists() else 0
            control.write_status(state="starting", tasks=tasks, runs=runs)
            self.proc = self._spawn(cmd)
            if then_lk:
                self.chain = threading.Thread(target=self._then_lk, args=(self.proc, offset), daemon=True)
                self.chain.start()


BOT = BotProcess()


def game_open(cfg: dict) -> bool:
    return window_info(cfg["game"]["window_title"]) is not None


def chronicle_report() -> dict:
    try:
        rep = chronicle.report(load_config())
    except (OSError, ValueError, StopIteration, KeyError) as e:
        return {"error": str(e)}
    for k in ("unique_codes", "set_codes"):
        del rep[k]
    return rep


def update_filter() -> str:
    """Refuses while the game or the bot runs: the game would overwrite the file when it closes."""
    if BOT.running():
        raise RuntimeError("stop the bot first")
    if game_open(load_config()):
        raise RuntimeError("close D2R first: it would overwrite the filter when it exits")
    r = subprocess.run([sys.executable, str(FILTER_TOOL), "--install"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        lines = (r.stdout + r.stderr).strip().splitlines()
        raise RuntimeError(lines[-1] if lines else "the filter tool failed")
    return "Filter updated and installed."


class Handler(BaseHTTPRequestHandler):
    server_version = "D2RBot/1"

    def log_message(self, fmt, *args):  # quieter than the default stderr line per request
        log.debug("%s %s", self.address_string(), fmt % args)

    def _authorized(self) -> bool:
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                _, _, pw = base64.b64decode(h[6:]).decode().partition(":")
            except ValueError:
                return False
            return hmac.compare_digest(pw, password())
        return False

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, default=str).encode())

    def _guard(self) -> bool:
        if self._authorized():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="D2R bot"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self._guard():
            return
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            st = control.read_status()
            self._json(200, {"bot": {**st, "running": BOT.running(), "stop": control.read()},
                             "game_open": game_open(load_config()),
                             "tasks": catalog(load_config()), "runs": recent_runs(), "loot": recent_loot()})
        elif self.path == "/api/chronicle":
            self._json(200, chronicle_report())
        else:
            self._send(404, b"{}")

    def do_POST(self) -> None:  # noqa: N802
        if not self._guard():
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/start":
                minutes = body.get("minutes")
                BOT.start(list(body.get("tasks", [])), int(body.get("runs", 20)), float(minutes) if minutes else None,
                          bool(body.get("then_lk")))
            elif self.path == "/api/stop":
                if not BOT.running():
                    raise RuntimeError("the bot isn't running")
                control.request(body.get("mode", "after_run"))
            elif self.path == "/api/filter":
                return self._json(200, {"ok": True, "message": update_filter()})
            else:
                return self._send(404, b"{}")
        except (ValueError, RuntimeError) as e:
            return self._json(400, {"error": str(e)})
        self._json(200, {"ok": True})


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    cfg = load_config().get("web", {})
    host, port = cfg.get("host", "127.0.0.1"), int(cfg.get("port", 8765))
    srv = ThreadingHTTPServer((host, port), Handler)
    shown = "127.0.0.1" if host in ("0.0.0.0", "") else host
    print(f"D2R bot page: http://{shown}:{port}  (password: {password()}, also in {PASSWORD_FILE})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
