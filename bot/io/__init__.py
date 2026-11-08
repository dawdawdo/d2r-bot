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


def _capture_gamma() -> float:
    from ..config import load_config  # config.yaml game.capture_gamma, per platform

    return float(load_config()["game"].get("capture_gamma") or 1.0)


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
        return Backend(win, MssCapture(win, gamma), UinputInput(win), PynputHotkeys())
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


def open_clicks() -> ClickListener:
    """The user's mouse clicks (screen coords)."""
    if sys.platform in ("win32", "linux"):
        from .common import PynputClicks

        return PynputClicks()
    raise NotImplementedError(f"no click listener for {sys.platform} yet")


__all__ = ["Backend", "Capture", "ClickListener", "GuardedInput", "HotkeyListener", "Input", "Region", "Window",
           "game_running", "open_backend", "open_clicks", "open_hotkeys"]
