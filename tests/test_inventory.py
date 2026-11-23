from pathlib import Path

import cv2

from bot.config import load_config
from bot.vision.inventory import protected_cells, scan

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "inventory"
KEY = cv2.imread(str(Path(__file__).resolve().parent.parent / "bot" / "assets" / "templates" / "inv_key.png"))
PROT = protected_cells(load_config()["inventory"]["protected"])
OLD_PROT = protected_cells([[3, 0, 7, 4], [2, 2, 1, 2]])  # Stephen's layout when the older fixtures were taken
PROT_1103 = protected_cells([[4, 0, 6, 4], [3, 1, 1, 3]])  # 2026-11-03 respec layout
PROT_1115 = protected_cells([[5, 0, 5, 4], [4, 1, 1, 1], [4, 3, 1, 1]])  # 2026-11-15 layout


def test_eight_key_stacks_and_a_rune():
    inv = scan(cv2.imread(str(FIX / "keys8_hel.png")), KEY, OLD_PROT)
    assert sorted(inv["key"]) == [(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1)]
    assert inv["other"] == [(1, 3)]  # Hel rune
    assert inv["empty"] == [(0, 0)]


def test_helm_rune_key_and_empties():
    inv = scan(cv2.imread(str(FIX / "stash_shared_helm.png")), KEY, OLD_PROT)
    assert inv["key"] == [(2, 1)]
    assert sorted(inv["other"]) == [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)]
    assert sorted(inv["empty"]) == [(0, 2), (0, 3), (1, 2), (1, 3)]


def test_protected_cells_1115():
    assert len(PROT_1115) == 22 and (4, 1) in PROT_1115 and (4, 3) in PROT_1115 and (9, 3) in PROT_1115
    assert (4, 0) not in PROT_1115 and (4, 2) not in PROT_1115 and not any(c == 3 for c, _ in PROT_1115)


def test_layout_20261119_protects_gheeds_in_col_4_and_the_skull():
    """2026-11-19: after Stephen played, Gheed's Fortune sat in col 4 rows 0-2 and a Flawless Skull at (3,3); the
    11-15 box let the stowaway stash both. Loot here: keys (3,2) and (0,3), rune (1,3), sapphire (2,3)."""
    assert len(PROT) == 25 and (3, 3) in PROT and all((4, r) in PROT for r in range(4))
    inv = scan(cv2.imread(str(FIX / "layout_20261119.png")), KEY, PROT)
    assert sorted(inv["key"]) == [(0, 3), (3, 2)]
    assert sorted(inv["other"]) == [(1, 3), (2, 3)]


def test_layout_20261115_sees_keys_and_loot_in_cols_3_4():
    """2026-11-15: the 11-03 box hid key stacks in col 3 (the bot kept buying keys, 199 went to shared page 1) and
    loot in col 4 (rune, diamond never stashed). Stephen's own items there: skull (4,1), small charm (4,3)."""
    inv = scan(cv2.imread(str(FIX / "layout_20261115.png")), KEY, PROT_1115)
    assert inv["key"] == [(3, 0), (3, 1)]
    assert sorted(inv["other"]) == [(2, 3), (3, 2), (3, 3), (4, 0), (4, 2)]


def test_current_layout_touches_none_of_stephens_items():
    """2026-11-03 after the respec: every charm, tome, the skull and the cube are protected; the key is the key."""
    inv = scan(cv2.imread(str(FIX / "respec_20261103.png")), KEY, PROT_1103)
    assert inv["key"] == [(3, 0)]
    assert inv["other"] == []
    assert sorted(inv["empty"]) == [(c, r) for c in range(3) for r in range(4)]


def test_weapon_set_tabs():
    from bot.vision.inventory import weapon_set

    assert weapon_set(cv2.imread(str(FIX / "respec_20261103.png"))) == 2
    assert weapon_set(cv2.imread(str(FIX / "weapons_cta_20261103.png"))) == 1


