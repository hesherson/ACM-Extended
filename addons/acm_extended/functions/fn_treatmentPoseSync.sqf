/* CBA global/JIP receiver for every frozen provider hold (stethoscope, pulse, roll). switchMove seeks the
 * normalized time when the owner could compute one; a phase below zero means freeze in place with no seek.
 * setAnimSpeedCoef is local on each machine, including joining providers. */
params ["_medic", "_epoch", "_operation", ["_main", ""], ["_phase", 0], ["_owner", -1], ["_rate", 1]];
if (isNull _medic) exitWith {};
if !(_operation in ["run", "hold", "exit", "release"]) exitWith {};
private _record = _medic getVariable ["ACME_treatmentPoseRemote", [-1, "", -1]];
if ((_record select 0) > _epoch) exitWith {};
if ((_record select 0) == _epoch && {(_record select 1) == "release"}) exitWith {};
if ((_record select 0) == _epoch && {(_record select 1) == "exit"} && {_operation != "release"}) exitWith {};
if ((_record select 0) == _epoch && {(_record select 1) == "hold"} && {_operation == "run"}) exitWith {};
// The JIP event and object variables have separate delivery paths. Wait for the
// atomic episode record when it is not known yet; unknown is not a cancelled hold.
private _episode = _medic getVariable ["ACME_treatmentPoseEpisode", [-1, false]];
if (_operation in ["run", "hold"] && {(_episode select 0) < _epoch}) exitWith {
    [{
        params ["_medic", "_epoch"];
        isNull _medic || {((_medic getVariable ["ACME_treatmentPoseEpisode", [-1, false]]) select 0) >= _epoch}
    }, {
        _this call ACME_fnc_treatmentPoseSync;
    }, _this, 3] call CBA_fnc_waitUntilAndExecute;
};
// Validate the episode before the owner shortcut too. A delayed hold must never freeze a provider
// after cancellation or during a newer treatment, even when this machine still owns the unit.
if (_operation in ["run", "hold"] && {!(_episode isEqualTo [_epoch, true])}) exitWith {};
// Public episode state may overtake an old stop packet before the new hold reaches this machine.
// That old packet must not restore speed on the new controller's unit.
if ((_episode select 0) > _epoch) exitWith {};
private _ownerChanged = if (isServer) then {owner _medic != _owner} else {local _medic && {clientOwner != _owner}};
if (_operation in ["run", "hold"] && {_ownerChanged}) exitWith {};
if (_operation == "hold" && {local _medic} && {clientOwner == _owner}) exitWith {
    // The owner already sought and froze this frame. Do not restart its animation or camera.
    _medic setVariable ["ACME_treatmentPoseRemote", [_epoch, "hold", -1]];
    _medic setAnimSpeedCoef 0;
};
// Repeated owner packets refresh the same hold, not a new animation. Its local watchdog already
// repairs speed/state drift. Replacing the handler here caused unnecessary unfreeze/seek cycles.
if (_operation == "hold" && {(_record select 0) == _epoch}
    && {(_record select 1) == "hold"} && {(_record select 2) >= 0}) exitWith {};
if ((_record select 2) >= 0) then {
    [(_record select 2)] call CBA_fnc_removePerFrameHandler;
    _medic setAnimSpeedCoef 1;
};
_medic setVariable ["ACME_treatmentPoseRemote", [_epoch, "release", -1]];
if (_operation != "hold") exitWith {
    if !(_rate isEqualType 0 && {finite _rate} && {_rate >= 1} && {_rate <= 3}) then {_rate = 1;};
    _medic setAnimSpeedCoef _rate;
    _medic setVariable ["ACME_treatmentPoseRemote", [_epoch, _operation, -1]];
    if (_operation == "exit") then {
        // The exit has a bounded presentation lifetime. Its epoch/operation check means a newer run/hold,
        // explicit release or cancellation wins even when this callback arrives late.
        [{
            params ["_medic", "_epoch"];
            if (isNull _medic) exitWith {};
            private _record = _medic getVariable ["ACME_treatmentPoseRemote", []];
            if !(_record isEqualTo [_epoch, "exit", -1]) exitWith {};
            if (((_medic getVariable ["ACME_treatmentPoseEpisode", [-1, false]]) select 0) > _epoch) exitWith {};
            if (local _medic && {[_medic] call ACME_fnc_providerStanceOwned}) exitWith {};
            _medic setAnimSpeedCoef 1;
            _medic setVariable ["ACME_treatmentPoseRemote", [_epoch, "release", -1]];
        }, [_medic, _epoch], if (_phase > 0) then {_phase} else {0.85 / _rate}] call CBA_fnc_waitAndExecute;
    };
};
// Remote ownership is server-only; clientOwner identifies the original sending machine.
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious", false]}
    || {_ownerChanged} || {!isNull objectParent _medic}
    || {!((_medic getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [_epoch, true])}) exitWith {};
