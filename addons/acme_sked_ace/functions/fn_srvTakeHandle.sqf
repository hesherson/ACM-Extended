/*
 * Server: give a rescuer the free handle nearest them. They stand at it, facing the head end, attached to
 * the SKED (done where they are local) until they lift, set down or let go. ACE drag of the SKED is off
 * while anyone holds a handle.
 * Arguments: 0: rescuer, 1: SKED.
 */
params ["_unit", "_litter"];
if (!isServer || {isNull _litter} || {_litter getVariable ["acme_sked_lifted", false]}) exitWith {};
if (!isNull (_unit getVariable ["acme_sked_bearing", objNull]) || {!isNull attachedTo _litter}
    || {!isNull (_litter getVariable ["ace_common_owner", objNull])} || {!isNull objectParent _unit}) exitWith {};
private _slots = ["handle_lh", "handle_rh", "handle_lf", "handle_rf"];
private _bearers = +(_litter getVariable ["acme_sked_bearers", [objNull, objNull, objNull, objNull]]);
private _best = -1;
private _bestD = 1e9;
{
    if (isNull (_bearers select _forEachIndex)) then {
        private _d = _unit distance (_litter modelToWorld (_litter selectionPosition _x));
        if (_d < _bestD) then {_bestD = _d; _best = _forEachIndex};
    };
} forEach _slots;
if (_best < 0) exitWith {};
_bearers set [_best, _unit];
_litter setVariable ["acme_sked_bearers", _bearers, true];
_unit setVariable ["acme_sked_bearing", _litter, true];
[_litter, false, nil, nil, nil, true] call ace_dragging_fnc_setDraggable;
private _h = _litter selectionPosition (_slots select _best);
[_unit, "bearerLocal", [_unit, _litter, "hold", _litter, [_h select 0, _h select 1, 0]]] call acme_sked_fnc_sendLocal;
