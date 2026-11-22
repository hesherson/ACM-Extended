/*
 * Server: reserve the free handle nearest the rescuer. ACE drag of the SKED is off
 * while anyone holds a handle.
 * Arguments: 0: rescuer, 1: SKED, 2: which end (-1 either, 0 the head end: the first two handles, 1 the foot end;
 * default -1).
 */
params ["_unit", "_litter", ["_end", -1]];
if (!isServer || {isNull _litter} || {_litter getVariable ["acme_sked_lifted", false]}) exitWith {};
if (!isNull (_unit getVariable ["acme_sked_bearing", objNull]) || {!isNull attachedTo _litter}
    || {!isNull (_litter getVariable ["ace_common_owner", objNull])} || {!isNull objectParent _unit} || {!isNull attachedTo _unit}) exitWith {};
private _slots = getArray (configOf _litter >> "acmeLitterHandles");
private _bearers = +(_litter getVariable ["acme_sked_bearers", [objNull, objNull, objNull, objNull]]);
if (({!isNull _x} count _bearers) >= (([_litter] call acme_sked_fnc_bearerLimits) select 1)) exitWith {};
private _best = -1;
private _bestD = 1e9;
{
    if (isNull (_bearers select _forEachIndex) && {_end < 0 || {floor (_forEachIndex / 2) == _end}}) then {
        private _d = _unit distance (_litter modelToWorld (_litter selectionPosition [_x, "Memory"]));
        if (_d < _bestD) then {_bestD = _d; _best = _forEachIndex};
    };
} forEach _slots;
if (_best < 0) exitWith {};
_bearers set [_best, _unit];
_litter setVariable ["acme_sked_bearers", _bearers, true];
_unit setVariable ["acme_sked_bearing", _litter, true];
["handle claimed", _litter, _unit, [_slots select _best]] call acme_sked_fnc_traceTransport;
// ACE needs a real position and direction here: with nil and a global call it throws before it sets anything.
[_litter, false, _litter getVariable ["ace_dragging_dragPosition", [0, 1.5, 0]],
    _litter getVariable ["ace_dragging_dragDirection", 0], false, true] call ace_dragging_fnc_setDraggable;
[_unit, "bearerLocal", [_unit, _litter, "hold"]] call acme_sked_fnc_sendLocal;
