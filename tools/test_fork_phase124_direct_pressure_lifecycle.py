#!/usr/bin/env python3
"""Phase 124: direct pressure coexists with menu/treatment actions and teardown is idempotent."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'addons/acm_extended/functions'
torso=(F/'fn_directPressureTorso.sqf').read_text()
tick=(F/'fn_directPressureTick.sqf').read_text()
pose=(F/'fn_directPressurePose.sqf').read_text()
stop=(F/'fn_directPressureStop.sqf').read_text()
start=(F/'fn_directPressureStart.sqf').read_text()
cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
assert 'call ACM_core_fnc_setContinuousActionActive' not in torso
assert 'call ACM_core_fnc_setContinuousActionActive' not in stop
assert '[true, _medic, false] call ACME_fnc_directPressureStop' in tick
assert '[false, _medic, false] call ACME_fnc_directPressureStop' in tick
assert 'ACME_treatmentPreflightActive' in pose and 'ace_medical_treatment_endInAnim' in pose
assert 'ACM_core_ContinuousAction_Active' in pose
assert 'params [["_silent", false, [false]], ["_medic", ACE_player' in stop
assert 'if !(_medic getVariable ["ACME_DP_Active", false]) exitWith' not in stop
for token in ['ACME_DP_Patient','ACME_DP_Part','ACME_DP_PFH','ACME_DP_KeyIDs',
              'ACME_DP_ClaimPending','ACME_DP_ClaimToken','ACME_DP_ClaimEpoch']:
    assert token in stop
# Patient-side TorsoMedic/LimbMedic markers are no longer provider-local teardown state.
# Atomic owner-side claim release clears those only when this exact token still owns the site.
assert '"directPressureClaim"' in stop and '"release"' in stop
assert 'ACME_DP_TorsoMedic' not in stop and 'ACME_DP_LimbMedic' not in stop
assert '[true, _medic] call ACME_fnc_directPressureStop' in start
assert '"directPressureClaim"' in start and 'ACME_DP_ClaimPending' in start
assert 'class ACME_StopDirectPressure: CheckPulse' in cfg
stop_action=cfg[cfg.index('class ACME_StopDirectPressure'):cfg.index('class ACME_AssessPupils')]
assert "ACME_DP_Active" in stop_action and "ACME_DP_Patient" in stop_action
assert '[false, _medic] call ACME_fnc_directPressureStop' in stop_action
print('PASS phase124: direct pressure has explicit stop/coexistence and idempotent medic-scoped cleanup')
