/*
 * A free place for a litter on the floor of a vehicle's cabin, with room for it.
 *
 * The room is the cargo bay the vehicle's makers define: VehicleTransport >> Carrier >> cargoBayDimensions, two
 * memory points that are opposite corners of the free space. Litters lie in it side by side, head toward the
 * nose, as many as its width takes; if the bay is too short for that and wide enough, across it one behind the
 * other. The floor under a place is found with a ray down. A place counts only when nothing is in the way
 * there (fn_vehicleLitterClear.sqf) and no other litter has it.
 * Only kinds of vehicle in acme_sked_vehicleLitterKinds are looked at, and only litters that are carried by
 * their handles go in (the Talon II; its size when stowed is acmeLitterStow[] in its class).
 * Arguments: 0: vehicle, 1: litter.
 * Returns: [index of the place, [across, along, up] of the litter's middle on the floor, heading against the
 * vehicle's nose (degrees)] or [].
 */
params ["_vehicle", "_litter"];
if (isNull _vehicle || {!alive _vehicle} || {isNull _litter}) exitWith {[]};
if (getNumber (configOf _litter >> "acmeLitterExtraCrew") <= 0) exitWith {[]};
if (((missionNamespace getVariable ["acme_sked_vehicleLitterKinds", ["vtx_H60_base"]]) findIf {_vehicle isKindOf _x}) < 0) exitWith {[]};
private _bay = getArray (configOf _vehicle >> "VehicleTransport" >> "Carrier" >> "cargoBayDimensions");
if (count _bay < 2) exitWith {[]};
private _p1 = _vehicle selectionPosition [_bay select 0, "Memory"];
private _p2 = _vehicle selectionPosition [_bay select 1, "Memory"];
if (_p1 distance _p2 < 0.5) exitWith {[]};
private _min = [(_p1 select 0) min (_p2 select 0), (_p1 select 1) min (_p2 select 1), (_p1 select 2) min (_p2 select 2)];
private _max = [(_p1 select 0) max (_p2 select 0), (_p1 select 1) max (_p2 select 1), (_p1 select 2) max (_p2 select 2)];
(getArray (configOf _litter >> "acmeLitterStow")) params [["_width", 0.58], ["_length", 1.99], ["_height", 0.46]];
if ((_max select 2) - (_min select 2) < _height) exitWith {[]};
private _gap = 0.05;
private _wide = (_max select 0) - (_min select 0);
private _long = (_max select 1) - (_min select 1);
// the places: [across, along, heading]
private _places = [];
if (_long >= _length) then {
    private _n = floor ((_wide + _gap) / (_width + _gap));
    private _first = (_min select 0) + (_wide - _n * _width - (_n - 1) * _gap) / 2 + _width / 2;
    for "_i" from 0 to (_n - 1) do {_places pushBack [_first + _i * (_width + _gap), ((_min select 1) + (_max select 1)) / 2, 0];};
} else {
    if (_wide >= _length) then {
        private _n = floor ((_long + _gap) / (_width + _gap));
        private _first = (_min select 1) + (_long - _n * _width - (_n - 1) * _gap) / 2 + _width / 2;
        for "_i" from 0 to (_n - 1) do {_places pushBack [((_min select 0) + (_max select 0)) / 2, _first + _i * (_width + _gap), 90];};
    };
};
private _held = _vehicle getVariable ["acme_sked_litters", []];
private _found = [];
{
    if (_found isEqualTo [] && {isNull (_held param [_forEachIndex, objNull])}) then {
        _x params ["_across", "_along", "_heading"];
        // the floor: the highest surface of the vehicle under the place, in any of its collision geometries
        private _from = _vehicle modelToWorldWorld [_across, _along, (_min select 2) + 0.5];
        private _to = _vehicle modelToWorldWorld [_across, _along, (_min select 2) - 0.6];
        private _floor = (_min select 2);
        {
            private _hits = (lineIntersectsSurfaces [_from, _to, _litter, objNull, true, 2, _x select 0, _x select 1]) select {(_x select 2) isEqualTo _vehicle};
            if (_hits isNotEqualTo []) then {_floor = _floor max ((_vehicle worldToModel (ASLToAGL ((_hits select 0) select 0))) select 2);};
        } forEach [["GEOM", "NONE"], ["FIRE", "NONE"], ["VIEW", "NONE"]];
        private _offset = [_across, _along, _floor + (missionNamespace getVariable ["acme_sked_vehicleLitterLift", 0.015])];
        if ([_vehicle, _litter, _offset, _heading, [_width, _length, _height]] call acme_sked_fnc_vehicleLitterClear) then {
            _found = [_forEachIndex, _offset, _heading];
        };
    };
} forEach _places;
_found
