#!/usr/bin/env python3
"""Phase 171: root-cause regressions for suction refill, chest-seal flip preemption, and auscultation audio."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

blood = read("addons/airway/functions/fnc_handleAirwayObstruction_Blood.sqf")
fluid = read("addons/acm_extended/functions/fn_laryngoFluidState.sqf")
drain = read("addons/acm_extended/functions/fn_laryngoFluidDrainLocal.sqf")
owner_init = read("addons/acm_extended/functions/fn_ownerInit.sqf")
owner_register = read("addons/acm_extended/functions/fn_ownerRegister.sqf")
fields = read("addons/acm_extended/functions/fn_clinicalFields.sqf")
seal_apply = read("addons/acm_extended/functions/fn_chestSealApply.sqf")
seal_flip = read("addons/acm_extended/functions/fn_chestSealFlip.sqf")
steth_init = read("addons/acm_extended/functions/fn_stethoscopeInit.sqf")
steth_tick = read("addons/acm_extended/functions/fn_stethoscopeTick.sqf")

# Airway blood production is patient-owner authoritative. A non-owner forwards to the owner instead of running
# another local PFH, and the native obstruction field is occupancy rather than an ever-growing event counter.
assert "if (!local _patient) exitWith" in blood
assert "CBA_fnc_targetEvent" in blood
assert "ACME_airwayBloodEventSerial" in blood
assert 'setVariable [QGVAR(AirwayObstructionBlood_State), 1, true]' in blood
assert "(_obstructionState + 1)" not in blood
assert "ACM_airway_AirwayObstructionBlood_PFH" in owner_init
assert "ACM_airway_fnc_handleAirwayObstruction_Blood" in owner_register

# Fluid volume and event identity are separate. Clearing the mouth keeps the zero-volume event ledger so a later
# bleed contributes one new delta instead of reconstructing the monotonic serial as current volume.
assert "_bloodEvent" in fluid
assert '["_ledgerVar", "_active", "_eventSerial"' in fluid
assert '["ACME_laryngo_poolBlood", _blood > 0, _bloodEvent' in fluid
assert 'setVariable ["ACME_laryngo_poolBlood", [_eventSerial, 0], true]' in drain
for key in ("ACME_laryngo_poolVomit", "ACME_laryngo_poolBlood", "ACME_airwayBloodEventSerial"):
    assert key in fields

# Chest seal placement is clinically committed immediately, but its provider gesture is presentation only.
# Flip must invalidate the old placement generation and retire its pose before rollProviderStart is called.
assert "ACME_CS_ApplyGestureSerial" in seal_apply
assert "ACME_CS_ApplyGestureSerial" in seal_flip
assert seal_flip.index("ACME_CS_ApplyGestureSerial") < seal_flip.index("ACME_fnc_rollProviderStart")
assert '[_provider,"chestSeal",_applyEpoch,true] call ACME_fnc_treatmentPoseStop' in seal_flip
assert 'uiNamespace setVariable ["ACME_CS_ApplyGestureUntil",0]' in seal_flip

# Auscultation is a local diagnostic transducer. It must never be world-spatialized or gear-occluded.
assert "playSoundUI" in steth_tick
assert "playSound3D" not in steth_tick
assert "say3D" not in steth_tick
assert "lineIntersects" not in steth_tick
assert " vest " not in (" " + steth_tick.lower() + " ")
assert "playSound3D" not in steth_init
assert "say3D" not in steth_init

print("PASS phase171: airway, chest-seal flip, and stethoscope root-cause invariants hold")
