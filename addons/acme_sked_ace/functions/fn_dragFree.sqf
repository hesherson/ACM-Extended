/*
 * Server: take a dragged thing off what it still hangs on (the drag's carrier, or the rescuer himself) and set
 * it down where it is. The carrier is removed. Does nothing to a thing that hangs on anything else.
 * Arguments: 0: the thing, 1: the rescuer <OBJECT> (default: objNull).
 */
params ["_thing", ["_unit", objNull]];
if (isNull _thing) exitWith {};
private _holder = attachedTo _thing;
if (isNull _holder) exitWith {};
private _carried = _holder getVariable ["acme_drag_carrier", false];
if (_carried || {!isNull _unit && {_holder isEqualTo _unit}}) then {
    private _at = getPosWorld _thing;
    private _dir = vectorDir _thing;
    private _up = vectorUp _thing;
    detach _thing;
    if (isNull objectParent _thing) then {
        _thing setPosWorld _at;
        if !(_thing isKindOf "CAManBase") then {_thing setVectorDirAndUp [_dir, _up];};
    };
    if (_carried) then {deleteVehicle _holder;};
    // a casualty who still lies in the drag's own pose goes back to an ordinary one
    if (_thing isKindOf "CAManBase" && {alive _thing} && {(toLowerANSI animationState _thing) in ["acme_drag_rest", "acme_drag_limp"]}) then {
        [_thing, ["AmovPpneMstpSnonWnonDnon", "unconscious"] select (_thing getVariable ["ACE_isUnconscious", false]), 2] call ace_common_fnc_doAnimation;
    };
};
