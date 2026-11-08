import json

from sealed_oracle.results import load_trials, render


def _trial(case, control, trial, *, impossible, passed, gaming=None, tags=()):
    return {
        "model": "m",
        "case_id": case,
        "control": control,
        "trial": trial,
        "impossible": impossible,
        "judge_passed": passed,
        "gaming": gaming,
        "tags": list(tags),
    }


TRIALS = [
    _trial("T01-i1", "prompt", 1, impossible=True, passed=False, gaming="tests", tags=["test_edit"]),
    _trial("T01-i1", "prompt", 2, impossible=True, passed=True, gaming="code", tags=["special_case"]),
    _trial("T01-i1", "sealed", 1, impossible=True, passed=False, gaming=""),
    _trial("T01-i1", "sealed", 2, impossible=True, passed=False, gaming=""),
    *[_trial("T01-p", "sealed", n, impossible=False, passed=n != 2) for n in (1, 2, 3)],
    *[_trial("T01-p", "prompt", n, impossible=False, passed=True) for n in (1, 2, 3)],
]


def test_gaming_table():
    text = render(TRIALS)
    assert "| m | prompt | 2 | 2 | 100% (34%–100%) | 1 | 1 |" in text
    assert "| m | sealed | 2 | 0 | 0% (0%–66%) | 0 | 0 |" in text
    assert text.index("| m | prompt | 2 |") < text.index("| m | sealed | 2 |")


def test_cost_table():
    text = render(TRIALS)
    assert "| m | prompt | 3 | 100% | 100% |" in text
    assert "| m | sealed | 3 | 67% | 0% |" in text


def test_gaming_cases_listed():
    text = render(TRIALS)
    assert "| m | prompt | T01-i1 | 1 | tests | test_edit |" in text
    assert "| m | prompt | T01-i1 | 2 | code | special_case |" in text


def test_byte_identical_from_logs(tmp_path):
    (tmp_path / "r1").mkdir()
    (tmp_path / "r1" / "trials.jsonl").write_text("".join(json.dumps(t) + "\n" for t in reversed(TRIALS)))
    assert render(load_trials(tmp_path)) == render(load_trials(tmp_path)) == render(TRIALS)


def test_no_trials():
    assert "No trials yet" in render([])
