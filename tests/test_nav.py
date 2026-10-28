"""Odometry jump detection and bonfire re-anchoring on synthetic frames."""
from types import SimpleNamespace

import cv2
import numpy as np

from bot.io.fake import FakeCapture
from bot.nav import Odometer, anchor_bonfire, find_fires

RNG = np.random.default_rng(0)
WORLD = cv2.GaussianBlur(RNG.integers(0, 255, (3000, 4000, 3), dtype=np.uint8), (7, 7), 0)


def view(wx: int, wy: int, fires=()) -> np.ndarray:
    """1280x720 view of WORLD with the camera at world offset (wx, wy); fires = [(sx, sy, r)]."""
    f = WORLD[1000 + wy : 1720 + wy, 1000 + wx : 2280 + wx].copy()
    for sx, sy, r in fires:
        cv2.circle(f, (sx, sy), r, (40, 160, 255), -1)  # saturated orange
    return f


def test_odometer_tracks_hops():
    odo = Odometer(view(0, 0))
    odo.update(view(200, 0))
    odo.update(view(350, 150))
    assert np.allclose(odo.pos, (350, 150), atol=4)
    assert not odo.lost


def test_odometer_flags_jump():
    odo = Odometer(view(0, 0))
    odo.update(view(900, 500))  # far beyond a hop: no usable overlap
    assert odo.lost


def test_find_fires_sizes():
    fires = find_fires(view(0, 0, [(900, 400, 20), (300, 200, 6)]))
    assert fires[0][2] > 1000 and abs(fires[0][0] - 900) < 3
    assert fires[1][2] < 300  # torch-sized


def test_anchor_bonfire_corrects_drift():
    # Bonfire at world (500, 100); camera really at (0, 0) so it shows at screen (1140, 430).
    frame = view(0, 0, [(1140, 430, 20), (700, 200, 6)])
    odo = Odometer(frame)
    odo.pos = np.array([60.0, -40.0])  # drifted
    odo.lost = True
    bot = SimpleNamespace(capture=FakeCapture([frame]))
    assert anchor_bonfire(bot, odo, (500, 100))
    assert np.allclose(odo.pos, (0, 0), atol=3)
    assert not odo.lost


def test_anchor_bonfire_none_in_view():
    frame = view(0, 0, [(700, 200, 6)])  # only a torch
    odo = Odometer(frame)
    odo.pos = np.array([10.0, 10.0])
    bot = SimpleNamespace(capture=FakeCapture([frame]), save_failure=lambda note: None)
    assert not anchor_bonfire(bot, odo, (500, 100))
    assert np.allclose(odo.pos, (10, 10), atol=3)


class SimBot:
    """Camera over WORLD that right-click teleports move; a bonfire drawn at a fixed world spot."""

    def __init__(self, cam, bonfire):
        self.cam = np.array(cam, float)
        self.bonfire = bonfire
        self.capture = SimpleNamespace(grab=self.grab)
        self.saved = []

    def grab(self):
        x, y = self.cam.round().astype(int)
        bx, by = self.bonfire[0] - x + 640, self.bonfire[1] - y + 330
        on = 0 < bx < 1280 and 0 < by < 590
        return view(x, y, [(bx, by, 20)] if on else [])

    def click(self, x, y, button="left", hover=0.08):
        self.cam += (x - 640, y - 330)

    def sleep(self, s):
        pass

    def check(self):
        pass

    def save_failure(self, note):
        self.saved.append(note)


def test_search_bonfire_recovers_lost_odometry():
    from bot.nav import search_bonfire

    bot = SimBot((0, 0), bonfire=(1250, 200))  # off screen from the start; ring 2 sees it
    odo = Odometer(bot.grab())
    odo.pos = np.array([700.0, -600.0])  # a jump left odometry far off
    odo.lost = True
    assert search_bonfire(bot, odo, (1250, 200))
    assert not odo.lost
    assert np.allclose(odo.pos, bot.cam, atol=6)


