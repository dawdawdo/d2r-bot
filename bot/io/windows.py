"""Windows backend: user32 window lookup, mss capture, pydirectinput input, pynput hotkeys."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import logging
from typing import Callable

import mss
import numpy as np
import pydirectinput
from pynput import keyboard, mouse

from .base import Capture, ClickListener, HotkeyListener, Input, Region, Window

log = logging.getLogger(__name__)

pydirectinput.FAILSAFE = False  # we have our own kill switch
pydirectinput.PAUSE = 0.02

_user32 = ctypes.windll.user32
try:  # make GetClientRect/ClientToScreen return physical pixels
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


class Win32Window(Window):
    def __init__(self, title: str) -> None:
        self.title = title
        self.hwnd = _user32.FindWindowW(None, title)
        if not self.hwnd:
            raise RuntimeError(f"window not found: {title!r}")

    def client_rect(self) -> Region:
        rc = wt.RECT()
        _user32.GetClientRect(self.hwnd, ctypes.byref(rc))
        pt = wt.POINT(0, 0)
        _user32.ClientToScreen(self.hwnd, ctypes.byref(pt))
        return pt.x, pt.y, rc.right - rc.left, rc.bottom - rc.top

    def is_foreground(self) -> bool:
        return _user32.GetForegroundWindow() == self.hwnd

    def focus(self) -> None:
        """Windows refuses SetForegroundWindow from a background process unless its input is
        attached to the current foreground thread (a toast or a desktop menu had focus 2026-10-26)."""
        fg = _user32.GetForegroundWindow()
        if fg == self.hwnd:
            return
        log.info("focus taken by %s", _describe(fg))
        me = ctypes.windll.kernel32.GetCurrentThreadId()
        other = _user32.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = bool(other) and other != me and _user32.AttachThreadInput(me, other, True)
        try:
            _user32.ShowWindow(self.hwnd, 9)  # SW_RESTORE
            _user32.BringWindowToTop(self.hwnd)
            _user32.SetForegroundWindow(self.hwnd)
        finally:
            if attached:
                _user32.AttachThreadInput(me, other, False)


def _describe(hwnd: int) -> str:
    """'title' [class] exe of a window, for logging who stole focus."""
    if not hwnd:
        return "no window"
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetWindowTextW(hwnd, buf, 256)
    title = buf.value
    _user32.GetClassNameW(hwnd, buf, 256)
    cls = buf.value
    pid = wt.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    exe = "?"
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if h:
        size = wt.DWORD(260)
        path = ctypes.create_unicode_buffer(260)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(size)):
            exe = path.value.rsplit("\\", 1)[-1]
        ctypes.windll.kernel32.CloseHandle(h)
    return f"{title!r} [{cls}] {exe} (pid {pid.value})"


def find_window(title: str) -> bool:
    return bool(_user32.FindWindowW(None, title))


def launch_game(exe: str, title: str, timeout: float = 90.0, args: list[str] | None = None) -> Win32Window:
    """Start the game (if its window isn't already up) and wait for the window."""
    import subprocess
    import time
    from pathlib import Path

    if not find_window(title):
        log.info("launching %s", exe)
        subprocess.Popen([exe, *(args or [])], cwd=str(Path(exe).parent))
        deadline = time.monotonic() + timeout
        while not find_window(title):
            if time.monotonic() > deadline:
                raise RuntimeError(f"game window {title!r} did not appear within {timeout}s")
            time.sleep(1)
    return Win32Window(title)


class DesktopCapture(Capture):
    """Whole primary monitor (for diagnostics when the game window isn't found)."""

    def __init__(self) -> None:
        self.sct = mss.mss()

    def grab(self, region: Region | None = None) -> np.ndarray:
        mon = self.sct.monitors[1]
        if region is not None:
            x, y, w, h = region
            mon = {"left": mon["left"] + x, "top": mon["top"] + y, "width": w, "height": h}
        return np.ascontiguousarray(np.asarray(self.sct.grab(mon))[:, :, :3])

    def close(self) -> None:
        self.sct.close()


def window_info(title: str) -> dict | None:
    if not find_window(title):
        return None
    w = Win32Window(title)
    rc = wt.RECT()
    _user32.GetWindowRect(w.hwnd, ctypes.byref(rc))
    return {"client": w.client_rect(), "window": (rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top),
            "foreground": w.is_foreground()}


class MssCapture(Capture):
    def __init__(self, window: Window) -> None:
        self.window = window
        self.sct = mss.mss()

    def grab(self, region: Region | None = None) -> np.ndarray:
        wx, wy, ww, wh = self.window.client_rect()
        if region is None:
            region = (0, 0, ww, wh)
        x, y, w, h = region
        shot = self.sct.grab({"left": wx + x, "top": wy + y, "width": w, "height": h})
        return np.ascontiguousarray(np.asarray(shot)[:, :, :3])  # BGRA -> BGR

    def close(self) -> None:
        self.sct.close()


_BUTTONS = {"left": pydirectinput.LEFT, "right": pydirectinput.RIGHT, "middle": pydirectinput.MIDDLE}


class DirectInput(Input):
    def __init__(self, window: Window) -> None:
        self.window = window
        self.held: set[str] = set()

    def _abs(self, x: int, y: int) -> tuple[int, int]:
        wx, wy, _, _ = self.window.client_rect()
        return wx + x, wy + y

    def move(self, x, y):
        pydirectinput.moveTo(*self._abs(x, y))

    def click(self, x, y, button="left", hover: float = 0.08):
        # D2R only interacts with an object (waypoint, chest) if the cursor hovered it for a
        # frame or two before the press; an instant move+click is treated as "walk here".
        import time

        ax, ay = self._abs(x, y)
        pydirectinput.moveTo(ax, ay)
        time.sleep(hover)
        pydirectinput.mouseDown(button=_BUTTONS[button])
        time.sleep(0.03)
        pydirectinput.mouseUp(button=_BUTTONS[button])

    def key_down(self, key):
        self.held.add(key)
        pydirectinput.keyDown(key)

    def key_up(self, key):
        self.held.discard(key)
        pydirectinput.keyUp(key)

    def release_all(self):
        # Only release what we hold: a stray mouseUp over the desktop opens context menus.
        for k in list(self.held):
            self.key_up(k)

    def cursor_pos(self):
        pt = wt.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        wx, wy, _, _ = self.window.client_rect()
        return pt.x - wx, pt.y - wy


class PynputHotkeys(HotkeyListener):
    """One background listener; `start` may be called once per key to add bindings."""

    def __init__(self) -> None:
        self.listener: keyboard.Listener | None = None
        self.bindings: dict = {}

    def start(self, key: str, callback: Callable[[], None]) -> None:
        target = getattr(keyboard.Key, key.lower(), None) or keyboard.KeyCode.from_char(key)
        self.bindings[target] = callback
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self._on_press, daemon=True)
            self.listener.start()

    def _on_press(self, k) -> None:
        cb = self.bindings.get(k)
        if cb is not None:
            try:
                cb()
            except Exception:
                log.exception("hotkey callback failed")

    def stop(self) -> None:
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.bindings.clear()


class PynputClicks(ClickListener):
    def __init__(self) -> None:
        self.listener: mouse.Listener | None = None

    def start(self, callback: Callable[[int, int, str], None]) -> None:
        def on_click(x, y, button, pressed) -> None:
            if pressed and button in (mouse.Button.left, mouse.Button.right):
                try:
                    callback(int(x), int(y), button.name)
                except Exception:
                    log.exception("click callback failed")

        self.listener = mouse.Listener(on_click=on_click, daemon=True)
        self.listener.start()

    def stop(self) -> None:
        if self.listener:
            self.listener.stop()
            self.listener = None
