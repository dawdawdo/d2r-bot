from bot import armory


def test_latest_backup_needs_a_shared_stash(tmp_path, monkeypatch):
    monkeypatch.setattr(armory, "ROOT", tmp_path)
    for name, stash in [("20261110-090900", True), ("20261110-093008", False), ("filter-20261111-000000", True)]:
        d = tmp_path / "backups" / name
        d.mkdir(parents=True)
        if stash:
            (d / armory.STASH).write_bytes(b"")
    assert armory.latest_backup({"paths": {"backups": "backups"}}).name == "20261110-090900"


def test_due_waits_for_quiet_saves_and_a_gap():
    snap = {"Blizzaga.d2s": [1_000 * 10**9, 2000]}
    assert not armory.due(snap, {"saves": {"Blizzaga.d2s": [1_000 * 10**9, 2000]}}, 2_000)  # unchanged
    assert not armory.due(snap, {}, 1_000 + armory.QUIET_S - 1)  # the game may still be writing
    assert armory.due(snap, {}, 1_000 + armory.QUIET_S)
    assert not armory.due(snap, {"at": 1_000}, 1_000 + armory.QUIET_S)  # built too recently
    assert armory.due(snap, {"at": 1_000 - armory.MIN_GAP_S}, 1_000 + armory.QUIET_S)


def test_live_copy_takes_characters_and_stash(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir()
    for name in ("Smoked.d2s", armory.STASH, "Smoked.ma1", "Settings.json",
                 "ModernSharedStashSoftCoreV2.sync-conflict-20261127-115944-LBBRA7D.d2i"):
        (saves / name).write_bytes(b"x")
    folder, state = armory.live_copy({"paths": {"save_dir": saves}}, tmp_path / "live")
    assert sorted(p.name for p in folder.iterdir()) == [armory.STASH, "Smoked.d2s"]
    assert sorted(state) == [armory.STASH, "Smoked.d2s"]


def _run_build(tmp_path, cur, prev):
    import json
    import shutil
    import subprocess
    import sys

    shutil.copy(armory.A / "build.py", tmp_path / "build.py")
    (tmp_path / "armory.html").write_text("__DATA__")
    (tmp_path / "pagedata.json").write_text(json.dumps(cur))
    (tmp_path / "prev.json").write_text(json.dumps(prev))
    subprocess.run([sys.executable, "build.py"], cwd=tmp_path, check=True, capture_output=True)
    return json.loads((tmp_path / "pagedata.json").read_text())


def test_build_stamps_new_items_and_keeps_news(tmp_path):
    chron = {"u": [1, 2], "s": [1, 2], "rw": ["Spirit"], "rwn": 99, "mu": ["A"], "ms": []}
    ring = {"n": "Raven Frost", "b": "Ring", "q": "Unique", "il": 80, "e": 0}
    old = {"n": "Shako", "b": "Shako", "q": "Unique", "il": 70, "e": 0, "nt": 5}
    prev = {"snap": 1, "items": [old], "runes": {"Ber": 0}, "chron": chron,
            "news": [{"t": 10**15, "runes": {"Ist": 1}, "u": [], "s": [], "rw": []}]}
    cur = {"snap": 2, "items": [dict(old, nt=None), ring], "runes": {"Ber": 1},
           "chron": dict(chron, rw=["Spirit", "Wisdom"])}
    d = _run_build(tmp_path, cur, prev)
    shako, rf = d["items"]
    assert shako["nt"] == 5            # carried from the previous build
    assert rf["nt"] >= d["built"] - 60_000  # first seen in this build
    ev = d["news"][-1]
    assert ev["runes"] == {"Ber": 1} and ev["rw"] == ["Wisdom"]
    assert d["news"][0]["runes"] == {"Ist": 1}  # older news kept
