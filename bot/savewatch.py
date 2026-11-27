"""Don't play with a D2R whose saves are stale.

D2R reads the .d2s / .d2i files when it starts and never again: not at the character screen, not between games.
Syncthing brings the other machine's saves in underneath it, and its next save & exit writes its old copy back over
them. 2026-11-27 13:25: GLaDOS's D2R, open since 11:49, played Smoked as he was at 12:06 (level 84) and wrote him
and the shared stash over Stephen's 13:13 saves from Singularity (level 86, new runewords); restored from the backup.

So every session records the save files as its D2R left them (Session.close), and the next one compares: changed
while D2R stayed open = someone else wrote them, close D2R so the session starts it fresh (launch_game).
Platform-neutral: the process check and close are bot.io's.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import ROOT

log = logging.getLogger(__name__)

SNAPSHOT = ROOT / "logs" / "save_snapshot.json"
PATTERNS = ("*.d2s", "*.d2i")  # characters and the shared stash: what D2R caches and writes back


def snapshot(save_dir: str | Path) -> dict[str, list[int]]:
    """{file name: [mtime_ns, size]} of the save files D2R caches (Syncthing conflict copies left out)."""
    out = {}
    for pattern in PATTERNS:
        for p in Path(save_dir).glob(pattern):
            if ".sync-conflict-" in p.name or not p.is_file():
                continue
            st = p.stat()
            out[p.name] = [st.st_mtime_ns, st.st_size]
    return out


def record(save_dir: str | Path, path: Path = SNAPSHOT) -> None:
    """The saves as this machine's D2R left them (call after its last save & exit)."""
    try:
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(snapshot(save_dir), indent=0, sort_keys=True))
    except OSError as e:
        log.warning("save snapshot not written: %s", e)


def changed_since_recorded(save_dir: str | Path, path: Path = SNAPSHOT) -> list[str]:
    """Save files that differ from the last recorded snapshot (all of them if there is none)."""
    now = snapshot(save_dir)
    try:
        old = json.loads(path.read_text())
    except (OSError, ValueError):
        return sorted(now) or ["(no snapshot)"]
    return sorted(n for n in set(now) | set(old) if now.get(n) != old.get(n))


def ensure_fresh_game(cfg: dict, running=None, close=None, path: Path = SNAPSHOT) -> bool:
    """Close D2R if it was already running while the save files changed under it. True if it was closed.
    Raises RuntimeError if it won't close (playing on would write stale saves)."""
    if running is None or close is None:
        from .io import close_game, game_running

        running, close = running or game_running, close or close_game
    if not running():
        return False  # it reads the current files when the session starts it
    changed = changed_since_recorded(cfg["paths"]["save_dir"], path)
    if not changed:
        return False
    log.warning("D2R stayed open while these saves changed on disk (Syncthing?): %s; closing it so it re-reads "
                "them", ", ".join(changed[:8]) + (" ..." if len(changed) > 8 else ""))
    if not close():
        raise RuntimeError("D2R holds stale saves and won't close: close it by hand before playing")
    return True
