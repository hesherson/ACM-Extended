/* Provider-only Semi-Fowler choreography.
 *
 * Patient motion is owned entirely by the patient-side start/stop functions. The provider sequence never waits on,
 * starts, cancels or acknowledges a patient animation. This keeps the authored patient and provider motions parallel
 * and prevents a provider UI/menu lifecycle from stranding the casualty half-way through Semi-Fowler.
 */
params [
    ["_medic", objNull, [objNull]],
    ["_mode", "elevate", [""]]
];
if (isNull _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};
_mode = toLowerANSI _mode;
if !(_mode in ["elevate", "lower"]) exitWith {};
if (!local _medic) exitWith {
    [_medic, "headElevMedicSeq", [_medic, _mode]] call ACME_fnc_ownerDispatch;
};
if ([_medic] call ACME_fnc_animBlocked) exitWith {};

// A new head-position episode supersedes any stale local provider theatre immediately.
[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
[_medic, true] call ACME_fnc_menuPoseStop;

private _rest = "AmovPknlMstpSnonWnonDnon";
private _forcePose = _rest;
private _first = "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown";
private _second = "AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon";

private _token = (_medic getVariable ["ACME_headElev_medicAnimToken", 0]) + 1;
_medic setVariable ["ACME_headElev_medicAnimToken", _token, false];
_medic setVariable ["ACME_headElev_medicAnimStage", -1, false];
_medic setVariable ["ACME_headElev_seqActive", true, false];
_medic setVariable ["ACME_headElev_seqMode", _mode, false];
// Retire the old cross-owner handshake variable. It is not part of the provider-only contract in B166.
_medic setVariable ["ACME_headElev_pendingMove", [], false];

_medic setVariable ["ACME_headElev_pinToken", (_medic getVariable ["ACME_headElev_pinToken", 0]) + 1, false];
private _rate = call ACME_fnc_choreographyRate;
if !(_rate isEqualType 0 && {finite _rate} && {_rate > 0}) then {_rate = 1.5;};
_medic setAnimSpeedCoef _rate;
["ace_common_setAnimSpeedCoef", [_medic, _rate]] call CBA_fnc_globalEvent;

private _prepDelay = [_medic] call ACME_fnc_medicAnimationPrep;
if !(_prepDelay isEqualType 0) then {_prepDelay = 0;};
private _prepUntil = CBA_missionTime + ((_prepDelay max 0) max 0.05);
// This is a fail-safe only. Normal authored playback completes well before it.
private _hardDeadline = CBA_missionTime + 6.0;

[{
    params ["_args", "_pfh"];
    _args params ["_u", "_token", "_mode", "_forcePose", "_first", "_second", "_rest",
        "_stage", "_seen", "_stageAt", "_prepUntil", "_hardDeadline"];

    private _finalize = {
        params ["_u", "_pfh", "_rest", "_token", ["_handoff", false]];
        [_pfh] call CBA_fnc_removePerFrameHandler;
        if (isNull _u) exitWith {};
        if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {};

        _u setVariable ["ACME_headElev_pendingMove", [], false];
        _u setVariable ["ACME_headElev_medicAnimStage", -1, false];
        _u setVariable ["ACME_headElev_seqActive", false, false];
        _u setVariable ["ACME_headElev_seqMode", "", false];

        private _dpPauseClass = _u getVariable ["ACME_DP_PauseTreatmentClass", ""];
        if ((_u getVariable ["ACME_DP_Active", false]) && {_dpPauseClass in ["acme_elevatehead", "acme_lowerhead"]}) then {
            _u setVariable ["ACME_DP_Paused", false, false];
            _u setVariable ["ACME_DP_PauseTreatmentClass", "", false];
            if (!_handoff) then {_u setVariable ["ACME_DP_TreatmentBusy", false, false];};
            _u setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
            _u setVariable ["ACME_DP_LastPoseAssert", 0, false];
        };

        _u setVariable ["ACME_headElev_pinToken", (_u getVariable ["ACME_headElev_pinToken", 0]) + 1, false];

        // Local bookkeeping above always retires. A newer treatment owns the provider presentation during a handoff.
        if (!local _u || {_handoff}) exitWith {};
        if ([_u] call ACME_fnc_providerStanceOwned) exitWith {};

        _u setAnimSpeedCoef 1;
        ["ace_common_setAnimSpeedCoef", [_u, 1]] call CBA_fnc_globalEvent;

        if (alive _u && {isNull objectParent _u} && {!(_u getVariable ["ACE_isUnconscious", false])}) then {
            _u selectWeapon "";
            _u setUnitPos "MIDDLE";
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
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    if (!alive _u || {!local _u} || {_u getVariable ["ACE_isUnconscious", false]}
        || {[_u] call ACME_fnc_animBlocked}) exitWith {
        [_u, _pfh, _rest, _token] call _finalize;
    };

    private _continuousOwns = !((_u getVariable ["ACM_core_ContinuousAction_Session", []]) isEqualTo [])
        && {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]};
    private _treatmentOwns = (_u getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []
        || {(_u getVariable ["ACME_nativeTreatmentRate", []]) isNotEqualTo []}
        || {_u getVariable ["ACME_treatmentPreflightActive", false]}
        || {_u getVariable ["ACME_chestAccessPreflightActive", false]}
        || {_u getVariable ["ACM_circulation_isPerformingCPR", false]};
    if (_continuousOwns || {_treatmentOwns}) exitWith {
        [_u, _pfh, _rest, _token, true] call _finalize;
    };

    // Movement cancels only provider theatre. It never changes the patient-side Semi-Fowler state.
    private _cancel = false;
    if (hasInterface && {!isNil "ACE_player"} && {_u isEqualTo ACE_player}) then {
        _cancel = ["MoveForward", "MoveBack", "TurnLeft", "TurnRight", "MoveLeft", "MoveRight",
            "MoveFastForward", "MoveSlowForward"] findIf {(inputAction _x) > 0.05} >= 0;
    };
    if (_cancel) exitWith {
        call ACME_fnc_headElevateCancelSeq;
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };

    private _now = CBA_missionTime;
    if (_now >= _hardDeadline) exitWith {
        [_u, _pfh, _rest, _token] call _finalize;
    };

    private _state = toLowerANSI animationState _u;
    private _forceLC = toLowerANSI _forcePose;
    private _firstLC = toLowerANSI _first;
    private _secondLC = toLowerANSI _second;

    if (_stage == -1) exitWith {
        if (currentWeapon _u != "" && {_now < _prepUntil}) exitWith {};
        if (currentWeapon _u != "") then {_u selectWeapon "";};
        _u setUnitPos "MIDDLE";
        [_u, _forcePose, 2] call ACME_fnc_doAnim;
        _u setVariable ["ACME_headElev_medicAnimStage", 0, false];
        _args set [7, 0];
        _args set [8, false];
        _args set [9, _now];
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

        private _nextAlreadyRunning = _state == _secondLC;
        private _finished = (_seen && {_state != _firstLC}) || {_nextAlreadyRunning};
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
        private _finished = _seen && {_state != _secondLC};
        if (!_finished && {!_seen} && {_now - _stageAt > 4}) then {_finished = true;};
        if (_finished) then {[_u, _pfh, _rest, _token] call _finalize;};
    };
}, 0, [_medic, _token, _mode, _forcePose, _first, _second, _rest, -1, false,
    CBA_missionTime, _prepUntil, _hardDeadline]] call CBA_fnc_addPerFrameHandler;
