"""Item pictures for the website's stash view, read from D2R's game archive.

Stephen OK'd reading the game files for the website (2026-11-27); the bot itself stays pixels-only. Read-only: nothing
is ever written into the game folder.

    bash armory/build_casclib.sh                       # once: armory/work/libcasc.so
    python armory/icons.py [--game DIR] [--out DIR]

Writes one WebP per item picture to --out (default ../convergentblue/public/bot/items/<asset>.webp, e.g.
ring/ring3.webp; 98 px per inventory cell, transparent background), tinted copies <asset>~<colour>.webp for the
uniques and set items the game recolours (Harlequin Crest's green hood, the sunder charms ...), and
armory/icon_map.json (item code / unique / set -> picture), which gen.py uses to give each item its `ic`.
Rerun after a game patch adds items.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import struct
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import casc  # noqa: E402

GAME = "/data/steam/games/Diablo II Resurrected"
OUT = HERE.parent.parent / "convergentblue" / "public" / "bot" / "items"
UI = "data:data\\hd\\global\\ui\\items\\"
EXCEL = "data:data\\global\\excel\\"
# Items whose picture is one of several, picked per item (the save's variable_gfx_id k -> "<asset>{k+1}"; checked
# against Blizzaga's inventory on screen). The sprite files hold exactly these counts (ring1-5, amulet1-3,
# charm_small1-3, perfect_diamond1-6 = jewel ...).
VARIANTS = {"rin": 5, "amu": 3, "vip": 3, "cm1": 3, "cm2": 3, "cm3": 3, "jew": 6}
# Unique / set colour tints (the tables' invtransform), as RGB gains on the picture's luminance: the game multiplies
# brightness by a colour. lblu and cgrn are fitted to Cold Rupture and Harlequin Crest on screen (2026-11-27), the
# rest are estimates from the colour names. Bases with InvTrans 0 (rings, amulets, small charms, jewels) never tint.
TINT = {"lblu": (0.83, 1.28, 1.78), "cgrn": (0.05, 2.13, 0.20), "cblu": (0.15, 0.95, 2.1), "dblu": (0.35, 0.55, 1.4),
        "cred": (2.2, 0.2, 0.15), "lred": (1.8, 0.8, 0.75), "dred": (1.25, 0.3, 0.25), "lgrn": (0.9, 1.7, 0.8),
        "dgrn": (0.3, 1.0, 0.3), "lyel": (1.7, 1.6, 0.6), "dyel": (1.2, 1.1, 0.35), "lgld": (1.6, 1.3, 0.7),
        "dgld": (1.2, 0.9, 0.4), "oran": (1.8, 1.0, 0.35), "lpur": (1.4, 0.9, 1.7), "dpur": (0.9, 0.45, 1.2),
        "whit": (1.5, 1.5, 1.5), "bwht": (1.8, 1.8, 1.8), "lgry": (1.15, 1.15, 1.15), "dgry": (0.7, 0.7, 0.7),
        "blac": (0.4, 0.4, 0.4)}
ikey = lambda n: re.sub(r"[^a-z0-9]+", "_", n.lower().replace("'", "")).strip("_")  # gen.py uses the same


def load_json(st: casc.Storage, name: str) -> dict:
    """data/hd/items/<name>: a list of one-key dicts -> one dict."""
    return {k: v for d in json.loads(st.read("data:data\\hd\\items\\" + name).decode("utf-8-sig")) for k, v in d.items()}


def excel(st: casc.Storage, name: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(st.read(EXCEL + name).decode("latin-1")), delimiter="\t"))


def decode(b: bytes) -> np.ndarray:
    """A D2R .sprite (SpA1, version 31: uncompressed RGBA) -> its first frame as BGRA."""
    magic, ver, frame_w, total_w, h = struct.unpack_from("<4sHHII", b, 0)
    if magic != b"SpA1" or ver != 31:
        raise ValueError(f"unsupported sprite {magic!r} v{ver}")
    px = np.frombuffer(b, np.uint8, total_w * h * 4, 40).reshape(h, total_w, 4)
    return np.ascontiguousarray(px[:, :frame_w, [2, 1, 0, 3]])


def tint(img: np.ndarray, code: str) -> np.ndarray:
    lum = img[:, :, :3].astype(np.float32) @ np.array([0.114, 0.587, 0.299], np.float32)
    r, g, b = TINT[code]
    out = img.copy()
    out[:, :, :3] = np.clip(lum[:, :, None] * np.array([b, g, r], np.float32), 0, 255).astype(np.uint8)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game", default=GAME)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--quality", type=int, default=90, help="WebP quality (alpha is kept)")
    a = ap.parse_args()

    st = casc.Storage(a.game)
    sprites = {n[len(UI):-len(".sprite")].replace("\\", "/"): n for n in st.find(UI + "*")
               if n.endswith(".sprite") and not n.endswith(".lowend.sprite")}
    by_asset = {"/".join(k.split("/")[-2:]): n for k, n in sprites.items()}  # items.json names the last two parts
    if len(by_asset) != len(sprites):
        raise SystemExit("two sprites share an asset name: the output layout needs a rethink")

    norm = lambda x: "/".join(x.split("/")[-2:])  # some entries say "../misc/body_part/fragment_cold"
    items = {k: norm(v["asset"]) for k, v in load_json(st, "items.json").items()}
    uniques, sets = ({k: {t: norm(x) for t, x in v.items()} for k, v in load_json(st, f).items()}
                     for f in ("uniques.json", "sets.json"))
    invtrans = {r["code"] for f in ("armor.txt", "weapons.txt", "misc.txt") for r in excel(st, f)
                if r.get("code") and r.get("InvTrans") not in ("", "0", None)}
    tints = {"uniques": {}, "sets": {}}
    jobs = {}  # tinted file -> (source asset, colour)
    for kind, table, code_col, names in (("uniques", "uniqueitems.txt", "code", uniques), ("sets", "setitems.txt", "item", sets)):
        for r in excel(st, table):
            col, code, k = r.get("invtransform", ""), r.get(code_col, ""), ikey(r.get("index", ""))
            if not col or code not in invtrans or col not in TINT:
                continue
            tints[kind][k] = col
            base = items.get(code)
            srcs = set((names.get(k) or names.get("the_" + k) or {}).values()) | ({base} if base else set())
            if base and code in VARIANTS:
                srcs |= {f"{base}{n}" for n in range(1, VARIANTS[code] + 1)}
            jobs.update({f"{s}~{col}": (s, col) for s in srcs if s in by_asset})

    n = size = 0

    def write(name: str, img: np.ndarray) -> None:
        nonlocal n, size
        out = a.out / f"{name}.webp"
        out.parent.mkdir(parents=True, exist_ok=True)
        ok, buf = cv2.imencode(".webp", img, [cv2.IMWRITE_WEBP_QUALITY, a.quality])
        if not ok:
            raise SystemExit(f"WebP encode failed: {name}")
        out.write_bytes(buf.tobytes())
        n += 1
        size += len(buf)

    cache = {}
    for asset in sorted(by_asset):  # every item picture, so items found later already have one
        cache[asset] = decode(st.read(by_asset[asset]))
        write(asset, cache[asset])
    for name, (src, col) in sorted(jobs.items()):
        write(name, tint(cache[src], col))
    st.close()

    (HERE / "icon_map.json").write_text(json.dumps(
        {"items": items, "uniques": uniques, "sets": sets, "variants": VARIANTS, "invtrans": sorted(invtrans),
         "tints": tints}, indent=0, sort_keys=True) + "\n")
    print(f"{n} pictures ({len(jobs)} tinted), {size / 1e6:.1f} MB -> {a.out}; map -> {HERE / 'icon_map.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
