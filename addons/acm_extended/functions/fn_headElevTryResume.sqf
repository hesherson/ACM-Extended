// a debounced restore, called a short delay after a maneuver ends.
// it bails if the restore was canceled or if the elevation itself was canceled, and it holds, re-checking, while
// CPR is still running on the casualty, so a continuous CPR session keeps them flat until it finishes. then they
// pop back up to elevated.
// the arg is [_patient].
params ["_patient", ["_token", ""]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient, "headElevTryResume", [_patient, _token]] call ACME_fnc_ownerDispatch;};
if (_token == "") then {_token = _patient getVariable ["ACME_headElev_poseToken", ""];};
if ((_patient getVariable ["ACME_headElev_poseToken", ""]) != _token) exitWith {};
if !(_patient getVariable ["ACME_headElev_ResumePending", false]) exitWith {};

// Unsupported/manual Semi-Fowler is never a passive posture. Once its provider hold was released by any competing
// maneuver, the episode is over and the casualty must be explicitly elevated again.
if (_patient getVariable ["ACME_headElev_manualUnsupported", false]) exitWith {
    private _alreadyFlat = _patient getVariable ["ACME_headElev_Suspended", false];
    [objNull, _patient, _alreadyFlat] call ACME_fnc_headElevateStop;
};

if (_patient getVariable ["ACME_CS_ProcedureActive", false]) exitWith {
    [{_this call ACME_fnc_headElevTryResume;}, [_patient, _token], 0.5] call CBA_fnc_waitAndExecute;
};

// A backpack-supported chest action restores its worn carrier through a visible reverse lift.
// Do not re-elevate the casualty underneath that animation or move the support/carrier props at the same time.
private _chestLeases = _patient getVariable ["ACME_chestAccess_leases", createHashMap];
private _chestBusy = _patient getVariable ["ACME_chestAccess_vestBusy", ""];
if ((count _chestLeases) > 0 || {_chestBusy != ""}) exitWith {
    [{_this call ACME_fnc_headElevTryResume;}, [_patient, _token], 0.5] call CBA_fnc_waitAndExecute;
};

private _readyAt = _patient getVariable ["ACME_headElev_suspendReadyAt", -1];
if (_readyAt > CBA_missionTime) exitWith {
    [{_this call ACME_fnc_headElevTryResume;}, [_patient, _token], ((_readyAt - CBA_missionTime) max 0.05) + 0.05] call CBA_fnc_waitAndExecute;
};

// The release-to-flat tail may still own the patient for a few frames after the nominal suspension time. Re-elevate
// only after that exact animation lease has retired; otherwise the grab request can be denied and leave Semi-Fowler
// logically active but visually flat.
private _animLock = _patient getVariable ["ACME_patientAnimLock", []];
if ((count _animLock) >= 5) then {
    private _lockUntil = _animLock param [4, -1];
    if (_lockUntil isEqualType 0 && {_lockUntil > serverTime}) exitWith {
        [{_this call ACME_fnc_headElevTryResume;}, [_patient, _token], ((_lockUntil - serverTime) max 0.05) + 0.05]
            call CBA_fnc_waitAndExecute;
    };
};

private _leases = _patient getVariable ["ACME_headElev_treatments", createHashMap];
{
    private _entry = _leases get _x;
    private _medic = _entry param [0, objNull];
    if (isNull _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
        || {CBA_missionTime - (_entry param [1, CBA_missionTime]) > 300}) then {_leases deleteAt _x;};
} forEach keys _leases;
if (count _leases > 0) exitWith {
    [{_this call ACME_fnc_headElevTryResume;}, [_patient, _token], 0.75] call CBA_fnc_waitAndExecute;
};
if !(_patient getVariable ["ACME_headElevated", false]) exitWith {
    _patient setVariable ["ACME_headElev_ResumePending", false, true];
};
private _maneuverHandoffUntil = _patient getVariable ["ACME_chestAccess_maneuverHandoffUntil", -1];
if (([_patient] call ACM_core_fnc_cprActive)
    || {(_maneuverHandoffUntil isEqualType 0) && {serverTime < _maneuverHandoffUntil}}) exitWith {
    [{ _this call ACME_fnc_headElevTryResume }, [_patient, _token], 0.50] call CBA_fnc_waitAndExecute;
};
_patient setVariable ["ACME_headElev_ResumePending", false, true];
[_patient] call ACME_fnc_headElevResume;
