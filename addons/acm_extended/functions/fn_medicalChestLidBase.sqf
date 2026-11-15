params ["_base", "_heading", "_chest", "_lid", ["_editor", false]];
private _right = [cos _heading, -(sin _heading), 0];
(0 boundingBoxReal _chest) params ["_min", "_max"];
private _extent = _max vectorDiff _min;
// Choose the original side from the chest footprint, independently of the release.
private _sideDirection = [[sin _heading, cos _heading, 0], _right] select ((_extent select 1) < (_extent select 2));
private _side = _base vectorAdd (_sideDirection vectorMultiply 0.82);
[_side, [_chest, _lid], 0.65, 0.7, _editor, true] call ACME_fnc_medicalChestGround
