/* Compatibility entry point for integrations that used the B276 warning.
   Enrichment requires a verified source attached to this physical ventilator;
   carrying a cylinder alone never authorizes it. The native O2 page uses its
   quiet supply status instead. This helper neither draws gas nor writes settings. */
private _patient = uiNamespace getVariable ["ACME_vent_target", ACE_player];
if (([_patient] call ACME_fnc_ventOxygenState) select 1) exitWith {true};

// Clear only oxygen edits; other ventilator settings remain independent.
if ((uiNamespace getVariable ["ACME_vent_editingParam", -1]) == 0) then {
    uiNamespace setVariable ["ACME_vent_editingParam", -1];
};
uiNamespace setVariable ["ACME_vent_editingFio2", false];
if (!hasInterface) exitWith {false};

disableSerialization;
private _screen = uiNamespace getVariable ["ACME_vent_screen", ""];
if (_screen == "o2") then {
    ["o2"] call ACME_fnc_ventPanelShowScreen;
} else {
    [] call ACME_fnc_ventPanelListRefresh;
};
private _parent = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _parent) exitWith {
    ["An O2 tank is required.", 2.5] call ace_common_fnc_displayTextStructured;
    false
};
if (!isNull (_parent getVariable ["ACME_vent_oxygenPrompt", displayNull])) exitWith {false};
private _prompt = _parent createDisplay "RscDisplayEmpty";
if (isNull _prompt) exitWith {false};
_parent setVariable ["ACME_vent_oxygenPrompt", _prompt];
_prompt setVariable ["ACME_vent_oxygenParent", _parent];
private _canvas = call ACME_fnc_uiCanvas;
_canvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
private _w = 0.32 * _uiW;
private _h = 0.16 * _uiH;
private _left = _uiX + (_uiW - _w) / 2;
private _top = _uiY + (_uiH - _h) / 2;
private _bg = _prompt ctrlCreate ["RscText", 1000];
_bg ctrlSetPosition [_left, _top, _w, _h];
_bg ctrlSetBackgroundColor [0.04, 0.04, 0.04, 0.98];
_bg ctrlCommit 0;
private _message = _prompt ctrlCreate ["RscText", 1001];
_message ctrlSetPosition [_left + _w * 0.06, _top + _h * 0.12, _w * 0.88, _h * 0.31];
_message ctrlSetText "An O2 tank is required.";
_message ctrlCommit 0;
private _accept = _prompt ctrlCreate ["RscButton", 1002];
_accept ctrlSetPosition [_left + _w * 0.30, _top + _h * 0.58, _w * 0.40, _h * 0.29];
_accept ctrlSetText "OK";
_accept ctrlCommit 0;
_accept ctrlAddEventHandler ["ButtonClick", {(ctrlParent (_this select 0)) closeDisplay 1;}];
_prompt displayAddEventHandler ["KeyDown", {
    params ["_prompt", "_key"];
    if (_key in [1, 28, 156]) exitWith {_prompt closeDisplay 1; true};
    false
}];
_prompt displayAddEventHandler ["Unload", {
    private _prompt = _this select 0;
    private _parent = _prompt getVariable ["ACME_vent_oxygenParent", displayNull];
    if (!isNull _parent && {(_parent getVariable ["ACME_vent_oxygenPrompt", displayNull]) isEqualTo _prompt}) then {
        _parent setVariable ["ACME_vent_oxygenPrompt", displayNull];
    };
}];
ctrlSetFocus _accept;
false
