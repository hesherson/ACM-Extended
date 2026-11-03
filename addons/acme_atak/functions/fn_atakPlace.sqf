params ["_d", "_b"];
private _area = _d displayCtrl 21670;
if (isNull _area) then { _area = _d displayCtrl 21650 };
if (isNull _area) exitWith {};
(ctrlPosition _area) params ["_x", "_y", "_w", "_h"];
private _bar = _d displayCtrl 46600;
if (!isNull _bar) then {
	private _top = (ctrlPosition _bar) select 1;
	if (_top > _y + _h * 0.5 && {_top < _y + _h}) then { _h = _top - _y };
};
_b ctrlSetPosition [_x, _y, _w, _h];
_b ctrlCommit 0;
