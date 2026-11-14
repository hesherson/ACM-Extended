params ["_base", "_heading", "_chest", "_lid", ["_editor", false]];
private _right = [cos _heading, -(sin _heading), 0];
private _side = _base vectorAdd (_right vectorMultiply 0.95);
[_side, [_chest, _lid], 0.65, 0.7, _editor] call ACME_fnc_medicalChestGround
