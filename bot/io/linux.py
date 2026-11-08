"""Linux (X11) backend: Xlib window lookup, kernel uinput input, mss capture, pynput hotkeys.

Why uinput: events come from a virtual kernel device, so X and Wine/Proton see them exactly
like a real mouse and keyboard (XTest events can be filtered or treated differently by games).
The mouse is an *absolute* pointer (like a VM tablet), with its axis range set to the X screen
size, so a coordinate maps to that pixel with no pointer acceleration. Every move is checked
against XQueryPointer and corrected once if it landed off target.

Needs write access to /dev/uinput. On GLaDOS the active desktop user already has it through
an ACL (Steam's udev rules, uaccess).
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path

from evdev import UInput
from evdev import ecodes as e
from Xlib import X, display
from Xlib.protocol import event as xevent

from .base import Input, Region, Window
from .common import DesktopCapture, MssCapture, PynputClicks, PynputHotkeys  # noqa: F401  (re-exported)

log = logging.getLogger(__name__)

_disp: display.Display | None = None


def _display() -> display.Display:
    global _disp
    if _disp is None:
        _disp = display.Display()
    return _disp


def _atom(name: str) -> int:
    return _display().intern_atom(name)


def _root():
    return _display().screen().root


def _title(win) -> str:
    try:
        prop = win.get_full_property(_atom("_NET_WM_NAME"), _atom("UTF8_STRING"))
        if prop is not None:
            return prop.value.decode("utf-8", "replace")
        name = win.get_wm_name()
        return name if isinstance(name, str) else (name or b"").decode("latin-1")
    except Exception:  # window vanished between listing and reading
        return ""


def find_window_id(title: str) -> int | None:
    """Top-level client window whose title equals `title` (from the WM's _NET_CLIENT_LIST)."""
    prop = _root().get_full_property(_atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
    for wid in (prop.value if prop else []):
        if _title(_display().create_resource_object("window", wid)) == title:
            return int(wid)
    return None


def find_window(title: str) -> bool:
    return find_window_id(title) is not None


class X11Window(Window):
    def __init__(self, title: str) -> None:
        self.title = title
        wid = find_window_id(title)
        if wid is None:
            raise RuntimeError(f"window not found: {title!r}")
        self.wid = wid
        self.win = _display().create_resource_object("window", wid)

    def _render_window(self):
        """Wine/Proton draws the game into a child X window inset by its own 2 px border
        (seen 2026-11-08: top-level 1284x724, child 1280x720 at +2+2). Use the largest
        mapped child if there is one, else the top-level window itself."""
        best, best_area = self.win, 0
        for child in self.win.query_tree().children:
            try:
                if child.get_attributes().map_state != X.IsViewable:
                    continue
                g = child.get_geometry()
            except Exception:
                continue
            if g.width * g.height > best_area:
                best, best_area = child, g.width * g.height
        return best

    def client_rect(self) -> Region:
        win = self._render_window()
        geo = win.get_geometry()
        pos = win.translate_coords(_root(), 0, 0)  # window origin relative to the root
        return -pos.x, -pos.y, geo.width, geo.height

    def set_client_size(self, w: int, h: int) -> bool:
        """Resize the top-level window so the game's render area is w x h; D2R follows the window."""
        _, _, cw, ch = self.client_rect()
        if (cw, ch) == (w, h):
            return True
        self.unmaximize()
        top = self.win.get_geometry()
        _, _, cw, ch = self.client_rect()
        log.info("window client %dx%d -> %dx%d", cw, ch, w, h)
        self.win.configure(width=top.width + (w - cw), height=top.height + (h - ch))
        _display().flush()
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            time.sleep(0.2)
            _, _, cw, ch = self.client_rect()
            if (cw, ch) == (w, h):
                return True
        return False

    def unmaximize(self) -> None:
        """The WM maximizes a window that starts out screen-sized; D2R then renders stretched."""
        state = self.win.get_full_property(_atom("_NET_WM_STATE"), X.AnyPropertyType)
        maxed = {_atom("_NET_WM_STATE_MAXIMIZED_VERT"), _atom("_NET_WM_STATE_MAXIMIZED_HORZ")}
        if not state or not maxed & set(state.value):
            return
        log.info("un-maximizing the game window")
        ev = xevent.ClientMessage(window=self.win, client_type=_atom("_NET_WM_STATE"),
                                  data=(32, [0, *sorted(maxed), 1, 0]))  # 0 = remove
        _root().send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        _display().flush()
        time.sleep(1.0)

    def window_rect(self) -> Region:
        """Outer frame (WM decorations included), screen coordinates."""
        frame = self.win
        while True:
            parent = frame.query_tree().parent
            if parent is None or parent.id == _root().id:
                break
            frame = parent
        geo = frame.get_geometry()
        pos = frame.translate_coords(_root(), 0, 0)
        return -pos.x, -pos.y, geo.width, geo.height

    def is_foreground(self) -> bool:
        prop = _root().get_full_property(_atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
        return bool(prop and prop.value and int(prop.value[0]) == self.wid)

    def focus(self) -> None:
        if self.is_foreground():
            return
        log.info("focusing %r (active window was someone else)", self.title)
        # source indication 2 = pager/user action: WMs honour it despite focus-stealing prevention
        ev = xevent.ClientMessage(window=self.win, client_type=_atom("_NET_ACTIVE_WINDOW"),
                                  data=(32, [2, X.CurrentTime, 0, 0, 0]))
        _root().send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self.win.raise_window()
        _display().flush()
        deadline = time.monotonic() + 1.0
        while not self.is_foreground() and time.monotonic() < deadline:
            time.sleep(0.05)


def window_info(title: str) -> dict | None:
    if not find_window(title):
        return None
    w = X11Window(title)
    return {"client": w.client_rect(), "window": w.window_rect(), "foreground": w.is_foreground()}


def _battlenet_running() -> bool:
    r = subprocess.run(["pgrep", "-f", r"Battle\.net\.exe"], capture_output=True)
    return r.returncode == 0


def _battlenet_ready() -> bool:
    """Battle.net's main window is up (the 'Battle.net Login' window means still signing in)."""
    return find_window("Battle.net")


def _wait(pred, timeout: float, what: str, poll: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while not pred():
        if time.monotonic() > deadline:
            raise RuntimeError(f"{what} did not happen within {timeout:.0f}s")
        time.sleep(poll)


def launch_game(launch: dict, title: str, timeout: float = 180.0) -> X11Window:
    """Start D2R if its window isn't up: Steam shortcut -> Battle.net (saved login) ->
    `Battle.net.exe --exec="launch <product>"` run inside the same Proton prefix.

    `launch` (config game.exe on Linux): {steam_appid, proton, product, steam_root?}.
    """
    if find_window(title):
        win = X11Window(title)
        win.unmaximize()
        return win
    root = Path(os.path.expanduser(launch.get("steam_root", "~/.steam/root")))
    appid = int(launch["steam_appid"])
    if not _battlenet_running():
        gameid = (appid << 32) | 0x02000000  # non-Steam shortcut id for steam://rungameid
        log.info("starting Battle.net via Steam shortcut %d", appid)
        subprocess.Popen(["steam", f"steam://rungameid/{gameid}"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    _wait(_battlenet_ready, 120, "Battle.net main window (login)")
    time.sleep(3)  # let the client finish loading before asking it to launch a game
    env = {**os.environ,
           "STEAM_COMPAT_DATA_PATH": str(root / "steamapps/compatdata" / str(appid)),
           "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(root)}
    proton = root / "steamapps/common" / launch.get("proton", "Proton - Experimental") / "proton"
    cmd = [str(proton), "run", r"C:\Program Files (x86)\Battle.net\Battle.net.exe",
           f"--exec=launch {launch.get('product', 'OSI')}"]
    deadline = time.monotonic() + timeout
    for attempt in (1, 2):  # Battle.net ignores the request while it's still busy (updates, news)
        log.info("asking Battle.net to launch %s (attempt %d)", launch.get("product", "OSI"), attempt)
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        try:
            _wait(lambda: find_window(title), min(60.0, max(1.0, deadline - time.monotonic())),
                  f"game window {title!r}")
            break
        except RuntimeError:
            if attempt == 2:
                raise
    time.sleep(2)
    win = X11Window(title)
    win.unmaximize()
    return win


# Key names as used by the bot (pydirectinput style) -> evdev key codes.
KEYMAP: dict[str, int] = {
    **{c: getattr(e, f"KEY_{c.upper()}") for c in "abcdefghijklmnopqrstuvwxyz"},
    **{str(d): getattr(e, f"KEY_{d}") for d in range(10)},
    **{f"f{i}": getattr(e, f"KEY_F{i}") for i in range(1, 13)},
    "esc": e.KEY_ESC, "escape": e.KEY_ESC, "enter": e.KEY_ENTER, "return": e.KEY_ENTER,
    "tab": e.KEY_TAB, "space": e.KEY_SPACE, " ": e.KEY_SPACE, "backspace": e.KEY_BACKSPACE,
    "alt": e.KEY_LEFTALT, "altleft": e.KEY_LEFTALT, "altright": e.KEY_RIGHTALT,
    "shift": e.KEY_LEFTSHIFT, "shiftleft": e.KEY_LEFTSHIFT, "shiftright": e.KEY_RIGHTSHIFT,
    "ctrl": e.KEY_LEFTCTRL, "ctrlleft": e.KEY_LEFTCTRL, "ctrlright": e.KEY_RIGHTCTRL,
    "up": e.KEY_UP, "down": e.KEY_DOWN, "left": e.KEY_LEFT, "right": e.KEY_RIGHT,
    "delete": e.KEY_DELETE, "home": e.KEY_HOME, "end": e.KEY_END,
    "pageup": e.KEY_PAGEUP, "pagedown": e.KEY_PAGEDOWN,
    "/": e.KEY_SLASH, "-": e.KEY_MINUS, "=": e.KEY_EQUAL, ".": e.KEY_DOT, ",": e.KEY_COMMA,
    ";": e.KEY_SEMICOLON, "'": e.KEY_APOSTROPHE, "[": e.KEY_LEFTBRACE, "]": e.KEY_RIGHTBRACE,
    "\\": e.KEY_BACKSLASH, "`": e.KEY_GRAVE,
}
_BUTTONS = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT, "middle": e.BTN_MIDDLE}


def keycode(key: str) -> int:
    try:
        return KEYMAP[key.lower()]
    except KeyError:
        raise ValueError(f"no uinput key code for {key!r}") from None


class UinputInput(Input):
    """Two virtual devices: a keyboard and an absolute pointer spanning the X screen."""

    def __init__(self, window: Window, screen_size: tuple[int, int] | None = None,
                 uinput_factory=UInput, pointer_query=None, settle: float = 0.5, lag: float = 0.0) -> None:
        """`lag`: extra seconds D2R under Proton needs to notice the cursor moved (measured 2026-11-08: a
        hover tooltip shows ~115 ms after the move, later than the Windows-tuned waits of 0.07-0.09 s).
        Added after every move and before every click, teleports included: with no wait between the move and
        the press, D2R sometimes still had the old cursor position and teleported on the spot (Durance hops
        "stuck", LK "odometry lost", 2026-11-08)."""
        self.window = window
        self.lag = lag
        if screen_size is None:
            geo = _root().get_geometry()
            screen_size = (geo.width, geo.height)
        self.sw, self.sh = screen_size
        self._query = pointer_query or self._xquery
        self.kbd = uinput_factory({e.EV_KEY: sorted(set(KEYMAP.values()))}, name="d2r-bot keyboard")
        self.ptr = uinput_factory({
            e.EV_KEY: list(_BUTTONS.values()),
            e.EV_ABS: [(e.ABS_X, (0, 0, self.sw - 1, 0, 0, 0)), (e.ABS_Y, (0, 0, self.sh - 1, 0, 0, 0))],
        }, name="d2r-bot pointer")
        self.held: set[str] = set()
        time.sleep(settle)  # give X/libinput time to pick up the new devices

    @staticmethod
    def _xquery() -> tuple[int, int]:
        p = _root().query_pointer()
        return p.root_x, p.root_y

    def _abs(self, x: int, y: int) -> tuple[int, int]:
        wx, wy, _, _ = self.window.client_rect()
        return wx + x, wy + y

    def _warp(self, ax: int, ay: int) -> None:
        ax = min(max(ax, 0), self.sw - 1)
        ay = min(max(ay, 0), self.sh - 1)
        self.ptr.write(e.EV_ABS, e.ABS_X, ax)
        self.ptr.write(e.EV_ABS, e.ABS_Y, ay)
        self.ptr.syn()

    def move(self, x, y):
        self._move(x, y)
        if self.lag:
            time.sleep(self.lag)

    def _move(self, x, y):
        ax, ay = self._abs(x, y)
        self._warp(ax, ay)
        time.sleep(0.01)
        px, py = self._query()
        if abs(px - ax) > 1 or abs(py - ay) > 1:  # scaling off by a pixel or two: correct once
            self._warp(ax + (ax - px), ay + (ay - py))
            time.sleep(0.01)

    def click(self, x, y, button="left", hover: float = 0.08):
        # D2R only interacts with an object if the cursor hovered it for a frame or two first.
        self._move(x, y)
        time.sleep(hover + self.lag)
        code = _BUTTONS[button]
        self.ptr.write(e.EV_KEY, code, 1)
        self.ptr.syn()
        time.sleep(0.03)
        self.ptr.write(e.EV_KEY, code, 0)
        self.ptr.syn()

    def key_down(self, key):
        code = keycode(key)
        self.held.add(key)
        self.kbd.write(e.EV_KEY, code, 1)
        self.kbd.syn()
        time.sleep(0.02)  # same pacing as pydirectinput.PAUSE on Windows

    def key_up(self, key):
        code = keycode(key)
        self.held.discard(key)
        self.kbd.write(e.EV_KEY, code, 0)
        self.kbd.syn()
        time.sleep(0.02)

    def release_all(self):
        for k in list(self.held):
            self.key_up(k)

    def cursor_pos(self):
        px, py = self._query()
        wx, wy, _, _ = self.window.client_rect()
        return px - wx, py - wy

    def close(self) -> None:
        self.release_all()
        self.kbd.close()
        self.ptr.close()
