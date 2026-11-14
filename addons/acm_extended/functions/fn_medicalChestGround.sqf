/* Both editor and mission visuals stand on the same surface. */
params ["_origin", "_ignore", "_above", "_below", ["_editor", false], ["_includeNormal", false]];
private _hits = lineIntersectsSurfaces [
    _origin vectorAdd [0, 0, _above],
    _origin vectorAdd [0, 0, -_below],
    _ignore param [0, objNull], _ignore param [1, objNull], true, [1, -1] select _editor, "ROADWAY", "GEOM"
];
private _index = _hits findIf {
    !(_editor && {
        (_x select 2) getVariable ["ACME_medicalChestEdenVisual", false]
        || {(_x select 3) getVariable ["ACME_medicalChestEdenVisual", false]}
    })
};
private _surface = if (_index < 0) then {
    [ATLToASL [_origin select 0, _origin select 1, 0], surfaceNormal [_origin select 0, _origin select 1]]
} else {
    private _hit = _hits select _index;
    [_hit select 0, _hit select 1]
};
if (_includeNormal) exitWith {_surface};
_surface select 0
