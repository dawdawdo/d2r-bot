"""Route recording on the live Durance 2 frames of test_durance (hops (300, 0), (300, 0), (0, -200))."""
import json
from pathlib import Path

import cv2

from bot.durance import AutomapOdometer
from bot.io.fake import FakeCapture, FakeClicks
from bot.teach import RouteRecorder

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "durance"


def test_clicks_become_steps(tmp_path):
    frames = [cv2.imread(str(FIX / f"automap_m{i}.png")) for i in range(4)]
    rec = RouteRecorder(FakeCapture(frames[1:]), AutomapOdometer(frames[0]), (100, 50), tmp_path,
                        sleep=lambda s: None)
    clicks = FakeClicks()
    clicks.start(rec.on_click)
    clicks.press(100 + 940, 50 + 330)
    clicks.press(100 + 940, 50 + 330)
    clicks.press(100 + 640, 50 + 130)
    clicks.press(5, 5)  # outside the game window: ignored
    steps = rec.finish(frames[3])
    assert [s["click"] for s in steps] == [[940, 330], [940, 330], [640, 130]]
    assert not any(s["lost"] for s in steps)
    assert 250 < steps[0]["pos"][0] < 330 and steps[2]["pos"][1] < steps[1]["pos"][1] - 60
    saved = json.loads((tmp_path / "route.json").read_text())["steps"]
    assert len(saved) == 3 and (tmp_path / saved[0]["view"]).exists() and (tmp_path / "views/final.jpg").exists()
