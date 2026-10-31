/* Shared flight exposure lookup. Confirmed seating/attachment or close floor
 * support identifies an airframe; proximity and enclosure alone do not.
 * A real seat can belong to a helper attached to or carried by another vehicle.
 * Follow those native transport relationships without class-name exceptions.
 * Enclosure is still checked separately: an exterior FFV seat has no cabin.
 */
params [["_patient",objNull,[objNull]], ["_allowDeadContact",false,[false]]];
// Contact inspection may locate a corpse in a live carrier. Flight physiology
// and floor containment keep their default live-patient contract.
if (isNull _patient || {!_allowDeadContact && {!alive _patient}}) exitWith {objNull};
private _parent = objectParent _patient;
if (isNull _parent) then {_parent = attachedTo _patient;};
if (!isNull _parent) exitWith {
    private _pending = [_parent];
    private _seen = [];
    private _result = objNull;
    // Native links should be acyclic, but scripts can briefly expose stale or
    // overlapping transport state. Bound both visits and repeated objects.
    for "_visit" from 0 to 15 do {
        if (_pending isEqualTo []) exitWith {};
        private _ancestor = _pending deleteAt 0;
        if (!isNull _ancestor && {!(_ancestor in _seen)} && {alive _ancestor}) then {
            _seen pushBack _ancestor;
            if (_ancestor isKindOf "Air") exitWith {_result = _ancestor;};
            {
                if (!isNull _x && {!(_x in _seen)} && {!(_x in _pending)}) then {
                    _pending pushBack _x;
                };
            } forEach [objectParent _ancestor, attachedTo _ancestor, isVehicleCargo _ancestor];
        };
        if (!isNull _result) exitWith {};
    };
    _result
};
private _support = [_patient,[],objNull,true,_allowDeadContact] call ACME_fnc_flightSupport;
if (_support isEqualTo []) then {objNull} else {_support select 0}
