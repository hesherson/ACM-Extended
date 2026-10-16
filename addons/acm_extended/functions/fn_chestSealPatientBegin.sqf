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

// B263: a timed-out/closed token may arrive AFTER its owner-targeted End
// (retries and locality redirection can reorder separate events). Never
// resurrect that abandoned workspace, re-remove a vest or restart its roll.
private _retired = _patient getVariable ["ACME_CS_ClosedTokens", []];
if ((_retired findIf {(_x param [0, ""]) == _token
    && {(_x param [1, 0]) > serverTime}}) >= 0) exitWith {};
private _tokens = +(_patient getVariable ["ACME_CS_ProcedureTokens", []]);
private _wasActive = _patient getVariable ["ACME_CS_ProcedureActive", false];
// B268: only a fresh Begin invocation may adopt unfinished preparation after
// ownership changes. An old wait callback must never recapture the new epoch.
// Existing viewers retain their shared token, original posture and live cargo.
private _previousPreparationOwner = _patient getVariable ["ACME_CS_PreparationOwner", []];
private _preparationOwner = [clientOwner, _patient getVariable ["ACME_providerLocalityEpoch", 0],
    _patient getVariable ["ACME_equipmentKitEpoch", 0]];
// A failed kit archive deliberately retains old custody as recovery evidence.
// Neither an old viewer retry nor a new viewer may adopt it into the newer kit.
if (_wasActive && {!(_tokens isEqualTo [])} && {(count _previousPreparationOwner) >= 3}
    && {(_previousPreparationOwner select 2) != (_preparationOwner select 2)}) exitWith {};
private _resumePreparation = _wasActive && {!(_tokens isEqualTo [])}
    && {(_patient getVariable ["ACME_CS_PreparationToken", ""]) != ""}
    && {(_patient getVariable ["ACME_CS_ProcedureReadyAt", -1]) < 0}
    && {(_previousPreparationOwner param [2, _preparationOwner select 2]) == (_preparationOwner select 2)}
    && {(_patient getVariable ["ACME_CS_PreparationOwner", []]) isNotEqualTo _preparationOwner};
if (_token in _tokens && {!_resumePreparation}) exitWith {};
private _first = (_tokens isEqualTo []) || {!_wasActive} || {_resumePreparation};
_patient setVariable ["ACME_CS_ProcedureGeneration", 1 + (_patient getVariable ["ACME_CS_ProcedureGeneration", 0])];
_tokens pushBackUnique _token;
_patient setVariable ["ACME_CS_ProcedureTokens", _tokens, true];
_patient setVariable ["ACME_CS_ProcedureActive", true, true];

// Additional viewers share the existing preparation/ready timestamp.
if (!_first) exitWith {};

// This identity belongs to preparation, not to an individual viewer's lifetime.
// Additional viewers can join/leave without invalidating the first preparation;
// last-viewer cancellation invalidates every queued continuation immediately.
private _prep = if (_resumePreparation) then {_patient getVariable ["ACME_CS_PreparationToken", _token]} else {_token};
_patient setVariable ["ACME_CS_PreparationToken", _prep, true];
_patient setVariable ["ACME_CS_PreparationOwner", _preparationOwner, true];
private _authority = [_patient getVariable ["ACME_equipmentKitEpoch", 0],
    _patient getVariable ["ACME_providerLocalityEpoch", 0], "", _prep];

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
if (_resumePreparation) then {
    _preGrounded = _patient getVariable ["ACME_CS_ProcedureGrounded", _preGrounded];
    private _original = _patient getVariable ["ACME_CS_PreProcedureState", []];
    if ((count _original) == 5) then {_preSide = _original select 0;};
};

// Reopening during teardown restarts preparation but retains the original
// restoration snapshot; an intermediate lift is not the pre-procedure posture.
if (!_wasActive || {(count (_patient getVariable ["ACME_CS_PreProcedureState", []])) != 5}) then {
    _patient setVariable ["ACME_CS_PreProcedureState", [_preSide, _preHeadElev, _preRecovery, _preLying, _preAnim], true];
};
_patient setVariable ["ACME_CS_ProcedureGrounded", _preGrounded, true];
_patient setVariable ["ACME_CS_facing", _preSide, true];
_patient setVariable ["ACME_CS_rollUntil", -1, false];
_patient setVariable ["ACME_CS_ProcedureReadyAt", -1, true];

// Chest preparation replaces recovery rather than saving it for restoration.
// Retire any pending episode too, so a late success callback cannot re-establish
// side positioning after the workspace normalizes the patient.
if (_preRecovery
    || {(_patient getVariable ["ACM_airway_RecoveryPosition_Pending", []]) isNotEqualTo []}
    || {(_patient getVariable ["ACM_airway_RecoveryPosition_Episode", ""]) != ""}) then {
    [_medic, _patient, false, true, "interrupt"] call ACM_airway_fnc_setRecoveryPosition;
};

// New workspace custody starts with clean carrier bookkeeping.
private _staleSaved = +(_patient getVariable ["ACME_CS_vestLoadout", []]);
if ((count _staleSaved) == 2 && {!_resumePreparation}) then {
    // A previous interrupted workspace left gear in custody. Restore correctness first, then begin this episode.
    [_patient, true, _medic, "chestseal", true] call ACME_fnc_chestAccessVestRestore;
};
_patient setVariable ["ACME_CS_vestReadyServer", -1, true];

