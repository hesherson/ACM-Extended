params ["_d"];
private _o = ACME_tempusls_rObj;
private _cam = missionNamespace getVariable ["ACME_tempusls_cam", objNull];
if (isNull _o || {isNull _cam}) exitWith {};
private _step = _d getVariable ["acme_tempusls_step", 0];
_d setVariable ["acme_tempusls_step", _step + 1];
private _aim = {
	([_o, 0, 86] call ACME_fnc_tempusLsFront) params ["_c", "_n"];
	private _up = vectorNormalized ((([_o, 0, 186] call ACME_fnc_tempusLsFront) select 0) vectorDiff _c);
	_cam setPosASL (_c vectorAdd (_n vectorMultiply (_d getVariable ["acme_tempusls_dist", 0.5])));
	_cam setVectorDirAndUp [_n vectorMultiply -1, _up];
	private _l = missionNamespace getVariable ["ACME_tempusls_light", objNull];
	if (!isNull _l) then { _l setPosASL (_c vectorAdd (_n vectorMultiply 0.7)) };
};
private _proj = { worldToScreen (ASLToAGL (([_o] + _this) call ACME_fnc_tempusLsFront select 0)) };
if (_step == 0) exitWith { call _aim };
if (_step in [2, 4]) exitWith {
	private _t = [0, 174] call _proj;
	private _b = [0, -2] call _proj;
	private _l = [-103, 86] call _proj;
	private _r = [103, 86] call _proj;
	if (count _t == 2 && {count _b == 2} && {count _l == 2} && {count _r == 2}) then {
		private _k = ((abs ((_b select 1) - (_t select 1))) / (0.86 * safezoneH)) max ((abs ((_r select 0) - (_l select 0))) / (0.92 * safezoneW));
		_d setVariable ["acme_tempusls_dist", (_d getVariable ["acme_tempusls_dist", 0.5]) * _k];
		call _aim;
	};
};
if (_step < 6 || {diag_tickTime - (_d getVariable ["acme_tempusls_at", 0]) > 0.2}) then {
	_d setVariable ["acme_tempusls_at", diag_tickTime];
	call _aim;
	private _rect = {
		params ["_x0", "_z0", "_x1", "_z1"];
		private _pts = [[_x0, _z0], [_x1, _z0], [_x0, _z1], [_x1, _z1]] apply { _x call _proj };
		if (({count _x == 2} count _pts) < 4) exitWith {[-3, -3, 0.01, 0.01]};
		private _xs = _pts apply { _x select 0 };
		private _ys = _pts apply { _x select 1 };
		private _left = selectMin _xs;
		private _top = selectMin _ys;
		[_left, _top, (selectMax _xs) - _left, (selectMax _ys) - _top]
	};
	private _place = {
		params ["_c", "_pos"];
		if ((_c getVariable ["acme_tempusls_rect", []]) isNotEqualTo _pos) then {
			_c setVariable ["acme_tempusls_rect", _pos];
			_c ctrlSetPosition _pos;
			_c ctrlCommit 0;
		};
	};
	[_d displayCtrl 100, [-82.1, 54.55, 46.0, 150.65] call _rect] call _place;
	{
		_x params ["_k", "_box"];
		[_k, _box call _rect] call _place;
	} forEach (_d getVariable ["acme_tempusls_keys", []]);
};
