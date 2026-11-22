/*
 * Where the rescuer is local, a few times a second while he drags a casualty: has he dragged him onto a laid
 * out, empty litter? Then the drag ends and the casualty is put into the litter (as "Load casualty" does at the
 * end of its timer). "Onto": the middle of his chest is over the litter's bed, within a third of a metre of where
 * it belongs across and half a metre along, for two checks running.
 * Setting: acme_drag_onto.
 * Arguments: 0: rescuer, 1: casualty, 2: let go with ACE's drag <BOOL> (default: false, ACME's drag).
 * Returns: he was put into a litter <BOOL>.
 */
params ["_unit", "_patient", ["_ace", false]];
if !(missionNamespace getVariable ["acme_drag_onto", true]) exitWith {false};
if (isNull _patient || {!(_patient isKindOf "CAManBase")} || {!alive _patient}
    || {lifeState _patient in ["HEALTHY", "INJURED"] && {!(missionNamespace getVariable ["acme_sked_allowConscious", false])}}
    || {!isNull (_patient getVariable ["acme_sked_litter", objNull])} || {_patient getVariable ["acme_sked_stowed", false]}) exitWith {false};
private _chest = ASLToAGL (_patient modelToWorldVisualWorld (_patient selectionPosition "spine3"));
private _found = objNull;
{
    if (isNull _found && {isNull attachedTo _x} && {isNull (_x getVariable ["acme_sked_patient", objNull])}
        && {!(_x getVariable ["acme_talon_busy", false])} && {!isObjectHidden _x}
        && {isNull (_x getVariable ["ace_common_owner", objNull])}
        && {(((_x getVariable ["acme_sked_placer", []]) param [1, -100]) < serverTime - 30)}) then {
        private _want = getArray (configOf _x >> "acmeLitterChest");
        if (count _want < 2) then {_want = [0, 0.45];};
        private _at = _x worldToModelVisual _chest;
        if (abs ((_at select 0) - (_want select 0)) < 0.34 && {abs ((_at select 1) - (_want select 1)) < 0.5} && {abs (_at select 2) < 0.7}) then {_found = _x;};
    };
} forEach (nearestObjects [_chest, ["ACME_SKED_Open"], 2.2]);
if (isNull _found) exitWith {
    _unit setVariable ["acme_drag_ontoSeen", nil];
    false
};
// (two checks running: a casualty who is only pulled across a litter's corner stays on the ground)
if ((_unit getVariable ["acme_drag_ontoSeen", objNull]) isNotEqualTo _found) exitWith {
    _unit setVariable ["acme_drag_ontoSeen", _found];
    false
};
_unit setVariable ["acme_drag_ontoSeen", nil];
if (_ace) then {
    [_unit, _patient] call ace_dragging_fnc_dropObject;
} else {
    [_unit, true] call acme_sked_fnc_dragStop;
};
// (a moment for the casualty to be let go everywhere, then the same request the strap timer ends with)
[{
    params ["_unit", "_patient", "_litter"];
    if (isNull _litter || {isNull _patient} || {!isNull (_patient getVariable ["acme_sked_litter", objNull])}) exitWith {};
    [_unit, "strap", _patient, _litter] call acme_sked_fnc_request;
}, [_unit, _patient, _found], 0.5] call CBA_fnc_waitAndExecute;
true
