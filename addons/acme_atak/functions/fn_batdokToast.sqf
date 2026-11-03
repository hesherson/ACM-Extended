params [["_t", ""]];
if (_t isEqualTo "" || {!hasInterface}) exitWith {};
if (!isNil "cTab_fnc_addNotification" && {!isNull (uiNamespace getVariable ["cTab_Android_dlg", displayNull])}) then {
	["BATDOK", _t, 6] call cTab_fnc_addNotification;
};
[_t, 2.5] call ace_common_fnc_displayTextStructured;
