/*
 * Server: reserve the free handle nearest the rescuer. ACE drag of the SKED is off
 * while anyone holds a handle.
 * Arguments: 0: rescuer, 1: SKED.
 */
params ["_unit", "_litter"];
if (!isServer || {isNull _litter} || {_litter getVariable ["acme_sked_lifted", false]}) exitWith {};
if (!isNull (_unit getVariable ["acme_sked_bearing", objNull]) || {!isNull attachedTo _litter}
    || {!isNull (_litter getVariable ["ace_common_owner", objNull])} || {!isNull objectParent _unit} || {!isNull attachedTo _unit}) exitWith {};
private _slots = getArray (configOf _litter >> "acmeLitterHandles");
private _bearers = +(_litter getVariable ["acme_sked_bearers", [objNull, objNull, objNull, objNull]]);
if (({!isNull _x} count _bearers) >= (([_litter] call acme_sked_fnc_bearerLimits) select 1)) exitWith {};
private _best = -1;
private _bestD = 1e9;
{
    if (isNull (_bearers select _forEachIndex)) then {
        private _d = _unit distance (_litter modelToWorld (_litter selectionPosition [_x, "Memory"]));
        if (_d < _bestD) then {_bestD = _d; _best = _forEachIndex};
    };
} forEach _slots;
if (_best < 0) exitWith {};
_bearers set [_best, _unit];
_litter setVariable ["acme_sked_bearers", _bearers, true];
_unit setVariable ["acme_sked_bearing", _litter, true];
["handle claimed", _litter, _unit, [_slots select _best]] call acme_sked_fnc_traceTransport;
[_litter, false, nil, nil, nil, true] call ace_dragging_fnc_setDraggable;
[_unit, "bearerLocal", [_unit, _litter, "hold"]] call acme_sked_fnc_sendLocal;
