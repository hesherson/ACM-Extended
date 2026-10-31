#!/usr/bin/env python3
"""Phase 54 regression: Extended patient ACE-medical writes cross the ACM core ACE integration bridge."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "addons" / "acm_extended"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_current_phase54_ace_medical_state_bridge():
    prep = read("addons/core/XEH_PREP.hpp")
    assert "PREP(setAceMedicalState);" in prep
    bridge = read("addons/core/functions/fnc_setAceMedicalState.sqf")
    for needle in (
        '"ace_medical_pain"',
        '"ace_medical_spo2"',
        '"ace_medical_openWounds"',
        '"ace_medical_bandagedWounds"',
        '"ace_medical_stitchedWounds"',
        '"ace_medical_bloodVolume"',
        '"ace_medical_bodyTemperature"',
        '"ace_medical_medications"',
        '"ace_medical_occludedMedications"',
        '"ace_medical_statemachine_AIUnconsciousness"',
        '"ace_medical_damage_InstantDeathImmune"',
        '"ace_medical_deathBlocked"',
    ):
        assert needle in bridge, needle
    assert "ACEState_ForkPublished" in bridge
    assert "local _patient" in bridge

    # Representative high-frequency paths must preserve the former setVarNet-style dedup flag.
    for rel in (
        "addons/acm_extended/functions/fn_ventDriveTick.sqf",
        "addons/acm_extended/functions/fn_blastLungTick.sqf",
        "addons/acm_extended/functions/fn_nrbTick.sqf",
        "addons/acm_extended/functions/fn_rhythmTick.sqf",
    ):
        text = read(rel)
        assert "ACM_core_fnc_setAceMedicalState" in text, rel

    # The current wake budget must not alter medical values to manufacture wake
    # eligibility. Its canonical canWake/requestWake delegation replaces the old
    # requirement to force ACE medical values from this gameplay backstop.
    budget = read("addons/acm_extended/functions/fn_consciousnessBudget.sqf")
    assert "call ACM_core_fnc_canWake;" in budget
    assert "call ACM_core_fnc_requestWake" in budget
    assert "ACM_core_fnc_setAceMedicalState" not in budget
    assert "PREP(requestWake);" in prep and "PREP(canWake);" in prep
    request = read("addons/core/functions/fnc_requestWake.sqf")
    assert "canWake" in request and "local _patient" in request

    # The medical GUI PFH is a UI integration flag, not patient medical state; it remains a separate GUI boundary target.
    allowed_direct = {"ace_medical_gui_menuPFH"}
    violations = []
    for path in EXT.rglob("*.sqf"):
        for lineno, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = raw.split("//", 1)[0]
            if not line.strip():
                continue
            for match in re.finditer(r"setVariable\s*\[\s*[\"'](ace_medical_[^\"']+)[\"']", line, re.I):
                var = match.group(1)
                if var not in allowed_direct:
                    violations.append((path, lineno, var, raw.strip(), "setVariable"))
            if "ACME_fnc_setVarNet" in line:
                match = re.search(r"\[\s*[^,\]]+\s*,\s*[\"'](ace_medical_[^\"']+)[\"']\s*,", line, re.I)
                if match and match.group(1) not in allowed_direct:
                    violations.append((path, lineno, match.group(1), raw.strip(), "setVarNet"))

    if violations:
        details = "\n".join(
            f"{p.relative_to(ROOT)}:{n}: {kind} {var}: {src}" for p, n, var, src, kind in violations
        )
        raise AssertionError("Extended still writes ACE patient medical state directly:\n" + details)

    print("fork phase 54 ACE medical-state bridge checks: PASS")


if __name__ == "__main__":
    test_current_phase54_ace_medical_state_bridge()
