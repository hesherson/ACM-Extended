/*
 * Where and how a chest part stands on what is under it: on its four feet, leaning with the ground.
 * The ground (fn_medicalChestGround.sqf) is found under the four corners of its footprint and under its middle;
 * the part lies in the plane through the corners, lifted so far that none of the five places stands through it.
 * It leans no more than 30 degrees: on steeper ground it stands less steeply than the ground, as a box does that
 * is wedged.
 * Arguments: 0: its middle (ASL, on or near the ground), 1: things to look through, 2: heading (the mod's own, see
 * fn_medicalChestPlace.sqf), 3: half its width and half its depth [m, m], 4: in the editor <BOOL>.
 * Returns: [place of its middle on the ground (ASL), the ground's normal there].
 */
params ["_origin", "_ignore", "_heading", ["_half", [0.26, 0.2]], ["_editor", false]];
private _front = [-(cos _heading), sin _heading, 0];
private _right = [sin _heading, cos _heading, 0];
_half params ["_w", "_d"];
private _corners = [[_w, _d], [_w, -_d], [-_w, -_d], [-_w, _d]];
private _heights = _corners apply {
    private _at = _origin vectorAdd (_right vectorMultiply (_x select 0)) vectorAdd (_front vectorMultiply (_x select 1));
    ([_at, _ignore, 0.45, 2, _editor] call ACME_fnc_medicalChestGround) select 2
};
private _middle = ([_origin, _ignore, 0.45, 2, _editor] call ACME_fnc_medicalChestGround) select 2;
_heights params ["_a", "_b", "_c", "_e"];
// how the ground rises to the right and to the front (m for a metre)
private _toRight = ((_a + _b) - (_c + _e)) / (4 * _w);
private _toFront = ((_a + _e) - (_b + _c)) / (4 * _d);
private _steep = sqrt (_toRight ^ 2 + _toFront ^ 2);
if (_steep > 0.577) then {
    _toRight = _toRight * 0.577 / _steep;
    _toFront = _toFront * 0.577 / _steep;
};
private _mean = (_a + _b + _c + _e) / 4;
// lifted so that none of the five places stands through the plane
private _lift = 0 max (_middle - _mean);
{
    private _plane = _mean + _toRight * ((_corners select _forEachIndex) select 0) + _toFront * ((_corners select _forEachIndex) select 1);
    _lift = _lift max (_x - _plane);
} forEach _heights;
private _normal = vectorNormalized (([0, 0, 1] vectorDiff (_right vectorMultiply _toRight)) vectorDiff (_front vectorMultiply _toFront));
[[_origin select 0, _origin select 1, _mean + _lift], _normal]
