"""bot/savewatch.py: a D2R left open while Syncthing changed the saves must be closed before a session plays."""
import os

import pytest

from bot import savewatch


@pytest.fixture
def saves(tmp_path):
    d = tmp_path / "saves"
    d.mkdir()
    (d / "Smoked.d2s").write_bytes(b"a" * 10)
    (d / "ModernSharedStashSoftCoreV2.d2i").write_bytes(b"b" * 20)
    (d / "Smoked.ma1").write_bytes(b"c")  # not cached state: ignored
    (d / "ModernSharedStashSoftCoreV2.sync-conflict-20261127-115944-LBBRA7D.d2i").write_bytes(b"d")
    return d


def cfg(d):
    return {"paths": {"save_dir": d}}


def test_snapshot_keeps_only_saves(saves):
    assert sorted(savewatch.snapshot(saves)) == ["ModernSharedStashSoftCoreV2.d2i", "Smoked.d2s"]


def test_unchanged_saves_keep_the_game(saves, tmp_path):
    snap = tmp_path / "snap.json"
    savewatch.record(saves, snap)
    closed = []
    assert not savewatch.ensure_fresh_game(cfg(saves), lambda: True, lambda: closed.append(1) or True, snap)
    assert not closed


def test_save_changed_under_an_open_game_closes_it(saves, tmp_path):
    snap = tmp_path / "snap.json"
    savewatch.record(saves, snap)
    st = (saves / "Smoked.d2s").stat()
    (saves / "Smoked.d2s").write_bytes(b"x" * 12)  # Syncthing brought Singularity's newer Smoked
    os.utime(saves / "Smoked.d2s", ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    assert savewatch.changed_since_recorded(saves, snap) == ["Smoked.d2s"]
    closed = []
    assert savewatch.ensure_fresh_game(cfg(saves), lambda: True, lambda: closed.append(1) or True, snap)
    assert closed


def test_no_snapshot_with_an_open_game_closes_it(saves, tmp_path):
    assert savewatch.ensure_fresh_game(cfg(saves), lambda: True, lambda: True, tmp_path / "none.json")


def test_closed_game_needs_nothing(saves, tmp_path):
    assert not savewatch.ensure_fresh_game(cfg(saves), lambda: False, lambda: pytest.fail("closed"),
                                           tmp_path / "none.json")


def test_game_that_wont_close_stops_the_session(saves, tmp_path):
    with pytest.raises(RuntimeError):
        savewatch.ensure_fresh_game(cfg(saves), lambda: True, lambda: False, tmp_path / "none.json")
