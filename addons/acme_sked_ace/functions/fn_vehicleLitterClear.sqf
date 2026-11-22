/*
 * Is there room for a litter with its casualty at a place in a vehicle?
 * First, the box they take up there must lie inside the vehicle's cargo bay (VehicleTransport >> Carrier >>
 * cargoBayDimensions), if it defines one. Seats often have no collision geometry: on the Hatchet H-60 neither
 * the rear bench nor the crew seats do, so no ray sees them, and the bay is what keeps a litter out of them.
 * Second, nothing of the vehicle, and no other thing, may be inside that box. Rays run through that box at three heights (just over the
 * floor, half way, at the casualty's top): along both sides and the middle, across both ends and the middle,
 * and both diagonals; each in the vehicle's collision geometry, fire geometry and view geometry. A hit on the
 * vehicle or on anything but people and the litters that lie in it already means: no room.
 * Arguments: 0: vehicle, 1: litter, 2: [across, along, up] of the litter's middle on the floor in the vehicle's
 * axes, 3: heading against the vehicle's nose (degrees), 4: [width, length, height] of the box.
 * Returns: there is room <BOOL>. (acme_sked_vehicleLitterBlock: what was in the way last time, for the tests.)
 */
params ["_vehicle", "_litter", "_offset", "_heading", "_size"];
_size params ["_width", "_length", "_height"];
private _patient = _litter getVariable ["acme_sked_patient", objNull];
private _own = (_vehicle getVariable ["acme_sked_litters", []]) + [_litter];
private _fwd = [sin _heading, cos _heading, 0];
private _side = [cos _heading, -(sin _heading), 0];
private _hw = _width / 2;
private _hl = _length / 2;
private _point = {
    params ["_a", "_b", "_z"];
    _vehicle modelToWorldWorld (((_offset vectorAdd (_side vectorMultiply _a)) vectorAdd (_fwd vectorMultiply _b)) vectorAdd [0, 0, _z])
};
acme_sked_vehicleLitterBlock = [];
private _bay = getArray (configOf _vehicle >> "VehicleTransport" >> "Carrier" >> "cargoBayDimensions");
private _outside = false;
if (count _bay >= 2) then {
    private _p1 = _vehicle selectionPosition [_bay select 0, "Memory"];
    private _p2 = _vehicle selectionPosition [_bay select 1, "Memory"];
    if (_p1 distance _p2 >= 0.5) then {
        // how far the box reaches from its middle across and along the vehicle
        private _reachX = abs (_hw * cos _heading) + abs (_hl * sin _heading);
        private _reachY = abs (_hw * sin _heading) + abs (_hl * cos _heading);
        private _slack = 0.02;
        _outside = (_offset select 0) - _reachX < ((_p1 select 0) min (_p2 select 0)) - _slack
            || {(_offset select 0) + _reachX > ((_p1 select 0) max (_p2 select 0)) + _slack}
            || {(_offset select 1) - _reachY < ((_p1 select 1) min (_p2 select 1)) - _slack}
            || {(_offset select 1) + _reachY > ((_p1 select 1) max (_p2 select 1)) + _slack}
            || {(_offset select 2) < ((_p1 select 2) min (_p2 select 2)) - _slack}
            || {(_offset select 2) + _height > ((_p1 select 2) max (_p2 select 2)) + _slack};
    };
};
if (_outside) exitWith {
    acme_sked_vehicleLitterBlock = ["outside the cargo bay", _offset apply {round (_x * 100) / 100}];
    false
};
private _blocked = false;
{
    private _z = _x;
    {
        if (!_blocked) then {
            _x params ["_a", "_b"];
            private _from = (_a + [_z]) call _point;
            private _to = (_b + [_z]) call _point;
            {
                private _hits = lineIntersectsSurfaces [_from, _to, _litter, _patient, true, 4, _x select 0, _x select 1];
                private _bad = _hits findIf {
                    private _object = _x select 2;
                    !isNull _object && {_object isEqualTo _vehicle || {!(_object isKindOf "CAManBase") && {!(_object in _own)}}}
                };
                if (_bad >= 0) exitWith {
                    _blocked = true;
                    acme_sked_vehicleLitterBlock = [typeOf ((_hits select _bad) select 2), _x select 0, _z, _a, _b,
                        (_vehicle worldToModel (ASLToAGL ((_hits select _bad) select 0))) apply {round (_x * 100) / 100}];
                };
            } forEach [["GEOM", "FIRE"], ["VIEW", "NONE"]];
        };
    } forEach [
        [[-_hw, -_hl], [-_hw, _hl]], [[_hw, -_hl], [_hw, _hl]], [[0, -_hl], [0, _hl]],
        [[-_hw, -_hl], [_hw, -_hl]], [[-_hw, 0], [_hw, 0]], [[-_hw, _hl], [_hw, _hl]],
        [[-_hw, -_hl], [_hw, _hl]], [[_hw, -_hl], [-_hw, _hl]]
    ];
} forEach [0.07, _height / 2, _height];
!_blocked