// Animated carrier preparation owns Semi-Fowler lowering, lift/remove/park/lower, and fixed world-space parking.
[_patient, _medic, "chestseal", false, "", "", _authority] call ACME_fnc_chestAccessVestAcquire;

// Only after the carrier transaction is done may the workspace normalize a legitimately controllable casualty
// to the anterior side. Carrier removal itself normally already leaves the casualty supine.
[{
    params ["_p","_preSide","_preGrounded","_prep","_medic","_authority"];
    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_equipmentKitEpoch", 0]) != (_authority select 0)}
        || {(_p getVariable ["ACME_providerLocalityEpoch", 0]) != (_authority select 1)}
        || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
        || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}) exitWith {true};
    private _ready = _p getVariable ["ACME_CS_vestReadyServer", -1];
    // A previous close may still have been returning the carrier when this
    // workspace joined. After that transaction finishes, acquire the worn vest
    // for this preparation rather than mistaking restoration for chest access.
    if (_ready isEqualType 0 && {_ready >= 0} && {(vest _p) != ""}
        && {(_p getVariable ["ACME_CS_vestBusy", ""]) == ""}
        && {(_p getVariable ["ACME_CS_frontBusy", ""]) == ""}) then {
        [_p, _medic, "chestseal", false, "", "", _authority] call ACME_fnc_chestAccessVestAcquire;
        _ready = _p getVariable ["ACME_CS_vestReadyServer", -1];
    };
    (_ready isEqualType 0) && {_ready >= 0} && {serverTime >= _ready}
        && {(_p getVariable ["ACME_CS_vestBusy", ""]) == ""}
        && {(_p getVariable ["ACME_CS_frontBusy", ""]) == ""}
}, {
    params ["_p","_preSide","_preGrounded","_prep","_medic","_authority"];

    if (isNull _p || {!local _p}
        || {(_p getVariable ["ACME_equipmentKitEpoch", 0]) != (_authority select 0)}
        || {(_p getVariable ["ACME_providerLocalityEpoch", 0]) != (_authority select 1)}
        || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
        || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}
        || {!(_p getVariable ["ACME_CS_ProcedureActive", false])}) exitWith {};

    private _canNormalize = alive _p && {isNull objectParent _p} && {_preGrounded};
    private _actual = [_p, _p getVariable ["ACME_CS_facing", _preSide]] call ACME_fnc_chestSealActualSide;

    if (_canNormalize && {_actual != "front"}) then {
        private _hasProvider = !isNull _medic && {!(_medic isEqualTo _p)} && {alive _medic};
        if (_hasProvider) then {
            [_medic,"chestSealEntryFrontRoll",[_medic,_p,true,_prep]] call ACME_fnc_ownerDispatch;
        } else {
            [_p, "front", false, objNull, true] call ACME_fnc_chestSealRoll;
        };

        // A nominal roll deadline can expire while its finish callback is still queued on a loaded owner.
        // Publish only after the canonical roll actually retires and the body is anterior-up. Provider-backed
        // retries use the same medic4 -> chestSealRoll handoff as the normal Flip button rather than inventing a
        // preparation-only animation.
        private _retryDelay = [0.25, 3.10] select _hasProvider;
        [{
            params ["_p","_prep","_retry","_medic","_authority"];
            if (isNull _p || {!local _p}
                || {(_p getVariable ["ACME_equipmentKitEpoch", 0]) != (_authority select 0)}
                || {(_p getVariable ["ACME_providerLocalityEpoch", 0]) != (_authority select 1)}
                || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
                || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}) exitWith {true};
            if (!alive _p || {!isNull objectParent _p}
                || {!([_p] call ACME_fnc_chestSealCanPhysicalRoll)}) exitWith {true};
            if ((_p getVariable ["ACME_CS_rollToken", ""]) != "") exitWith {false};
            if (([_p, "front"] call ACME_fnc_chestSealActualSide) == "front") exitWith {true};

            private _lock = _p getVariable ["ACME_patientAnimLock", []];
            if (((count _lock) < 5 || {(_lock param [4,-1]) <= serverTime})
                && {CBA_missionTime >= (_retry select 0)}) then {
                private _hasProvider = !isNull _medic && {!(_medic isEqualTo _p)} && {alive _medic};
                private _delay = [0.25, 3.10] select _hasProvider;
                _retry set [0, CBA_missionTime + _delay];
                if (_hasProvider) then {
                    [_medic,"chestSealEntryFrontRoll",[_medic,_p,true,_prep]] call ACME_fnc_ownerDispatch;
                } else {
                    [_p, "front", false, objNull, true] call ACME_fnc_chestSealRoll;
                };
            };
            false
        }, {
            params ["_p","_prep","","","_authority"];
            if (isNull _p || {!local _p}
                || {(_p getVariable ["ACME_equipmentKitEpoch", 0]) != (_authority select 0)}
                || {(_p getVariable ["ACME_providerLocalityEpoch", 0]) != (_authority select 1)}
                || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep}
                || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}) exitWith {};
            _p setVariable ["ACME_CS_ProcedureReadyAt", serverTime, true];
        }, [_p,_prep,[CBA_missionTime + _retryDelay],_medic,_authority]] call CBA_fnc_waitUntilAndExecute;
    } else {
        _p setVariable ["ACME_CS_facing", "front", true];
        _p setVariable ["ACME_CS_ProcedureReadyAt", serverTime, true];
    };
}, [_patient,_preSide,_preGrounded,_prep,_medic,_authority]] call CBA_fnc_waitUntilAndExecute;
