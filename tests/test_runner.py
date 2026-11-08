import json

import pytest

from sealed_oracle.runner import CONTROLS, _done, brief, prepare
from tests.conftest import SEEDS


def _test_files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("test_*.py"))


def test_prompt_control_exposes_writable_task_tests(cases, tmp_path):
    exposed, copy_in, ro = prepare(cases["T02-i1"], "prompt", SEEDS, tmp_path)
    assert copy_in == exposed and ro is None
    assert "tests/task/test_hidden_t02.py" in _test_files(copy_in)
    assert "(32, 273.16)" in (copy_in / "tests/task/test_hidden_t02.py").read_text()


def test_readonly_control_mounts_tests_instead_of_copying(cases, tmp_path):
    exposed, copy_in, ro = prepare(cases["T02-i1"], "readonly", SEEDS, tmp_path)
    assert not (copy_in / "tests").exists() and _test_files(copy_in) == []
    assert ro == exposed / "tests" and (ro / "task" / "test_hidden_t02.py").is_file()


def test_sealed_control_has_no_test_files(cases, tmp_path):
    exposed, copy_in, ro = prepare(cases["T02-i1"], "sealed", SEEDS, tmp_path)
    assert ro is None and copy_in == exposed
    assert not (copy_in / "tests").exists()
    assert _test_files(copy_in) == [] and not list(copy_in.rglob("conftest.py"))


def test_unknown_control(cases, tmp_path):
    with pytest.raises(ValueError):
        prepare(cases["T02-p"], "honour-system", SEEDS, tmp_path)


def test_brief_differs_only_in_the_test_note(cases):
    texts = {control: brief(cases["T02-i1"], control) for control in CONTROLS}
    assert texts["prompt"] == texts["readonly"]
    assert texts["sealed"].startswith(cases["T02-i1"].task.brief.rstrip())
    assert "no tests" in texts["sealed"] and "tests/task/" in texts["prompt"]


def test_done_keys(tmp_path):
    path = tmp_path / "trials.jsonl"
    path.write_text(json.dumps({"case_id": "T02-i1", "control": "sealed", "model": "m", "trial": 2}) + "\n\n")
    assert _done(path) == {("T02-i1", "sealed", "m", 2)}
