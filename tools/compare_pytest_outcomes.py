#!/usr/bin/env python3
"""Fail closed on pytest outcome regressions while exposing existing failures.

The full historical suite is not green: unchanged failures, setup errors and
collection errors may remain only when the same occurrence existed in the
baseline. New tests must pass, including tests outside the focused CI lists.
Focused release gates use ``require-pass`` and permit no failures or skips.

Duplicate JUnit identities are matched by their document occurrence number.
They are never collapsed into a dictionary keyed only by classname/name.
Fatal pytest exit codes are rejected even when JUnit appears complete.
An old synthetic module collection error may disappear only when that exact
module now supplies executed passing tests and no nonpassing/collection cases.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


@dataclass(frozen=True, order=True)
class CaseId:
    classname: str
    name: str
    occurrence: int

    def display(self) -> str:
        return f"{self.classname}::{self.name} [occurrence {self.occurrence}]"


@dataclass(frozen=True)
class Outcome:
    identity: CaseId
    state: str
    collection_error: bool = False


@dataclass(frozen=True)
class Report:
    path: str
    exit_code: int
    cases: tuple[Outcome, ...]
    problems: tuple[str, ...] = ()

    def counts(self) -> dict[str, int]:
        return dict(Counter(case.state for case in self.cases))


@dataclass(frozen=True)
class Comparison:
    problems: tuple[str, ...]
    known_baseline_failures: tuple[str, ...]
    improvements: tuple[str, ...]
    new_passing: tuple[str, ...]
    resolved_collection_errors: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.problems


def read_report(path: str | Path, exit_code: int) -> Report:
    """Read a complete pytest JUnit report without losing duplicate cases."""
    path = Path(path)
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        return Report(str(path), exit_code, (), (f"cannot read JUnit report: {exc}",))
    if root.tag not in {"testsuite", "testsuites"}:
        return Report(str(path), exit_code, (), (f"unexpected JUnit root: {root.tag}",))

    seen: Counter[tuple[str, str]] = Counter()
    cases = []
    problems = []
    for case in root.iter("testcase"):
        key = (case.get("classname", ""), case.get("name", ""))
        if not key[1]:
            problems.append("testcase has no name")
        seen[key] += 1
        error = case.find("error")
        state = (
            "error" if error is not None else
            "failed" if case.find("failure") is not None else
            "skipped" if case.find("skipped") is not None else
            "passed"
        )
        # pytest uses message="collection failure". Preserve the distinction
        # from runtime/setup errors so a new collection failure cannot hide
        # behind an old error with the same JUnit identity.
        collection_error = error is not None and (
            "collection failure" in error.get("message", "").lower()
            or "collecterror" in error.get("type", "").lower()
        )
        cases.append(Outcome(CaseId(*key, seen[key]), state, collection_error))
    # A suite-level error has no case identity against which to establish a
    # known baseline failure, so it must never be silently discarded.
    for suite in root.iter("testsuite"):
        if suite.find("error") is not None or suite.find("failure") is not None:
            problems.append(f"suite-level error without testcase: {suite.get('name', '')}")
    if not cases:
        problems.append("JUnit report contains no testcases")
    return Report(str(path), exit_code, tuple(cases), tuple(problems))


def report_problems(report: Report, label: str) -> list[str]:
    problems = [f"{label}: {problem}" for problem in report.problems]
    if report.exit_code not in {0, 1}:
        problems.append(f"{label}: fatal pytest exit code {report.exit_code}")
    has_failures = any(case.state in {"failed", "error"} for case in report.cases)
    if report.exit_code == 0 and has_failures:
        problems.append(f"{label}: pytest exited 0 but JUnit contains failures/errors")
    if report.exit_code == 1 and not has_failures:
        problems.append(f"{label}: pytest exited 1 without a recorded failure/error")
    return problems


def compare_reports(before: Report, after: Report) -> Comparison:
    problems = report_problems(before, "baseline") + report_problems(after, "current")
    old_cases = {case.identity: case for case in before.cases}
    new_cases = {case.identity: case for case in after.cases}
    known, improvements, new_passing, resolved = [], [], [], []
    for identity, old in old_cases.items():
        name = identity.display()
        new = new_cases.get(identity)
        if new is None:
            # Pytest's import/collection failure is a synthetic ::module row,
            # not an executed test. A fixed top-level assertion module can now
            # collect genuine named tests instead. Require exact module identity
            # and a fully passing candidate module; deletion/renaming/skipping
            # is never evidence of resolution. Duplicate old collection rows
            # remain fail-closed because occurrence coverage would be ambiguous.
            module = identity.name
            if old.collection_error and not identity.classname and identity.occurrence == 1:
                prior_errors = [case for case in before.cases if case.collection_error
                                and not case.identity.classname and case.identity.name == module]
                candidates = [case for case in after.cases if case.identity.classname == module
                              or case.identity.classname.startswith(module + ".")]
                remaining_collection = any(case.collection_error and (
                    (not case.identity.classname and (case.identity.name == module
                        or case.identity.name.startswith(module + ".")))
                    or case in candidates
                ) for case in after.cases)
                exact_module_collected = any(case.identity.classname == module for case in candidates)
                if len(prior_errors) == 1 and exact_module_collected and not remaining_collection and all(
                    case.state == "passed" and not case.collection_error for case in candidates
                ):
                    resolved.append(f"{module}: collection error resolved; {len(candidates)} passing tests executed")
                    continue
            problems.append(f"missing existing testcase: {name}")
            continue
        if new.collection_error and not old.collection_error:
            problems.append(f"new collection error: {name}")
        elif new.state == old.state:
            if new.state in {"failed", "error"}:
                kind = "collection error" if new.collection_error else new.state
                known.append(f"{name}: {kind}")
        elif new.state == "passed" or (old.state == "error" and new.state == "failed"):
            improvements.append(f"{name}: {old.state} -> {new.state}")
            if new.state == "failed":
                known.append(f"{name}: failed (baseline error)")
        else:
            # In particular, skipping a previously failing/erroring test does
            # not qualify as fixing it. Existing baseline skips may remain.
            problems.append(f"regressed testcase: {name}: {old.state} -> {new.state}")

    for identity, new in new_cases.items():
        if identity in old_cases:
            continue
        name = identity.display()
        if new.state == "passed":
            new_passing.append(name)
        else:
            kind = "collection error" if new.collection_error else new.state
            problems.append(f"new testcase must pass: {name}: {kind}")
    return Comparison(tuple(problems), tuple(known), tuple(improvements), tuple(new_passing), tuple(resolved))


def require_all_pass(report: Report) -> Comparison:
    problems = report_problems(report, "focused gate")
    problems.extend(
        f"focused testcase must pass: {case.identity.display()}: {case.state}"
        for case in report.cases if case.state != "passed"
    )
    return Comparison(tuple(problems), (), (), ())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("compare", help="reject regressions against a recorded baseline")
    compare.add_argument("--before", required=True, type=Path)
    compare.add_argument("--before-exit-code", required=True, type=int)
    compare.add_argument("--after", required=True, type=Path)
    compare.add_argument("--after-exit-code", required=True, type=int)
    focused = commands.add_parser("require-pass", help="require every focused testcase to pass")
    focused.add_argument("--report", required=True, type=Path)
    focused.add_argument("--exit-code", required=True, type=int)
    for command in (compare, focused):
        command.add_argument("--label", default="pytest")
        command.add_argument("--json-report", type=Path)
    args = parser.parse_args(argv)
    if args.command == "compare":
        before = read_report(args.before, args.before_exit_code)
        after = read_report(args.after, args.after_exit_code)
        result = compare_reports(before, after)
        counts = {"baseline": before.counts(), "current": after.counts()}
    else:
        report = read_report(args.report, args.exit_code)
        result = require_all_pass(report)
        counts = {"current": report.counts()}
    payload = {"label": args.label, "passed": result.passed, "counts": counts, **asdict(result)}
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"{args.label}: {'PASS' if result.passed else 'FAIL'}; outcomes: {counts}")
    print(f"new passing: {len(result.new_passing)}; improvements: {len(result.improvements)}")
    print(f"resolved collection errors: {len(result.resolved_collection_errors)}")
    for resolution in result.resolved_collection_errors:
        print(f"  RESOLVED COLLECTION ERROR: {resolution}")
    if result.known_baseline_failures:
        print(f"NOT A GREEN SUITE: {len(result.known_baseline_failures)} known baseline failures/errors remain")
        for failure in result.known_baseline_failures:
            print(f"  KNOWN BASELINE: {failure}")
    for problem in result.problems:
        print(f"  ERROR: {problem}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
