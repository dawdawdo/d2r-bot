"""Linux uinput backend, offline: fake uinput devices and a fake pointer, no real input sent."""
import sys

import pytest

if sys.platform != "linux":
    pytest.skip("Linux backend", allow_module_level=True)
pytest.importorskip("evdev")
pytest.importorskip("Xlib")

from evdev import ecodes as e  # noqa: E402

from bot.config import load_config  # noqa: E402
from bot.io.fake import FakeWindow  # noqa: E402
from bot.io.linux import KEYMAP, UinputInput, keycode  # noqa: E402


class FakeUInput:
    def __init__(self, caps, name=""):
        self.caps, self.name, self.events = caps, name, []

    def write(self, etype, code, value):
        self.events.append((etype, code, value))

    def syn(self):
        self.events.append("syn")

    def close(self):
        pass


class Pointer:
    """Simulated X pointer: lands where the device says, plus an optional fixed error."""

    def __init__(self, inp_ref, err=(0, 0)):
        self.ref, self.err = inp_ref, err

    def __call__(self):
        abs_ = [ev for ev in self.ref[0].ptr.events if ev != "syn" and ev[0] == e.EV_ABS]
        x = next(v for t, c, v in reversed(abs_) if c == e.ABS_X)
        y = next(v for t, c, v in reversed(abs_) if c == e.ABS_Y)
        return x + self.err[0], y + self.err[1]


def make(err=(0, 0), win=FakeWindow(1280, 720, x=320, y=180)):
    ref = []
    inp = UinputInput(win, screen_size=(1920, 1080), uinput_factory=FakeUInput,
                      pointer_query=Pointer(ref, err), settle=0)
    ref.append(inp)
    return inp


def abs_writes(inp):
    return [(c, v) for ev in inp.ptr.events if ev != "syn" for t, c, v in [ev] if t == e.EV_ABS]


def test_every_key_the_bot_uses_has_a_code():
    hk = load_config()["hotkeys"]
    keys = [hk["kill_switch"], hk["show_items"], hk["inventory"], *hk["potions"], *hk["skills"].values(),
            "esc", "enter", "tab", "space", "shift", "ctrl", "alt", *"/players 7"]
    for k in keys:
        assert keycode(k) in KEYMAP.values(), k
    with pytest.raises(ValueError):
        keycode("nosuchkey")


def test_devices_declare_keys_and_screen_sized_axes():
    inp = make()
    assert set(inp.kbd.caps[e.EV_KEY]) == set(KEYMAP.values())
    axes = dict(inp.ptr.caps[e.EV_ABS])
    assert axes[e.ABS_X][2] == 1919 and axes[e.ABS_Y][2] == 1079


def test_move_is_client_relative():
    inp = make()
    inp.move(100, 50)
    assert abs_writes(inp) == [(e.ABS_X, 420), (e.ABS_Y, 230)]
    assert inp.cursor_pos() == (100, 50)


def test_move_corrects_once_when_pointer_lands_off_target():
    inp = make(err=(3, -2))
    inp.move(100, 50)
    assert abs_writes(inp) == [(e.ABS_X, 420), (e.ABS_Y, 230), (e.ABS_X, 417), (e.ABS_Y, 232)]


def test_move_clamps_to_screen():
    inp = make(win=FakeWindow(1280, 720, x=1000, y=900))
    inp.move(1200, 700)
    assert abs_writes(inp)[:2] == [(e.ABS_X, 1919), (e.ABS_Y, 1079)]


def test_click_presses_and_releases_the_button():
    inp = make()
    inp.click(10, 20, button="right", hover=0)
    keys = [ev[1:] for ev in inp.ptr.events if ev != "syn" and ev[0] == e.EV_KEY]
    assert keys == [(e.BTN_RIGHT, 1), (e.BTN_RIGHT, 0)]


def test_release_all_lifts_held_keys():
    inp = make()
    inp.key_down("shift")
    inp.key_down("ctrl")
    inp.press("a")
    inp.release_all()
    assert inp.held == set()
    down = [c for ev in inp.kbd.events if ev != "syn" for _, c, v in [ev] if v == 1]
    up = [c for ev in inp.kbd.events if ev != "syn" for _, c, v in [ev] if v == 0]
    assert sorted(down) == sorted(up)


def test_gamma_lut_brightens_dark_and_keeps_ends():
    from bot.io.common import gamma_lut

    assert gamma_lut(1.0) is None
    lut = gamma_lut(0.70)
    assert lut[0] == 0 and lut[255] == 255
    assert 60 <= lut[42] <= 75  # measured: Linux 42 ~ Windows 65 (fit runs a little bright mid-tone)
