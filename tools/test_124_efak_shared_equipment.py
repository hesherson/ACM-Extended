#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = (ROOT / "addons/acm_extended/config.cpp").read_text(encoding="utf-8", errors="replace")
COUNT = (ROOT / "addons/acm_extended/functions/fn_treatmentSupplyCount.sqf").read_text(encoding="utf-8")
TAKE = (ROOT / "addons/acm_extended/functions/fn_treatmentSupplyTake.sqf").read_text(encoding="utf-8")
HPMK = (ROOT / "addons/acm_extended/functions/fn_hpmkPrep.sqf").read_text(encoding="utf-8")

for name in ("itemCount", "itemTake", "itemList"):
    assert f"class {name} {{}};" in CFG

assert "ACME_fnc_treatmentSupplyOrder" in COUNT
assert "ACME_fnc_itemCount" in COUNT
assert "ace_medical_treatment_fnc_useItem" in TAKE
assert "efak_medical_fnc_countItem" in TAKE
assert "efak_medical_fnc_takeItem" in TAKE
assert "ACME_fnc_treatmentSupplyOrder" in TAKE
assert "ACME_fnc_treatmentSupplyTake" in HPMK

print("ACME 1.2.4 EFAK/shared-equipment compatibility contracts: PASS")
