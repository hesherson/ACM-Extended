// Restore a temporarily removed chest plate carrier.
//
// Visible reverse choreography:
//   provider exit is owned by the closing action > patient Grab/Hold > real carrier restored while lifted > patient Release supine.
// Forced cleanup, dead/vehicle patients, or unsafe body-control cases restore gear immediately.
params [
    ["_patient", objNull, [objNull]],
    ["_force", false, [false]],
    ["_medic", objNull, [objNull]],
    ["_context", "access", [""]],
    ["_frontNormalized", false, [false]]
];
if (isNull _patient || {!local _patient}) exitWith {false};
_context = toLowerANSI _context;
if !(_context in ["access","chestseal"]) then {_context = "access";};

private _savedVar = ["ACME_chestAccess_vestLoadout","ACME_CS_vestLoadout"] select (_context == "chestseal");
private _propVar = ["ACME_chestAccess_vestProp","ACME_CS_vestProp"] select (_context == "chestseal");
private _busyVar = ["ACME_chestAccess_vestBusy","ACME_CS_vestBusy"] select (_context == "chestseal");
private _readyVar = ["ACME_chestAccess_readyServer","ACME_CS_vestReadyServer"] select (_context == "chestseal");
private _pfhVar = ["ACME_chestAccess_vestPFH","ACME_CS_vestPFH"] select (_context == "chestseal");

