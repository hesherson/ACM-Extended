// Input cannot outlive its captured patient/device panel.
if !([] call ACME_fnc_ventPanelContext) exitWith {};
// the 4-second power-off hold: measure it, show it, and fire it.
// the bar is not decoration, it is the safety. a timer alone would mean an accidental middle-click-and-drag could
// silently kill a ventilated patient four seconds later with no warning whatsoever.
// a bar that fills across the middle of the screen saying POWERING OFF, for four full seconds, cannot be missed and
// cancels the instant you let go. the countdown is the confirmation dialog, and it simply does not make you click
// anything, which is exactly right for a device you might be operating with one hand in the dark.
if (!hasInterface) exitWith {};
disableSerialization;

private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith { [] call ACME_fnc_ventHoldClear; };

private _down = uiNamespace getVariable ["ACME_vent_mmbDown", -1];
if (_down < 0) exitWith { [] call ACME_fnc_ventHoldClear; };
if (uiNamespace getVariable ["ACME_vent_mmbFired", false]) exitWith {};

private _need = missionNamespace getVariable ["ACME_vent_powerHoldSeconds", 4];
private _held = diag_tickTime - _down;

// below the arming threshold this is an ordinary click on its way to being a select, so say nothing.
if (_held < (missionNamespace getVariable ["ACME_vent_powerHoldArm", 0.45])) exitWith {};

(uiNamespace getVariable ["ACME_vent_scrRect", [0,0,1,1]]) params ["_sx","_sy","_sw","_sh"];
private _frac = (_held / _need) min 1;

private _ctrls = uiNamespace getVariable ["ACME_vent_holdUI", []];
if (_ctrls isEqualTo []) then {
    private _mk = {
        params ["_cls","_x","_y","_w","_h"];
        private _c = _dlg ctrlCreate [_cls, -1];
        _c ctrlSetPosition [_sx + _sw*_x, _sy + _sh*_y, _sw*_w, _sh*_h];
        _c ctrlSetBackgroundColor [0,0,0,0];
        _c ctrlCommit 0; _c ctrlShow true;
        _c
    };
    private _frame = ["RscText", 0.10, 0.40, 0.80, 0.22] call _mk;
    _frame ctrlSetBackgroundColor [0.04, 0.04, 0.04, 0.96];

    private _lbl = ["RscText", 0.12, 0.425, 0.76, 0.075] call _mk;
    _lbl ctrlSetText "POWERING OFF";
    _lbl ctrlSetFontHeight (_sh * 0.075);
    _lbl ctrlSetTextColor [1, 0.35, 0.30, 1];

    private _track = ["RscText", 0.13, 0.515, 0.74, 0.055] call _mk;
    _track ctrlSetBackgroundColor [0.20, 0.20, 0.20, 1];

    private _fill = ["RscText", 0.13, 0.515, 0.0, 0.055] call _mk;
    _fill ctrlSetBackgroundColor [0.86, 0.10, 0.10, 1];

    private _hint = ["RscText", 0.12, 0.575, 0.76, 0.045] call _mk;
    _hint ctrlSetText "release to cancel";
    _hint ctrlSetFontHeight (_sh * 0.048);
    _hint ctrlSetTextColor [0.70, 0.72, 0.75, 1];

    _ctrls = [_frame, _lbl, _track, _fill, _hint];
    uiNamespace setVariable ["ACME_vent_holdUI", _ctrls];
    playSound "ACME_VentClick";
};

private _fill = _ctrls select 3;
if (!isNull _fill) then {
    _fill ctrlSetPosition [_sx + _sw*0.13, _sy + _sh*0.515, _sw * 0.74 * _frac, _sh*0.055];
    _fill ctrlCommit 0;
};

if (_frac < 1) exitWith {};

// held the full four seconds. it fires once: the flag stops the tick repeating it and stops the coming
// MouseButtonUp from also registering as a select.
uiNamespace setVariable ["ACME_vent_mmbFired", true];
uiNamespace setVariable ["ACME_vent_mmbDown", -1];
[] call ACME_fnc_ventHoldClear;
[] call ACME_fnc_ventPowerOff;
