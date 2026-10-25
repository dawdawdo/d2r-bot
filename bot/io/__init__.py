"""I/O boundary. Only this package may import platform capture/input libraries."""
from __future__ import annotations

import sys
from dataclasses import dataclass

from .base import Capture, GuardedInput, HotkeyListener, Input, Region, Window


@dataclass
class Backend:
    window: Window
    capture: Capture
    input: Input
    hotkeys: HotkeyListener


def open_backend(window_title: str, launch_exe: str | None = None) -> Backend:
    """Open the platform backend attached to the game window, launching the game first
    if `launch_exe` is given and the window isn't up."""
    if sys.platform == "win32":
        from .windows import DirectInput, MssCapture, PynputHotkeys, Win32Window, launch_game

        win = launch_game(launch_exe, window_title) if launch_exe else Win32Window(window_title)
        return Backend(win, MssCapture(win), DirectInput(win), PynputHotkeys())
    raise NotImplementedError(f"no I/O backend for {sys.platform} yet")


def open_hotkeys() -> HotkeyListener:
    """Hotkey listener alone (doesn't need the game window)."""
    if sys.platform == "win32":
        from .windows import PynputHotkeys

        return PynputHotkeys()
    raise NotImplementedError(f"no hotkey backend for {sys.platform} yet")


__all__ = ["Backend", "Capture", "GuardedInput", "HotkeyListener", "Input", "Region", "Window",
           "open_backend", "open_hotkeys"]
