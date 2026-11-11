"""I/O boundary. Only this package may import platform capture/input libraries."""
from __future__ import annotations

import sys
from dataclasses import dataclass

from .base import Capture, ClickListener, GuardedInput, HotkeyListener, Input, Region, Window


@dataclass
class Backend:
    window: Window
    capture: Capture
    input: Input
    hotkeys: HotkeyListener


def _game_cfg() -> dict:
    from ..config import load_config  # config.yaml game.capture_gamma / game.input_lag, per platform

    return load_config()["game"]


def _capture_gamma() -> float:
    return float(_game_cfg().get("capture_gamma") or 1.0)


def open_backend(window_title: str, launch_exe=None, capture_gamma: float | None = None) -> Backend:
    """Open the platform backend attached to the game window, launching the game first
    if `launch_exe` is given and the window isn't up. `capture_gamma` defaults to config."""
    gamma = _capture_gamma() if capture_gamma is None else capture_gamma
    if sys.platform == "win32":
        from .windows import DirectInput, MssCapture, PynputHotkeys, Win32Window, launch_game

        win = launch_game(launch_exe, window_title) if launch_exe else Win32Window(window_title)
        return Backend(win, MssCapture(win, gamma), DirectInput(win), PynputHotkeys())
    if sys.platform == "linux":
        from .linux import MssCapture, PynputHotkeys, UinputInput, X11Window, launch_game

        win = launch_game(launch_exe, window_title) if launch_exe else X11Window(window_title)
        lag = float(_game_cfg().get("input_lag") or 0.0)
        return Backend(win, MssCapture(win, gamma), UinputInput(win, lag=lag), PynputHotkeys())
    raise NotImplementedError(f"no I/O backend for {sys.platform} yet")


def open_desktop_capture() -> Capture:
    if sys.platform == "win32":
        from .windows import DesktopCapture

        return DesktopCapture()
    if sys.platform == "linux":
        from .common import DesktopCapture

        return DesktopCapture()
    raise NotImplementedError(sys.platform)


def window_info(title: str) -> dict | None:
    """{'client': rect, 'window': rect, 'foreground': bool} or None if not found."""
    if sys.platform == "win32":
        from .windows import window_info as wi

        return wi(title)
    if sys.platform == "linux":
        from .linux import window_info as wi

        return wi(title)
    raise NotImplementedError(sys.platform)


def open_hotkeys() -> HotkeyListener:
    """Hotkey listener alone (doesn't need the game window)."""
    if sys.platform in ("win32", "linux"):
        from .common import PynputHotkeys

        return PynputHotkeys()
    raise NotImplementedError(f"no hotkey backend for {sys.platform} yet")


def game_running(exe: str = "D2R.exe") -> bool:
    """Is the game process running? (Filters and settings may only be installed while it's closed.)"""
    import subprocess

    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"], capture_output=True, text=True).stdout
        return exe in out
    # Linux/Proton: the Windows exe shows up in the wine process command lines
    pattern = "[" + exe[0] + "]" + exe[1:].replace(".", r"\.")  # [D]2R\.exe: pgrep never matches itself
    return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0


def idle_seconds() -> float | None:
    """Seconds since the last keyboard/mouse input on this desktop (any device), or None if unknown.
    The supervisor reads it while no bot runs, so it measures the person, not the bot."""
    if sys.platform == "win32":
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
    if sys.platform == "linux":
        try:
            from .linux import idle_seconds as linux_idle
        except Exception:
            return None
        return linux_idle()
    return None


def open_clicks() -> ClickListener:
    """The user's mouse clicks (screen coords)."""
    if sys.platform in ("win32", "linux"):
        from .common import PynputClicks

        return PynputClicks()
    raise NotImplementedError(f"no click listener for {sys.platform} yet")


__all__ = ["Backend", "Capture", "ClickListener", "GuardedInput", "HotkeyListener", "Input", "Region", "Window",
           "game_running", "open_backend", "open_clicks", "open_hotkeys"]
