#!/usr/bin/env python3
"""Phase 172: intervention-animation toggle, ACRE vest handoff, vent closure scope and chest-hole ceiling."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

settings = read("addons/acm_extended/XEH_preInit.sqf")
do_anim = read("addons/acm_extended/functions/fn_doAnim.sqf")
pose_start = read("addons/acm_extended/functions/fn_treatmentPoseStart.sqf")
pose_stop = read("addons/acm_extended/functions/fn_treatmentPoseStop.sqf")
treatment = read("addons/core/overrides/fnc_treatment.sqf")
native = read("addons/core/functions/fnc_treatmentNative.sqf")
chest_provider = read("addons/acm_extended/functions/fn_chestAccessVestProvider.sqf")
chest_acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
flip_tick = read("addons/acm_extended/functions/fn_chestSealFlipTick.sqf")
roll = read("addons/acm_extended/functions/fn_chestSealRoll.sqf")
holes = read("addons/acm_extended/functions/fn_chestSealGenHoles.sqf")
vent = read("addons/acm_extended/functions/fn_ventPanelInit.sqf")

# Mission-authoritative toggle defaults on and suppresses presentation, not clinical treatment time.
assert '"ACME_interventionAnimations", "CHECKBOX"' in settings
assert 'missionNamespace getVariable ["ACME_interventionAnimations", true]' in do_anim
assert 'missionNamespace getVariable ["ACME_interventionAnimations", true]' in native
assert 'private _animationsEnabled = missionNamespace getVariable ["ACME_interventionAnimations", true]' in treatment
assert 'if !(missionNamespace getVariable ["ACME_interventionAnimations", true]) exitWith' in pose_start
assert "ACME_treatmentPoseState" in pose_start
assert "_window" in pose_start
assert "_animationsEnabled" in pose_stop
assert 'ACME_chestAccessProviderReady' in chest_provider
assert 'missionNamespace getVariable ["ACME_interventionAnimations", true]' in chest_provider
assert "_presentationReady" in flip_tick
assert 'missionNamespace getVariable ["ACME_interventionAnimations", true]' in roll

# ACRE remains optional. If its local player is transmitting, use ACRE's own key-up path before removeVest.
assert '!isNil "acre_sys_core_fnc_handleMultiPttKeyPressUp"' in chest_acquire
assert 'missionNamespace getVariable ["acre_sys_core_pttKeyDown", false]' in chest_acquire
assert chest_acquire.index("acre_sys_core_fnc_handleMultiPttKeyPressUp") < chest_acquire.index("removeVest _p")

# Vent delayed callback owns every variable it reads; no outer _viewer closure survives into CBA waitAndExecute.
jingle = vent[vent.index("// the power-on jingle"):vent.index("} else {", vent.index("// the power-on jingle"))]
assert 'params ["_bT0", "_viewer"]' in jingle
assert '[_bT0, _viewer]' in jingle

# Penetrating chest wounds use real damage for exit severity, conservative historical fallback and a hard total cap.
assert "private _maxTotalHoles = 6;" in holes
assert "private _totalCount = count _holes;" in holes
assert "(_minChance + _maxChance) * 0.5" in holes
assert "linearConversion [_minDamage, _maxDamage, _damage" in holes
assert "_totalCount < _maxTotalHoles" in holes
assert "|| {!_historical}" not in holes
assert "_totalCount = _totalCount + 1" in holes

print("PASS phase172: animation, ACRE, vent scope and chest-hole invariants hold")
