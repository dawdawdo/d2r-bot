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

from .. import control
from ..config import ROOT, load_config
from ..tasks import CATALOG

log = logging.getLogger("bot.web")
PAGE = Path(__file__).with_name("index.html")
PASSWORD_FILE = ROOT / "logs" / "web_password.txt"
BOT_OUT = ROOT / "logs" / "web_bot.out"
RUNS_CSV = ROOT / "runs.csv"
LOOT_CSV = ROOT / "logs" / "loot.csv"
STALE_S = 300  # a "running" status older than this (and no process of ours) means the bot died


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
        self.lock = threading.Lock()

    def running(self) -> bool:
        if self.proc is not None and self.proc.poll() is None:
            return True
        st = control.read_status()  # started by an earlier server, or from a terminal
        return st.get("state") == "running" and time.time() - float(st.get("updated", 0)) < STALE_S

    def start(self, tasks: list[str], runs: int, minutes: float | None) -> None:
        ready = {t["name"] for t in CATALOG if t["ready"]}
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
            BOT_OUT.parent.mkdir(exist_ok=True)
            out = open(BOT_OUT, "ab")
            control.write_status(state="starting", tasks=tasks, runs=runs)
            self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
            log.info("started bot: %s (pid %d)", " ".join(cmd[1:]), self.proc.pid)


BOT = BotProcess()


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
                             "tasks": CATALOG, "runs": recent_runs(), "loot": recent_loot()})
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
                BOT.start(list(body.get("tasks", [])), int(body.get("runs", 20)), float(minutes) if minutes else None)
            elif self.path == "/api/stop":
                if not BOT.running():
                    raise RuntimeError("the bot isn't running")
                control.request(body.get("mode", "after_run"))
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
