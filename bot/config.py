"""Load config.yaml, plus this machine's config.local.yaml if it has one, into a plain dict with expanded paths."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.yaml"


def _merge(base: dict, over: dict) -> dict:
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


_PLATFORMS = {"win32", "linux", "darwin"}
_WIN_VAR = re.compile(r"%([^%]+)%")


def _expand(value: str) -> str:
    """Expand ~, $VAR and Windows-style %VAR% on any OS."""
    value = _WIN_VAR.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    return os.path.expandvars(os.path.expanduser(value))


# config.yaml `features:` (Stephen 2026-11-20: every extra that trades run time / safety for loot is one switch) -> the
# keys the code reads. A feature left out of the block keeps whatever its own section says.
FEATURES = {
    "gold_pickup": ("loot", "pick_gold"),
    "gold_deposit": ("stash", "deposit"),
    "weapon_racks": ("lk", "racks"),
    "armor_stands": ("lk", "armor_stands"),
    "gems_and_bases": ("loot", "pick_white_other"),
    "spare_rejuvs": ("loot", "rejuv_spares"),
    "war_cries": ("lk", "war_cries"),
    "cube": ("cube", "enabled"),
    "act4_exit": ("game", "act4_exit"),
    "wait_out_terror": ("game", "skip_terror"),
    "skip_huts": ("lk", "skip_targets"),
    "save_rejuvs": ("town", "lk_save_rejuvs"),
}


def apply_features(cfg: dict) -> None:
    feats = cfg.get("features") or {}
    unknown = set(feats) - set(FEATURES) - {"charms"}
    if unknown:
        raise ValueError(f"config features: unknown {sorted(unknown)} (known: {sorted(FEATURES)}, charms)")
    for name, (section, key) in FEATURES.items():
        if name in feats:
            cfg.setdefault(section, {})[key] = feats[name]
    if "charms" in feats:  # blue labels that say "Charm" (loot.pick "magic")
        pick = [k for k in cfg.setdefault("loot", {}).get("pick", []) if k != "magic"]
        cfg["loot"]["pick"] = pick + ["magic"] if feats["charms"] else pick


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    """config.local.yaml sits beside `path` and isn't in git: what differs per machine (game and save paths)."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    local = path.with_name(f"{path.stem}.local{path.suffix}")
    if local.exists():
        _merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    if "risk" in cfg:  # one switch for what trades her safety for speed (config.yaml risk_levels)
        _merge(cfg, cfg["risk_levels"][cfg["risk"]])
    apply_features(cfg)
    paths = cfg.setdefault("paths", {})
    for key, value in paths.items():
        if isinstance(value, dict):  # per-platform value, keyed by sys.platform ("win32", "linux")
            value = value[sys.platform]
        p = Path(_expand(str(value)))
        paths[key] = p if p.is_absolute() else ROOT / p
    game = cfg.get("game") or {}
    for key, value in game.items():
        if isinstance(value, dict) and set(value) <= _PLATFORMS:
            game[key] = value.get(sys.platform)
    if "character" in game:
        game["default_character"] = game["character"]
    if os.environ.get(CHARACTER_ENV) and "character" in game:  # tools run as another character (probes, route learning)
        apply_profile(cfg, os.environ[CHARACTER_ENV])
    return cfg


# A session plays one character. game.character (Blizzaga) is the default; a task whose config section names another
# (baal: {character: Smoked}, Stephen's Hammerdin 2026-11-27) runs that character with `profiles.<name>` merged over the
# config: his route (maps/<route>/), hotkeys, buffs. hotkeys.skills is replaced whole (Blizzaga's blizzard: a must not
# leak into his a = Concentration). Tools take the character from the environment: D2R_CHARACTER=Smoked.
CHARACTER_ENV = "D2R_CHARACTER"
REPLACED = (("hotkeys", "skills"), ("inventory", "protected"))


def apply_profile(cfg: dict, character: str | None) -> dict:
    if not character or character == cfg["game"]["character"]:
        return cfg
    prof = (cfg.get("profiles") or {}).get(character)
    if prof is None:
        raise ValueError(f"no config profiles.{character} (known: {sorted(cfg.get('profiles') or {})})")
    import copy

    prof = copy.deepcopy(prof)
    whole = {path: prof[path[0]].pop(path[1]) for path in REPLACED if path[1] in (prof.get(path[0]) or {})}
    _merge(cfg, prof)
    for (sec, key), value in whole.items():
        cfg.setdefault(sec, {})[key] = value
    cfg["game"]["character"] = character
    return cfg


def task_character(cfg: dict, names) -> str:
    """The character the tasks `names` are played with (their config `character`, else game.character)."""
    chars = {(cfg.get(n) or {}).get("character") or cfg["game"].get("default_character") or cfg["game"]["character"]
             for n in names}
    if len(chars) > 1:
        raise ValueError(f"tasks {', '.join(names)} need different characters ({', '.join(sorted(chars))}): "
                         "one character per session")
    return chars.pop() if chars else cfg["game"]["character"]


def for_character(cfg: dict, character: str) -> dict:
    """A copy of `cfg` as `character` plays it (cfg itself unchanged)."""
    import copy

    if character == cfg["game"]["character"]:
        return cfg
    base = copy.deepcopy(cfg)
    if base["game"]["character"] != base["game"].get("default_character", base["game"]["character"]):
        raise ValueError("for_character: cfg already has another character's profile")
    return apply_profile(base, character)
