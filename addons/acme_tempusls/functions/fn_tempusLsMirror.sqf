// CT_WEBBROWSER documents JSDialog; the bundled HEMTT event table predates it.
private _jsDialogEvent = "JSDialog";
private _now = diag_tickTime;
private _dlg = uiNamespace getVariable ["ACME_TempusLS_dlg", displayNull];
private _mine = [objNull, ACME_tempusls_rObj] select !isNull _dlg;
if (_now >= ACME_tempusls_scanAt) then {
	ACME_tempusls_scanAt = _now + 0.5;
	private _cam = positionCameraToWorld [0, 0, 0];
	private _all = (nearestObjects [_cam, ["ACME_TempusLS"], 40]) select { _x isNotEqualTo _mine };
	ACME_tempusls_near = _all;
	{ [_x] call ACME_fnc_tempusLsLights } forEach _all;
	if (!isNull _mine) then {
		[_mine, ACME_tempusls_cObj] call ACME_fnc_tempusLsLights;
		[_mine, "#(argb,8,8,3)color(0,0,0,1,co)"] call ACME_fnc_tempusLsScreen;
	};
	private _near = [];
	{
		if ((_x getVariable ["acme_tempusls_pw", [false]]) select 0) then {
			private _p = _x modelToWorldVisual [0, 0, 0.1];
			private _dist = _p distance _cam;
			if (_dist < 6 && {(worldToScreen _p) isNotEqualTo []}) then { _near pushBack [_dist, _x] };
		};
	} forEach _all;
	_near sort true;
	_near = _near select [0, 2];
	private _want = _near apply { _x select 1 };
	{
		private _o = _x select 1;
		if (!isNull _o && {!(_o in _want)}) then {
			_x set [1, objNull];
			[_o, ""] call ACME_fnc_tempusLsScreen;
		};
	} forEach ACME_tempusls_pool;
	private _web = { ((findDisplay (_this select 0)) getVariable ["acme_tempusls_b", controlNull]) };
	{
		_x params ["_dist", "_o"];
		private _i = ACME_tempusls_pool findIf { (_x select 1) isEqualTo _o };
		if (_i < 0) then {
			_i = ACME_tempusls_pool findIf { isNull (_x select 1) && {((_x call _web) getVariable ["acme_tempusls_obj", objNull]) isEqualTo _o} };
			if (_i < 0) then { _i = ACME_tempusls_pool findIf { isNull (_x select 1) } };
			if (_i < 0) then { _i = ACME_tempusls_pool pushBack [format ["acme_tempusls_m%1", count ACME_tempusls_pool], objNull, 0, 9] };
			private _slot = ACME_tempusls_pool select _i;
			_slot set [1, _o];
			private _b = _slot call _web;
			if (!isNull _b) then {
				if ((_b getVariable ["acme_tempusls_obj", objNull]) isEqualTo _o) then {
					[_b, _o, true] call ACME_fnc_tempusLsPush;
				} else {
					_b setVariable ["acme_tempusls_obj", _o];
					_b setVariable ["acme_tempusls_ready", false];
					_b ctrlWebBrowserAction ["OpenDataAsURL", call ACME_fnc_tempusLsHtml];
				};
			};
			[_o, format ["#(rgb,1024,1024,1)ui('RscDisplayEmpty','%1')", _slot select 0]] call ACME_fnc_tempusLsScreen;
		};
		(ACME_tempusls_pool select _i) set [3, _dist];
	} forEach _near;
	{
		if !(_x in _want) then { [_x, ""] call ACME_fnc_tempusLsScreen };
	} forEach _all;
	if (!isNull _dlg) then {
		private _o = ACME_tempusls_cObj;
		private _link = _o getVariable ["acme_tempusls_link", objNull];
		if (!isNull _link && {!((_link getVariable ["acme_tempus_pw", [false]]) select 0) || {_link distance _o > 10}}) then { _o setVariable ["acme_tempusls_link", objNull, true] };
	};
};
{
	_x params ["_name", "_o", "_upd", "_dist"];
	if (isNull _o) then { continue };
	private _d = findDisplay _name;
	if (isNull _d) then { continue };
	private _b = _d getVariable ["acme_tempusls_b", controlNull];
	if (isNull _b) then {
		_b = _d ctrlCreate ["ACME_TempusLS_Web", -1];
		_b ctrlSetPosition [0, 0, 1, 1];
		_b ctrlCommit 0;
		_b setVariable ["acme_tempusls_mode", "mirror"];
		_b setVariable ["acme_tempusls_obj", _o];
		_b ctrlAddEventHandler [_jsDialogEvent, {
			[{ _this call ACME_fnc_tempusLsUiMessage }, _this] call CBA_fnc_execNextFrame;
			true
		}];
		_b ctrlWebBrowserAction ["OpenDataAsURL", call ACME_fnc_tempusLsHtml];
		_d setVariable ["acme_tempusls_b", _b];
		continue;
	};
	if (_now - (_b getVariable ["acme_tempusls_pushAt", 0]) > 0.25) then {
		_b setVariable ["acme_tempusls_pushAt", _now];
		[_b, _o] call ACME_fnc_tempusLsPush;
	};
	if (_now - _upd > ([0.15, 0.05] select (_dist < 3))) then {
		displayUpdate _d;
		_x set [2, _now];
	};
} forEach ACME_tempusls_pool;
call ACME_fnc_tempusLsMetro;
if (!isNull _dlg) then {
	[_dlg] call ACME_fnc_tempusLsView;
	private _o = ACME_tempusls_cObj;
	private _b = _dlg displayCtrl 100;
	if (_now - (_b getVariable ["acme_tempusls_pushAt", 0]) > 0.25) then {
		_b setVariable ["acme_tempusls_pushAt", _now];
		[_b, _o] call ACME_fnc_tempusLsPush;
	};
	if (isNull _o || {!alive player} || {player distance _o > 4} || {!((_o getVariable ["acme_tempusls_pw", [false]]) select 0)}) then { closeDialog 2 };
};