// Seek first, then freeze. If switchMove resets animation speed internally, the final command still leaves the
// exact requested frame stopped. An unknown owner duration arrives as phase -1 and only freezes in place.
if (_phase >= 0) then {_medic switchMove [_main, _phase, 1, false];};
_medic setAnimSpeedCoef 0;
private _record = [_epoch, "hold", -1, CBA_missionTime];
_medic setVariable ["ACME_treatmentPoseRemote", _record];
private _pfh = [{
    params ["_args", "_pfh"];
    _args params ["_medic", "_epoch", "_main", "_phase", "_owner"];
    private _record = _medic getVariable ["ACME_treatmentPoseRemote", [-1, "", -1]];
    if (isNull _medic || {(_record select 0) != _epoch} || {(_record select 1) != "hold"}) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    private _episodeActive = (_medic getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [_epoch, true];
    private _ownerChanged = if (isServer) then {owner _medic != _owner} else {local _medic && {clientOwner != _owner}};
    private _hardRelease = !alive _medic
        || {_medic getVariable ["ACE_isUnconscious", false]}
        || {!isNull objectParent _medic}
        || {_ownerChanged}
        || {!_episodeActive};
    if (_hardRelease) exitWith {
        // A newer episode may already have applied its rate before this old PFH observes retirement.
        if (((_medic getVariable ["ACME_treatmentPoseEpisode", [-1, false]]) select 0) <= _epoch) then {
            _medic setAnimSpeedCoef 1;
        };
        _medic setVariable ["ACME_treatmentPoseRemote", [_epoch, "release", -1]];
        [_pfh] call CBA_fnc_removePerFrameHandler;
        // Ownership transfer aborts the old provider's theatre on the new owner too.
        if (_ownerChanged && {isServer || {local _medic}}) then {
            if ((_medic getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [_epoch, true]) then {
                _medic setVariable ["ACME_treatmentPoseEpisode", [_epoch, false], true];
            };
            [format ["ACME_treatmentPose_%1_%2", netId _medic, _epoch]] call CBA_fnc_removeGlobalEventJIP;
            if (local _medic && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])}
                && {isNull objectParent _medic} && {toLower animationState _medic == toLower _main}) then {
                [_medic, "AmovPknlMstpSnonWnonDnon", 1] call ACME_fnc_doAnim;
            };
        };
    };
    // Remote animation updates can arrive after the hold packet. Keep observing the active episode:
    // the owner may stay perfectly frozen and therefore never send another correction for this peer.
    private _stateDrift = toLower animationState _medic != toLower _main;
    private _phaseDrift = false;
    if (!_stateDrift && {_phase >= 0}) then {
        private _visiblePhase = _medic getUnitMovesInfo 0;
        if (_visiblePhase isEqualType 0 && {finite _visiblePhase}) then {_phaseDrift = abs (_visiblePhase - _phase) > 0.001;};
    };
    // switchMove on a remote unit is temporary (BI command contract): a later owner animation update can
    // overwrite its phase while the local coefficient still reports zero. Correct actual drift in this frame,
    // before the next render; the old 250 ms throttle allowed visible motion between repairs. No network replay.
    if ((_stateDrift || {_phaseDrift}) && {_phase >= 0}) then {
        _medic switchMove [_main, _phase, 1, false];
        _record set [3, CBA_missionTime];
    };
    // Speed-only drift needs no switchMove. Reassert locally without restarting the move or broadcasting
    // another hold. Even a deferred engine transition cannot make this observer abandon the episode.
    if (getAnimSpeedCoef _medic != 0) then {_medic setAnimSpeedCoef 0;};
}, 0, [_medic, _epoch, _main, _phase, _owner]] call CBA_fnc_addPerFrameHandler;
_record set [2, _pfh];
