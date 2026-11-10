from bot import armory


def test_latest_backup_needs_a_shared_stash(tmp_path, monkeypatch):
    monkeypatch.setattr(armory, "ROOT", tmp_path)
    for name, stash in [("20261110-090900", True), ("20261110-093008", False), ("filter-20261111-000000", True)]:
        d = tmp_path / "backups" / name
        d.mkdir(parents=True)
        if stash:
            (d / armory.STASH).write_bytes(b"")
    assert armory.latest_backup({"paths": {"backups": "backups"}}).name == "20261110-090900"
