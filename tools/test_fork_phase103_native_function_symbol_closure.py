#!/usr/bin/env python3
"""Phase 103: native ACM/DD1380 function references must resolve to PREP ownership in this fork."""
from __future__ import annotations
from pathlib import Path
import re
from test_fork_phase93_cfgpatches_dependency_gate import namespace_for

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXT = {".sqf", ".cpp", ".hpp", ".inc", ".h"}


def component(prep: Path) -> str:
    sc = prep.parent / "script_component.hpp"
    text = sc.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^\s*#define\s+COMPONENT\s+([A-Za-z0-9_]+)\s*$", text, re.M)
    assert m, sc
    return m.group(1)


def strip_comments_keep_strings(text: str) -> str:
    out: list[str] = []
    i = 0
    state = "code"
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        if state == "line":
            if c == "\n": state = "code"; out.append("\n")
            else: out.append(" ")
        elif state == "block":
            if c == "*" and n == "/": state = "code"; out.extend("  "); i += 1
            else: out.append("\n" if c == "\n" else " ")
        elif state == "string":
            out.append(c)
            if c == '"':
                if n == '"': out.append(n); i += 1
                else: state = "code"
        else:
            if c == "/" and n == "/": state = "line"; out.extend("  "); i += 1
            elif c == "/" and n == "*": state = "block"; out.extend("  "); i += 1
            else:
                out.append(c)
                if c == '"': state = "string"
        i += 1
    return "".join(out)


def main() -> None:
    registered: set[str] = set()
    for prep in sorted(ROOT.glob("addons/*/XEH_PREP.hpp")):
        comp = component(prep)
        namespace = namespace_for(prep.parent)
        text = prep.read_text(encoding="utf-8", errors="replace")
        for name in re.findall(r"\bPREP\(([^)]+)\)\s*;", text):
            registered.add(f"{namespace}_{comp}_fnc_{name}".casefold())

    refs: dict[str, list[str]] = {}
    rx = re.compile(r"\b(?:ACM|DD1380)_[A-Za-z0-9]+_fnc_[A-Za-z0-9_]+\b", re.I)
    for path in sorted(ROOT.glob("addons/**/*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXT:
            continue
        text = strip_comments_keep_strings(path.read_text(encoding="utf-8", errors="replace"))
        for match in rx.finditer(text):
            raw = match.group(0)
            refs.setdefault(raw.casefold(), []).append(str(path.relative_to(ROOT)))

    unresolved = sorted(set(refs) - registered)
    assert not unresolved, "unresolved native ACM/DD1380 function symbols:\n" + "\n".join(
        f"{sym}: {refs[sym][:5]}" for sym in unresolved[:100]
    )
    assert len(refs) > 80, f"unexpectedly low native symbol reference set: {len(refs)}"
    print(f"fork phase 103 native function-symbol closure: PASS ({len(registered)} registered, {len(refs)} referenced symbols)")


if __name__ == "__main__":
    main()
