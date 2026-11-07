import pytest

from bot.config import load_config
from bot.tasks import Task, get_task


def test_lk_task_loads_the_route():
    t = get_task("lk", load_config())
    assert isinstance(t, Task) and t.act == 3
    assert [x["name"] for x in t.route["targets"]][:3] == ["east_ne", "east_nw", "east_nw_deep"]


def test_unknown_task():
    with pytest.raises(SystemExit, match="unknown task"):
        get_task("pindle", load_config())