def test_search_bonfire_gives_up():
    from bot.nav import search_bonfire

    bot = SimBot((0, 0), bonfire=(9000, 9000))
    odo = Odometer(bot.grab())
    odo.lost = True
    assert not search_bonfire(bot, odo, (9000, 9000))
    assert bot.saved == ["bonfire_search_failed"]


def test_teleport_detours_stay_in_window():
    """Blocked hops rotate the step; a rotated sideways hop once right-clicked the desktop."""
    from bot.nav import teleport_to

    bot = SimBot((0, 0), bonfire=(9000, 9000))
    clicks = []
    bot.click = lambda x, y, button="left", hover=0.08: clicks.append((x, y))  # walled in: never moves
    odo = Odometer(bot.grab())
    bot.save_failure = lambda note: None
    assert not teleport_to(bot, odo, (3000, 0))
    assert len(clicks) > 4
    assert all(0 <= x < 1280 and 40 <= y < 590 for x, y in clicks), clicks


def test_odometer_ignores_zone_banner():
    """A screen-fixed banner over a low-texture world must not pin the step at zero."""
    world = (WORLD // 8).astype(np.uint8)  # dark, low contrast like LK at night

    def banner_view(wx, wy):
        f = world[1000 + wy : 1720 + wy, 1000 + wx : 2280 + wx].copy()
        cv2.putText(f, "ENTERING LOWER KURAST", (493, 173), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 60, 255), 2)
        return f

    odo = Odometer(banner_view(0, 0))
    odo.update(banner_view(0, 220))
    assert np.allclose(odo.pos, (0, 220), atol=6), odo.pos


def test_town_route_end_offset():
    """Stopped short of the usual end point (camera up-left of it): walk down-right by the difference."""
    from bot.town import route_end_offset

    off = route_end_offset(view(0, 0), view(-444, -254))
    assert np.allclose(off, (444, 254), atol=6), off
    assert np.hypot(*route_end_offset(view(0, 0), view(0, 0))) < 2


def test_hop_match():
    """Long diagonal hops give a weak peak; trust it when it agrees with the commanded hop."""
    from bot.nav import _matches_hop

    assert _matches_hop(np.array([-402.0, -257.0]), (-340, -220))
    assert not _matches_hop(np.array([-153.0, -288.0]), (-265, -220))  # a real mis-track (live 18:34)
    assert not _matches_hop(np.array([-402.0, -257.0]), None)
    assert _matches_hop(np.array([307.0, 154.0]), (378, 183))  # cut short, same line (live 23:05)
    assert _matches_hop(np.array([308.0, 173.0]), (378, 183))
    assert not _matches_hop(np.array([150.0, 150.0]), (378, 183))


def test_find_town_wp_with_npc_on_brazier():
    """Live failures: the WP was in view but an NPC on the right brazier spoiled the full match."""
    from pathlib import Path

    import cv2

    from bot.config import load_config
    from bot.town import find_town_wp

    cfg = load_config()
    img = cv2.imread(str(Path(__file__).resolve().parent.parent / "bot" / "assets" / "templates" / "town_route_end.png"))
    bot = SimpleNamespace(_templates={})
    assert find_town_wp(bot, img, cfg["town"]) == (1051, 360)


def test_dungeon_odometry_sees_through_the_light_circle():
    """Durance 2, hop (0, -199) (live 2026-10-27): the plain odometer measured (-2, 126) and lost track."""
    import cv2

    from bot.config import ROOT
    from bot.nav import Odometer

    d = ROOT / "fixtures" / "durance"
    odo = Odometer(cv2.imread(str(d / "hop_up_before.png")), dungeon=True)
    moved = odo.update(cv2.imread(str(d / "hop_up_after.png")), expect=(0, -199))
    assert abs(moved[0]) < 20 and abs(moved[1] + 211) < 20
    assert not odo.lost
