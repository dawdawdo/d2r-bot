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


ROUTE = FIX / "route"


def test_stairs_click_from_the_recorded_view():
    from bot.durance import stairs_click

    ref = cv2.imread(str(ROUTE / "001.jpg"))
    x, y = stairs_click(ref, ref)
    assert abs(x - 636) <= 10 and abs(y - 251) <= 10  # phase correlation has a ~half canvas px bias
    assert stairs_click(ref, cv2.imread(str(ROUTE / "000.jpg"))) is None  # 5800 px away: no match


def test_level_from_the_area_name():
    from bot.durance import durance_level

    assert [durance_level(cv2.imread(str(ROUTE / f"{n}.jpg"))) for n in ("000", "001", "002", "final")] == [2, 2, 3, 3]
    assert durance_level(cv2.imread(str(FIX / "hop_up_before.png"))) is None  # automap off: no name


def test_stairs_view_places_east_on_the_search_canvas():
    """Stephen held the right button (one click logged for ~10 teleports): the stand spot comes from the
    canvas, not the clicks. Needs the search canvas (maps/, not in fixtures): skipped without it."""
    import pytest

    from bot.durance import STAIRS, view_mask

    folder = FIX.parent.parent / "maps" / "blizzaga_hell" / "durance2_auto"
    if not (folder / "automap.npz").exists():
        pytest.skip("no search canvas")
    odo = AutomapOdometer.load(folder)
    pos, resp = odo.localize(view_mask(cv2.imread(str(ROUTE / "001.jpg"))), (5000, 500))
    assert resp > 0.3 and abs(pos[0] - STAIRS["stand"][0]) < 60 and abs(pos[1] - STAIRS["stand"][1]) < 60
