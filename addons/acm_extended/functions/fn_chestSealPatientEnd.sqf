// End the chest-seal casualty workspace.
//
// Supine invariant:
//   - if the casualty is already anterior-up (lying on their back), do not roll them;
//   - if they are posterior-up, roll to the anterior/front view first;
//   - carrier restoration and Semi-Fowler resume happen only after that;
//   - chest work never restores a prone/posterior or recovery-position pose on exit.
params [
    ["_patient", objNull, [objNull]],
    ["_token", "", [""]],
    ["_medic", objNull, [objNull]]
];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    [_patient, "chestSealPatientEnd", [_patient, _token, _medic]] call ACME_fnc_ownerDispatch;
};

private _tokens = +(_patient getVariable ["ACME_CS_ProcedureTokens", []]);
if (_token == "" || {!(_token in _tokens)}) exitWith {};
_tokens = _tokens - [_token];
private _generation = _patient getVariable ["ACME_CS_ProcedureGeneration", 0];
_patient setVariable ["ACME_CS_ProcedureTokens", _tokens, true];
if !(_tokens isEqualTo []) exitWith {};
if !(_patient getVariable ["ACME_CS_ProcedureActive", false]) exitWith {};

// Last-viewer cancellation retires only this workspace's unfinished preparation.
// Queued lift/front-roll callbacks must not restart it after teardown or reopen.
_patient setVariable ["ACME_CS_PreparationToken", "", true];
_patient setVariable ["ACME_CS_ProcedureReadyAt", -1, true];
_patient setVariable ["ACME_CS_frontBusy", "", false];
private _prepareBusy = _patient getVariable ["ACME_CS_vestBusy", ""];
if ((_prepareBusy find "vest:chestseal:") == 0) then {
    _patient setVariable ["ACME_CS_vestBusy", "", false];
    if ((_patient getVariable ["ACME_chestAccess_removeSpeedToken", ""]) == _prepareBusy) then {
        _patient setVariable ["ACME_chestAccess_removeSpeedToken", "", false];
        ["ace_common_setAnimSpeedCoef", [_patient, 1]] call CBA_fnc_globalEvent;
    };
    private _prepareLock = _patient getVariable ["ACME_patientAnimLock", []];
    if ((_prepareLock param [0, ""]) == _prepareBusy
        && {(_prepareLock param [1, ""]) == "chest-access-vest"}) then {
        _patient setVariable ["ACME_patientAnimLock", [], true];
    };
    [_patient, true] call ACME_fnc_headElevCollision;
};

private _pre = +(_patient getVariable ["ACME_CS_PreProcedureState", ["front", false, false, false, ""]]);
private _preHeadElev = _pre param [1, false, [false]];

private _forceFrontRest = {
    params ["_p","_generation"];
    // Delayed/timeout cleanup must not reposition a newly opened workspace.
    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_CS_ProcedureGeneration",-1]) != _generation}
        || {!((_p getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo [])}) exitWith {};

    private _lock = _p getVariable ["ACME_patientAnimLock", []];
    if ((count _lock) >= 5 && {(_lock param [4,-1]) > serverTime}) exitWith {};

    _p setVariable ["ACME_CS_facing", "front", true];

    if (alive _p && {isNull objectParent _p} && {[_p] call ACME_fnc_chestSealCanPhysicalRoll}) then {
        private _actual = [_p, "front"] call ACME_fnc_chestSealActualSide;
        if (_actual != "front") then {
            private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"];
            ["ace_common_switchMove", [_p, _faceUp]] call CBA_fnc_globalEvent;
        };
    };
};

private _finalize = {
    params ["_p","_wasHeadElev","_generation","_forceFront"];
    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_CS_ProcedureGeneration",-1]) != _generation}
        || {!((_p getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo [])}) exitWith {};

    [_p,_generation] call _forceFront;

    _p setVariable ["ACME_CS_ProcedureActive", false, true];
    _p setVariable ["ACME_CS_PreparationToken", "", true];
    _p setVariable ["ACME_CS_ProcedureReadyAt", -1, true];
    _p setVariable ["ACME_CS_ProcedureGrounded", false, true];
    _p setVariable ["ACME_CS_PreProcedureState", [], true];
    _p setVariable ["ACME_CS_rollUntil", -1, false];
    _p setVariable ["ACME_CS_rollToken", "", false];
    _p setVariable ["ACME_CS_vestReadyServer", -1, true];

    private _headProp = _p getVariable ["ACME_headElev_propObj", objNull];
    if (!isNull _headProp) then {_headProp setVariable ["ACME_chestFixedPark", nil, false];};

    // Semi-Fowler is still a back-lying posture. Resume it only after the patient has been normalized front/supine.
    if (_wasHeadElev
        && {_p getVariable ["ACME_headElevated", false]}
        && {_p getVariable ["ACME_headElev_Suspended", false]}
        && {((_p getVariable ["ACME_lido_seizureState",""]) in ["","postictal"])}) then {
        _p setVariable ["ACME_headElev_ResumePending", true, true];
        [{_this call ACME_fnc_headElevTryResume;}, [_p], 0.25] call CBA_fnc_waitAndExecute;
    };
};

