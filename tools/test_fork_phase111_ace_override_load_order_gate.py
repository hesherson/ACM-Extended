#!/usr/bin/env python3
"""Phase 111: compile-time ACE overrides must load after every ACE addon they replace."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"


def required_addons(config: Path) -> set[str]:
    text = config.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"requiredAddons\s*\[\]\s*=\s*\{(.*?)\}\s*;", text, re.S)
    assert m, f"missing requiredAddons[]: {config.relative_to(ROOT)}"
    return set(re.findall(r'"([^"\r\n]+)"', m.group(1)))


def override_tags(cfg_functions: Path) -> set[str]:
    if not cfg_functions.is_file():
        return set()
    text = cfg_functions.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r'\btag\s*=\s*"(ace_[A-Za-z0-9_]+)"\s*;', text))


owners: list[tuple[str, set[str], set[str]]] = []
missing: list[tuple[str, str]] = []
for addon in sorted(ADDONS.iterdir()):
    if not addon.is_dir() or not (addon / "config.cpp").is_file():
        continue
    tags = override_tags(addon / "CfgFunctions.hpp")
    if not tags:
        continue
    req = required_addons(addon / "config.cpp")
    owners.append((addon.name, tags, req))
    for tag in sorted(tags):
        if tag not in req:
            missing.append((addon.name, tag))

assert owners, "no compile-time ACE override owners found"
assert not missing, "ACE override target missing from owner requiredAddons[]: " + repr(missing)

core = next((x for x in owners if x[0] == "core"), None)
assert core is not None, "core ACE override owner missing"
assert len(core[1]) == 15, f"expected 15 ACE override target addons in core, found {len(core[1])}: {sorted(core[1])}"

gui = next((x for x in owners if x[0] == "gui"), None)
assert gui is not None and gui[1] == {"ace_medical_gui"}, "GUI override ownership changed unexpectedly"

print(
    "PASS phase111: ACE override load order is explicit "
    f"({sum(len(tags) for _, tags, _ in owners)} target addons across {len(owners)} fork owners)"
)
