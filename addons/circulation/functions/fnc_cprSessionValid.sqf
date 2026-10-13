#include "..\script_component.hpp"
// Paused CPR still reserves the patient. isPerformingCPR only describes active compressions.
// Heartbeat age is intentionally not compared here: CPR_lastSeen is written on the provider client, while
// watchdog expiry is measured on the dedicated server's receive clock in registerCPRRuntime.
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient} || {!alive _medic}
    || {!([_medic] call ACEFUNC(common,isAwake))}) exitWith {false};
private _claimExpired = false;
private _ownerClaim = false;
if (isMultiplayer) then {
    private _claim = _patient getVariable ["ACME_resus_cpr",[]];
    _claimExpired = count _claim == 11 && {
        (_claim select 0) isNotEqualTo _medic
        || {(_claim select 2) != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {!(_claim select 7) && {serverTime >= (_claim select 6)}}
        || {(_patient getVariable [QGVAR(CPR_session),[]]) isNotEqualTo [_medic,_claim select 5]}
    };
    _ownerClaim = count _claim == 11 && {!_claimExpired};
};
if (_claimExpired) exitWith {false};
private _session = _patient getVariable [QGVAR(CPR_session), []];
(_ownerClaim || {(count _session == 2)
    && {(_session select 0) isEqualTo _medic}
    && {(_medic getVariable [QGVAR(CPR_Patient), objNull]) isEqualTo _patient}
    && {(_medic getVariable [QGVAR(CPR_Epoch), -1]) == (_session select 1)}})
    && {[_medic,_patient] call ACME_fnc_patientInteractionContact}
