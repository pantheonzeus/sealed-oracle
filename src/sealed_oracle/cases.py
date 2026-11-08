"""Cases: a kit task with its own hidden tests (possible) or with one assertion flipped (impossible)."""

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml
from sdlc_eval_kit.task import Task

FIELDS = ("id", "task", "find", "replace", "contradicts")


class VariantError(ValueError):
    """Raised for a variant that does not match the schema or its task's tests."""


@dataclass(frozen=True)
class Variant:
    id: str
    task: str
    find: str
    replace: str
    contradicts: str

    def new_tokens(self) -> set[str]:
        """Literals the flip introduces, e.g. {"273.16"}: special-casing them in source is a gaming signal."""
        return _tokens(self.replace) - _tokens(self.find)


@dataclass(frozen=True)
class Case:
    task: Task
    variant: Variant | None = None

    @property
    def id(self) -> str:
        return self.variant.id if self.variant else self.task.id.split("-", 1)[0] + "-p"

    @property
    def impossible(self) -> bool:
        return self.variant is not None

    def write_tests(self, dest: Path) -> Path:
        """Copy the task's hidden tests to dest, with the variant's flip applied."""
        shutil.copytree(self.task.hidden_tests, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if self.variant:
            path = _target(self.variant, dest)
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace(self.variant.find, self.variant.replace), encoding="utf-8")
        return dest


def load_variants(path: Path, tasks: list[Task]) -> list[Variant]:
    """Load and validate variants.yaml against the kit's tasks."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise VariantError(f"{path}: expected a list")
    by_id = {t.id: t for t in tasks}
    variants, seen = [], set()
    for entry in data:
        if not isinstance(entry, dict) or sorted(entry) != sorted(FIELDS):
            raise VariantError(f"{path}: every variant needs exactly {', '.join(FIELDS)}: {entry!r}")
        variant = Variant(**{key: str(entry[key]) for key in FIELDS})
        if variant.id in seen:
            raise VariantError(f"{path}: duplicate id {variant.id}")
        seen.add(variant.id)
        if variant.task not in by_id:
            raise VariantError(f"{variant.id}: unknown task {variant.task}")
        if variant.find == variant.replace:
            raise VariantError(f"{variant.id}: find and replace are equal")
        _target(variant, by_id[variant.task].hidden_tests)
        variants.append(variant)
    return variants


def all_cases(tasks: list[Task], variants: list[Variant]) -> list[Case]:
    """One possible case per task, then every impossible variant, in task order."""
    by_id = {t.id: t for t in tasks}
    possible = [Case(t) for t in tasks]
    return possible + [Case(by_id[v.task], v) for v in sorted(variants, key=lambda v: v.id)]


def _target(variant: Variant, tests_dir: Path) -> Path:
    hits = [(p, p.read_text(encoding="utf-8").count(variant.find)) for p in sorted(tests_dir.glob("test_*.py"))]
    total = sum(n for _, n in hits)
    if total != 1:
        raise VariantError(f"{variant.id}: find must occur exactly once in {tests_dir}, found {total}")
    return next(p for p, n in hits if n)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"-?\d+(?:\.\d+)?|\"[^\"]*\"|'[^']*'", text))
