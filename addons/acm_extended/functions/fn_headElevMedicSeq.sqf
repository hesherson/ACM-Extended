/* B89 provider-only head-position sequence.
 *
 * Patient animations are not owned or modified here.
 *
 * ELEVATE AND LOWER / SUPINE PROVIDER CONTRACT
 *   1. Put the provider in empty hands.
 *   2. Force AmovPknlMstpSnonWnonDnon.
 *   3. Play AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown once.
 *   4. Play AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon once.
 *   5. Finish in AmovPknlMstpSnonWnonDnon.
 *
 * Both head-position actions deliberately use the same provider sequence. Each finite move is REQUESTED AT MOST
 * ONCE. If the vanilla move graph has already entered the next requested move by itself, the controller adopts
 * that state instead of requesting it again. This prevents the exact-once Putdown moves from restarting at their
 * completion boundary.
 */
params [
    ["_medic", objNull, [objNull]],
    ["_mode", "elevate", [""]]
];
// Provider consciousness is separate from the casualty's eligibility for head positioning.
if (isNull _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};
_mode = toLower _mode;
if !(_mode in ["elevate", "lower"]) exitWith {};
if (!local _medic) exitWith {
    [_medic, "headElevMedicSeq", [_medic, _mode]] call ACME_fnc_ownerDispatch;
};
if ([_medic] call ACME_fnc_animBlocked) exitWith {};

private _rest = "AmovPknlMstpSnonWnonDnon";
private _forcePose = _rest;
private _first = "AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown";
private _second = "AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon";

private _token = (_medic getVariable ["ACME_headElev_medicAnimToken", 0]) + 1;
_medic setVariable ["ACME_headElev_medicAnimToken", _token, false];
_medic setVariable ["ACME_headElev_medicAnimStage", -1, false];
_medic setVariable ["ACME_headElev_seqActive", true, false];
_medic setVariable ["ACME_headElev_seqMode", _mode, false];

// Neutralize legacy provider-only animation modifiers. B89 uses the native authored speeds and no position pin.
_medic setVariable ["ACME_headElev_pinToken", (_medic getVariable ["ACME_headElev_pinToken", 0]) + 1, false];
["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;

// Empty hands are requested once. If another mod delays the holster beyond the normal settle window, selectWeapon
// is only a fallback to enforce the contract; ACME never restores the weapon after head positioning.
private _prepDelay = [_medic] call ACME_fnc_medicAnimationPrep;
if !(_prepDelay isEqualType 0) then {_prepDelay = 0;};
private _prepUntil = CBA_missionTime + ((_prepDelay max 0) max 0.05);

[{
    params ["_args", "_pfh"];
    _args params ["_u", "_token", "_mode", "_forcePose", "_first", "_second", "_rest", "_stage", "_seen", "_stageAt", "_prepUntil"];

    private _finalize = {
        params ["_u", "_pfh", "_rest", "_token"];
        [_pfh] call CBA_fnc_removePerFrameHandler;
        if (isNull _u) exitWith {};
        // A newer provider sequence owns the unit now. Retire this PFH without touching the new sequence.
        if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {};
        _u setVariable ["ACME_headElev_medicAnimStage", -1, false];
        _u setVariable ["ACME_headElev_seqActive", false, false];
        _u setVariable ["ACME_headElev_seqMode", "", false];
        private _dpPauseClass = _u getVariable ["ACME_DP_PauseTreatmentClass", ""];
        if ((_u getVariable ["ACME_DP_Active", false]) && {_dpPauseClass in ["acme_elevatehead", "acme_lowerhead"]}) then {
            _u setVariable ["ACME_DP_Paused", false, false];
            _u setVariable ["ACME_DP_PauseTreatmentClass", "", false];
            _u setVariable ["ACME_DP_TreatmentBusy", false, false];
            _u setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
            _u setVariable ["ACME_DP_LastPoseAssert", 0, false];
        };
        _u setVariable ["ACME_headElev_pinToken", (_u getVariable ["ACME_headElev_pinToken", 0]) + 1, false];
        ["ace_common_setAnimSpeedCoef", [_u, 1]] call CBA_fnc_globalEvent;

        if (alive _u && {local _u} && {isNull objectParent _u}
            && {!(_u getVariable ["ACE_isUnconscious", false])}) then {
            _u selectWeapon "";
            _u setUnitPos "MIDDLE";
            // Final state is always the requested unarmed crouch, regardless of which move graph edge ended the
            // finite sequence.
            [_u, _rest, 2] call ACME_fnc_doAnim;
            // MIDDLE is only the entry/final-pose guard. Release it after the crouch is established so the player
            // is never trapped by head positioning and can move/change stance normally.
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

    private _now = CBA_missionTime;
    private _state = toLower animationState _u;
    private _forceLC = toLower _forcePose;
    private _firstLC = toLower _first;
    private _secondLC = toLower _second;
    private _restLC = toLower _rest;

    // -1: one-time empty-hands preflight, then force the requested starting stance/state.
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

    // 0: the forced unarmed stand/crouch is established. Start the first finite move once.
    if (_stage == 0) exitWith {
        if (_state != _forceLC && {_now - _stageAt < 0.20}) exitWith {};
        [_u, _first, 2] call ACME_fnc_doAnim;
        _u setVariable ["ACME_headElev_medicAnimStage", 1, false];
        _args set [7, 1];
        _args set [8, false];
        _args set [9, _now];
    };

    // 1: wait for the first finite move to finish. Never request it a second time.
    if (_stage == 1) exitWith {
        if (_state == _firstLC) then {
            _seen = true;
            _args set [8, true];
        };

        private _nextAlreadyRunning = _state == _secondLC;
        private _finished = (_seen && {_state != _firstLC}) || {_nextAlreadyRunning};
        // Safety only: if a third-party move graph hides/renames the state, do not strand the provider forever.
        if (!_finished && {!_seen} && {_now - _stageAt > 4}) then {_finished = true;};
        if (!_finished) exitWith {};

        // A vanilla Putdown graph may already be in the requested exit. In that case adopt it; requesting it
        // again would play the exit twice.
        if (!_nextAlreadyRunning) then {[_u, _second, 2] call ACME_fnc_doAnim;};
        _u setVariable ["ACME_headElev_medicAnimStage", 2, false];
        _args set [7, 2];
        _args set [8, _nextAlreadyRunning];
        _args set [9, _now];
    };

    // 2: let the second finite move play exactly once, then force the final unarmed crouch.
    if (_stage == 2) exitWith {
        if (_state == _secondLC) then {
            _seen = true;
            _args set [8, true];
        };

        private _finished = _seen && {_state != _secondLC};
        if (!_finished && {!_seen} && {_now - _stageAt > 4}) then {_finished = true;};
        if (_finished) then {[_u, _pfh, _rest, _token] call _finalize;};
    };
}, 0, [_medic, _token, _mode, _forcePose, _first, _second, _rest, -1, false, CBA_missionTime, _prepUntil]] call CBA_fnc_addPerFrameHandler;
