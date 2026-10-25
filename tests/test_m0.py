import re
import threading
import time
from pathlib import Path

import numpy as np
import pytest

from bot.backup import backup_saves
from bot.config import ROOT, load_config
from bot.io import GuardedInput
from bot.io.fake import FakeCapture, FakeHotkeys, FakeInput
from bot.killswitch import KillSwitch, KillSwitchTripped
from bot.session import start_session


def test_config_loads_and_expands_paths():
    cfg = load_config()
    assert cfg["game"]["resolution"] == [1280, 720]
    assert cfg["hotkeys"]["kill_switch"] == "f12"
    assert cfg["paths"]["backups"].is_absolute()
    assert "%USERPROFILE%" not in str(cfg["paths"]["save_dir"])


def test_killswitch_check_and_sleep():
    k = KillSwitch()
    k.check()
    threading.Timer(0.05, k.trip, args=("test",)).start()
    t0 = time.monotonic()
    with pytest.raises(KillSwitchTripped):
        k.sleep(5)
    assert time.monotonic() - t0 < 1
    with pytest.raises(KillSwitchTripped):
        k.check()


def test_guarded_input_blocks_after_trip_but_releases():
    k = KillSwitch()
    inner = FakeInput()
    inp = GuardedInput(inner, k)
    inp.key_down("alt")
    inp.click(10, 20)
    k.trip()
    with pytest.raises(KillSwitchTripped):
        inp.click(1, 1)
    with pytest.raises(KillSwitchTripped):
        inp.press("1")
    inp.release_all()
    assert inner.held == set()
    assert ("click", 1, 1, "left") not in inner.events


def test_session_hotkey_trips_killswitch(tmp_path):
    cfg = load_config()
    cfg["paths"]["logs"] = tmp_path / "logs"
    hk = FakeHotkeys()
    s = start_session(cfg, backup=False, hotkeys=hk)
    assert not s.kill.tripped
    hk.fire("f12")
    assert s.kill.tripped
    s.close()


def test_backup_copies_without_touching_source(tmp_path):
    src = tmp_path / "saves"
    src.mkdir()
    (src / "Char.d2s").write_bytes(b"\x55\xaa" * 10)
    (src / "Settings.json").write_text("{}")
    before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in src.iterdir()}
    dest = backup_saves(src, tmp_path / "backups")
    dest2 = backup_saves(src, tmp_path / "backups")
    assert dest != dest2
    assert (dest / "Char.d2s").read_bytes() == b"\x55\xaa" * 10
    after = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in src.iterdir()}
    assert before == after


def test_backup_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_saves(tmp_path / "nope", tmp_path / "b")


def test_fake_capture_region():
    frame = np.arange(720 * 1280 * 3, dtype=np.uint32).astype(np.uint8).reshape(720, 1280, 3)
    cap = FakeCapture([frame])
    sub = cap.grab((100, 50, 30, 20))
    assert sub.shape == (20, 30, 3)
    assert (sub == frame[50:70, 100:130]).all()


FORBIDDEN = re.compile(r"^\s*(import|from)\s+(pydirectinput|mss|win32\w*|pywintypes|pynput)\b", re.M)


def test_platform_imports_only_in_bot_io():
    offenders = []
    for py in list((ROOT / "bot").rglob("*.py")) + list((ROOT / "tools").rglob("*.py")):
        if (ROOT / "bot" / "io") in py.parents:
            continue
        text = py.read_text(encoding="utf-8")
        if FORBIDDEN.search(text) or "ctypes.windll" in text:
            offenders.append(str(py.relative_to(ROOT)))
    assert offenders == []
