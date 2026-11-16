/*
 * Where a rescuer is local: hold a handle. The attach and the heading are set here together, so the
 * heading is relative to what they are attached to.
 * "hold": standing at the handle, attached to the SKED, facing the head end.
 * "lead": free to walk (forced walk), the SKED attached to them.
 * "follow": attached to the lead at their handle; they walk in step while the lead moves, stand while the
 * lead stands. Weapons go on the back for all three.
 * Arguments: 0: rescuer, 1: SKED, 2: mode, 3: parent (objNull for lead), 4: offset on the parent.
 */
params ["_unit", "_litter", "_mode", ["_parent", objNull], ["_off", []]];
if (!local _unit) exitWith {};
if !((_unit getVariable ["acme_sked_bearing", objNull]) isEqualTo _litter) exitWith {};
if (currentWeapon _unit != "") then {_unit action ["SwitchWeapon", _unit, _unit, 299]};
[_unit, "forceWalk", "acme_sked", _mode == "lead"] call ace_common_fnc_statusEffect_set;
if (_mode == "lead") exitWith {_unit setVariable ["acme_sked_bearerParent", nil];};
if (isNull _parent || {_off isEqualTo []}) exitWith {};
_unit attachTo [_parent, _off];
_unit setVariable ["acme_sked_bearerParent", _parent];
_unit setDir 0;
[_unit, "AmovPercMstpSnonWnonDnon", 2] call ace_common_fnc_doAnimation;
if (_mode != "follow") exitWith {};
_unit setVariable ["acme_sked_walk", false];
[{
    params ["_args", "_id"];
    _args params ["_unit", "_litter"];
    private _lead = _litter getVariable ["acme_sked_lead", objNull];
    if (!local _unit || {!alive _unit} || {isNull _lead} || {!(_litter getVariable ["acme_sked_lifted", false])} || {!((_unit getVariable ["acme_sked_bearing", objNull]) isEqualTo _litter)}) exitWith {
        [_id] call CBA_fnc_removePerFrameHandler;
        _unit setVariable ["acme_sked_walk", nil];
    };
    private _walk = speed _lead > 1.5;
    if (_walk isEqualTo (_unit getVariable ["acme_sked_walk", false])) exitWith {};
    _unit setVariable ["acme_sked_walk", _walk];
    [_unit, ["AmovPercMstpSnonWnonDnon", "AmovPercMwlkSnonWnonDf"] select _walk, 2] call ace_common_fnc_doAnimation;
}, 0.2, [_unit, _litter]] call CBA_fnc_addPerFrameHandler;
