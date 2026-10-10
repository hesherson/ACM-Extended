/* Provider-only Semi-Fowler choreography.
 *
 * Patient motion is owned entirely by the patient-side start/stop functions. The provider sequence never waits on,
 * starts or cancels a patient animation. Chest-seal close publishes a bounded provider-readiness marker so its
 * reverse carrier lift can follow medicEnd; ordinary Semi-Fowler patient/provider motions remain parallel.
 */
params [
    ["_medic", objNull, [objNull]],
    ["_mode", "elevate", [""]],
    ["_exitSession", "", [""]],
    ["_presentation", [], [[]]]
];
if (isNull _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};
_mode = toLowerANSI _mode;
if !(_mode in ["elevate", "lower", "contactexit", "chestsealexit", "mask"]) exitWith {};
if (!local _medic) exitWith {
    [_medic, "headElevMedicSeq", [_medic, _mode, _exitSession, _presentation]] call ACME_fnc_ownerDispatch;
};
if ([_medic] call ACME_fnc_animBlocked) exitWith {};
// B220 optional request fingerprint for owner-acknowledged manual replacement.
// A late packet must not holster/stop the provider's newer treatment or run after
// the provider changed locality. Native treatments and head-position sequences
// can advance without a new finite-pose epoch, so fingerprint both as well.
// All normal head-position callers retain their path.
if (_presentation isNotEqualTo [] && {
    count _presentation != 5
    || {(_presentation param [0, -1]) != (_medic getVariable ["ACME_treatmentPoseEpoch", 0])}
    || {(_presentation param [1, -1]) != (_medic getVariable ["ACME_providerLocalityEpoch", 0])}
    || {serverTime > (_presentation param [2, -1])}
    || {(_presentation param [3, -1]) != (_medic getVariable ["ACME_providerTreatmentEpoch", 0])}
    || {(_presentation param [4, -1]) != (_medic getVariable ["ACME_headElev_medicAnimToken", 0])}
}) exitWith {};

private _prone = stance _medic == "PRONE";
_medic setVariable ["ACME_headElev_providerProne", _prone, false];
// A new head-position episode supersedes any stale local provider theatre immediately.
[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
[_medic, true] call ACME_fnc_menuPoseStop;

private _rest = [_medic, "AmovPknlMstpSnonWnonDnon", _prone] call ACME_fnc_providerAnimation;
_prone = _prone || {_rest == "AmovPpneMstpSnonWnonDnon"};
_medic setVariable ["ACME_headElev_providerProne", _prone, false];
private _forcePose = _rest;
private _first = [_medic, "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown", _prone] call ACME_fnc_providerAnimation;
private _second = if (_prone) then {_rest} else {"AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon"};

private _token = (_medic getVariable ["ACME_headElev_medicAnimToken", 0]) + 1;
_medic setVariable ["ACME_headElev_medicAnimToken", _token, false];
_medic setVariable ["ACME_headElev_medicAnimStage", -1, false];
_medic setVariable ["ACME_headElev_seqActive", true, false];
_medic setVariable ["ACME_headElev_seqMode", _mode, false];
_medic setVariable ["ACME_headElev_seqLastSeen", CBA_missionTime, false];
_medic setVariable ["ACME_headElev_seqPFH", -1, false];
_medic setVariable ["ACME_headElev_pinToken", (_medic getVariable ["ACME_headElev_pinToken", 0]) + 1, false];
private _rate = call ACME_fnc_choreographyRate;
if !(_rate isEqualType 0 && {finite _rate} && {_rate > 0}) then {_rate = 1.5;};
if (_mode == "chestsealexit") then {_rate = 1.5;};
_medic setAnimSpeedCoef _rate;
["ace_common_setAnimSpeedCoef", [_medic, _rate]] call CBA_fnc_globalEvent;

// The closed workspace already owns empty hands. Do not replay holstering or a neutral crouch between its
// frozen contact frame and medicEnd. Logical selection must stay empty when Arma exits the weaponless RTM.
private _prepDelay = if (_mode == "chestsealexit") then {
    _medic selectWeapon "";
    0
} else {[_medic] call ACME_fnc_medicAnimationPrep};
if !(_prepDelay isEqualType 0) then {_prepDelay = 0;};
private _prepUntil = CBA_missionTime + ((_prepDelay max 0) max 0.05);
// This is a fail-safe only. Normal authored playback completes well before it.
private _hardDeadline = CBA_missionTime + 6.0;
private _end = "AinvPknlMstpSnonWnonDnon_medicEnd";
private _endDuration = 2;
if (_mode == "chestsealexit") then {
    private _speed = getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _end >> "speed");
    if (_speed < 0) then {_endDuration = -_speed;} else {if (_speed > 0) then {_endDuration = 1 / _speed;};};
    _endDuration = (_endDuration max 0.05) min 8;
    _hardDeadline = _hardDeadline + _endDuration / _rate + 2;
    // Readiness concerns presentation only. The patient owner still removes workspace tokens, cancels entry
    // and normalizes the casualty immediately. Its carrier lift waits for this exact bounded exit episode.
    _medic setVariable ["ACME_CS_ProviderExitReady", [_exitSession, _token, false, serverTime + _endDuration / _rate + 2], true];
};

