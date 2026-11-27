"""Bot session setup shared by the runner and tools: logging, kill switch, save backup."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .backup import backup_saves
from .config import load_config
from .io import HotkeyListener, open_hotkeys
from .killswitch import KillSwitch
from .log import setup_logging
from . import savewatch

log = logging.getLogger(__name__)


@dataclass
class Session:
    cfg: dict
    kill: KillSwitch
    hotkeys: HotkeyListener
    played: bool = True

    def close(self) -> None:
        self.hotkeys.stop()
        if self.played:  # the saves as this machine's D2R left them (bot/savewatch.py)
            savewatch.record(self.cfg["paths"]["save_dir"])


def start_session(cfg: dict | None = None, backup: bool = True,
                  hotkeys: HotkeyListener | None = None) -> Session:
    cfg = cfg or load_config()
    setup_logging(cfg["paths"]["logs"])
    kill = KillSwitch()
    hotkeys = hotkeys or open_hotkeys()
    key = cfg["hotkeys"]["kill_switch"]
    hotkeys.start(key, lambda: kill.trip(f"{key.upper()} pressed"))
    log.info("kill switch armed on %s", key.upper())
    if backup:  # a session that may play: D2R must not hold stale saves (bot/savewatch.py, 2026-11-27)
        savewatch.ensure_fresh_game(cfg)
        backup_saves(cfg["paths"]["save_dir"], cfg["paths"]["backups"])
    return Session(cfg, kill, hotkeys, played=backup)
