params ["_d"];
private _o = ACME_tempus_rObj;
private _cam = missionNamespace getVariable ["ACME_tempus_cam", objNull];
if (isNull _o || {isNull _cam}) exitWith {};
private _step = _d getVariable ["acme_tempus_step", 0];
_d setVariable ["acme_tempus_step", _step + 1];
private _aim = {
	([_o, 0, 92] call ACME_fnc_tempusFront) params ["_c", "_n"];
	private _up = vectorNormalized ((([_o, 0, 192] call ACME_fnc_tempusFront) select 0) vectorDiff _c);
	_cam setPosASL (_c vectorAdd (_n vectorMultiply (_d getVariable ["acme_tempus_dist", 0.5])));
	_cam setVectorDirAndUp [_n vectorMultiply -1, _up];
	private _l = missionNamespace getVariable ["ACME_tempus_light", objNull];
	if (!isNull _l) then { _l setPosASL (_c vectorAdd (_n vectorMultiply 0.7)) };
};
private _proj = { worldToScreen (ASLToAGL (([_o] + _this) call ACME_fnc_tempusFront select 0)) };
if (_step == 0) exitWith { call _aim };
if (_step in [2, 4]) exitWith {
	private _t = [0, 186] call _proj;
	private _b = [0, 0] call _proj;
	private _l = [-120, 93] call _proj;
	private _r = [120, 93] call _proj;
	if (count _t == 2 && {count _b == 2} && {count _l == 2} && {count _r == 2}) then {
		private _k = ((abs ((_b select 1) - (_t select 1))) / (0.86 * safezoneH)) max ((abs ((_r select 0) - (_l select 0))) / (0.92 * safezoneW));
		_d setVariable ["acme_tempus_dist", (_d getVariable ["acme_tempus_dist", 0.5]) * _k];
		call _aim;
	};
};
if (_step < 6 || {diag_tickTime - (_d getVariable ["acme_tempus_at", 0]) > 0.2}) then {
	_d setVariable ["acme_tempus_at", diag_tickTime];
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
		if ((_c getVariable ["acme_tempus_rect", []]) isNotEqualTo _pos) then {
			_c setVariable ["acme_tempus_rect", _pos];
			_c ctrlSetPosition _pos;
			_c ctrlCommit 0;
		};
	};
	[_d displayCtrl 100, [-66.5, 52.6, 67.5, 153.1] call _rect] call _place;
	{
		_x params ["_k", "_box"];
		[_k, _box call _rect] call _place;
	} forEach (_d getVariable ["acme_tempus_keys", []]);
};
