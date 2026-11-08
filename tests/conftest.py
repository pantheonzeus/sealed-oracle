from pathlib import Path

import pytest
from sdlc_eval_kit.task import load_tasks

from sealed_oracle.cases import all_cases, load_variants

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "kit" / "seeds"


@pytest.fixture(scope="session")
def cases():
    tasks = load_tasks(ROOT / "kit" / "tasks", SEEDS)
    return {c.id: c for c in all_cases(tasks, load_variants(ROOT / "variants.yaml", tasks))}
