params ["_k"];
private _d = ctrlParent _k;
private _name = _k getVariable ["acme_tempusls_key", ""];
private _o = ACME_tempusls_cObj;
private _b = _d displayCtrl 100;
if (isNull _o) exitWith {};
switch (_name) do {
	case "power": {}; // Hold events own power, not ButtonClick.
	case "shock": {
		private _pat = _o getVariable ["acme_tempusls_pat", objNull];
		if (!isNull _pat && {(player distance _pat) > (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])}) exitWith {
			["Too far from the patient to shock", 1.5] call ace_common_fnc_displayTextStructured;
		};
		_b ctrlWebBrowserAction ["ExecJS", "tls.key('shock')"];
	};
	default { _b ctrlWebBrowserAction ["ExecJS", format ["tls.key('%1')", _name]] };
};
