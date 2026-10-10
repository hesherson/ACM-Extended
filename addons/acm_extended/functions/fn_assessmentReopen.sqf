/* Deferred menu handoff after ACE success/failure and any carrier return release their owners.
 * A successor click, menu, locality change or range loss cancels this exact return request. */
params ["_medic", "_patient", "_epoch"];
if (isNull _medic || {!local _medic} || {!([_medic] call ace_common_fnc_isPlayer)}) exitWith {};
private _request = [_epoch, _patient, _medic getVariable ["ACME_providerLocalityEpoch", 0], _medic getVariable ["ACME_menuPoseEpoch", 0]];
_medic setVariable ["ACME_assessmentReturn", _request, false];
private _valid = {
    params ["_m", "_p", "_request"];
    !isNull _m && {local _m} && {alive _m} && {!(_m getVariable ["ACE_isUnconscious", false])}
        && {!isNull _p} && {(_m getVariable ["ACME_assessmentReturn", []]) isEqualTo _request}
        && {(_m getVariable ["ACME_providerLocalityEpoch", 0]) == (_request select 2)}
        && {(_m getVariable ["ACME_menuPoseEpoch", 0]) == (_request select 3)}
        && {([_m, _p] call ACME_fnc_patientInteractionDistance) <= ace_medical_gui_maxDistance}
};
// Defer creation of the waiter too: it must not run inside ACE's current callback/event stack.
[{
    params ["_m", "_p", "_request", "_valid"];
    [{
        params ["_m", "_p", "_request", "_valid"];
        !([_m, _p, _request] call _valid) || {!([_m] call ACME_fnc_providerStanceOwned)}
    }, {
        params ["_m", "_p", "_request", "_valid"];
        if !([_m, _p, _request] call _valid) exitWith {
            if (!isNull _m && {(_m getVariable ["ACME_assessmentReturn", []]) isEqualTo _request}) then {
                _m setVariable ["ACME_assessmentReturn", [], false];
            };
        };
        _m setVariable ["ACME_assessmentReturn", [], false];
        // Do not steal focus from a successor dialog. Native progress has already been destroyed.
        if (dialog) exitWith {};
        if (isNull objectParent _m && {stance _m != "PRONE"}) then {
            [_m, [["treatmentEndInAnim"]]] call ACM_core_fnc_setAceMedicalState;
            [_m, "ACM_GenericContinuous", 1] call ACME_fnc_doAnim;
        };
        _m setVariable ["ACME_menuPoseAfterTreatment", _p];
        ace_medical_gui_pendingReopen = false;
        ["ACM_core_openMedicalMenu", _p] call CBA_fnc_localEvent;
    }, _this, 6, {
        params ["_m", "", "_request"];
        if (!isNull _m && {(_m getVariable ["ACME_assessmentReturn", []]) isEqualTo _request}) then {
            _m setVariable ["ACME_assessmentReturn", [], false];
        };
    }] call CBA_fnc_waitUntilAndExecute;
}, [_medic, _patient, _request, _valid]] call CBA_fnc_execNextFrame;
