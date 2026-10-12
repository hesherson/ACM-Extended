/* Shared flight exposure lookup. Confirmed seating or actual close floor
 * support identifies an airframe; proximity and enclosure alone do not. */
params [["_patient",objNull,[objNull]]];
if (isNull _patient || {!alive _patient}) exitWith {objNull};
private _parent = objectParent _patient;
if (!isNull _parent && {_parent isKindOf "Air"}) exitWith {_parent};
if (!isNull _parent) exitWith {objNull};
private _support = [_patient] call ACME_fnc_flightSupport;
if (_support isEqualTo []) then {objNull} else {_support select 0}
