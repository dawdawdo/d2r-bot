"""One-line summary of runs.csv rows since a timestamp: python tools/batch_summary.py "2026-10-27 03:00:00" """
import csv
import sys
from pathlib import Path

since = sys.argv[1] if len(sys.argv) > 1 else ""
FIELDS = ["start", "duration_s", "result", "chests", "picked", "error", "task"]  # the file's header predates chests/picked
with open(Path(__file__).resolve().parent.parent / "runs.csv") as f:
    next(f)
    rows = [r for r in csv.DictReader(f, FIELDS) if r["start"] >= since]
ok = [r for r in rows if r["result"] == "ok"]
other = [f'{r["result"]}({(r["error"] or "")[:40]})' for r in rows if r["result"] != "ok"]
avg = sum(float(r["duration_s"]) for r in ok) / len(ok) if ok else 0
chests = sum(int(r["chests"] or 0) for r in rows)
picks = [p for r in rows for p in (r["picked"] or "").split() if p not in ("key", "rejuv")]
print(f"{len(ok)}/{len(rows)} ok, avg {avg:.1f}s, {chests} chests, valuables {picks}, other {other}")
