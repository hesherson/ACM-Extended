/* B395: play a Hang Bag arm gesture on the provider and show it on every other machine.
 * _action: a CfgMovesBasic ManActions alias (ACME_HangBagArmUp / Hold / Down / None). The provider's own machine
 * plays it with playActionNow; the others are told to switch their copy of the unit to the same gesture state
 * (as the seizure gestures do, fn_seizureGestureSync.sqf), and only when theirs differs, so a machine that already
 * shows it is not restarted. Also used to remind late joiners (fn_hangBagTick.sqf). Pass the standing name; a
 * crouching provider gets the crouch version (...K). Returns the gesture state played. */
params [["_unit", objNull, [objNull]], ["_action", "", [""]], ["_remoteOnly", false, [false]]];
if (isNull _unit || {_action == ""}) exitWith {""};
// the crouching provider gets the set made against the crouch's torso (tools/build_hangbag_arm_gesture.py)
if (_action in ["ACME_HangBagArmUp", "ACME_HangBagArmHold", "ACME_HangBagArmDown"] && {stance _unit == "CROUCH"}) then {
    _action = _action + "K";
};
private _state = (getArray (configFile >> "CfgMovesBasic" >> "ManActions" >> _action)) param [0, _action];
if (local _unit && {!_remoteOnly}) then {
    _unit playActionNow _action;
    // where the gesture graph does not lead from the current gesture to this one, set it directly
    [{
        params ["_unit", "_state"];
        if (isNull _unit) exitWith {};
        private _now = toLowerANSI gestureState _unit;
        if (_now != toLowerANSI _state && {!(_state == "GestureEmpty" && {(_now find "acme_hangbagarm") != 0})}) then {
            _unit switchGesture [_state, 0, 1, false];
        };
    }, [_unit, _state], 0.15] call CBA_fnc_waitAndExecute;
};
["ACME_hangBagGesture", [_unit, _state]] call CBA_fnc_remoteEvent;
_state