private _restoreCarrier = {
    params ["_p","_medic","_head","_generation","_finalize","_forceFront","_restoreCarrier"];
    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_CS_ProcedureGeneration",-1]) != _generation}
        || {!((_p getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo [])}) exitWith {};

    private _busy = _p getVariable ["ACME_CS_vestBusy",""];
    if (_busy != "" && {(_busy find "restore:") != 0}) exitWith {
        [{
            params ["_p","","","_generation"];
            isNull _p || {!local _p}
                || {(_p getVariable ["ACME_CS_ProcedureGeneration",-1]) != _generation}
                || {(_p getVariable ["ACME_CS_vestBusy",""]) == ""}
        }, {
            params ["_p","_medic","_head","_generation","_finalize","_forceFront","_restoreCarrier"];
            [_p,_medic,_head,_generation,_finalize,_forceFront,_restoreCarrier] call _restoreCarrier;
        }, [_p,_medic,_head,_generation,_finalize,_forceFront,_restoreCarrier]] call CBA_fnc_waitUntilAndExecute;
    };

    private _saved = +(_p getVariable ["ACME_CS_vestLoadout", []]);
    if ((count _saved) != 2) exitWith {
        [_p,_generation] call _forceFront;
        [_p,_head,_generation,_forceFront] call _finalize;
    };

    // Rollable casualties are front/supine; an ineligible body is left under its own control.
    private _lock = _p getVariable ["ACME_patientAnimLock", []];
    private _foreignBodyWork = (count _lock) >= 5 && {(_lock param [4,-1]) > serverTime};
    private _started = [_p,_foreignBodyWork,_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
    if (!_started) exitWith {
        [_p,_generation] call _forceFront;
        [_p,_head,_generation,_forceFront] call _finalize;
    };

    [{
        params ["_p","","_generation"];
        isNull _p || {!local _p}
            || {(_p getVariable ["ACME_CS_ProcedureGeneration",-1]) != _generation}
            || {(_p getVariable ["ACME_CS_vestBusy",""]) == ""
                && {(count (_p getVariable ["ACME_CS_vestLoadout",[]])) != 2}}
    }, {
        params ["_p","_head","_generation","_finalize","_forceFront"];
        [_p,_generation] call _forceFront;
        [_p,_head,_generation,_forceFront] call _finalize;
    }, [_p,_head,_generation,_finalize,_forceFront]] call CBA_fnc_waitUntilAndExecute;
};

private _beginRestore = {
    params ["_p","_medic","_head","_generation","_restoreCarrier","_finalize","_forceFront"];
    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_CS_ProcedureGeneration",-1]) != _generation}
        || {!((_p getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo [])}) exitWith {};

    // Cancellation restores gear without seizing a valid competing body lease.
    private _lock = _p getVariable ["ACME_patientAnimLock", []];
    if ((count _lock) >= 5 && {(_lock param [4,-1]) > serverTime}) exitWith {
        [_p,_medic,_head,_generation,_finalize,_forceFront,_restoreCarrier] call _restoreCarrier;
    };

    private _actual = [_p, _p getVariable ["ACME_CS_facing","front"]] call ACME_fnc_chestSealActualSide;
    if (_actual == "front") exitWith {
        _p setVariable ["ACME_CS_facing","front",true];
        [_p,_medic,_head,_generation,_finalize,_forceFront,_restoreCarrier] call _restoreCarrier;
    };

    private _canRoll = alive _p
        && {isNull objectParent _p}
        && {[_p] call ACME_fnc_chestSealCanPhysicalRoll};

    if (_canRoll) exitWith {
        [_p, "front", false, objNull, true] call ACME_fnc_chestSealRoll;
        private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime",1.85];
        if !(_rollTime isEqualType 0 && {finite _rollTime}) then {_rollTime = 1.85;};

        [{
            params ["_p","_medic","_head","_generation","_restoreCarrier","_finalize","_forceFront"];
            [_p,_generation] call _forceFront;
            [_p,_medic,_head,_generation,_finalize,_forceFront,_restoreCarrier] call _restoreCarrier;
        }, [_p,_medic,_head,_generation,_restoreCarrier,_finalize,_forceFront], (_rollTime max 0.1) + 0.08]
            call CBA_fnc_waitAndExecute;
    };

    // No physical-roll permission: leave the body alone while completing gear restoration.
    [_p,_generation] call _forceFront;
    [{
        params ["_p","_medic","_head","_generation","_finalize","_forceFront","_restoreCarrier"];
        [_p,_medic,_head,_generation,_finalize,_forceFront,_restoreCarrier] call _restoreCarrier;
    }, [_p,_medic,_head,_generation,_finalize,_forceFront,_restoreCarrier]] call CBA_fnc_execNextFrame;
};

// Closing during a live Flip always settles the casualty anterior-up before any other teardown animation.
private _rollToken = _patient getVariable ["ACME_CS_rollToken",""];
private _rollUntil = _patient getVariable ["ACME_CS_rollUntil",-1];
private _rollActive = (_rollToken != "") || {(_rollUntil isEqualType 0) && {_rollUntil > CBA_missionTime}};
if (_rollActive) then {
    [_patient, "front"] call ACME_fnc_patientRollCancel;
};

[_patient,_medic,_preHeadElev,_generation,_restoreCarrier,_finalize,_forceFrontRest] call _beginRestore;
