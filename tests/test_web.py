import base64
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from bot import control
from bot.web import server


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "CONTROL", tmp_path / "control.txt")
    monkeypatch.setattr(control, "STATUS", tmp_path / "status.json")
    monkeypatch.setattr(server, "PASSWORD_FILE", tmp_path / "pw.txt")
    monkeypatch.setattr(server, "BOT_OUT", tmp_path / "bot.out")
    started = []

    class FakeProc:
        pid = 4242

        def poll(self):
            return None

    monkeypatch.setattr(server.subprocess, "Popen", lambda cmd, **kw: started.append(cmd) or FakeProc())
    monkeypatch.setattr(server, "BOT", server.BotProcess())
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", server.password(), started
    srv.shutdown()


def call(base, path, pw, body=None):
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                 method="GET" if body is None else "POST")
    if pw is not None:
        req.add_header("Authorization", "Basic " + base64.b64encode(f"x:{pw}".encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_needs_password(web):
    base, pw, _ = web
    assert call(base, "/", None)[0] == 401
    assert call(base, "/", "wrong")[0] == 401
    code, body = call(base, "/", pw)
    assert code == 200 and b"D2R Bot" in body


def test_status_lists_tasks(web):
    base, pw, _ = web
    code, body = call(base, "/api/status", pw)
    d = json.loads(body)
    assert code == 200 and d["bot"]["running"] is False
    assert {t["name"]: t["ready"] for t in d["tasks"]} == {"lk": True, "meph": True}  # Durance 2 graph learned


def test_start_validates_and_launches_once(web):
    base, pw, started = web
    assert call(base, "/api/start", pw, {"tasks": ["nope"], "runs": 5})[0] == 400  # unknown task
    assert call(base, "/api/start", pw, {"tasks": [], "runs": 5})[0] == 400
    assert call(base, "/api/start", pw, {"tasks": ["lk"], "runs": 5, "minutes": 30})[0] == 200
    assert started[0][1:] == ["-m", "bot.run", "--mode", "chests", "--tasks", "lk", "--runs", "5", "--max-minutes", "30.0"]
    code, body = call(base, "/api/start", pw, {"tasks": ["lk"], "runs": 5})
    assert code == 400 and b"already running" in body


def test_stop_writes_the_request(web):
    base, pw, _ = web
    assert call(base, "/api/stop", pw, {"mode": "now"})[0] == 400  # nothing running
    call(base, "/api/start", pw, {"tasks": ["lk"], "runs": 5})
    assert call(base, "/api/stop", pw, {"mode": "after_run"})[0] == 200
    assert control.read() == "after_run"
    assert call(base, "/api/stop", pw, {"mode": "sometime"})[0] == 400
