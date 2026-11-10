"""Rebuild Blizzaga's Armory data from the newest save backup and send it to convergentblue.com/armory/.

    python -m bot.armory            # build from the newest backup if it's new, upload
    python -m bot.armory --force    # rebuild and upload even if that backup was already done
    python -m bot.armory --no-upload

Reads only backups/<ts>/ (the copy bot/session.py makes at every session start), never the live save folder. The
pipeline is the armory project's (armory/README.md): d2dump each .d2s and the shared stash -> inv.py -> gen.py ->
chron.py -> build.py, in armory/work/. armory/pagedata.json is both the result and the next build's "previous
snapshot" (build.py works out what changed from it). The supervisor calls maybe_refresh() each tick; it builds in a
thread, at most once per new backup.
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

from .config import ROOT, load_config

log = logging.getLogger("bot.armory")
A = ROOT / "armory"
WORK = A / "work"
LAST = WORK / "last.json"
STASH = "ModernSharedStashSoftCoreV2.d2i"
SCRIPTS = ("inv.py", "gen.py", "chron.py", "build.py", "armory.html")
CHECK_EVERY_S = 300


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


def build(backup: Path) -> Path:
    """Run the pipeline on one backup folder; returns armory/pagedata.json."""
    if not (WORK / "d2dump").exists():
        WORK.mkdir(parents=True, exist_ok=True)
        with tarfile.open(A / "scanbundle.tgz") as t:
            t.extractall(WORK, filter="data")
        (WORK / "d2dump").chmod(0o755)
    saves = WORK / "saves"
    shutil.rmtree(saves, ignore_errors=True)
    saves.mkdir()
    for f in SCRIPTS:
        shutil.copy2(A / f, WORK / f)
    shutil.copy2(A / "pagedata.json", WORK / "pagedata.json")
    shutil.copy2(A / "pagedata.json", WORK / "prev.json")
    for d2s in sorted(backup.glob("*.d2s")):
        _run(["./d2dump", "c", str(d2s)], saves / f"{d2s.stem}.json")
    _run(["./d2dump", "s", str(backup / STASH)], saves / "stash.json")
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


_busy = threading.Lock()
_checked = 0.0


def maybe_refresh(cfg: dict) -> None:
    """Supervisor hook: cheap check, build in a background thread when a new backup appeared."""
    global _checked
    if time.time() - _checked < CHECK_EVERY_S or _busy.locked():
        return
    _checked = time.time()
    b = latest_backup(cfg)
    last = json.loads(LAST.read_text()) if LAST.exists() else {}
    if b is None or last.get("backup") == b.name:
        return

    def job():
        with _busy:
            try:
                log.info("armory: %s", refresh(cfg))
            except Exception as e:  # the armory must never disturb the bot
                log.warning("armory refresh failed: %s", e)
    threading.Thread(target=job, name="armory", daemon=True).start()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    print(refresh(load_config(), force=a.force, send=not a.no_upload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
