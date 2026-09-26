#!/usr/bin/env python3
"""Static integration contract for the selected ACM:MDF feature port."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for addon in ("burns", "infection", "ophthalmology", "card", "card_main"):\n    assert (ROOT / "addons" / addon).is_dir(), addon\nfor addon in ("FAK-core", "FAK-main"):\n    assert not (ROOT / "addons" / addon).exists(), f"bundled EFAK must remain external: {addon}"

injuries = (ROOT / "addons/damage/ACE_Medical_Injuries.hpp").read_text(encoding="utf-8")
wounds = (ROOT / "addons/core/overrides/fnc_woundsHandlerBase.sqf").read_text(encoding="utf-8")
assert all(name in injuries for name in ("Burn1", "Burn2", "Burn3", "class burn"))
assert "burnApplied" in wounds

medications = (ROOT / "addons/core/ACM_Medication.hpp").read_text(encoding="utf-8")
assert "class Moxifloxacin" in medications

temperature = (ROOT / "addons/acm_extended/functions/fn_hypothermiaTick.sqf").read_text(encoding="utf-8")
assert "ACM_infection_Fever_Offset" in temperature
assert "ACME_fnc_hypothermiaTemperatureCommit" in temperature

wash = (ROOT / "addons/cbrn/functions/fnc_washEyes.sqf").read_text(encoding="utf-8")
assert "ACM_ophthalmology_fnc_clearEyeInjury" in wash

print("MDF feature-port contracts: PASS")