#!/usr/bin/env python3
"""RC4 regression: closing chest-seal/stethoscope during Flip must hard-cancel provider and patient roll ownership."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUN = ROOT / "addons" / "acm_extended" / "functions"

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

provider_cancel = read(FUN / "fn_rollProviderCancel.sqf")
patient_cancel = read(FUN / "fn_patientRollCancel.sqf")
chest_close = read(FUN / "fn_chestSealClose.sqf")
chest_flip = read(FUN / "fn_chestSealFlip.sqf")
chest_tick = read(FUN / "fn_chestSealFlipTick.sqf")
patient_end = read(FUN / "fn_chestSealPatientEnd.sqf")
steth_close = read(FUN / "fn_stethoscopeClose.sqf")
steth_flip = read(FUN / "fn_stethoscopeFlip.sqf")
steth_tick = read(FUN / "fn_stethoscopeFlipTick.sqf")
owner = read(FUN / "fn_ownerDispatch.sqf")
cfg = read(ROOT / "addons" / "acm_extended" / "config.cpp")
startup = read(FUN / "fn_initForkStartupRuntime.sqf")

# Immediate provider cancellation uses switchMove "" instead of letting medic4 finish through the move graph.
assert 'ACME_rollProviderPFH' in provider_cancel
assert '[_medic, "roll", _epoch] call ACME_fnc_treatmentPoseStop;' in provider_cancel
assert '_medic switchMove "";' in provider_cancel
assert 'setUnitPos "AUTO"' in provider_cancel

# Patient cancellation invalidates both delayed callbacks and settles to a stable rest side.
assert 'setVariable ["ACME_CS_rollToken", "", false]' in patient_cancel
assert 'setVariable ["ACME_CS_rollUntil", -1, false]' in patient_cancel
assert 'ACME_fnc_patientAnimRelease' in patient_cancel
assert 'ACME_CS_facing' in patient_cancel

# Both minigames own and synchronously remove their flip PFHs on close.
assert 'ACME_CS_FlipPFH' in chest_flip
assert 'ACME_CS_FlipPFH' in chest_tick
assert 'ACME_CS_FlipPFH' in chest_close
assert '[_flipMedic,"chestSealFlip"] call ACME_fnc_rollProviderCancel;' in chest_close

assert 'ACME_stethFlipPFH' in steth_flip
assert 'ACME_stethFlipPFH' in steth_tick
assert 'ACME_stethFlipPFH' in steth_close
assert '[_medic,"stethoscopeFlip"] call ACME_fnc_rollProviderCancel;' in steth_close
# Supine is explicit on close; the retired one-argument assertion rejected this fix.
assert '[_patient,"front"] call ACME_fnc_patientRollCancel;' in steth_close

# Chest-seal patient teardown invalidates a live patient roll immediately before reverse restoration.
assert 'private _rollActive' in patient_end
assert 'ACME_fnc_patientRollCancel' in patient_end
assert '[_patient, "front"] call ACME_fnc_patientRollCancel;' in patient_end
assert '(_rollUntil - CBA_missionTime) + 0.08' not in patient_end

# Owner routing and registration are explicit.
assert 'case "patientRollCancel": {_args call ACME_fnc_patientRollCancel;};' in owner
assert 'class rollProviderCancel {};' in cfg
assert 'class patientRollCancel {};' in cfg

print("PASS: immediate minigame flip cancellation")
