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

    def trip(self, reason: str = "kill switch") -> None:
        if not self._event.is_set():
            self.reason = reason
            log.warning("KILL SWITCH: %s", reason)
        self._event.set()

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
