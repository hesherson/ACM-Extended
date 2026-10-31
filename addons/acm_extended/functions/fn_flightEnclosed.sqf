/* Cabin metadata may be used only by seated occupants or by someone with a
 * confirmed ceiling AND opposing same-airframe lateral boundaries. A roof,
 * rotor/tail overhang or wing floor alone is not a
 * protected cabin, and enclosure never invents cabin pressure or oxygen. */
params [["_patient",objNull,[objNull]], ["_air",objNull,[objNull]]];
if (isNull _patient || {isNull _air} || {!(_air isKindOf "Air")}) exitWith {false};
private _parent = objectParent _patient;
if (_parent isEqualTo _air) exitWith {true};
// A helper seat establishes aircraft ancestry, not cabin enclosure. Confirm
// actual same-airframe boundaries for seats on an external rack or FFV mount.
if (!isNull _parent && {!(([_patient] call ACME_fnc_flightAirframe) isEqualTo _air)}) exitWith {false};
private _head = eyePos _patient;
private _up = vectorUp _air;
private _enclosed = false;
{
    private _hits = lineIntersectsSurfaces [_head vectorAdd (_up vectorMultiply 0.05),
        _head vectorAdd (_up vectorMultiply 50),_patient,objNull,true,1,_x,"NONE"];
    if !(_hits isEqualTo []) then {
        private _hit = _hits select 0;
        private _surface = _hit param [2,objNull];
        if (isNull _surface || {!(_surface isKindOf "Air")}) then {_surface = _hit param [3,objNull];};
        if (_surface isEqualTo _air) then {_enclosed = true;};
    };
} forEach ["GEOM","PHYSX"];
if (!_enclosed) exitWith {false};
// Overhead geometry alone also occurs outside under a wing/rotor. A bounded
// cross section must contain the head on both sides of the aircraft's X axis.
private _right = _air vectorModelToWorld [1,0,0];
private _sides = 0;
{
    private _end = _head vectorAdd (_right vectorMultiply (_x * 50));
    private _sameAir = false;
    {
        private _hits = lineIntersectsSurfaces [_head,_end,_patient,objNull,true,1,_x,"NONE"];
        if !(_hits isEqualTo []) then {
            private _hit = _hits select 0;
            private _surface = _hit param [2,objNull];
            if (isNull _surface || {!(_surface isKindOf "Air")}) then {_surface = _hit param [3,objNull];};
            if (_surface isEqualTo _air) then {_sameAir = true;};
        };
    } forEach ["GEOM","PHYSX"];
    if (_sameAir) then {_sides = _sides + 1;};
} forEach [-1,1];
_sides == 2
