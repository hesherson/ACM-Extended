// the persistent "RMB / Esc to lower the IV bag" prompt, shown the whole time a bag is held so the cancel control is
// always visible.
// it is a single RscStructuredText control on the main display, 46, and the hang-bag tick re-asserts it every frame
// if it ever gets cleared by a HUD refresh, so it stays up.
// [true] shows it, and it is idempotent, recreating it if missing. [false] hides it.
params [["_show", false, [false]]];
if (!hasInterface) exitWith {};
// no helper text. the prompt is suppressed by forcing the hide path, so every call site stays valid and setting
// ACME_ui_helpText true brings it back.
if (!(missionNamespace getVariable ["ACME_ui_helpText", false])) then { _show = false; };
disableSerialization;

private _disp = findDisplay 46;
if (isNull _disp) exitWith {};

private _old = uiNamespace getVariable ["ACME_hang_HintCtrl", controlNull];
if (!isNull _old) then { ctrlDelete _old; };
uiNamespace setVariable ["ACME_hang_HintCtrl", controlNull];
uiNamespace setVariable ["ACME_hang_HintMedic", objNull];

if (!_show) exitWith {};

private _ctrl = _disp ctrlCreate ["RscStructuredText", -1];
_ctrl ctrlSetPosition [
    safeZoneX + safeZoneW * 0.5 - 0.21,
    safeZoneY + safeZoneH * 0.855,
    0.42,
    0.05
];
_ctrl ctrlSetBackgroundColor [0, 0, 0, 0.4];
_ctrl ctrlSetStructuredText parseText (
    "<t align='center' size='1.05' shadow='1' shadowColor='#000000'>" +
    "<t color='#ffffff'>RMB / Esc</t><t color='#a3d4ec'>  -  Lower IV Bag</t>" +
    "</t>"
);
_ctrl ctrlCommit 0;
uiNamespace setVariable ["ACME_hang_HintCtrl", _ctrl];
uiNamespace setVariable ["ACME_hang_HintMedic", call ACME_fnc_controlledProvider];
