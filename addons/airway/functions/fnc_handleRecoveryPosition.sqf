#include "..\script_component.hpp"
/* B215 owner-local recovery lifetime. A provisional visual pose is not airway treatment.
 * The accepted animation token plus observed settled pose authorizes the eventual native state commit.
 */
params ["_medic", "_patient", ["_token", ""], ["_hops", 0]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    if (_hops < 4) then {[QGVAR(handleRecoveryPosition), [_medic, _patient, _token, _hops + 1], _patient] call CBA_fnc_targetEvent;};
};
if (_token == "") then {_token = _patient getVariable [QGVAR(RecoveryPosition_Episode), ""];};
if (_token == "") exitWith {};
[{
    params ["_args", "_handle"];
    _args params ["_medic", "_patient", "_token", "_localityEpoch"];
    if (isNull _patient) exitWith {[_handle] call CBA_fnc_removePerFrameHandler;};
    private _pending = _patient getVariable [QGVAR(RecoveryPosition_Pending), []];
    private _isPending = (_pending param [0, ""]) == _token;
    private _isActive = (_patient getVariable [QGVAR(RecoveryPosition_Episode), ""]) == _token
        && {_patient getVariable [QGVAR(RecoveryPosition_State), false]};
    if (!_isPending && {!_isActive}) exitWith {[_handle] call CBA_fnc_removePerFrameHandler;};
    if (!local _patient) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        // In-flight owner changes cancel the exact transaction; established recovery transfers its watcher.
        if (_isPending) then {
            [_medic, _patient, false, true, "cancel", _token] call FUNC(setRecoveryPosition);
        } else {
            [QGVAR(handleRecoveryPosition), [_medic, _patient, _token], _patient] call CBA_fnc_targetEvent;
        };
    };
    if (_isPending && {(_patient getVariable ["ACME_providerLocalityEpoch", 0]) != _localityEpoch}) exitWith {
        [_medic, _patient, false, true, "cancel", _token] call FUNC(setRecoveryPosition);
        [_handle] call CBA_fnc_removePerFrameHandler;
    };
    // Established interventions remain part of the postmortem record; only provisional work is cancelled.
    if (_isActive && {!alive _patient}) exitWith {[_handle] call CBA_fnc_removePerFrameHandler;};
    private _invalid = !alive _patient || {!(IS_UNCONSCIOUS(_patient))} || {!isNull objectParent _patient}
        || {[_patient] call ACEFUNC(common,isBeingDragged)} || {[_patient] call ACEFUNC(common,isBeingCarried)}
        || {_patient getVariable ["ACME_vent_driving", false]}
        || {[_patient] call EFUNC(core,cprActive)}
        || {alive (_patient getVariable ["ACM_breathing_BVM_Medic", objNull])};
    if (_invalid) exitWith {
        [_medic, _patient, false, true, ["", "cancel"] select _isPending, _token] call FUNC(setRecoveryPosition);
        [_handle] call CBA_fnc_removePerFrameHandler;
    };
    if (_isActive) exitWith {
        // Passive fallback for direct pose changes or missed animation events.
        // Never force recovery back onto a patient another action has repositioned.
        if ((toLowerANSI animationState _patient) != "acm_recoveryposition") then {
            [_medic, _patient, false, true, "interrupt"] call FUNC(setRecoveryPosition);
            [_handle] call CBA_fnc_removePerFrameHandler;
        };
    };
    private _lock = _patient getVariable ["ACME_patientAnimLock", []];
    private _accepted = _pending param [5, false];
    private _owns = (_lock param [0, ""]) == _token;
    private _providerEpoch = if (isNull _medic) then {-1} else {_medic getVariable ["ACME_treatmentPoseEpoch", -1]};
    private _expectedEpoch = _pending param [7, -1];
    private _providerValid = isNull _medic || {alive _medic && {[_medic] call ACEFUNC(common,isAwake)}
        && {isNull objectParent _medic} && {(_medic distance _patient) <= 5} && {_providerEpoch <= _expectedEpoch}};
    if (!_providerValid || {serverTime >= (_pending select 2)} || {_accepted && {!_owns}}
        || {(_pending param [8, -1]) != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {_patient getVariable ["ACME_CS_ProcedureActive", false]}) exitWith {
        [_medic, _patient, false, true, "cancel", _token] call FUNC(setRecoveryPosition);
        [_handle] call CBA_fnc_removePerFrameHandler;
    };
    // The begin packet can precede replication of its exact provider epoch. Wait boundedly; never
    // capture a remote old epoch as this action's identity and never accept a newer provider action.
    if (!isNull _medic && {_providerEpoch < _expectedEpoch}) exitWith {};
    if (!_accepted) exitWith {
        // Head elevation's authored release must finish first. Never cut it off or race its settled-pose callback.
        if ((_lock param [1, ""]) == "head-elev-lower" && {(_lock param [4, -1]) > serverTime}) exitWith {};
        if (_patient getVariable ["ACME_headElevated", false]) exitWith {};
        private _lease = [_patient, "", 1, "recovery-position", _medic, 5.5, 2, _token] call ACME_fnc_patientAnimRequest;
        if (_lease == "") then {
            [_medic, _patient, false, true, "cancel", _token] call FUNC(setRecoveryPosition);
            [_handle] call CBA_fnc_removePerFrameHandler;
        } else {
            // Arma 2.18 array syntax blends from the current pose (factor 0) and queues the move itself.
            // This owner-only one-shot deliberately bypasses ACE's string-only animation wrapper.
            _patient switchMove ["ACM_RecoveryPosition", 0, 0, false];
            _pending set [5, true];
            _patient setVariable [QGVAR(RecoveryPosition_Pending), _pending, true];
        };
    };
    if ((toLowerANSI animationState _patient) != "acm_recoveryposition") exitWith {
        // After entering the requested pose, any unrelated move is a successor, never a reason to force it back.
        if ((_pending param [4, -1]) >= 0) then {
            [_medic, _patient, false, true, "cancel", _token] call FUNC(setRecoveryPosition);
            [_handle] call CBA_fnc_removePerFrameHandler;
        };
    };
    if ((_pending param [4, -1]) < 0) then {
        _pending set [4, serverTime];
        _patient setVariable [QGVAR(RecoveryPosition_Pending), _pending, true];
    };
    private _moveBlend = _patient getUnitMovesInfo 3;
    private _settled = _moveBlend isEqualType 0 && {finite _moveBlend} && {_moveBlend >= 0.99};
    if ((_pending param [3, false]) && {_settled} && {serverTime >= ((_pending select 4) + 2)}) then {
        [_medic, _patient, true, _pending param [6, false], "apply", _token] call FUNC(setRecoveryPosition);
    };
}, 0.05, [_medic, _patient, _token, _patient getVariable ["ACME_providerLocalityEpoch", 0]]] call CBA_fnc_addPerFrameHandler;
