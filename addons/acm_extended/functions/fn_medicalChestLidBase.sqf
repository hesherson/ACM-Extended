params ["_base", "_seatPose", "_ignore", ["_editor", false]];
_seatPose params ["_seated", "_forward", "_up"];
// Keep the landing point at the depth of the released lid.
private _side = _seated vectorAdd (_forward vectorMultiply 0.11) vectorAdd (_up vectorMultiply -0.82);
_side set [2, _base select 2];
[_side, _ignore, 0.65, 0.7, _editor, true] call ACME_fnc_medicalChestGround
