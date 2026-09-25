/* Provider theatre for every physical front/back patient roll.
 *
 * B48 routes the roll through the same transition owner as the examination actions. B54: the provider crouches
 * first if needed, then plays AinvPknlMstpSnonWnonDnon_medic4 at the shared rate, frozen at native
 * 2.2 s and blended back to the crouch by the controller. Empty hands are selected once at episode entry; there is
 * no TSP sling chain, repeated holster request, or automatic weapon redraw.
 * Movement cancels the provider theatre immediately. The patient roll itself remains owned by the action that
 * requested it and is not cancelled by moving the provider.
 */
params [["_medic", objNull, [objNull]], ["_source", "", [""]], ["_patient", objNull, [objNull]]];
if (isNull _medic || {!local _medic} || {!alive _medic}) exitWith {false};
if ([_medic] call ACME_fnc_animBlocked) exitWith {false};

private _oldPFH = _medic getVariable ["ACME_rollProviderPFH", -1];
if (_oldPFH >= 0) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};

private _token = format ["%1:%2:%3", clientOwner, netId _medic, diag_tickTime];
_medic setVariable ["ACME_rollProviderToken", _token];
_medic setVariable ["ACME_rollProviderActive", true];
_medic setVariable ["ACME_rollProviderSource", _source];
_medic setVariable ["ACME_rollProviderStarted", diag_tickTime];

private _duration = missionNamespace getVariable ["ACME_rollProviderDuration", 2.2];
private _poseEpoch = [_medic, "roll", _duration, _patient] call ACME_fnc_treatmentPoseStart;
if (_poseEpoch < 0) exitWith {
    _medic setVariable ["ACME_rollProviderActive", false];
    _medic setVariable ["ACME_rollProviderToken", ""];
    false
};

private _finish = {
    params ["_unit", "_tok", "_epoch", ["_cancelled", false]];
    if (isNull _unit) exitWith {};
    if ((_unit getVariable ["ACME_rollProviderToken", ""]) != _tok) exitWith {};
    private _id = _unit getVariable ["ACME_rollProviderPFH", -1];
    if (_id >= 0) then {[_id] call CBA_fnc_removePerFrameHandler;};
    _unit setVariable ["ACME_rollProviderActive", false];
    _unit setVariable ["ACME_rollProviderToken", ""];
    _unit setVariable ["ACME_rollProviderPFH", -1];
    [_unit, "roll", _epoch] call ACME_fnc_treatmentPoseStop;
};

// B54: the pose controller ends the roll theatre itself from the frozen 2.2 s frame (ACME_poseHoldAt and
// ACME_poseStopAfterHold). This timer is only a fail-safe; it allows for the crouch entry that precedes the RTM.
[{
    params ["_unit", "_tok", "_epoch", "_fnFinish"];
    [_unit, _tok, _epoch, false] call _fnFinish;
}, [_medic, _token, _poseEpoch, _finish], _duration + 2.5] call CBA_fnc_waitAndExecute;

private _pfh = [{
    params ["_args", "_id"];
    _args params ["_unit", "_tok", "_epoch", "_fnFinish"];
    if (isNull _unit || {!local _unit} || {!alive _unit} || {(_unit getVariable ["ACME_rollProviderToken", ""]) != _tok}) exitWith {
        if (!isNull _unit) then {[_unit, _tok, _epoch, true] call _fnFinish;};
        [_id] call CBA_fnc_removePerFrameHandler;
    };
    // The treatment controller ends at the held sample. Retire its roll ownership on the next frame,
    // so a completed roll cannot block menu return or the bounded exit-speed/stance release.
    private _pose = _unit getVariable ["ACME_treatmentPoseState", []];
    if ((_pose param [0, -1]) != _epoch) exitWith {
        [_unit, _tok, _epoch, false] call _fnFinish;
    };
    private _move =
        (inputAction "MoveForward" > 0.05) || (inputAction "MoveBack" > 0.05) ||
        (inputAction "TurnLeft" > 0.05) || (inputAction "TurnRight" > 0.05) ||
        (inputAction "MoveLeft" > 0.05) || (inputAction "MoveRight" > 0.05);
    if (_move) exitWith {
        [_unit, _tok, _epoch, true] call _fnFinish;
        [_id] call CBA_fnc_removePerFrameHandler;
    };
}, 0, [_medic, _token, _poseEpoch, _finish]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_rollProviderPFH", _pfh];
true
