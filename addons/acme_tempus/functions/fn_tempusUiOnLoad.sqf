// CT_WEBBROWSER documents JSDialog; the bundled HEMTT event table predates it.
private _jsDialogEvent = "JSDialog";
params ["_d"];
uiNamespace setVariable ["ACME_Tempus_dlg", _d];
private _o = ACME_tempus_cObj;
private _b = _d displayCtrl 100;
_b ctrlSetPosition [-3, -3, 0.2, 0.15];
_b ctrlCommit 0;
_b setVariable ["acme_tempus_mode", "dialog"];
_b setVariable ["acme_tempus_obj", _o];
_b ctrlAddEventHandler [_jsDialogEvent, {
	[{ _this call ACME_fnc_tempusUiMessage }, _this] call CBA_fnc_execNextFrame;
	true
}];
_b ctrlWebBrowserAction ["OpenDataAsURL", call ACME_fnc_tempusHtml];
private _keys = [
    ["power", "Hold to turn on/off", [-96, 80, -78, 98]],
	["home", "Home", [-65.6, 16.2, -45.1, 32.6]],
	["trends", "Trends", [-44.7, 16.2, -25.7, 32.6]],
	["diagnostic", "12 lead ECG", [-25.3, 16.2, -6.0, 32.6]],
	["tc3", "Patient record", [-5.6, 16.2, 13.4, 32.6]],
	["alarms", "Alarms", [-85.5, 15.3, -67.7, 33.1]],
	["alarms", "Alarms", [-95.6, 29.3, -82.0, 42.9]],
	["tc3", "Event record", [83.8, 55.0, 100.8, 76.5]],
	["trends", "Trends", [83.8, 12.3, 100.8, 33.9]]
] apply {
	_x params ["_target", "_tip", "_box"];
	private _k = _d ctrlCreate ["ACME_Tempus_Key", -1];
	_k ctrlSetPosition [-3, -3, 0.01, 0.01];
	_k ctrlCommit 0;
    if (_target == "power") then {
        _k setVariable ["ACME_power_device", _o];
        _k ctrlAddEventHandler ["MouseButtonDown", {[_this select 0, _this select 1, true, false] call ACME_fnc_tempusPowerKey}];
        _k ctrlAddEventHandler ["MouseButtonUp", {[_this select 0, _this select 1, false, false] call ACME_fnc_tempusPowerKey}];
    };

	_k ctrlSetTooltip _tip;
	_k setVariable ["acme_tempus_key", _target];
	_k ctrlAddEventHandler ["ButtonClick", {
		params ["_k"];
        if ((_k getVariable ["acme_tempus_key", ""]) == "power") exitWith {};
		((ctrlParent _k) displayCtrl 100) ctrlWebBrowserAction ["ExecJS", format ["tp.key('%1')", _k getVariable ["acme_tempus_key", "home"]]];
	}];
	[_k, _box]
};
_d setVariable ["acme_tempus_keys", _keys];
_d setVariable ["acme_tempus_step", 0];
_d setVariable ["acme_tempus_dist", 0.5];
private _cam = "camera" camCreate (positionCameraToWorld [0, 0, 0]);
_cam cameraEffect ["internal", "back"];
_cam camSetFov 0.5;
_cam camCommit 0;
showCinemaBorder false;
ACME_tempus_cam = _cam;
private _l = "#lightpoint" createVehicleLocal (getPosATL ACME_tempus_rObj);
_l setLightBrightness 0.1;
_l setLightColor [0.95, 0.97, 1];
_l setLightAmbient [0.25, 0.25, 0.27];
ACME_tempus_light = _l;
[_d] call ACME_fnc_tempusView;
ctrlSetFocus _b;
