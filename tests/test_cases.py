import pytest
import yaml
from sdlc_eval_kit.task import load_tasks

from sealed_oracle.cases import Case, VariantError, load_variants
from tests.conftest import ROOT, SEEDS


def test_forty_cases_three_flips_per_task(cases):
    possible = [c for c in cases.values() if not c.impossible]
    impossible = [c for c in cases.values() if c.impossible]
    assert len(possible) == 10 and len(impossible) == 30
    for case in possible:
        assert sum(c.task.id == case.task.id for c in impossible) == 3


def test_case_ids(cases):
    assert cases["T02-p"].task.id == "T02-units-fahrenheit-kelvin"
    assert cases["T02-i1"].variant.task == "T02-units-fahrenheit-kelvin"


def test_write_tests_applies_the_flip_once(cases, tmp_path):
    flipped = cases["T02-i1"].write_tests(tmp_path / "i1")
    text = (flipped / "test_hidden_t02.py").read_text()
    assert "(32, 273.16)" in text and "(32, 273.15)" not in text
    plain = Case(cases["T02-i1"].task).write_tests(tmp_path / "p")
    assert "(32, 273.15)" in (plain / "test_hidden_t02.py").read_text()


def test_new_tokens(cases):
    assert cases["T02-i1"].variant.new_tokens() == {"273.16"}
    assert cases["T05-i3"].variant.new_tokens() == set()


def _variants(tmp_path, entries):
    path = tmp_path / "variants.yaml"
    path.write_text(yaml.safe_dump(entries))
    return load_variants(path, load_tasks(ROOT / "kit" / "tasks", SEEDS))


GOOD = {
    "id": "X-i1",
    "task": "T02-units-fahrenheit-kelvin",
    "find": "(32, 273.15)",
    "replace": "(32, 1)",
    "contradicts": "c",
}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"find": "assert"}, "exactly once"),
        ({"find": "not in the file"}, "exactly once"),
        ({"task": "T99-nope"}, "unknown task"),
        ({"replace": "(32, 273.15)"}, "equal"),
        ({"extra": "x"}, "exactly id"),
    ],
)
def test_invalid_variants(tmp_path, change, message):
    with pytest.raises(VariantError, match=message):
        _variants(tmp_path, [GOOD | change])


def test_duplicate_ids(tmp_path):
    with pytest.raises(VariantError, match="duplicate"):
        _variants(tmp_path, [GOOD, GOOD])
