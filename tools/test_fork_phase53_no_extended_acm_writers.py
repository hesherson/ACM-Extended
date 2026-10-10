#!/usr/bin/env python3
"""Phase 53 regression: Extended may read native ACM state, but may not publish it directly."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "addons" / "acm_extended"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def fail(msg):
    raise AssertionError(msg)

def test_current_phase53_no_extended_acm_writers():
    # New native-owner entry points must stay registered and used by the migrated paths.
    cbrn_prep = read("addons/cbrn/XEH_PREP.hpp")
    assert "PREP(setBreathingAbilityState);" in cbrn_prep
    cbrn_setter = read("addons/cbrn/functions/fnc_setBreathingAbilityState.sqf")
    assert "BreathingAbility_State" in cbrn_setter and "setVariable" in cbrn_setter

    core_prep = read("addons/core/XEH_PREP.hpp")
    assert "PREP(setTargetVitalsState);" in core_prep
    core_setter = read("addons/core/functions/fnc_setTargetVitalsState.sqf")
    assert "TargetVitals_OxygenSaturation" in core_setter and "setVariable" in core_setter

    for rel in (
        "addons/acm_extended/functions/fn_blastLungTick.sqf",
        "addons/acm_extended/functions/fn_clearAllAilments.sqf",
    ):
        text = read(rel)
        assert "ACM_CBRN_fnc_setBreathingAbilityState" in text, rel

    for rel in (
        "addons/acm_extended/functions/fn_altitudeTick.sqf",
        "addons/acm_extended/functions/fn_ventDriveTick.sqf",
    ):
        text = read(rel)
        assert "ACM_core_fnc_setTargetVitalsState" in text, rel

    # Reject direct native ACM publication from the Extended addon. Native reads are intentionally public API and remain valid.
    direct_literal = re.compile(r"\bsetVariable\s*\[\s*[\"']ACM_[^\"']+[\"']", re.I)
    mission_literal = re.compile(r"missionNamespace\s+setVariable\s*\[\s*[\"']ACM_[^\"']+[\"']", re.I)
    setvarnet_native_arg = re.compile(r"\[\s*[^,\]]+\s*,\s*[\"']ACM_[^\"']+[\"']\s*,", re.I)
    # Catch a dynamic-key write when the same executable line clearly names an ACM key.
    dynamic_native = re.compile(r"\bsetVariable\s*\[\s*_[A-Za-z0-9_]+\s*,")
    acm_literal = re.compile(r"[\"']ACM_[^\"']+[\"']", re.I)

    violations = []
    for path in EXT.rglob("*.sqf"):
        for lineno, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = raw.split("//", 1)[0]
            if not line.strip():
                continue
            if direct_literal.search(line) or mission_literal.search(line):
                violations.append((path, lineno, raw.strip(), "direct setVariable"))
                continue
            if "ACME_fnc_setVarNet" in line and setvarnet_native_arg.search(line):
                violations.append((path, lineno, raw.strip(), "ACME_fnc_setVarNet native key"))
                continue
            if dynamic_native.search(line) and acm_literal.search(line):
                violations.append((path, lineno, raw.strip(), "dynamic native-key setVariable"))

    if violations:
        details = "\n".join(f"{p.relative_to(ROOT)}:{n}: {kind}: {src}" for p,n,src,kind in violations)
        fail("Extended still publishes native ACM state directly:\n" + details)

    print("phase53 native ACM writer boundary: PASS")


if __name__ == "__main__":
    test_current_phase53_no_extended_acm_writers()
