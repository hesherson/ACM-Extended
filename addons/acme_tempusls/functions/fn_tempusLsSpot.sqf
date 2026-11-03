private _eye = eyePos player;
private _hits = lineIntersectsSurfaces [_eye, _eye vectorAdd ((getCameraViewDirection player) vectorMultiply 2.4), player, objNull, true, 1, "GEOM", "VIEW"];
private _spot = [];
if (_hits isNotEqualTo []) then {
	(_hits select 0) params ["_p", "_n"];
	if ((_n select 2) > 0.75) then { _spot = _p };
};
if (_spot isEqualTo []) then {
	private _p = AGLToASL (player modelToWorld [0, 0.7, 0]);
	private _down = lineIntersectsSurfaces [_p vectorAdd [0, 0, 1.4], _p vectorAdd [0, 0, -2], player, objNull, true, 1, "GEOM", "VIEW"];
	_spot = if (_down isEqualTo []) then { [_p select 0, _p select 1, getTerrainHeightASL _p] } else { (_down select 0) select 0 };
};
_spot