def test_runes_added_hel():
    from bot.vision.inventory import runes_added

    a = cv2.imread(str(FIX / "runes_tab_before.png"))
    b = cv2.imread(str(FIX / "runes_tab_hel_added.png"))
    assert runes_added(a, b) == ["Hel"]
    assert runes_added(a, a) == []


def test_session_start_protects_charms_found_in_the_save():
    """2026-11-19: Gheed's (cm3) in col 4 and the old box: the save tells us where his charms really are."""
    from bot.run import protect_own_items
    from bot.vision.inventory import protected_cells
    cfg = {"inventory": {"protected": [[5, 0, 5, 4], [4, 1, 1, 1], [4, 3, 1, 1]]}}
    items = [("cm3", 4, 0), ("cm3", 5, 0), ("cm1", 4, 3), ("skl", 3, 3), ("key", 3, 2), ("box", 8, 2), ("tbk", 9, 0)]
    protect_own_items(cfg, items)
    cells = protected_cells(cfg["inventory"]["protected"])
    assert {(4, 0), (4, 1), (4, 2)} <= cells and (3, 2) not in cells
    assert (3, 3) in cells  # the skull too, since 2026-11-21: everything in the save but the working key stack


def test_session_start_protects_everything_but_the_working_key_stack(monkeypatch, tmp_path):
    """Stephen 2026-11-21: his skull and extra key stacks moved while he played; nothing of his may be stashed or
    dropped. The working key stack (state key_cell) stays the bot's."""
    from bot import state
    from bot.run import protect_own_items
    from bot.vision.inventory import protected_cells
    monkeypatch.setattr(state, "PATH", tmp_path / "state.json", raising=False)
    monkeypatch.setattr(state, "load", lambda: {"key_cell": [3, 2]})
    cfg = {"inventory": {"protected": [[4, 0, 6, 4], [3, 3, 1, 1]]}}
    items = [("key", 4, 0), ("key", 4, 1), ("skl", 4, 2), ("key", 3, 3), ("key", 3, 2), ("cm3", 5, 0),
             ("box", 8, 2), ("rin", 0, 0), ("uap", 1, 0)]
    protect_own_items(cfg, items)
    cells = protected_cells(cfg["inventory"]["protected"])
    assert (3, 2) not in cells  # her working key stack
    assert {(4, 0), (4, 1), (4, 2), (3, 3), (0, 0)} <= cells
    assert (1, 0) in cells  # a helm in col 1: 2x2 when the tables are there, its corner at least


def test_bot_loot_since_stephen_last_played_is_not_protected(monkeypatch, tmp_path):
    """2026-11-23: back-to-back sessions carry the inventory baseline (Stephen's layout); what the bot picked up since
    then goes to the stowaway instead of being protected at each restart."""
    import time

    from bot import state
    from bot.run import protect_own_items
    from bot.vision.inventory import protected_cells
    base = [["skl", 4, 2], ["cm3", 5, 0], ["key", 4, 1]]
    saved = {}
    monkeypatch.setattr(state, "load", lambda: {"key_cell": [4, 1], "inventory_baseline": base,
                                                "session_ended_at": time.time() - 60})
    monkeypatch.setattr(state, "save", lambda d: saved.update(d))
    cfg = {"inventory": {"protected": [[4, 0, 6, 4]]}}
    items = [("skl", 4, 2), ("cm3", 5, 0), ("key", 4, 1), ("gzv", 0, 0), ("tes", 1, 0)]
    protect_own_items(cfg, items)
    cells = protected_cells(cfg["inventory"]["protected"])
    assert (0, 0) not in cells and (1, 0) not in cells  # the night's gem and essence: the stowaway's
    # after a long gap (Stephen may have played) everything is protected again and becomes the new baseline
    monkeypatch.setattr(state, "load", lambda: {"key_cell": [4, 1], "inventory_baseline": base,
                                                "session_ended_at": time.time() - 3600})
    cfg = {"inventory": {"protected": [[4, 0, 6, 4]]}}
    protect_own_items(cfg, items)
    assert (0, 0) in protected_cells(cfg["inventory"]["protected"])
    assert saved["inventory_baseline"] == [list(i) for i in items]
