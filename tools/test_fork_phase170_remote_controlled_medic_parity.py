#!/usr/bin/env python3
"""Phase 170: Zeus remote-controlled NPC medics retain normal intervention access."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

treatment = read("addons/core/overrides/fnc_treatment.sqf")
native = read("addons/core/functions/fnc_treatmentNative.sqf")
progress = read("addons/core/functions/fnc_progressBarAction.sqf")
discard = read("addons/circulation/functions/fnc_Syringe_Discard.sqf")
collector = read("addons/gui/overrides/fnc_collectActions.sqf")
provider = read("addons/acm_extended/functions/fn_controlledProvider.sqf")

assert "call ACME_fnc_controlledProvider" in collector
assert "ace_common_fnc_player" in provider
assert "_remoteControlledMedic" in treatment
assert "_medic isNotEqualTo player" in treatment
assert "_providerInteractChecks" in treatment
assert treatment.count('[_medic, _patient, _providerInteractChecks] call ace_common_fnc_canInteractWith') >= 3

for source in (native, progress, discard):
    assert "_medic isEqualTo (call ACME_fnc_controlledProvider)" in source
    assert "_medic isNotEqualTo player" in source
    assert '["isNotInside", "isNotSwimming"]' in source

print("PASS phase170: remote-controlled NPC medic intervention parity gates are present")
