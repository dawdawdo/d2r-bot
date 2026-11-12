import json

import numpy as np

from bot.recorder import DetSaver


class SyncWriter:
    def put(self, job):
        job()


def test_detsaver_writes_frame_and_meta_and_caps(tmp_path):
    t = [1_800_000_000.0]
    d = DetSaver(tmp_path, daily_cap=2, writer=SyncWriter(), clock=lambda: t[0])
    f = np.zeros((720, 1280, 3), np.uint8)
    assert d.save(f, "chest", point=(470, 266), scan_i=3)
    t[0] += 1
    assert d.save(f, "bonfire", box=(10, 20, 30, 40))
    t[0] += 1
    assert d.save(f, "chest", point=(1, 2))
    t[0] += 1
    assert not d.save(f, "chest", point=(3, 4))  # cap 2 per class per day
    metas = sorted(tmp_path.rglob("*.json"))
    assert len(metas) == 3 and len(list(tmp_path.rglob("*.jpg"))) == 3
    m = json.loads(metas[0].read_text())
    assert m == {"cls": "chest", "box": None, "point": [470, 266], "size": [1280, 720], "scan_i": 3}


def test_detsaver_counts_existing_files_after_restart(tmp_path):
    t = 1_800_000_000.0
    a = DetSaver(tmp_path, daily_cap=1, writer=SyncWriter(), clock=lambda: t)
    assert a.save(np.zeros((4, 4, 3), np.uint8), "chest", point=(1, 1))
    b = DetSaver(tmp_path, daily_cap=1, writer=SyncWriter(), clock=lambda: t + 5)
    assert not b.save(np.zeros((4, 4, 3), np.uint8), "chest", point=(1, 1))
    assert b.save(np.zeros((4, 4, 3), np.uint8), "chest_open", point=(1, 1))
