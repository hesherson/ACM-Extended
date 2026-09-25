// Begin the temporary casualty workspace used by the chest-seal minigame.
// The first viewer owns physical preparation; later viewers join the already prepared state.
params [
    ["_patient", objNull, [objNull]],
    ["_token", "", [""]],
    ["_medic", objNull, [objNull]]
];
if (isNull _patient || {_token == ""}) exitWith {};
if (!local _patient) exitWith {
    [_patient, "chestSealPatientBegin", [_patient, _token, _medic]] call ACME_fnc_ownerDispatch;
};

private _tokens = +(_patient getVariable ["ACME_CS_ProcedureTokens", []]);
if (_token in _tokens) exitWith {};
private _wasActive = _patient getVariable ["ACME_CS_ProcedureActive", false];
private _first = (_tokens isEqualTo []) || {!_wasActive};
_patient setVariable ["ACME_CS_ProcedureGeneration", 1 + (_patient getVariable ["ACME_CS_ProcedureGeneration", 0])];
_tokens pushBack _token;
_patient setVariable ["ACME_CS_ProcedureTokens", _tokens, true];
_patient setVariable ["ACME_CS_ProcedureActive", true, true];

// Additional viewers share the existing preparation/ready timestamp.
if (!_first) exitWith {};

// This identity belongs to preparation, not to an individual viewer's lifetime.
// Additional viewers can join/leave without invalidating the first preparation;
// last-viewer cancellation invalidates every queued continuation immediately.
_patient setVariable ["ACME_CS_PreparationToken", _token, true];

private _preHeadElev = _patient getVariable ["ACME_headElevated", false];
private _preSide = if (_preHeadElev) then {
    "front"
} else {
    [_patient, _patient getVariable ["ACME_CS_facing", "front"]] call ACME_fnc_chestSealActualSide
};
private _preRecovery = _patient getVariable ["ACM_airway_RecoveryPosition_State", false];
private _preLying = _patient getVariable ["ACM_core_Lying_State", false];
private _preAnim = animationState _patient;
private _preGrounded = [_patient] call ACME_fnc_chestSealCanPhysicalRoll;

// Reopening during teardown restarts preparation but retains the original
// restoration snapshot; an intermediate lift is not the pre-procedure posture.
if (!_wasActive || {(count (_patient getVariable ["ACME_CS_PreProcedureState", []])) != 5}) then {
    _patient setVariable ["ACME_CS_PreProcedureState", [_preSide, _preHeadElev, _preRecovery, _preLying, _preAnim], true];
};
_patient setVariable ["ACME_CS_ProcedureGrounded", _preGrounded, true];
_patient setVariable ["ACME_CS_facing", _preSide, true];
_patient setVariable ["ACME_CS_rollUntil", -1, false];
_patient setVariable ["ACME_CS_ProcedureReadyAt", -1, true];

// Recovery position is suspended for the workspace; exact restoration happens after carrier restoration on close.
if (_preRecovery) then {
    _patient setVariable ["ACM_airway_RecoveryPosition_State", false, true];
    _patient setVariable ["ACM_airway_HeadTilt_State", false, true];
};

// New workspace custody starts with clean carrier bookkeeping.
private _staleSaved = +(_patient getVariable ["ACME_CS_vestLoadout", []]);
if ((count _staleSaved) == 2) then {
    // A previous interrupted workspace left gear in custody. Restore correctness first, then begin this episode.
    [_patient, true, _medic, "chestseal", true] call ACME_fnc_chestAccessVestRestore;
};
_patient setVariable ["ACME_CS_vestReadyServer", -1, true];

// Animated carrier preparation owns Semi-Fowler lowering, lift/remove/park/lower, and fixed world-space parking.
[_patient, _medic, "chestseal"] call ACME_fnc_chestAccessVestAcquire;

// Only after the carrier transaction is done may the workspace normalize a legitimately controllable casualty
// to the anterior side. Carrier removal itself normally already leaves the casualty supine.
[{
    params ["_p","_preSide","_preGrounded","_prep","_medic"];
    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
        || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}) exitWith {true};
    private _ready = _p getVariable ["ACME_CS_vestReadyServer", -1];
    // A previous close may still have been returning the carrier when this
    // workspace joined. After that transaction finishes, acquire the worn vest
    // for this preparation rather than mistaking restoration for chest access.
    if (_ready isEqualType 0 && {_ready >= 0} && {(vest _p) != ""}
        && {(_p getVariable ["ACME_CS_vestBusy", ""]) == ""}
        && {(_p getVariable ["ACME_CS_frontBusy", ""]) == ""}) then {
        [_p, _medic, "chestseal"] call ACME_fnc_chestAccessVestAcquire;
        _ready = _p getVariable ["ACME_CS_vestReadyServer", -1];
    };
    (_ready isEqualType 0) && {_ready >= 0} && {serverTime >= _ready}
        && {(_p getVariable ["ACME_CS_vestBusy", ""]) == ""}
        && {(_p getVariable ["ACME_CS_frontBusy", ""]) == ""}
}, {
    params ["_p","_preSide","_preGrounded","_prep"];

    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
        || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}
        || {!(_p getVariable ["ACME_CS_ProcedureActive", false])}) exitWith {};

    private _canNormalize = alive _p && {isNull objectParent _p} && {_preGrounded};
    private _actual = [_p, _p getVariable ["ACME_CS_facing", _preSide]] call ACME_fnc_chestSealActualSide;

    if (_canNormalize && {_actual != "front"}) then {
        [_p, "front", false, objNull] call ACME_fnc_chestSealRoll;
        // A nominal roll deadline can expire while its finish callback is still
        // queued on a loaded owner. Publish only after the roll actually retires
        // and the body is anterior-up; a denied competing lease is not readiness.
        [{
            params ["_p","_prep","_retry"];
            if (isNull _p || {!local _p}
                || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
                || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}) exitWith {true};
            if (!alive _p || {!isNull objectParent _p}
                || {!([_p] call ACME_fnc_chestSealCanPhysicalRoll)}) exitWith {true};
            if ((_p getVariable ["ACME_CS_rollToken", ""]) != "") exitWith {false};
            if (([_p, "front"] call ACME_fnc_chestSealActualSide) == "front") exitWith {true};

            // A denied request has no roll token. Retry only after the competing
            // lease retires, at a bounded cadence, without stealing that lease.
            private _lock = _p getVariable ["ACME_patientAnimLock", []];
            if (((count _lock) < 5 || {(_lock param [4,-1]) <= serverTime})
                && {CBA_missionTime >= (_retry select 0)}) then {
                _retry set [0, CBA_missionTime + 0.25];
                [_p, "front", false, objNull] call ACME_fnc_chestSealRoll;
            };
            false
        }, {
            params ["_p","_prep"];
            if (isNull _p || {!local _p}
                || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
                || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}) exitWith {};
            _p setVariable ["ACME_CS_ProcedureReadyAt", serverTime, true];
        }, [_p,_prep,[CBA_missionTime + 0.25]]] call CBA_fnc_waitUntilAndExecute;
    } else {
        _p setVariable ["ACME_CS_facing", "front", true];
        _p setVariable ["ACME_CS_ProcedureReadyAt", serverTime, true];
    };
}, [_patient,_preSide,_preGrounded,_token,_medic]] call CBA_fnc_waitUntilAndExecute;
