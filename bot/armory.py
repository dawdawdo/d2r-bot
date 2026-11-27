"""Rebuild Blizzaga's Armory data from the newest save backup and send it to convergentblue.com/bot/ (armory tabs).

    python -m bot.armory            # build from the save files if they changed since the last build, upload
    python -m bot.armory --force    # rebuild and upload even if nothing changed
    python -m bot.armory --backup   # build from the newest save backup instead
    python -m bot.armory --no-upload

Builds from a private copy of the save files (armory/work/live/, copied read-only), never the live folder itself. The
pipeline is the armory project's (armory/README.md): dump each .d2s and the shared stash (bot/d2save.py, same JSON
as the old Linux-only d2dump) -> inv.py -> gen.py ->
chron.py -> build.py, in armory/work/. armory/pagedata.json is both the result and the next build's "previous
snapshot" (build.py works out what changed from it and stamps when each item first showed up).

The supervisor calls maybe_refresh() each tick. Stephen 2026-11-27: "capture any time there is a change", not only at
session starts: every CHECK_EVERY_S it compares the save files (bot/savewatch.snapshot) with the last build's, and once
they have been quiet for QUIET_S (the game has finished writing) it rebuilds in a thread, at most every MIN_GAP_S.
Saves that arrive from the other machine (Syncthing) count too, so his own play shows up while a supervisor runs.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
from pathlib import Path

from . import d2save, savewatch
from .config import ROOT, load_config

log = logging.getLogger("bot.armory")
A = ROOT / "armory"
WORK = A / "work"
LAST = WORK / "last.json"
STASH = "ModernSharedStashSoftCoreV2.d2i"
SCRIPTS = ("inv.py", "gen.py", "chron.py", "build.py", "armory.html", "icon_map.json")
CHECK_EVERY_S = 60   # how often the supervisor looks at the save files
QUIET_S = 20         # newest save write at least this old: the game has finished writing them
MIN_GAP_S = 120      # at most one build per this many seconds (an LK run saves every ~2 min)
LIVE = WORK / "live"


def latest_backup(cfg: dict) -> Path | None:
    root = ROOT / cfg["paths"]["backups"]
    dirs = [p for p in root.glob("*") if p.is_dir() and re.fullmatch(r"\d{8}-\d{6}(_\d+)?", p.name)
            and (p / STASH).exists()]
    return max(dirs, key=lambda p: p.name) if dirs else None


def _run(args: list[str], out: Path | None = None) -> None:
    if out is None:
        subprocess.run(args, cwd=WORK, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=300)
        return
    with open(out, "wb") as fh:
        subprocess.run(args, cwd=WORK, stdout=fh, stderr=subprocess.PIPE, check=True, timeout=300)


def _dump(obj, out: Path) -> None:
    out.write_text(json.dumps(obj, separators=(",", ":")), encoding="ascii")  # inv.py opens with the platform default


def build(backup: Path) -> Path:
    """Run the pipeline on one backup folder; returns armory/pagedata.json."""
    if not (WORK / "xl").exists() or not (WORK / "txt105").exists():  # game tables (the bundle's d2dump is unused)
        WORK.mkdir(parents=True, exist_ok=True)
        with tarfile.open(A / "scanbundle.tgz") as t:
            t.extractall(WORK, filter="data")
    saves = WORK / "saves"
    shutil.rmtree(saves, ignore_errors=True)
    saves.mkdir()
    for f in SCRIPTS:
        shutil.copy2(A / f, WORK / f)
    shutil.copy2(A / "pagedata.json", WORK / "pagedata.json")
    shutil.copy2(A / "pagedata.json", WORK / "prev.json")
    for d2s in sorted(backup.glob("*.d2s")):
        _dump(d2save.read_d2s(d2s), saves / f"{d2s.stem}.json")
    _dump(d2save.read_d2i(backup / STASH), saves / "stash.json")
    py = sys.executable
    _run([py, "inv.py", "."])
    _run([py, "gen.py"])
    _run([py, "chron.py", str(backup / STASH)], WORK / "chron.json")
    _run([py, "build.py"])
    json.loads((WORK / "pagedata.json").read_text())  # sanity: valid before it replaces the last good one
    shutil.copy2(WORK / "pagedata.json", A / "pagedata.json")
    return A / "pagedata.json"


def upload(cfg: dict, path: Path) -> int:
    r = cfg.get("remote") or {}
    url, tf = r.get("url"), r.get("token_file")
    if not url or not tf:
        raise RuntimeError("no remote.url / remote.token_file in config.local.yaml")
    token = Path(tf).expanduser().read_text().strip()
    body = gzip.compress(path.read_bytes(), 9)
    req = urllib.request.Request(url.rsplit("/", 1)[0] + "/armory", data=body, method="POST",
                                 headers={"Content-Type": "application/gzip", "User-Agent": "d2r-bot-supervisor/1",
                                          "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        json.loads(resp.read() or b"{}")
    return len(body)


def refresh(cfg: dict, force: bool = False, send: bool = True) -> str:
    b = latest_backup(cfg)
    if b is None:
        return "no backup with a shared stash yet"
    last = json.loads(LAST.read_text()) if LAST.exists() else {}
    if not force and last.get("backup") == b.name:
        return f"already built from {b.name}"
    t0 = time.time()
    path = build(b)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    msg = f"built from {b.name} in {time.time() - t0:.1f} s"
    if not send:  # a dry run must not mark this backup done, or it would never be uploaded
        return msg + " (not uploaded)"
    if force or digest != last.get("sent"):
        msg += f", uploaded {upload(cfg, path) // 1024} KB"
        last["sent"] = digest
    LAST.write_text(json.dumps(last | {"backup": b.name, "at": time.time()}))
    return msg


def live_copy(cfg: dict, dest: Path = LIVE) -> tuple[Path, dict] | None:
    """Copy the characters and the shared stash out of the save folder (read only). None if a file changed while
    copying (the game was writing): try again at the next check."""
    src = Path(cfg["paths"]["save_dir"])
    before = savewatch.snapshot(src)
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for p in sorted(src.glob("*.d2s")) + [src / STASH]:
        if ".sync-conflict-" not in p.name:
            shutil.copy2(p, dest / p.name)
    after = savewatch.snapshot(src)
    return (dest, after) if after == before else None


def _last() -> dict:
    try:
        return json.loads(LAST.read_text())
    except (OSError, ValueError):
        return {}


def refresh_live(cfg: dict, force: bool = False, send: bool = True) -> str:
    """Build from the save files as they are now and upload (only if they changed since the last build)."""
    last = _last()
    state = json.loads(json.dumps(savewatch.snapshot(cfg["paths"]["save_dir"])))  # same shape as stored
    if not force and last.get("saves") == state:
        return "saves unchanged since the last build"
    got = live_copy(cfg)
    if got is None:
        return "saves changed while copying: next time"
    folder, state = got
    t0 = time.time()
    path = build(folder)
    msg = f"built from the saves in {time.time() - t0:.1f} s"
    if not send:
        return msg + " (not uploaded)"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if force or digest != last.get("sent"):
        msg += f", uploaded {upload(cfg, path) // 1024} KB"
        last["sent"] = digest
    LAST.write_text(json.dumps(last | {"saves": state, "at": time.time()}))
    return msg


def due(snap: dict, last: dict, now: float) -> bool:
    """Rebuild now? The saves differ from the last build's, the newest write is QUIET_S old, MIN_GAP_S since the last."""
    snap = json.loads(json.dumps(snap))
    if not snap or last.get("saves") == snap:
        return False
    newest = max(m for m, _ in snap.values()) / 1e9
    return now - newest >= QUIET_S and now - float(last.get("at") or 0) >= MIN_GAP_S


_busy = threading.Lock()
_checked = 0.0


def maybe_refresh(cfg: dict) -> None:
    """Supervisor hook: cheap check (file times), build in a background thread when the saves changed."""
    global _checked
    if time.time() - _checked < CHECK_EVERY_S or _busy.locked():
        return
    _checked = time.time()
    if not due(savewatch.snapshot(cfg["paths"]["save_dir"]), _last(), time.time()):
        return

    def job():
        with _busy:
            try:
                log.info("armory: %s", refresh_live(cfg))
            except Exception as e:  # the armory must never disturb the bot
                log.warning("armory refresh failed: %s", e)
    threading.Thread(target=job, name="armory", daemon=True).start()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--backup", action="store_true", help="build from the newest save backup instead of the saves")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    fn = refresh if a.backup else refresh_live
    print(fn(load_config(), force=a.force, send=not a.no_upload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
