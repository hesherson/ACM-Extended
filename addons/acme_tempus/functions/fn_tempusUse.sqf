params ["_o"];
if !([_o] call ACME_fnc_tempusCanUse) exitWith {};
private _r = _o;
if (_o isEqualTo player) then {
	private _d = getDir player;
	private _f = [sin _d, cos _d, 0];
	private _p = (eyePos player) vectorAdd (_f vectorMultiply 0.8) vectorAdd [0, 0, -0.3];
	_r = "ACME_TempusPro" createVehicleLocal [0, 0, 0];
	_r enableSimulation false;
	_r setDir (_d + 180);
	_r setPosASL _p;
	private _bl = _r selectionPosition ["scr_bl", "Memory"];
	private _n = ((_r selectionPosition ["scr_br", "Memory"]) vectorDiff _bl) vectorCrossProduct ((_r selectionPosition ["scr_tl", "Memory"]) vectorDiff _bl);
	if (((_r vectorModelToWorld _n) vectorDotProduct _f) > 0) then {
		_r setDir _d;
		_r setPosASL _p;
	};
};
ACME_tempus_cObj = _o;
ACME_tempus_rObj = _r;
createDialog "ACME_Tempus_dlg";
