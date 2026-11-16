/*
 * Server: a rescuer lets go of their handle. If the SKED is lifted and they lead, or too few are left,
 * it is set down first. ACE drag comes back when nobody holds a handle.
 * Arguments: 0: rescuer.
 */
params ["_unit"];
if (!isServer) exitWith {};
private _litter = _unit getVariable ["acme_sked_bearing", objNull];
_unit setVariable ["acme_sked_bearing", nil, true];
if (isNull _litter) exitWith {
    [_unit, "bearerRelease", [_unit, _litter]] call acme_sked_fnc_sendLocal;
};
private _bearers = +(_litter getVariable ["acme_sked_bearers", []]);
{
    if (_x isEqualTo _unit) then {_bearers set [_forEachIndex, objNull]};
} forEach _bearers;
_litter setVariable ["acme_sked_bearers", _bearers, true];
if (_litter getVariable ["acme_sked_lifted", false]) then {
    private _left = {!isNull _x && {alive _x}} count _bearers;
    if (_left < (([_litter] call acme_sked_fnc_bearerLimits) select 0) || {(_litter getVariable ["acme_sked_lead", objNull]) isEqualTo _unit}) then {
        [_litter] call acme_sked_fnc_srvSetDown;
    };
};
if ((_bearers findIf {!isNull _x}) < 0) then {
    private _cfg = configOf _litter;
    [_litter, getNumber (_cfg >> "ace_dragging_canDrag") > 0,
        getArray (_cfg >> "ace_dragging_dragPosition"), getNumber (_cfg >> "ace_dragging_dragDirection"),
        false, true] call ace_dragging_fnc_setDraggable;
};
["handle released", _litter, _unit, _bearers] call acme_sked_fnc_traceTransport;
[_unit, "bearerRelease", [_unit, _litter]] call acme_sked_fnc_sendLocal;
