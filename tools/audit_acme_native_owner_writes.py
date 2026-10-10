#!/usr/bin/env python3
"""Diagnose literal native-state writes from Extended; --strict makes them a CI gate.

Scope: literal ACM core/airway/breathing/circulation/damage/CBRN and ACE keys in setVariable or direct
calls to ACME_fnc_setVarNet/Approx. Comments, ordinary strings, reads and native
setter calls are excluded. This lexical check is not a data-flow analysis of
computed keys/aliased functions or a policy for legacy bare global assignments.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "addons" / "acm_extended" / "functions"
sys.path.insert(0, str(ROOT / "addons" / "acm_extended" / "tools"))
from source_scan import code_streams, matching, split_args

PREFIXES = ("ACM_core_", "ACM_breathing_", "ACM_circulation_", "ACM_airway_",
            "ACM_damage_", "ACM_CBRN_", "ace_")


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    key: str
    kind: str


def native_key(argument):
    if len(argument) != 1 or argument[0].kind != "string":
        return None
    key = argument[0].value
    return key if key.lower().startswith(tuple(prefix.lower() for prefix in PREFIXES)) else None


def scan_source(source: str, path: str = "<source>") -> list[Violation]:
    findings = []
    for tokens in code_streams(source):
        pairs = matching(tokens)
        for i, token in enumerate(tokens):
            if token.kind != "ident":
                continue
            kind = token.value.lower()
            if kind == "setvariable" and i + 1 < len(tokens) and tokens[i + 1].value == "[":
                opening = i + 1
                if opening not in pairs:
                    raise ValueError(f"{path}:{token.line}: unclosed setVariable argument array")
                arguments = split_args(tokens, opening + 1, pairs[opening], pairs)
                key = native_key(arguments[0]) if arguments else None
                if key:
                    findings.append(Violation(path, token.line, key, "direct setVariable"))
            elif kind in {"acme_fnc_setvarnet", "acme_fnc_setvarnetapprox"}:
                # SQF invocation order is [object, key, value] call function.
                if i < 2 or tokens[i - 1].value.lower() != "call" or tokens[i - 2].value != "]":
                    continue
                closing = i - 2
                if closing not in pairs:
                    raise ValueError(f"{path}:{token.line}: unmatched network helper argument array")
                arguments = split_args(tokens, pairs[closing] + 1, closing, pairs)
                key = native_key(arguments[1]) if len(arguments) >= 2 else None
                if key:
                    findings.append(Violation(path, token.line, key, token.value))
    return findings


def scan_directory(directory: Path) -> list[Violation]:
    if not directory.is_dir():
        raise ValueError(f"Extended function directory does not exist: {directory}")
    paths = sorted(directory.rglob("*.sqf"))
    if not paths:
        raise ValueError(f"No SQF functions found in {directory}")
    return [finding for path in paths for finding in scan_source(
        path.read_text(encoding="utf-8-sig", errors="strict"), str(path.relative_to(directory))
    )]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit nonzero if any literal native write is found")
    parser.add_argument("--functions-dir", type=Path, default=EXT)
    args = parser.parse_args(argv)
    try:
        findings = scan_directory(args.functions_dir)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Native-owner audit could not complete: {exc}", file=sys.stderr)
        return 2
    for prefix in PREFIXES:
        rows = [finding for finding in findings if finding.key.lower().startswith(prefix.lower())]
        print(f"=== {prefix} actual direct/native writes: {len(rows)} ===")
        for finding in rows:
            print(f"{finding.path}:{finding.line}: {finding.kind}: {finding.key}")
    if args.strict:
        print(f"Native-owner strict gate: {'FAIL' if findings else 'PASS'} ({len(findings)} violations)")
    return int(args.strict and bool(findings))


if __name__ == "__main__":
    sys.exit(main())
