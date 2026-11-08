"""Command line: sealed-oracle {validate,check-variants,run,judge,self-check,results}."""

import argparse
import json
import sys
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

from sdlc_eval_kit.score import materialize
from sdlc_eval_kit.task import TaskError, load_tasks

from sealed_oracle.cases import Case, VariantError, all_cases, load_variants
from sealed_oracle.judge import judge, self_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sealed-oracle", description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="repo root holding variants.yaml, kit/, runs/")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate variants.yaml against the kit's tasks")
    sub.add_parser("check-variants", help="each flip fails exactly one test on the reference; possible cases pass")
    run_cmd = sub.add_parser("run", help="run an agent on cases under controls, k trials each")
    run_cmd.add_argument("--model", required=True, help="litellm model name, e.g. ollama_chat/qwen3-coder:30b")
    run_cmd.add_argument("--cases", nargs="*", default=[], help="case ids (default: all)")
    run_cmd.add_argument("--controls", nargs="*", default=[], help="prompt, readonly, sealed (default: all)")
    run_cmd.add_argument("-k", type=int, default=3, help="trials per case and control")
    run_cmd.add_argument("--step-limit", type=int, default=50, help="model calls per trial")
    run_cmd.add_argument("--run-id", help="default: <date>-<model>; an existing run id resumes it")
    judge_cmd = sub.add_parser("judge", help="grade a workspace with pristine tests and config, print JSON")
    judge_cmd.add_argument("case_id")
    judge_cmd.add_argument("workspace", type=Path)
    self_cmd = sub.add_parser("self-check", help="the workspace's own pytest run as the agent left it, print JSON")
    self_cmd.add_argument("workspace", type=Path)
    sub.add_parser("results", help="write RESULTS.md from runs/")
    args = parser.parse_args(argv)

    if args.command == "self-check":
        print(json.dumps({"self_green": self_check(args.workspace)}))
        return 0
    if args.command == "results":
        from sealed_oracle.results import load_trials, render

        (args.root / "RESULTS.md").write_text(render(load_trials(args.root / "runs")), encoding="utf-8")
        print(f"wrote {args.root / 'RESULTS.md'}")
        return 0
    root = args.root
    seeds = root / "kit" / "seeds"
    try:
        tasks = load_tasks(root / "kit" / "tasks", seeds)
        cases = all_cases(tasks, load_variants(root / "variants.yaml", tasks))
    except (TaskError, VariantError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    by_id = {c.id: c for c in cases}

    if args.command == "validate":
        print(f"{len(cases)} cases valid ({sum(c.impossible for c in cases)} impossible)")
        return 0
    if args.command == "check-variants":
        return _check_variants(cases, seeds)
    if args.command == "judge":
        if args.case_id not in by_id:
            print(f"unknown case: {args.case_id}", file=sys.stderr)
            return 2
        verdict = judge(by_id[args.case_id], args.workspace, seeds)
        print(json.dumps(asdict(verdict) | {"passed": verdict.passed}))
        return 0

    from sdlc_eval_kit.runner import RunConfig, default_run_id

    from sealed_oracle.runner import CONTROLS, run

    unknown = sorted(set(args.cases) - set(by_id)) + sorted(set(args.controls) - set(CONTROLS))
    if unknown:
        print(f"unknown case or control: {', '.join(unknown)}", file=sys.stderr)
        return 2
    selected = [c for c in cases if not args.cases or c.id in args.cases]
    cfg = RunConfig(model=args.model, k=args.k, step_limit=args.step_limit)
    run_id = args.run_id or default_run_id(args.model, date.today())
    run(selected, args.controls or list(CONTROLS), cfg, root.resolve(), run_id)
    return 0


def _check_variants(cases: list[Case], seeds: Path) -> int:
    """Possible cases pass on the reference. Each impossible case fails on the seed and on the
    reference, where exactly one test fails and the seed's own tests still pass."""
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for case in cases:
            ref = judge(case, materialize(case.task, seeds, Path(tmp) / case.id / "ref", True), seeds)
            problems = []
            if not case.impossible:
                if not ref.passed:
                    problems.append("reference fails")
            else:
                base = judge(case, materialize(case.task, seeds, Path(tmp) / case.id / "base", False), seeds)
                if base.task.passed:
                    problems.append("passes on the seed")
                if ref.task.passed:
                    problems.append("passes on the reference")
                elif ref.task.failed != 1:
                    problems.append(f"{ref.task.failed} tests fail on the reference, expected 1")
                if not ref.visible.passed:
                    problems.append("seed's own tests fail on the reference")
            bad += bool(problems)
            print(f"{'FAIL' if problems else 'ok  '} {case.id} {'; '.join(problems)}".rstrip())
    print(f"{len(cases) - bad}/{len(cases)} cases sound")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
