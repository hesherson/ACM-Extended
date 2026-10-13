#include "..\script_component.hpp"
// ACM's BVM_Medic reserves the patient even while breaths are paused. Recover only an
// unavailable provider; replicated cleanup tokens and clocks do not decide who is active.
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient} || {!alive _medic}
    || {!([_medic] call ACEFUNC(common,isAwake))}) exitWith {false};
private _claimExpired = false;
if (isMultiplayer) then {
    private _claim = _patient getVariable ["ACME_resus_bvm",[]];
    _claimExpired = count _claim == 11 && {
        (_claim select 0) isNotEqualTo _medic
        || {(_claim select 2) != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {!(_claim select 7) && {serverTime >= (_claim select 6)}}
        || {(_patient getVariable [QGVAR(BVM_session),[]]) isNotEqualTo [_medic,_claim select 5]}
    };
};
if (_claimExpired) exitWith {false};
((_patient getVariable [QGVAR(BVM_Medic), objNull]) isEqualTo _medic)
    && {[_medic,_patient] call ACME_fnc_patientInteractionContact}
