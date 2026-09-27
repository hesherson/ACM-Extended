// Local top-center preparation banner for long chest-access choreography.
// The medical menu is closed before this is shown, so the original action cannot be spam-clicked.
// Call [true, medic, patient, token] to show and [false, medic, patient, token] to hide.
disableSerialization;
params [
    ["_show", true, [true]],
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_token", "", [""]]
];

if (!hasInterface) exitWith {false};

private _entry = uiNamespace getVariable ["ACME_ChestAccessPreparing", []];
private _oldCtrl = _entry param [0, controlNull];
private _oldToken = _entry param [1, "", [""]];

if (!_show) exitWith {
    if (_token == "" || {_oldToken == _token}) then {
        if (!isNull _oldCtrl) then {ctrlDelete _oldCtrl;};
        uiNamespace setVariable ["ACME_ChestAccessPreparing", []];
    };
    true
};

// Cleanup above is token-owned even if the provider has respawned or changed locality.
if (isNil "ACE_player" || {isNull _medic} || {!(_medic isEqualTo ACE_player)}) exitWith {false};

if (!isNull _oldCtrl) then {ctrlDelete _oldCtrl;};
private _display = findDisplay 46;
if (isNull _display) exitWith {
    uiNamespace setVariable ["ACME_ChestAccessPreparing", []];
    false
};

private _w = safeZoneW * 0.30;
private _h = safeZoneH * 0.052;
private _x = safeZoneX + (safeZoneW - _w) / 2;
private _y = safeZoneY + safeZoneH * 0.025;

private _ctrl = _display ctrlCreate ["RscStructuredText", -1];
_ctrl ctrlEnable false;
_ctrl ctrlSetPosition [_x, _y, _w, _h];
_ctrl ctrlSetBackgroundColor [0, 0, 0, 0];
_ctrl ctrlSetStructuredText parseText "<t align='center' valign='middle' size='1.15'>Preparing...</t>";
_ctrl ctrlCommit 0;
uiNamespace setVariable ["ACME_ChestAccessPreparing", [_ctrl, _token, _patient]];
true
