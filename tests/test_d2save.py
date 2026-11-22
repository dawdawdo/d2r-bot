"""bot/d2save.py: the pure-Python save reader must give exactly what the Rust d2dump gave.

Save files are not in git (*.d2s is ignored), so the comparisons read the local session-start backups and skip when
there are none (or, for the d2dump half, when the Linux binary can't run here). 2026-11-22: 608 unique backup files
(15,910 copies) compared identical, field for field.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

from bot import d2save, mf
from bot.config import ROOT

EXE = ROOT / "armory" / "work" / "d2dump"


def _backups(n=3):
    root = ROOT / "backups"
    dirs = sorted(p for p in root.glob("2*") if p.is_dir() and any(p.glob("*.d2s"))) if root.exists() else []
    return dirs[-n:]


def _d2dump_runs() -> bool:
    return os.name == "posix" and EXE.exists() and os.access(EXE, os.X_OK)


def test_bit_reader_is_lsb_first():
    r = d2save.Reader(bytes([0b10110101, 0xFF]))
    assert r.bits(3) == 0b101 and r.bits(5) == 0b10110 and r.bits(8) == 0xFF
    with pytest.raises(EOFError):
        r.bits(1)
    assert d2save.Reader(bytes([0b11101])).signed(5) == -3


def test_huffman_decodes_item_codes():
    # encode "key " / "r30 " with the table (MSB-first codes, written LSB-first) and decode them back
    enc = {s: (c, n) for s, c, n in d2save._HUFF}
    for code in ("key ", "r30 ", "cm3 ", "jew "):
        bits = "".join(format(enc[ch][0], f"0{enc[ch][1]}b") for ch in code)
        val = int(bits[::-1], 2) if bits else 0
        r = d2save.Reader(val.to_bytes(8, "little"))
        assert d2save.code_str(d2save._huffman(r)) == code.strip()


def test_item_sizes_come_from_the_tables():
    assert mf.item_size("cm3") == (1, 3)
    assert mf.item_size("key") == (1, 1)
    assert mf.item_size("utp") == (2, 3)  # Archon Plate
    assert mf.item_size("zzz") == (1, 1)  # unknown: top-left cell only


@pytest.mark.skipif(not _backups(), reason="no save backups on this machine")
def test_backups_parse_and_inventory_fits_the_grid():
    for b in _backups():
        for f in b.glob("*.d2s"):
            save = d2save.read_d2s(f)
            cells = set()
            for code, c, r in mf.inventory_items(save):
                w, h = mf.item_size(code)
                assert 0 <= c and c + w <= 10 and 0 <= r and r + h <= 4, (f.name, code, c, r)
                mine = {(c + i, r + j) for i in range(w) for j in range(h)}
                assert not cells & mine, (f.name, code, c, r)  # no two items in one cell
                cells |= mine
        for f in b.glob("*.d2i"):
            d2save.read_d2i(f)


@pytest.mark.skipif(not (_backups() and _d2dump_runs()), reason="needs save backups and the Linux d2dump")
def test_same_json_as_d2dump():
    for b in _backups(2):
        for f in sorted(b.glob("*.d2s")) + sorted(b.glob("*.d2i")):
            mode = "c" if f.suffix == ".d2s" else "s"
            rust = json.loads(subprocess.run([str(EXE), mode, str(f)], capture_output=True, check=True).stdout)
            mine = d2save.read_d2s(f) if mode == "c" else d2save.read_d2i(f)
            assert json.loads(json.dumps(mine)) == rust, f.name
