/*
 * Height (ASL) of what a dragged thing lies on at a place: the terrain, or a walk surface over it (ROADWAY LOD:
 * a floor, stairs, a pier, a ramp). Solid geometry does not count: a car, a wheel or a low wall beside the way
 * is not ground. The place is looked for from a height that is known already, the rescuer's feet or the place
 * before this one along the thing, and only as far up and down from it as ground can go over the distance
 * between the two: up by a high step and a slope of 45 degrees, down by a step and somewhat more. So stairs are
 * followed up and down, and the floor above, a roof, or a platform beside the way are never taken for ground.
 * Where nothing is within that reach (off the edge of a pier or a roof) it stays level. In water too deep to
 * wade it floats.
 * Arguments: 0: x, 1: y, 2: the known height (ASL), 3 and 4: objects to look through, 5: distance from the place
 * of the known height <NUMBER> (default: 0.8). Returns: number.
 */
params ["_x", "_y", "_from", "_ignore1", "_ignore2", ["_reach", 0.8]];
private _up = 0.5 + _reach;
private _down = 0.5 + 1.5 * _reach;
private _terrain = (getTerrainHeightASL [_x, _y]) max -0.6;
private _height = if (_terrain < _from - _down) then {_from} else {_terrain};
private _hits = lineIntersectsSurfaces [[_x, _y, _from + _up], [_x, _y, _from - _down], _ignore1, _ignore2, true, 1, "ROADWAY", "NONE"];
if (_hits isNotEqualTo []) then {
    private _z = ((_hits select 0) select 0) select 2;
    if (_z > _terrain) then {_height = _z;};
};
_height