private _providerPFH = [{
    params ["_args", "_pfh"];
    _args params ["_u", "_token", "_mode", "_forcePose", "_first", "_second", "_rest",
        "_stage", "_seen", "_stageAt", "_prepUntil", "_hardDeadline", "_prone", "_proneWorkTime",
        "_end", "_endDuration"];

    private _releaseChestGate = {
        params ["_unit", "_finishedToken"];
        if (isNull _unit || {!local _unit}) exitWith {};
        private _ready = _unit getVariable ["ACME_CS_ProviderExitReady", []];
        if ((_ready param [1, -1]) == _finishedToken && {!(_ready param [2, true])}) then {
            _ready set [2, true];
            _unit setVariable ["ACME_CS_ProviderExitReady", _ready, true];
        };
    };

    private _finalize = {
        params ["_u", "_pfh", "_rest", "_token", ["_handoff", false], ["_prone", false]];
        [_pfh] call CBA_fnc_removePerFrameHandler;
        if (isNull _u) exitWith {};
        if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {};
        [_u, _token] call _releaseChestGate;

        _u setVariable ["ACME_headElev_medicAnimStage", -1, false];
        _u setVariable ["ACME_headElev_seqActive", false, false];
        _u setVariable ["ACME_headElev_seqMode", "", false];
        _u setVariable ["ACME_headElev_seqPFH", -1, false];
        _u setVariable ["ACME_headElev_seqLastSeen", CBA_missionTime, false];

        private _dpPauseClass = _u getVariable ["ACME_DP_PauseTreatmentClass", ""];
        if ((_u getVariable ["ACME_DP_Active", false]) && {_dpPauseClass in ["acme_elevatehead", "acme_lowerhead"]}) then {
            _u setVariable ["ACME_DP_Paused", false, false];
            _u setVariable ["ACME_DP_PauseTreatmentClass", "", false];
            if (!_handoff) then {_u setVariable ["ACME_DP_TreatmentBusy", false, false];};
            _u setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
            _u setVariable ["ACME_DP_LastPoseAssert", 0, false];
        };

        _u setVariable ["ACME_headElev_pinToken", (_u getVariable ["ACME_headElev_pinToken", 0]) + 1, false];

        // Local bookkeeping above always retires. Speed ownership is separate from stance ownership: a handoff
        // skips the neutral/rest animation, but it may not strand this sequence's accelerated coefficient.
        if (!local _u) exitWith {};
        if !([_u] call ACME_fnc_providerAnimSpeedOwned) then {
            _u setAnimSpeedCoef 1;
            ["ace_common_setAnimSpeedCoef", [_u, 1]] call CBA_fnc_globalEvent;
        };
        if (_handoff) exitWith {};
        if ([_u] call ACME_fnc_providerStanceOwned) exitWith {};

        if (alive _u && {isNull objectParent _u} && {!(_u getVariable ["ACE_isUnconscious", false])}) then {
            _u selectWeapon "";
            _u setUnitPos (["MIDDLE", "DOWN"] select (_prone || {stance _u == "PRONE"}));
            [_u, _rest, 2] call ACME_fnc_doAnim;
            [{
                params ["_unit", "_finishedToken"];
                if (isNull _unit || {!local _unit} || {!alive _unit} || {!isNull objectParent _unit}
                    || {_unit getVariable ["ACE_isUnconscious", false]}) exitWith {};
                if ((_unit getVariable ["ACME_headElev_medicAnimToken", -1]) != _finishedToken) exitWith {};
                if (_unit getVariable ["ACME_headElev_seqActive", false]) exitWith {};
                if ([_unit] call ACME_fnc_providerStanceOwned) exitWith {};
                _unit setUnitPos "AUTO";
            }, [_u, _token], 0.25] call CBA_fnc_waitAndExecute;
        };
    };

    if (isNull _u) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
    if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {
        // A newer provider episode may supersede this exit without replacing the chest readiness record.
        // Only release this old token; never acknowledge a later chest session.
        [_u, _token] call _releaseChestGate;
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    // A provider can select prone during preflight. Promote the captured posture once,
    // and replace every expected state together so a late stage never requests kneeling.
    if (local _u && {!_prone}
        && {([_u, "AmovPknlMstpSnonWnonDnon"] call ACME_fnc_providerAnimation) == "AmovPpneMstpSnonWnonDnon"}) then {
        _prone = true;
        _forcePose = [_u, _forcePose, true] call ACME_fnc_providerAnimation;
        _first = [_u, _first, true] call ACME_fnc_providerAnimation;
        _rest = [_u, _rest, true] call ACME_fnc_providerAnimation;
        _second = _rest;
        _u setVariable ["ACME_headElev_providerProne", true, false];
        _args set [3, _forcePose]; _args set [4, _first];
        _args set [5, _second]; _args set [6, _rest];
        _args set [12, true];
        _seen = false; _args set [8, false];
    };
    if (!alive _u || {!local _u} || {_u getVariable ["ACE_isUnconscious", false]}
        || {[_u] call ACME_fnc_animBlocked}) exitWith {
        [_u, _pfh, _rest, _token, false, _prone] call _finalize;
    };
    _u setVariable ["ACME_headElev_seqLastSeen", CBA_missionTime, false];

    private _continuousOwns = !((_u getVariable ["ACM_core_ContinuousAction_Session", []]) isEqualTo [])
        && {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]};
    private _treatmentOwns = (_u getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []
        || {(_u getVariable ["ACME_nativeTreatmentRate", []]) isNotEqualTo []}
        || {_u getVariable ["ACME_treatmentPreflightActive", false]}
        || {_u getVariable ["ACME_chestAccessPreflightActive", false]}
        || {_u getVariable ["ACM_circulation_isPerformingCPR", false]};
    if (_continuousOwns || {_treatmentOwns}) exitWith {
        [_u, _pfh, _rest, _token, true, _prone] call _finalize;
    };

    // Movement cancels only provider theatre. It never changes the patient-side Semi-Fowler state.
    private _cancel = false;
    if (hasInterface && {local _u} && {[_u] call ace_common_fnc_isPlayer}) then {
        _cancel = ["MoveForward", "MoveBack", "TurnLeft", "TurnRight", "MoveLeft", "MoveRight",
            "MoveFastForward", "MoveSlowForward"] findIf {(inputAction _x) > 0.05} >= 0;
    };
    if (_cancel) exitWith {
        [_u, _token] call _releaseChestGate;
        call ACME_fnc_headElevateCancelSeq;
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };

    private _now = CBA_missionTime;
    if (_now >= _hardDeadline) exitWith {
        [_u, _pfh, _rest, _token, false, _prone] call _finalize;
    };

    private _state = toLowerANSI animationState _u;
    private _forceLC = toLowerANSI _forcePose;
    private _firstLC = toLowerANSI _first;
    private _secondLC = toLowerANSI _second;

    if (_stage == -3) exitWith {
        private _inEnd = _state == toLowerANSI _end;
        if (_inEnd) then {
            if (!_seen) then {
                _seen = true;
                _args set [8, true];
                _stageAt = _now;
                _args set [9, _now];
            };
            // Animate Rewrite can reset speed on the first non-walk AnimStateChanged event. Restore our
            // owned rate after actual entry, without restarting/seeking the move or affecting another owner.
            if (getAnimSpeedCoef _u != 1.5) then {
                _u setAnimSpeedCoef 1.5;
                ["ace_common_setAnimSpeedCoef", [_u, 1.5]] call CBA_fnc_globalEvent;
            };
            private _nativeDuration = _u getUnitMovesInfo 2;
            if (_nativeDuration isEqualType 0 && {finite _nativeDuration} && {_nativeDuration > 0}) then {
                _endDuration = _nativeDuration;
                _args set [15, _endDuration];
            };
        };
        private _elapsed = (_now - _stageAt) * 1.5;
        if (_inEnd) then {
            private _nativeElapsed = _u getUnitMovesInfo 1;
            if (_nativeElapsed isEqualType 0 && {finite _nativeElapsed} && {_nativeElapsed > 0}) then {
                _elapsed = _nativeElapsed;
                // Entry can be observed after the RTM has already advanced. Preserve that native progress
                // when BI's graph reaches idle and getUnitMovesInfo begins describing the next move.
                _stageAt = _now - _nativeElapsed / 1.5;
                _args set [9, _stageAt];
            };
        };
        private _neutralAfterEnd = _state == toLowerANSI _rest
            || {(_state find "aidlpknlmstpsnonwnondnon") == 0};
        if (_seen && {!_inEnd} && {!_prone} && {!_neutralAfterEnd}) exitWith {
            // Wall time cannot turn a later unrelated move into successful completion of this old sequence.
            [_u, _pfh, _rest, _token, true, _prone] call _finalize;
        };
        private _complete = _prone || {_seen && {_elapsed >= _endDuration - 0.025}};
        if (!_complete && {_seen && {!_inEnd}}) exitWith {
            // A different move interrupted medicEnd. Do not append the carrier reach behind it.
            [_u, _pfh, _rest, _token, true, _prone] call _finalize;
        };
        if (!_complete && {!_seen} && {_now - _stageAt > _endDuration / 1.5 + 2}) exitWith {
            [_u, _pfh, _rest, _token, false, _prone] call _finalize;
        };
        if (!_complete) exitWith {};
        [_u, _token] call _releaseChestGate;
        // Request the existing carrier reach through BI's native exit graph after completed medicEnd.
        [_u, _first, 1] call ACME_fnc_doAnim;
        _u setVariable ["ACME_headElev_medicAnimStage", 1, false];
        _args set [7, 1]; _args set [8, false]; _args set [9, _now];
    };

    if (_stage == -1) exitWith {
        if (currentWeapon _u != "" && {_now < _prepUntil}) exitWith {};
        if (currentWeapon _u != "") then {_u selectWeapon "";};
        _u setUnitPos (["MIDDLE", "DOWN"] select (_prone || {stance _u == "PRONE"}));

        if (_mode == "chestsealexit") exitWith {
            // medicEnd has no authored prone equivalent. Keep the supported prone work instead of raising
            // a prone provider just for the exit, as required by the shared provider posture policy.
            if (_prone) then {
                [_u, _token] call _releaseChestGate;
                [_u, _first, 1] call ACME_fnc_doAnim;
                _u setVariable ["ACME_headElev_medicAnimStage", 1, false];
                _args set [7, 1];
            } else {
                [_u, _end, 1] call ACME_fnc_doAnim;
                _u setVariable ["ACME_headElev_medicAnimStage", -3, false];
                _args set [7, -3];
            };
            _args set [8, false]; _args set [9, _now];
        };

        // B175 standing-casualty auscultation already owns the held hand-out frame of the Putdown entry.
        // Resume directly into the authored Putdown -> crouch return instead of replaying the reach.
        if (_mode == "contactexit") then {
            [_u, _second, 1] call ACME_fnc_doAnim;
            _u setVariable ["ACME_headElev_medicAnimStage", 2, false];
            _args set [7, 2];
            _args set [8, false];
            _args set [9, _now];
        } else {
            [_u, _forcePose, 2] call ACME_fnc_doAnim;
            _u setVariable ["ACME_headElev_medicAnimStage", 0, false];
            _args set [7, 0];
            _args set [8, false];
            _args set [9, _now];
        };
    };

    if (_stage == 0) exitWith {
        if (_state != _forceLC && {_now - _stageAt < 0.20}) exitWith {};
        [_u, _first, 2] call ACME_fnc_doAnim;
        _u setVariable ["ACME_headElev_medicAnimStage", 1, false];
        _args set [7, 1];
        _args set [8, false];
        _args set [9, _now];
    };

    if (_stage == 1) exitWith {
        if (_state == _firstLC) then {
            _seen = true;
            _args set [8, true];
        };

        private _nextAlreadyRunning = _state == _secondLC
            && {!_prone || {_seen && {_now - _stageAt >= _proneWorkTime}}};
        private _finished = (_seen && {_state != _firstLC}) || {_nextAlreadyRunning};
        // The shipped prone support pose loops; it has no Putdown transition edge.
        // Use the same provider work window, then return directly to prone idle.
        if (_prone && {_now - _stageAt >= _proneWorkTime}) then {_finished = true;};
        if (!_finished && {!_seen} && {_now - _stageAt > 4}) then {_finished = true;};
        if (!_finished) exitWith {};

        if (!_nextAlreadyRunning) then {[_u, _second, 2] call ACME_fnc_doAnim;};
        _u setVariable ["ACME_headElev_medicAnimStage", 2, false];
        _args set [7, 2];
        _args set [8, _nextAlreadyRunning];
        _args set [9, _now];
    };

    if (_stage == 2) exitWith {
        if (_state == _secondLC) then {
            _seen = true;
            _args set [8, true];
        };
        private _finished = _seen && {_state != _secondLC || {_prone}};
        if (!_finished && {!_seen} && {_now - _stageAt > 4}) then {_finished = true;};
        if (_finished) then {[_u, _pfh, _rest, _token, false, _prone] call _finalize;};
    };
}, 0, [_medic, _token, _mode, _forcePose, _first, _second, _rest, -1, false,
    CBA_missionTime, _prepUntil, _hardDeadline, _prone, 2.1 / _rate, _end, _endDuration]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_headElev_seqPFH", _providerPFH, false];
