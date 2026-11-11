"""Global kill switch. Call `check()` every loop tick; it raises once tripped."""
from __future__ import annotations

import logging
import threading

log = logging.getLogger(__name__)


class KillSwitchTripped(RuntimeError):
    pass


class KillSwitch:
    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason = ""
        self.kind = ""  # "f12" (a person pressed it: stay stopped) or "mouse" (the cursor was moved)

    def trip(self, reason: str = "kill switch", kind: str = "f12") -> None:
        if not self._event.is_set():
            self.reason = reason
            self.kind = kind
            log.warning("KILL SWITCH: %s", reason)
        self._event.set()

    def rearm(self) -> None:
        """Clear a trip so a mouse-trip exit (save & exit) can send input. F12 still trips it again."""
        self._event.clear()

    @property
    def tripped(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        if self._event.is_set():
            raise KillSwitchTripped(self.reason)

    def sleep(self, seconds: float) -> None:
        """Sleep that wakes up (and raises) immediately when tripped."""
        if self._event.wait(seconds):
            raise KillSwitchTripped(self.reason)
