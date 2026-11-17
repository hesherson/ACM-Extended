#include "\x\acm\addons\main\ui_theme.hpp"
/* Local technician-code entry. The child display contains no patient simulation.
   The accepted code unlocks only its parent panel; the normal item confirmation remains required. */
disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
params [["_label", "this setting"]];
private _parent = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _parent) exitWith { false };
if (!isNull (_parent getVariable ["ACME_vent_techPrompt", displayNull])) exitWith { false };
private _prompt = _parent createDisplay "RscDisplayEmpty";
if (isNull _prompt) exitWith { false };
_parent setVariable ["ACME_vent_techPrompt", _prompt];
_prompt setVariable ["ACME_vent_techParent", _parent];
_prompt setVariable ["ACME_vent_techTarget", uiNamespace getVariable ["ACME_vent_target", ACE_player]];
private _w = 0.30 * _uiW;
private _h = 0.24 * safeZoneH;
private _left = _uiX + (_uiW - _w) / 2;
private _top = safeZoneY + (safeZoneH - _h) / 2;
private _bg = _prompt ctrlCreate ["RscText", 1000];
_bg ctrlSetPosition [_left, _top, _w, _h];
_bg ctrlSetBackgroundColor (ACM_UI_PANEL_RGB + [0.98]);
_bg ctrlCommit 0;
private _title = _prompt ctrlCreate ["RscText", 1001];
_title ctrlSetPosition [_left + _w * 0.05, _top + _h * 0.04, _w * 0.90, _h * 0.19];
_title ctrlSetText "TECHNICIAN ACCESS";
_title ctrlCommit 0;
private _edit = _prompt ctrlCreate ["ACME_ThemeEdit", 1002];
_edit ctrlSetPosition [_left + _w * 0.05, _top + _h * 0.27, _w * 0.90, _h * 0.20];
_edit ctrlSetText "";
_edit ctrlCommit 0;
private _status = _prompt ctrlCreate ["RscText", 1003];
_status ctrlSetPosition [_left + _w * 0.05, _top + _h * 0.50, _w * 0.90, _h * 0.19];
_status ctrlSetText "Enter the mission technician code.";
_status ctrlCommit 0;
private _submit = {
    disableSerialization;
    params ["_prompt"];
    if (isNull _prompt) exitWith {};
    private _parent = _prompt getVariable ["ACME_vent_techParent", displayNull];
    private _target = _prompt getVariable ["ACME_vent_techTarget", objNull];
    if (isNull _parent || {!(_parent isEqualTo (uiNamespace getVariable ["ACME_vent_dlg", displayNull]))}
        || {!(_target isEqualTo (uiNamespace getVariable ["ACME_vent_target", ACE_player]))}) exitWith {
        _prompt closeDisplay 2;
    };
    private _status = _prompt displayCtrl 1003;
    if (!isNull _target && {_target getVariable ["ACME_vent_driving", false]}) exitWith {
        _status ctrlSetText "Stop ventilation before technician access.";
    };
    private _expected = missionNamespace getVariable ["ACME_vent_techCode", "0000"];
    if !(_expected isEqualType "") exitWith { _status ctrlSetText "Invalid mission code configuration."; };
    private _entered = ctrlText (_prompt displayCtrl 1002);
    if !(_entered isEqualTo _expected) exitWith {
        (_prompt displayCtrl 1002) ctrlSetText "";
        _status ctrlSetText "Incorrect code. Try again or cancel.";
    };
    _parent setVariable ["ACME_vent_techUnlocked", true];
    _parent setVariable ["ACME_vent_techAuthCode", _expected];
    _parent setVariable ["ACME_vent_techAuthTarget", _target];
    _parent setVariable ["ACME_vent_itemConfirmed", []];
    _prompt closeDisplay 1;
    ["Access granted for this panel. Select the item again to confirm.", 2.5] call ace_common_fnc_displayTextStructured;
};
_prompt setVariable ["ACME_vent_techSubmit", _submit];
private _accept = _prompt ctrlCreate ["ACME_ThemeButton", 1004];
_accept ctrlSetPosition [_left + _w * 0.05, _top + _h * 0.74, _w * 0.42, _h * 0.20];
_accept ctrlSetText "UNLOCK";
_accept ctrlCommit 0;
_accept ctrlAddEventHandler ["ButtonClick", {
    private _prompt = ctrlParent (_this select 0);
    [_prompt] call (_prompt getVariable ["ACME_vent_techSubmit", {}]);
}];
private _cancel = _prompt ctrlCreate ["ACME_ThemeButton", 1005];
_cancel ctrlSetPosition [_left + _w * 0.53, _top + _h * 0.74, _w * 0.42, _h * 0.20];
_cancel ctrlSetText "CANCEL";
_cancel ctrlCommit 0;
_cancel ctrlAddEventHandler ["ButtonClick", { (ctrlParent (_this select 0)) closeDisplay 2; }];
_prompt displayAddEventHandler ["KeyDown", {
    params ["_prompt", "_key"];
    if (_key == 1) exitWith { _prompt closeDisplay 2; true };
    if (_key in [28, 156]) exitWith {
        [_prompt] call (_prompt getVariable ["ACME_vent_techSubmit", {}]);
        true
    };
    false
}];
_prompt displayAddEventHandler ["Unload", {
    private _parent = (_this select 0) getVariable ["ACME_vent_techParent", displayNull];
    if (!isNull _parent) then { _parent setVariable ["ACME_vent_techPrompt", displayNull]; };
}];
ctrlSetFocus _edit;
true
