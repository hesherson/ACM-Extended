// CT_WEBBROWSER documents JSDialog; the bundled HEMTT event table predates it.
private _jsDialogEvent = "JSDialog";
params ["_d"];
uiNamespace setVariable ["ACME_TempusLS_dlg", _d];
private _o = ACME_tempusls_cObj;
_o setVariable ["acme_tempusls_operator", call ACME_fnc_controlledProvider, true];
private _b = _d displayCtrl 100;
_b ctrlSetPosition [-3, -3, 0.2, 0.15];
_b ctrlCommit 0;
_b setVariable ["acme_tempusls_mode", "dialog"];
_b setVariable ["acme_tempusls_obj", _o];
_b ctrlAddEventHandler [_jsDialogEvent, {
	[{ _this call ACME_fnc_tempusLsUiMessage }, _this] call CBA_fnc_execNextFrame;
	true
}];
_b ctrlWebBrowserAction ["OpenDataAsURL", call ACME_fnc_tempusLsHtml];
private _keys = [
	["soft1", "", [50.8, 121.9, 77.6, 134.7]],
	["soft2", "", [50.8, 105.2, 77.6, 118.0]],
	["soft3", "", [50.8, 88.6, 77.6, 101.4]],
	["soft4", "", [50.8, 72.6, 77.6, 85.4]],
	["soft5", "", [50.8, 56.6, 77.6, 69.4]],
	["power", "Power", [-77.6, 26.5, -60.2, 43.9]],
	["down", "Energy down", [-46.0, 24.9, -34.6, 36.3]],
	["up", "Energy up", [-32.3, 34.1, -20.9, 45.5]],
	["charge", "Charge", [-7.3, 25.7, 11.5, 44.5]],
	["shock", "Shock", [25.1, 23.9, 48.1, 46.9]]
] apply {
	_x params ["_target", "_tip", "_box"];
	private _k = _d ctrlCreate ["ACME_TempusLS_Key", -1];
	_k ctrlSetPosition [-3, -3, 0.01, 0.01];
	_k ctrlCommit 0;
    if (_target == "power") then {
        _k setVariable ["ACME_power_device", _o];
        _k ctrlAddEventHandler ["MouseButtonDown", {[_this select 0, _this select 1, true, true] call ACME_fnc_tempusPowerKey}];
        _k ctrlAddEventHandler ["MouseButtonUp", {[_this select 0, _this select 1, false, true] call ACME_fnc_tempusPowerKey}];
    };

	if (_tip isNotEqualTo "") then { _k ctrlSetTooltip _tip };
	_k setVariable ["acme_tempusls_key", _target];
	_k ctrlAddEventHandler ["ButtonClick", { _this call ACME_fnc_tempusLsKey }];
	[_k, _box]
};
_d setVariable ["acme_tempusls_keys", _keys];
_d setVariable ["acme_tempusls_step", 0];
_d setVariable ["acme_tempusls_dist", 0.5];
private _cam = "camera" camCreate (positionCameraToWorld [0, 0, 0]);
_cam cameraEffect ["internal", "back"];
_cam camSetFov 0.5;
_cam camCommit 0;
showCinemaBorder false;
ACME_tempusls_cam = _cam;
private _l = "#lightpoint" createVehicleLocal (getPosATL ACME_tempusls_rObj);
_l setLightBrightness 0.1;
_l setLightColor [0.95, 0.97, 1];
_l setLightAmbient [0.25, 0.25, 0.27];
ACME_tempusls_light = _l;
[_d] call ACME_fnc_tempusLsView;
ctrlSetFocus _b;
