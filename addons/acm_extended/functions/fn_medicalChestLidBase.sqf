params ["_base", "_heading", "_chest", "_lid", ["_editor", false]];
private _right = [sin _heading, cos _heading, 0];
private _side = _base vectorAdd (_right vectorMultiply 0.82);
[_side, [_chest, _lid], 0.65, 0.7, _editor, true] call ACME_fnc_medicalChestGround
