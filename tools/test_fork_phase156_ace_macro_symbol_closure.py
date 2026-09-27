#!/usr/bin/env python3
"""Phase 156: resolve ACE function macros as well as literal function symbols."""
from pathlib import Path
import re

from test_fork_phase113_ace_function_symbol_closure import BASE, overrides, strip_comments

ROOT = Path(__file__).resolve().parents[1]
# The phase113 PREP manifest predates scans of ACEX_PREP. These referenced symbols
# are also compiled by the supplied ACE addons/field_rations/XEH_PREP.hpp.
ACEX_PREP_API = {
    f"ace_field_rations_fnc_{function}".casefold()
    for function in ("addStatusModifier", "getRemainingWater", "setRemainingWater")
}
references = {}
for path in (ROOT / "addons").rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".sqf", ".hpp", ".cpp"}:
        continue
    source = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    # Macro definitions contain argument placeholders, not function references.
    source = re.sub(r"(?m)^\s*#\s*define[^\n]*(?:\\\n[^\n]*)*", "", source)
    for match in re.finditer(r"\b(?:Q?ACEFUNC|ACELINKFUNC)\(\s*(\w+)\s*,\s*(\w+)\s*\)", source):
        component, function = match.groups()
        symbol = f"ace_{component}_fnc_{function}".casefold()
        references.setdefault(symbol, set()).add(str(path.relative_to(ROOT)))

missing = sorted(set(references) - (BASE | overrides | ACEX_PREP_API))
assert not missing, "unresolved ACE function macros:\n" + "\n".join(
    f"{symbol}: {', '.join(sorted(references[symbol]))}" for symbol in missing
)
assert len(references) >= 70, f"ACE macro reference scan unexpectedly small: {len(references)}"
assert "ace_medical_status_fnc_adjustpainlevel" in references
print(f"PASS phase156: {len(references)} ACE function macro targets resolve to supplied ACE or fork overrides")
