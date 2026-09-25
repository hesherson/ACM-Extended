// Release only the matching episode; stale callbacks cannot end a newer action.
// Every ACME-owned treatment pose exits to a movable, unarmed crouch. Weapons are never automatically reselected.
params [["_medic", objNull, [objNull]], ["_mode", "", [""]], ["_epoch", -1, [0]], ["_handoff", false, [false]]];
if (isNull _medic) exitWith {};
private _state = _medic getVariable ["ACME_treatmentPoseState", []];
if (_state isEqualTo []) exitWith {
    // The finite work can be gone while its accelerated exit still owns a timer.
    // A different controller must retire that timer before applying its own rate.
    private _remote = _medic getVariable ["ACME_treatmentPoseRemote", []];
    private _oldEpoch = _remote param [0, -1];
    if (!_handoff || {_epoch >= 0 && {_epoch != _oldEpoch}}) exitWith {};
    if (local _medic && {(_remote param [1, ""]) == "exit"}
        && {(_medic getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [_oldEpoch, false]}) then {
        private _packet = [_medic, _oldEpoch, "release"];
        _packet call ACME_fnc_treatmentPoseSync;
        ["ACME_treatmentPoseSync", _packet] call CBA_fnc_globalEvent;
    };
};
private _currentEpoch = _state param [0, -1];
private _currentMode = _state param [1, ""];
private _main = _state param [2, ""];
private _stage = _state param [3, 0];
private _pfh = _state param [5, -1];
private _exclusion = _state param [7, ""];
private _upright = _state param [16, false];
// B57: these assessment/roll episodes always finish in the project's default unarmed crouch, even if a stale
// upright/menu target made B56 choose a standing medicUp entry.
private _exitUpright = _upright && {!(_currentMode in ["roll","inspect","pulse"])};
if (_mode != "" && {_mode != _currentMode}) exitWith {};
if (_epoch >= 0 && {_epoch != _currentEpoch}) exitWith {};

_medic setVariable ["ACME_treatmentPoseState", []];
if (local _medic && {(_medic getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [_currentEpoch, true]}) then {
    _medic setVariable ["ACME_treatmentPoseEpisode", [_currentEpoch, false], true];
};
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};

// Every phase, including accelerated preparation, is retired through the same ordered receiver.
// A handoff releases immediately; a normal exit blends at the shared rate and has a bounded speed reset.
private _canExit = !_handoff && {local _medic} && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious", false])} && {!([_medic] call ACME_fnc_animBlocked)};
private _operation = ["release", "exit"] select _canExit;
private _rate = if (_canExit) then {call ACME_fnc_choreographyRate} else {1};
[format ["ACME_treatmentPose_%1_%2", netId _medic, _currentEpoch]] call CBA_fnc_removeGlobalEventJIP;
private _packet = [_medic, _currentEpoch, _operation, "", -1, clientOwner, _rate];
_packet call ACME_fnc_treatmentPoseSync;
if (local _medic) then {["ACME_treatmentPoseSync", _packet] call CBA_fnc_globalEvent;};

if (!isNil "ace_advanced_fatigue_setAnimExclusions" && {_exclusion != ""}) then {
    private _index = ace_advanced_fatigue_setAnimExclusions find _exclusion;
    if (_index >= 0) then {ace_advanced_fatigue_setAnimExclusions deleteAt _index;};
};

// Cancel pending queue/reassert ownership so an old entry cannot restart after a cancellation.
_medic setVariable ["ACME_animQ", []];
_medic setVariable ["ACME_animQEnd", 0];
_medic setVariable ["ACME_dah_gen", (_medic getVariable ["ACME_dah_gen", 0]) + 1];
[_medic, [["treatmentEndInAnim"]]] call ACM_core_fnc_setAceMedicalState;

private _current = toLower animationState _medic;
private _ownsEntry = _stage <= 1 && {
    (_current find "amovpknlmstpsnonwnondnon") == 0
    || {(_current find "amovpercmstpsnonwnondnon_amovpknlmstpsnonwnondnon") == 0}
    || {(_current find "amovppnemstpsnonwnondnon_amovpknlmstpsnonwnondnon") == 0}
    || {_upright && {(_current find "amovpercmstpsnonwnondnon") == 0}}
    || {(_current find "aidlpknlmstpsnonwnondnon") == 0}
    || {_main != "" && {(_current find (toLower _main)) >= 0}}
};

// Use playMoveNow through the move graph, never switchMove, so the work state blends back into the normal
// unarmed crouch. Weapon selection is not touched here; the start preflight already cleared it exactly once.
if (!_handoff
    && {local _medic}
    && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {!([_medic] call ACME_fnc_animBlocked)}
    && {_current == toLower _main || {_ownsEntry} || {_stage >= 2} || {_currentMode in ["stethoscope","pulse"]}}) then {
    // B56: a standing medicUp episode exits to the unarmed standing idle; every kneeling episode exits to
    // the unarmed crouch.
    _medic setUnitPos (["MIDDLE", "UP"] select _exitUpright);
    [_medic, ["AmovPknlMstpSnonWnonDnon", "AmovPercMstpSnonWnonDnon"] select _exitUpright, 1] call ACME_fnc_doAnim;

    if (!_exitUpright) then {
        // ACE/ACM can apply its treatment-end move after callbackSuccess. Check once after that handoff; only if
        // the engine actually put us back on our feet do we request the normal stand-to-crouch transition. This is
        // a one-shot correction, not an animation watchdog/restart loop.
        [{
            params ["_unit", "_endedEpoch"];
            if (isNull _unit || {!local _unit} || {!alive _unit} || {_unit getVariable ["ACE_isUnconscious", false]}) exitWith {};
            if ((_unit getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []) exitWith {};
            if ((_unit getVariable ["ACME_treatmentPoseEpoch", 0]) != _endedEpoch) exitWith {};
            if (!isNull objectParent _unit) exitWith {};
            // A newer controller may own stance without incrementing the treatment-pose epoch.
            if ([_unit] call ACME_fnc_providerStanceOwned) exitWith {};
            if (stance _unit == "STAND") then {
                _unit setUnitPos "MIDDLE";
                [_unit, "AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 1] call ACME_fnc_doAnim;
            };
            // MIDDLE is only an animation-entry guard. Release it after the one-shot crouch handoff so the provider
            // remains visually crouched but is never stance-locked once the treatment theatre is finished.
            [{
                params ["_u", "_ep"];
                if (isNull _u || {!local _u} || {!alive _u} || {!isNull objectParent _u}) exitWith {};
                if ((_u getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []) exitWith {};
                if ((_u getVariable ["ACME_treatmentPoseEpoch", 0]) != _ep) exitWith {};
                // A different controller may have acquired the provider after this treatment ended without touching
                // treatmentPoseEpoch. Never let the old delayed stance release break that newer pose.
                if ([_u] call ACME_fnc_providerStanceOwned) exitWith {};
                _u setUnitPos "AUTO";
            }, [_unit, _endedEpoch], 0.85 / (call ACME_fnc_choreographyRate)] call CBA_fnc_waitAndExecute;
        }, [_medic, _currentEpoch], 0.12] call CBA_fnc_waitAndExecute;
    };
};

// A handoff intentionally skips the neutral exit so the next authored action can take over without a visual pop.
// If no newer provider controller actually acquires the medic, release the temporary MIDDLE stance after a short
// grace and once more after ordinary short treatments have had time to finish. Token/owner checks prevent an old
// handoff from breaking a newer pose.
if (_handoff && {local _medic} && {alive _medic}) then {
    private _releaseIfFree = {
        params ["_u","_endedEpoch"];
        if (isNull _u || {!local _u} || {!alive _u} || {!isNull objectParent _u}) exitWith {};
        if ((_u getVariable ["ACME_treatmentPoseEpoch",0]) != _endedEpoch) exitWith {};
        if ([_u] call ACME_fnc_providerStanceOwned) exitWith {};
        _u setUnitPos "AUTO";
    };
    [{
        params ["_u","_endedEpoch","_fn"];
        [_u,_endedEpoch] call _fn;
    }, [_medic,_currentEpoch,_releaseIfFree], 0.35] call CBA_fnc_waitAndExecute;
    [{
        params ["_u","_endedEpoch","_fn"];
        [_u,_endedEpoch] call _fn;
    }, [_medic,_currentEpoch,_releaseIfFree], 4.25] call CBA_fnc_waitAndExecute;
};
