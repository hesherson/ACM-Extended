/* Provider-local reply for the patient-owner Direct Pressure site claim. */
params ["_patient","_medic","_part","_token","_accepted","_epoch","_providerOwner"];
if (isNull _medic || {!local _medic}) exitWith {};

private _pending = _medic getVariable ["ACME_DP_ClaimPending",[]];
private _same = (_pending isEqualType []) && {count _pending >= 4}
    && {(_pending select 0) isEqualTo _patient}
    && {(_pending select 1) == _part}
    && {(_pending select 2) == _token}
    && {(_pending select 3) == _epoch};
if (!_same) exitWith {
    // A delayed accepted ACK from a timed-out/superseded request must release only its own owner-side token.
    // Token matching in directPressureClaimLocal prevents this from touching a newer episode from the same medic.
    if (_accepted && {!isNull _patient}) then {
        [_patient,"directPressureClaim",["release",[_medic,_part,_token,_epoch,_providerOwner]]] call ACME_fnc_ownerDispatch;
    };
};

_medic setVariable ["ACME_DP_ClaimPending",[],false];
_medic setVariable ["ACME_DP_ClaimRequestedAt",-1,false];

private _stillValid = _accepted
    && {!isNull _patient}
    && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious",false])}
    && {_providerOwner == owner _medic}
    && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {!(missionNamespace getVariable ["ACM_core_ContinuousAction_Active",false])}
    && {!(_medic getVariable ["ACM_circulation_isPerformingCPR",false])}
    && {!(_medic getVariable ["ACM_breathing_isUsingBVM",false])}
    && {missionNamespace getVariable ["ACME_sys_dp",true]};

if (!_stillValid) exitWith {
    if (_accepted) then {
        [_patient,"directPressureClaim",["release",[_medic,_part,_token,_epoch,_providerOwner]]] call ACME_fnc_ownerDispatch;
    };
    if (!_accepted) then {
        ["Direct pressure is already being maintained on this site.",2,_medic] call ace_common_fnc_displayTextStructured;
    };
};

_medic setVariable ["ACME_DP_ClaimToken",_token,true];
_medic setVariable ["ACME_DP_ClaimEpoch",_epoch,true];

[_patient,0.85] call ACME_fnc_markImportantSfx;
[_medic,"ACME_DirectPressure"] remoteExec ["say3D",0];

if (_part == "body") then {
    [_medic,_patient,_part] call ACME_fnc_directPressureTorso;
} else {
    if (_patient isEqualTo _medic) then {
        [_medic,_patient,_part] call ACME_fnc_directPressureSelf;
    } else {
        [_medic,_patient,_part] call ACME_fnc_directPressureLimb;
    };
};
