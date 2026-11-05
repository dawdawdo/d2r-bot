"""config.local.yaml holds what differs per machine (GLaDOS: Proton paths)."""
from pathlib import Path

from bot.config import load_config


def _write(folder, text, name="config.yaml"):
    p = folder / name
    p.write_text(text, encoding="utf-8")
    return p


def test_local_file_overrides_only_what_it_names(tmp_path):
    saves = tmp_path / "linux_saves"
    path = _write(tmp_path, "game: {exe: win.exe, character: Blizzaga}\npaths: {save_dir: elsewhere}\n")
    _write(tmp_path, f"game: {{exe: linux.exe}}\npaths: {{save_dir: '{saves.as_posix()}'}}\n", "config.local.yaml")
    cfg = load_config(path)
    assert cfg["game"] == {"exe": "linux.exe", "character": "Blizzaga"}
    assert cfg["paths"]["save_dir"] == Path(saves)


def test_no_local_file_is_fine(tmp_path):
    path = _write(tmp_path, "game: {exe: win.exe}\n")
    assert load_config(path)["game"]["exe"] == "win.exe"
