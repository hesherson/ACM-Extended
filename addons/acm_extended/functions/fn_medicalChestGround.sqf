/* Both editor and mission visuals stand on the same surface. */
params ["_origin", "_ignore", "_above", "_below", ["_editor", false]];
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
if (_index < 0) exitWith {ATLToASL [_origin select 0, _origin select 1, 0]};
_hits select _index select 0
