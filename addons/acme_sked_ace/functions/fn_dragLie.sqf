/*
 * How a dragged thing lies on what is under it: as a board does. The height of the ground (fn_dragGround.sqf) is
 * taken at nine places along it, each looked for from the one before (the pulled end from the rescuer's feet),
 * and it rests on the two of them that carry its middle with none of the others sticking through (the edge of
 * their upper hull over its middle): on even ground and on a slope those are its ends; over a kerb, a step or a
 * sill they are the edge and one end, the other end in the air; on stairs the noses of two steps. Where two such
 * lines meet under its middle it takes the flatter.
 * (Measured 2026-11-18: with the ground under the two ends only, a casualty pulled up a doorstep had its middle
 * 12 cm inside the step; with five places the nose of a 0.4 m stair step still stood up to 0.5 m through it.)
 * Arguments: 0: x, y of its pulled end, 1: x, y of its trailing end, 2: where the rescuer stands (ASL),
 * 3 and 4: objects to look through, 5: how far it reaches beyond its pulled end <NUMBER> (default: 0; a casualty
 * is pulled by the neck and the head lies beyond it). Returns: [height of its pulled end, height of its trailing
 * end] (ASL), and how it leans to its right (rise per metre).
 */
params ["_front", "_rear", "_hand", "_ignore1", "_ignore2", ["_beyond", 0]];
private _length = (_front distance2D _rear) max 0.1;
// the far end of what is laid out: the pulled end, or what reaches beyond it
private _tip = [(_front select 0) + ((_front select 0) - (_rear select 0)) * _beyond / _length, (_front select 1) + ((_front select 1) - (_rear select 1)) * _beyond / _length];
private _z = [0, 0, 0, 0, 0, 0, 0, 0, 0];
private _known = _hand select 2;
private _reach = ((_tip distance2D _hand) max 0.3) min 0.8;
private _part = (_length + _beyond) / 8;
for "_i" from 8 to 0 step -1 do {
    private _s = _i / 8;
    _known = [(_rear select 0) + ((_tip select 0) - (_rear select 0)) * _s, (_rear select 1) + ((_tip select 1) - (_rear select 1)) * _s,
        _known, _ignore1, _ignore2, _reach] call acme_sked_fnc_dragGround;
    _z set [_i, _known];
    _reach = _part;
};
// the upper hull of the nine, from the trailing end (0) to the far end (8)
private _hull = [];
for "_i" from 0 to 8 do {
    while {
        private _n = count _hull;
        _n >= 2 && {
            private _a = _hull select (_n - 2);
            private _b = _hull select (_n - 1);
            ((_z select _b) - (_z select _a)) * (_i - _a) <= ((_z select _i) - (_z select _a)) * (_b - _a) + 1e-6
        }
    } do {
        _hull deleteAt ((count _hull) - 1);
    };
    _hull pushBack _i;
};
// the edge of it that carries the middle (4); where the middle is a corner of it, the flatter of the two
private _best = [_z select 8, _z select 0];
private _least = 1e9;
for "_k" from 0 to ((count _hull) - 2) do {
    private _a = _hull select _k;
    private _b = _hull select (_k + 1);
    if (_a <= 4 && {_b >= 4}) then {
        private _slope = ((_z select _b) - (_z select _a)) / (_b - _a);       // per eighth of its length
        if (abs _slope < _least) then {
            _least = abs _slope;
            private _base = (_z select _a) - _slope * _a;
            _best = [_base + _slope * 8 * _length / (_length + _beyond), _base];
        };
    };
};
// How it leans to the side: with the terrain, where it lies on the terrain. (Not with kerbs and steps beside it:
// that would throw it over from one frame to the next. Measured on a 23 degree slope: without this a SKED lying
// across the slope had one edge 12 cm in the ground and the other as far over it.)
private _midAt = [((_rear select 0) + (_tip select 0)) / 2, ((_rear select 1) + (_tip select 1)) / 2];
private _side = 0;
if (abs ((_z select 4) - getTerrainHeightASL _midAt) < 0.05) then {
    private _normal = surfaceNormal _midAt;
    // to its right: the rise per metre
    _side = (-(((_normal select 0) * ((_front select 1) - (_rear select 1)) - (_normal select 1) * ((_front select 0) - (_rear select 0))) / _length)
        / ((_normal select 2) max 0.5)) max -0.6 min 0.6;
};
_best + [_side]