private _restoreBlocked = false;
if (!_force) then {
    if (_context == "access") then {
        private _leases = _patient getVariable ["ACME_chestAccess_leases", createHashMap];
        if ((count _leases) > 0) then {
            _restoreBlocked = true;
        } else {
            private _workspaceBusy = (_patient getVariable ["ACME_CS_ProcedureActive", false])
                || {_patient getVariable ["ACME_Thora_ChestAccessActive", false]};
            private _maneuverBusy = ([_patient] call ACM_core_fnc_cprActive)
                || {[_patient] call ACM_core_fnc_bvmActive};
            private _handoffUntil = _patient getVariable ["ACME_chestAccess_maneuverHandoffUntil", -1];
            private _handoffBusy = (_handoffUntil isEqualType 0) && {serverTime < _handoffUntil};

            if (_workspaceBusy || {_maneuverBusy} || {_handoffBusy}) then {
                _restoreBlocked = true;
                // A final lease can disappear during provider cleanup, but active CPR/BVM or an owner-authoritative
                // swap window still owns an open chest. Defer restoration until every owner is genuinely gone.
                [{
                    params ["_p"];
                    private _until = _p getVariable ["ACME_chestAccess_maneuverHandoffUntil", -1];
                    !(_p getVariable ["ACME_CS_ProcedureActive", false])
                        && {!(_p getVariable ["ACME_Thora_ChestAccessActive", false])}
                        && {!([_p] call ACM_core_fnc_cprActive)}
                        && {!([_p] call ACM_core_fnc_bvmActive)}
                        && {!((_until isEqualType 0) && {serverTime < _until})}
                        && {(count (_p getVariable ["ACME_chestAccess_leases", createHashMap])) == 0}
                }, {
                    _this call ACME_fnc_chestAccessVestRestore;
                }, [_patient,false,_medic,"access",_frontNormalized], 900] call CBA_fnc_waitUntilAndExecute;
            };
        };
    } else {
        if !((_patient getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []) then {
            _restoreBlocked = true;
        };
    };
};
if (_restoreBlocked) exitWith {false};

// Every chest-access exit normalizes anterior-up BEFORE any carrier-restoration animation.
// This also runs when there is no carrier in custody, so closing auscultation after a posterior Flip cannot leave
// the casualty on their stomach.
if (!_frontNormalized && {alive _patient} && {isNull objectParent _patient}) then {
    private _rollToken = _patient getVariable ["ACME_CS_rollToken",""];
    private _rollUntil = _patient getVariable ["ACME_CS_rollUntil",-1];
    private _rollActive = (_rollToken != "") || {(_rollUntil isEqualType 0) && {_rollUntil > CBA_missionTime}};
    if (_rollActive) then {
        [_patient,"front"] call ACME_fnc_patientRollCancel;
    };
};

private _actualBeforeRestore = [_patient, _patient getVariable ["ACME_CS_facing","front"]]
    call ACME_fnc_chestSealActualSide;
private _needFrontNormalize = !_frontNormalized
    && {alive _patient}
    && {isNull objectParent _patient}
    && {_actualBeforeRestore != "front"};

if (_needFrontNormalize) exitWith {
    private _canRollFront = [_patient] call ACME_fnc_chestSealCanPhysicalRoll;
    if (_canRollFront) then {
        [_patient,"front",false,objNull,true] call ACME_fnc_chestSealRoll;
        private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime",1.85];
        if !(_rollTime isEqualType 0 && {finite _rollTime}) then {_rollTime = 1.85;};
        [{
            params ["_p","_force","_medic","_ctx"];
            if (!isNull _p && {local _p}) then {
                _p setVariable ["ACME_CS_facing","front",true];
                [_p,_force,_medic,_ctx,true] call ACME_fnc_chestAccessVestRestore;
            };
        }, [_patient,_force,_medic,_context], (_rollTime max 0.1) + 0.08] call CBA_fnc_waitAndExecute;
    } else {
        // A denied physical roll is not permission to force an unconscious rest pose.
        // Retain the existing deferred gear-restoration path without taking body control.
        [{
            params ["_p","_force","_medic","_ctx"];
            if (!isNull _p && {local _p}) then {
                [_p,_force,_medic,_ctx,true] call ACME_fnc_chestAccessVestRestore;
            };
        }, [_patient,_force,_medic,_context]] call CBA_fnc_execNextFrame;
    };
    true
};

_patient setVariable ["ACME_CS_facing","front",true];

private _saved = +(_patient getVariable [_savedVar, []]);
private _prop = _patient getVariable [_propVar, objNull];

private _finishBookkeeping = {
    params ["_p","_savedVar","_propVar","_busyVar","_readyVar","_pfhVar"];
    private _pfh = _p getVariable [_pfhVar,-1];
    if (_pfh isEqualType 0 && {_pfh >= 0}) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
    _p setVariable [_pfhVar,-1,false];
    _p setVariable [_propVar,objNull,true];
    _p setVariable [_savedVar,[],true];
    _p setVariable [_busyVar,"",false];
    _p setVariable [_readyVar,serverTime,true];

    // The Semi-Fowler support prop can now leave its chest-workspace park point and resume its normal placement.
    private _headProp = _p getVariable ["ACME_headElev_propObj", objNull];
    if (!isNull _headProp) then {_headProp setVariable ["ACME_chestFixedPark", nil, false];};
};

private _restoreNow = {
    params ["_p","_saved","_prop","_savedVar","_propVar","_busyVar","_readyVar","_pfhVar","_finish"];
    private _restored = true;
    if ((vest _p) == "") then {
        private _vestClass = _saved param [0,"",[""]];
        if (_vestClass != "") then {
            private _loadout = getUnitLoadout _p;
            if ((count _loadout) > 4) then {
                _loadout set [4,+_saved];
                _p setUnitLoadout [_loadout,false];
                _restored = (vest _p) == _vestClass;
            };
        };
    };
    if (!isNull _prop) then {detach _prop; deleteVehicle _prop;};
    [_p,_savedVar,_propVar,_busyVar,_readyVar,_pfhVar] call _finish;
    _restored
};

// Nothing is in custody.
if ((count _saved) != 2) exitWith {
    if (!isNull _prop) then {detach _prop; deleteVehicle _prop;};
    [_patient,_savedVar,_propVar,_busyVar,_readyVar,_pfhVar] call _finishBookkeeping;
    true
};

// Never run two reverse lifts for one custody record.
private _busy = _patient getVariable [_busyVar, ""];
if (_busy != "") exitWith {(_busy find "restore:") == 0};

// Animate only a stable, legitimately controllable casualty. Front/supine was guaranteed above.
private _canAnimate = !_force
    && {alive _patient}
    && {isNull objectParent _patient}
    && {!([_patient] call ACME_fnc_animBlocked)}
    && {[_patient] call ACME_fnc_chestSealCanPhysicalRoll};

if (!_canAnimate) exitWith {
    [_patient,_saved,_prop,_savedVar,_propVar,_busyVar,_readyVar,_pfhVar,_finishBookkeeping] call _restoreNow
};

if (_context == "chestseal") then {[_patient] call ACME_fnc_chestSealParkCarrier}
else {[_patient] call ACME_fnc_chestAccessVestPark};

private _liftTime = missionNamespace getVariable ["ACME_chestAccess_vestRestoreLiftTime", 0.50];
if (!(_liftTime isEqualType 0) || {_liftTime <= 0}) then {_liftTime = 0.50;};
private _lowerTime = missionNamespace getVariable ["ACME_chestAccess_vestRestoreLowerTime", 0.55];
if (!(_lowerTime isEqualType 0) || {_lowerTime <= 0}) then {_lowerTime = 0.55;};
private _holdTime = missionNamespace getVariable ["ACME_chestAccess_vestRestoreHold", 0.02];
if (!(_holdTime isEqualType 0) || {_holdTime < 0}) then {_holdTime = 0.02;};
private _animSpeed = missionNamespace getVariable ["ACME_chestAccess_vestRestoreAnimSpeed", 1.60];
if (!(_animSpeed isEqualType 0) || {!finite _animSpeed} || {_animSpeed < 1}) then {_animSpeed = 1.60;};
private _total = _liftTime + _holdTime + _lowerTime;

private _serial = (_patient getVariable ["ACME_chestAccess_restoreSerial",0]) + 1;
_patient setVariable ["ACME_chestAccess_restoreSerial",_serial,false];
private _token = format ["restore:%1:%2:%3",_context,netId _patient,_serial];
_patient setVariable [_busyVar,_token,false];
_patient setVariable [_readyVar,-1,true];

private _beginRestore = {
    params [
        "_p","_medic","_ctx","_saved","_savedVar","_propVar","_busyVar","_readyVar","_pfhVar","_token",
        "_liftTime","_holdTime","_lowerTime","_animSpeed","_total","_finish"
    ];
    if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};

    _p setVariable [_readyVar,serverTime + _total,true];

    // Speed only this restoration episode. A failsafe below resets the coefficient even if a newer patient owner
    // invalidates the restore token before the normal completion callback runs.
    _p setVariable ["ACME_chestAccess_restoreSpeedToken", _token, false];
    ["ace_common_setAnimSpeedCoef", [_p, _animSpeed]] call CBA_fnc_globalEvent;

    [_p,false] call ACME_fnc_headElevCollision;
    [_p,"ACME_HeadElevPatientGrab",2,"chest-access-vest-restore",_medic,_total + 0.5,4,_token]
        call ACME_fnc_patientAnimRequest;
    [_p,_liftTime + _holdTime + 0.25] call ACME_fnc_headElevPinPose;

    // At the top of the lift, put the exact saved carrier back on before the casualty is lowered.
    [{
        params ["_p","_ctx","_saved","_propVar","_busyVar","_token","_lowerTime","_medic"];
        if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};

        if (_ctx == "chestseal") then {[_p] call ACME_fnc_chestSealParkCarrier}
        else {[_p] call ACME_fnc_chestAccessVestPark};

        if ((vest _p) == "") then {
            private _vestClass = _saved param [0,"",[""]];
            if (_vestClass != "") then {
                private _loadout = getUnitLoadout _p;
                if ((count _loadout) > 4) then {
                    _loadout set [4,+_saved];
                    _p setUnitLoadout [_loadout,false];
                };
            };
        };

        private _prop = _p getVariable [_propVar,objNull];
        if (!isNull _prop) then {detach _prop; deleteVehicle _prop;};
        _p setVariable [_propVar,objNull,true];

        if (alive _p && {isNull objectParent _p}) then {
            [_p,"ACME_HeadElevPatientRelease",2,"chest-access-vest-restore",_medic,_lowerTime + 0.4,4,_token]
                call ACME_fnc_patientAnimRequest;
            [_p,_lowerTime + 0.2] call ACME_fnc_headElevPinPose;
        };
    }, [_p,_ctx,_saved,_propVar,_busyVar,_token,_lowerTime,_medic], _liftTime + _holdTime] call CBA_fnc_waitAndExecute;

    // Patient is fully back down before custody clears and the provider exits to normal crouch.
    [{
        params ["_p","_medic","_savedVar","_propVar","_busyVar","_readyVar","_pfhVar","_token","_finish"];
        if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};

        [_p,true] call ACME_fnc_headElevCollision;

        private _lock = _p getVariable ["ACME_patientAnimLock",[]];
        if ((_lock param [0,""]) == _token && {(_lock param [1,""]) == "chest-access-vest-restore"}) then {
            _p setVariable ["ACME_patientAnimLock",[],true];
        };

        if (alive _p && {isNull objectParent _p} && {[_p] call ACME_fnc_chestSealCanPhysicalRoll}) then {
            private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"];
            if ((toLowerANSI animationState _p) != (toLowerANSI _faceUp)) then {
                ["ace_common_switchMove",[_p,_faceUp]] call CBA_fnc_globalEvent;
            };
            _p setVariable ["ACME_CS_facing","front",true];
        };

        if ((_p getVariable ["ACME_chestAccess_restoreSpeedToken",""]) == _token) then {
            _p setVariable ["ACME_chestAccess_restoreSpeedToken", "", false];
            ["ace_common_setAnimSpeedCoef", [_p, 1]] call CBA_fnc_globalEvent;
        };

        [_p,_savedVar,_propVar,_busyVar,_readyVar,_pfhVar] call _finish;
    }, [_p,_medic,_savedVar,_propVar,_busyVar,_readyVar,_pfhVar,_token,_finish], _total]
        call CBA_fnc_waitAndExecute;

    [{
        params ["_p","_tok"];
        if (isNull _p || {!local _p}) exitWith {};
        if ((_p getVariable ["ACME_chestAccess_restoreSpeedToken",""]) == _tok) then {
            _p setVariable ["ACME_chestAccess_restoreSpeedToken", "", false];
            ["ace_common_setAnimSpeedCoef", [_p, 1]] call CBA_fnc_globalEvent;
        };
    }, [_p,_token], _total + 0.25] call CBA_fnc_waitAndExecute;
};

// Provider exit is owned by the minigame/action that is closing. Chest Seal and Auscultation both use the
// Semi-Fowler Putdown/inventory sequence and end in crouch. Carrier restoration therefore animates ONLY the patient;
// starting another medic4 episode here was the unwanted extra animation seen after closing the panels.
[
    _patient,_medic,_context,_saved,_savedVar,_propVar,_busyVar,_readyVar,_pfhVar,_token,
    _liftTime,_holdTime,_lowerTime,_animSpeed,_total,_finishBookkeeping
] call _beginRestore;

true
