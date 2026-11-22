params ["_base", "_heading", "_chest", "_lid", ["_editor", false]];
private _right = [sin _heading, cos _heading, 0];
private _side = _base vectorAdd (_right vectorMultiply 0.82);
// (on its whole footprint, not on the one point under its middle: fn_medicalChestRest.sqf)
[_side, [_chest, _lid], _heading, [0.2, 0.3], _editor] call ACME_fnc_medicalChestRest
