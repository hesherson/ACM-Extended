// knob emulation through the mouse wheel. the selection is a single continuous loop across the list rows of the
// screen and then the bottom strip buttons, left to right, wrapping back to the first row. it is the same model
// on every screen, because this is the one dial that drives everything.
// _dir is +1 for a wheel up and -1 for a wheel down.
// for values, such as the FiO2 and the BPM and vt edits, up increases and down decreases, so _dir is used as-is.
// for selection, on the list rows, live fields and the graph, up moves up the list and down moves down, so
// _selDir is used, which is minus _dir.
// these are deliberately opposite signs, because advancing a list index moves downward on screen, so the
// selection must negate the wheel to feel correct.
params ["_dir"];
if !([ACE_player, "ventilator", true] call ACME_fnc_procedureAllowed) exitWith {};

// the dial is on the front of the device. turning it while looking at the back would be reaching around the
// machine to move a selection you cannot see, so the wheel does nothing here. the two things the back does
// have, the power button and the battery hatch, are clicks rather than scrolls and are unaffected.
// this has to be the first thing in the function. it was further down, below the cooldown stamp and the knob
// rotation flash, so scrolling on the back still flashed the knob overlay before the exit was reached.
if (uiNamespace getVariable ["ACME_vent_flipped", false]) exitWith {};
// a dead machine has no selection to move either.
if !(uiNamespace getVariable ["ACME_vent_powered", false]) exitWith {};
private _vTgt = uiNamespace getVariable ["ACME_vent_target", ACE_player]; if (isNull _vTgt) then { _vTgt = ACE_player; };

// the scroll rate cap. the mouse wheel can fire many steps in a fraction of a second, which blows through menus
// and machine-guns the dial sound. any scroll step that arrives sooner than a minimum interval after the last
// accepted one is ignored, with no move and no sound. it is tunable through ACME_vent_scrollCooldown, in
// seconds.
private _cooldown = missionNamespace getVariable ["ACME_vent_scrollCooldown", 0.065];
private _lastT = uiNamespace getVariable ["ACME_vent_lastScrollT", -1];
private _now = diag_tickTime;
if (_lastT >= 0 && {(_now - _lastT) < _cooldown}) exitWith {};  // too soon, so drop this step entirely.
uiNamespace setVariable ["ACME_vent_lastScrollT", _now];

// the knob rotation flash. it is placed here, immediately after the cooldown gate, so it fires exactly once per
// accepted step and therefore in lockstep with the dial click that every branch below plays. steps dropped by
// the cooldown produce neither a sound nor a flash, which is what keeps the two in sync.
// it toggles rather than staying on. a rotation held up continuously reads as a knob stuck at an angle, and
// alternating on and off between steps reads as one being turned. the direction follows the art: a wheel up is
// left and a wheel down is right.
if (hasInterface) then {
    private _kd = findDisplay 87700;
    if (!isNull _kd) then {
        private _kc = _kd displayCtrl 87703;
        if (!isNull _kc) then {
            private _on = !(uiNamespace getVariable ["ACME_vent_knobFlashOn", false]);
            uiNamespace setVariable ["ACME_vent_knobFlashOn", _on];
            uiNamespace setVariable ["ACME_vent_knobFlashT", _now];
            if (_on) then {
                private _tex = if (_dir > 0) then {
                    "\acm_extended\ui\vent\ventway_sparrow_robust_knob_rotate_left_ca.paa"
                } else {
                    "\acm_extended\ui\vent\ventway_sparrow_robust_knob_rotate_right_ca.paa"
                };
                // ctrlSetText on a picture is a texture reload, so only swap when the direction actually changed.
                if ((uiNamespace getVariable ["ACME_vent_knobTexCur", ""]) != _tex) then {
                    _kc ctrlSetText _tex;
                    uiNamespace setVariable ["ACME_vent_knobTexCur", _tex];
                };
            };
            _kc ctrlShow _on;
        };
    };
};

// BRIGHTNESS and ALARM VOLUME are dial-edited in place: the knob changes the level and the panel responds while
// you watch. that is how the real device behaves, and for the night setting it is the only sensible design,
// because the entire effect of that setting is on the screen you are looking at while you set it.
private _scr = uiNamespace getVariable ["ACME_vent_screen", ""];

// an open level popup takes precedence over the screen underneath, because the dial is doing nothing but moving
// the level, which is the entire interaction. there are four levels, with hard stops at each end rather than
// wrapping, because a brightness control that jumps from full to night when you overshoot is a control you
// cannot trust at night.
if (uiNamespace getVariable ["ACME_vent_lvlWinOpen", false]) exitWith {
    playSound "ACME_VentDial";
    private _kindL = uiNamespace getVariable ["ACME_vent_lvlKind", "brightness"];
    private _varL  = if (_kindL isEqualTo "brightness") then { "ACME_vent_brightness" } else { "ACME_vent_alarmVol" };
    private _curL  = (round (uiNamespace getVariable [_varL, 3])) max 1 min 4;
    private _newL  = (_curL + _dir) max 1 min 4;
    if (_newL != _curL) then {
        uiNamespace setVariable [_varL, _newL];
        // night drops the alarm volume with it, per the manual: the robust low setting lowers the brightness and the
        // volume together, because the point of that mode is not being seen or heard.
        // it fires on the transition only. firing it every time the dial moved while already at night meant the operator
        // could turn the alarm up and have it silently reset the next time they touched brightness. it is a suggested
        // default on entering night, not a lock.
        if (_kindL isEqualTo "brightness" && {_newL isEqualTo 1} && {_curL > 1}) then {
            uiNamespace setVariable ["ACME_vent_alarmVol", 1];
        };
        ["repaint"] call ACME_fnc_ventLevelWindow;
        // brightness repaints the whole panel, because every color on it runs through the new level.
        if (_kindL isEqualTo "brightness") then {
            [uiNamespace getVariable ["ACME_vent_screen", "live"]] call ACME_fnc_ventPanelShowScreen;
            ["repaint"] call ACME_fnc_ventLevelWindow;  // a rebuilt screen would have torn the window down.
        };
    };
};
// the bright and alarmvol screens are gone. both settings are popups now, through fn_ventlevelwindow, and the
// popup branch at the top of this function owns the dial while one is open.

playSound "ACME_VentDial";
private _selDir = -_dir;  // the selection index moves opposite the wheel, so up is an earlier item.
private _screen = uiNamespace getVariable ["ACME_vent_screen", "live"];
private _simple = ((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])});
// Clear stale edits before any dial branch can write a stored advanced setting.
// Alarm thresholds stay editable; the automatic delivery pressure limit does not.
if (_simple) then {
    uiNamespace setVariable ["ACME_vent_editingParam", -1];
    uiNamespace setVariable ["ACME_vent_editingPeep", false];
    uiNamespace setVariable ["ACME_vent_editingIE", false];
    uiNamespace setVariable ["ACME_vent_editingFio2", false];
    if (_screen == "alerts" && {(uiNamespace getVariable ["ACME_vent_editingAlert", -1]) == 2}) then {
        uiNamespace setVariable ["ACME_vent_editingAlert", -1];
    };
};

// an open alarm window takes precedence over any screen. the dial moves between the x and the next arrow, and
// the next arrow only when there is more than one alarm, and a repaint redraws the highlight. a middle-click,
// which is activate, fires it.
if (uiNamespace getVariable ["ACME_vent_alarmWinOpen", false]) exitWith {
    private _tgtW = uiNamespace getVariable ["ACME_vent_target", objNull];
    private _alarmsW = if (isNull _tgtW) then {[]} else {_tgtW getVariable ["ACME_vent_alarms", []]};
    private _multiW = (count _alarmsW) > 1;
    if (_multiW) then {
        private _s = uiNamespace getVariable ["ACME_vent_alarmSel", 0];
        _s = (_s + 1) mod 2;  // two targets: x at 0 and next at 1.
        uiNamespace setVariable ["ACME_vent_alarmSel", _s];
        ["repaint"] call ACME_fnc_ventAlarmWindow;
    };
};

// o2 enrichment edit mode, on its own screen, takes precedence, because the dial changes the value from 21 to
// 100 percent. room air is 21 percent and 100 percent is pure oxygen. it is the same interaction model as the
// BPM field.
// PARAMS edits in place. rows 0 for o2, 1 for i:e and 2 for PEEP change on the PARAMS page itself, with no
// sub-screen. it is the same dial-turns-the-value model as ALERTS, and ventPanelSetValue writes the field text
// while the painter keeps it lit.
if ((_screen == "params") && {(uiNamespace getVariable ["ACME_vent_editingParam", -1]) >= 0}) exitWith {
    private _row = uiNamespace getVariable ["ACME_vent_editingParam", -1];
    private _tP = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    // page 1 holds every in-place editable row, so the row index alone now says which parameter is being turned and
    // the old page-2 offset is gone. page 2 is MODE, INTERFACE and WEIGHT, all of which open a sub-screen and none
    // of which the dial edits here, so this branch cannot be reached from it.
    private _pg = uiNamespace getVariable ["ACME_vent_paramsPage", 0];
    if (_pg != 0) exitWith {};
    switch (_row) do {
        case 3: {  // PRESSURE SUPPORT, 0 to 50 cmH2O, above PEEP. page 1, row 3.
            private _v = ((if (isNull _tP) then {10} else {_tP getVariable ["ACME_vent_psup", 10]}) + _dir) max 0 min 50;
            if (!isNull _tP) then { _tP setVariable ["ACME_vent_psup", _v, true]; };
            [3, str _v] call ACME_fnc_ventPanelSetValue;  // the number only, because the unit is its own piece.
        };
        case 4: {  // TRIGGER sensitivity, -10 to -0.25 cmH2O, with OFF at 0, which is a real setting on this device. page 1, row 4.
            private _ladder = [0, -0.25, -0.5, -1, -1.5, -2, -3, -4, -5, -7, -10];
            private _cur = if (isNull _tP) then {missionNamespace getVariable ["ACME_vent_trigSensCmH2O", -2]} else {_tP getVariable ["ACME_vent_trigSensCmH2O", missionNamespace getVariable ["ACME_vent_trigSensCmH2O", -2]]};
            private _idx = _ladder findIf {abs (_x - _cur) < 0.01};
            if (_idx < 0) then { _idx = _ladder find -2; if (_idx < 0) then { _idx = 0 }; };
            _idx = (_idx + _dir) max 0 min ((count _ladder) - 1);
            private _v = _ladder select _idx;
            if (!isNull _tP) then { _tP setVariable ["ACME_vent_trigSensCmH2O", _v, true]; };
            [4, (if (_v == 0) then {"OFF"} else {str _v})] call ACME_fnc_ventPanelSetValue;  // the number only, row 4.
        };
        case 0: {  // o2 ENRICHMENT, 21 to 100 percent.
            private _v = ((if (isNull _tP) then {uiNamespace getVariable ["ACME_vent_fio2", 21]} else {_tP getVariable ["ACME_vent_fio2", 21]}) + _dir) max 21 min 95;  // the sparrow spec is an FiO2 of 21 to 95 percent. a turbine on ambient air with o2 enrichment cannot reach 100 percent.
            uiNamespace setVariable ["ACME_vent_fio2", _v];
            if (!isNull _tP) then { _tP setVariable ["ACME_vent_fio2", _v, true]; };
            [0, str _v] call ACME_fnc_ventPanelSetValue;  // the number only, because the percent sign is its own piece.
        };
        case 1: {  // the i:e ratio ladder.
            private _ladder = [4.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.33];
            private _invOK = if (isNull _tP) then {true} else {_tP getVariable ["ACME_vent_alertInvIE", true]};
            if (!_invOK) then { _ladder = _ladder select {_x >= 1} };
            private _cur = if (isNull _tP) then {2.0} else {_tP getVariable ["ACME_vent_ie", 2.0]};
            private _idx = _ladder findIf {abs (_x - _cur) < 0.01};
            if (_idx < 0) then { _idx = _ladder find 2.0; if (_idx < 0) then { _idx = 0 }; };
            _idx = (_idx + _dir) max 0 min ((count _ladder) - 1);
            private _v = _ladder select _idx;
            if (!isNull _tP) then { _tP setVariable ["ACME_vent_ie", _v, true]; };
            [1, ([_v] call ACME_fnc_ventFormatIE)] call ACME_fnc_ventPanelSetValue;
        };
        case 2: {  // PEEP, 0 to 20 cmH2O.
            private _v = ((if (isNull _tP) then {5} else {_tP getVariable ["ACME_vent_peep", 5]}) + _dir) max 0 min 20;
            if (!isNull _tP) then { _tP setVariable ["ACME_vent_peep", _v, true]; };
            [2, str _v] call ACME_fnc_ventPanelSetValue;  // the number only.
        };
    };
};

if ((_screen == "peep") && {uiNamespace getVariable ["ACME_vent_editingPeep", false]}) exitWith {
    disableSerialization;
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    private _tP = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    private _v = ((_tP getVariable ["ACME_vent_peep", 5]) + _dir) max 0 min 20;
    _tP setVariable ["ACME_vent_peep", _v, true];
    if (!isNull _dlg) then { (_dlg displayCtrl 87781) ctrlSetText format ["PEEP   %1 cmH2O", _v]; };
};

if ((_screen == "ie") && {uiNamespace getVariable ["ACME_vent_editingIE", false]}) exitWith {
    disableSerialization;
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    private _tI3 = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    // the ladder, longest expiratory time first. the last two are inverse and are only offered when INV i:e is
    // on.
    private _ladder = [4.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.33];
    private _invOK = _tI3 getVariable ["ACME_vent_alertInvIE", true];
    if (!_invOK) then { _ladder = _ladder select {_x >= 1} };  // with INV i:e off, the machine refuses to invert.
    private _cur = _tI3 getVariable ["ACME_vent_ie", 2.0];
    private _idx = _ladder findIf {abs (_x - _cur) < 0.01};
    if (_idx < 0) then { _idx = _ladder find 2.0; if (_idx < 0) then { _idx = 0 }; };
    _idx = (_idx + _dir) max 0 min ((count _ladder) - 1);
    private _v = _ladder select _idx;
    _tI3 setVariable ["ACME_vent_ie", _v, true];
    if (!isNull _dlg) then { (_dlg displayCtrl 87781) ctrlSetText format ["I:E   %1", [_v] call ACME_fnc_ventFormatIE]; };
};

if ((_screen == "alerts") && {(uiNamespace getVariable ["ACME_vent_editingAlert", -1]) >= 0}) exitWith {
    disableSerialization;
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    private _row = uiNamespace getVariable ["ACME_vent_editingAlert", -1];
    private _tA = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    // the bounds are clinical rather than arbitrary. an rr floor below 2 or a ceiling above 60 is not a rate any
    // patient has, and a pressure alert below 20 would fire on every normal breath while one above 60 would never
    // fire at all.
    switch (_row) do {
        case 0: {
            private _v = ((_tA getVariable ["ACME_vent_alertRRLow", 6]) + _dir) max 2 min 15;
            _tA setVariable ["ACME_vent_alertRRLow", _v, true];
            [0, str _v] call ACME_fnc_ventPanelSetValue;
        };
        case 1: {
            private _v = ((_tA getVariable ["ACME_vent_alertRRHigh", 25]) + _dir) max 16 min 60;
            _tA setVariable ["ACME_vent_alertRRHigh", _v, true];
            [1, str _v] call ACME_fnc_ventPanelSetValue;
        };
        case 2: {
            private _v = ((_tA getVariable ["ACME_vent_alertPLimit", 40]) + _dir) max 20 min 60;
            _tA setVariable ["ACME_vent_alertPLimit", _v, true];
            [2, str _v] call ACME_fnc_ventPanelSetValue;
        };
        case 3: {
            private _v = ((_tA getVariable ["ACME_vent_alertPAlert", 40]) + _dir) max 20 min 60;
            _tA setVariable ["ACME_vent_alertPAlert", _v, true];
            [3, str _v] call ACME_fnc_ventPanelSetValue;
        };
    };
};

// ALERTS page 2 of 2: LOW TVe, LEAK, APNEA t., mv low, mv high and PEEP. it uses the same edit-by-row-index
// model as page 1. MV values are absolute L/min, with low kept below high.
if ((_screen == "alerts2") && {(uiNamespace getVariable ["ACME_vent_editingAlert", -1]) >= 0}) exitWith {
    disableSerialization;
    private _row = uiNamespace getVariable ["ACME_vent_editingAlert", -1];
    private _tA = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    switch (_row) do {
        case 0: {
            private _v = ((_tA getVariable ["ACME_vent_alertLowTVe", 85]) + _dir) max 50 min 95;
            _tA setVariable ["ACME_vent_alertLowTVe", _v, true];
            [0, str _v] call ACME_fnc_ventPanelSetValue;
        };
        case 1: {
            private _v = ((_tA getVariable ["ACME_vent_alertLeak", 100]) + _dir * 5) max 50 min 100;
            _tA setVariable ["ACME_vent_alertLeak", _v, true];
            [1, str _v] call ACME_fnc_ventPanelSetValue;
        };
        case 2: {
            private _v = ((_tA getVariable ["ACME_vent_alertApnea", 30]) + _dir * 5) max 10 min 60;
            _tA setVariable ["ACME_vent_alertApnea", _v, true];
            [2, str _v] call ACME_fnc_ventPanelSetValue;
        };
        case 3: {
            ([_tA] call ACME_fnc_ventMVLimits) params ["_lo", "_hi"];
            private _v = (round (((_lo + _dir * 0.5) max 0 min (_hi - 0.5)) * 10)) / 10;
            _tA setVariable ["ACME_vent_alertMVlowLpm", _v, true];
            [3, _v toFixed 1] call ACME_fnc_ventPanelSetValue;
        };
        case 4: {
            ([_tA] call ACME_fnc_ventMVLimits) params ["_lo", "_hi"];
            private _v = (round (((_hi + _dir * 0.5) max (_lo + 0.5) min 30) * 10)) / 10;
            _tA setVariable ["ACME_vent_alertMVhighLpm", _v, true];
            [4, _v toFixed 1] call ACME_fnc_ventPanelSetValue;
        };
        case 5: {
            private _v = ((_tA getVariable ["ACME_vent_alertPEEP", 5.0]) + _dir * 0.5) max 0 min 20;
            _tA setVariable ["ACME_vent_alertPEEP", _v, true];
            [5, _v toFixed 1] call ACME_fnc_ventPanelSetValue;
        };
    };
};


if ((_screen == "o2") && {uiNamespace getVariable ["ACME_vent_editingFio2", false]}) exitWith {
    disableSerialization;
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    private _v = (uiNamespace getVariable ["ACME_vent_fio2", 21]) + _dir;
    _v = _v max 21 min 95;  // the sparrow spec is an FiO2 of 21 to 95 percent, the same ceiling as the params-page path above.
    uiNamespace setVariable ["ACME_vent_fio2", _v];
    _vTgt setVariable ["ACME_vent_fio2", _v, true];
    private _vc = uiNamespace getVariable ["ACME_vent_o2ValCtrl", controlNull];
    if (!isNull _vc) then { _vc ctrlSetText format ["%1%2", _v, "%"]; };
};

// the o2 screen when not editing. the dial cycles 0 for the value and 1 for BACK, painting the back highlight on
// 1.
if (_screen == "o2") exitWith {
    private _sel = (uiNamespace getVariable ["ACME_vent_selIdx", 0]) + _selDir;
    _sel = ((_sel mod 2) + 2) mod 2;
    uiNamespace setVariable ["ACME_vent_selIdx", _sel];
    disableSerialization;
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    if (!isNull _dlg) then {
        (_dlg displayCtrl 87756) ctrlSetBackgroundColor (if (_sel == 1) then {[0, 0.988, 0.992,1]} else {[0,0,0,0]});
        // the value box. brighten its border-ish highlight when selected, because it already has the blue fill, so nudge
        // the alpha.
        private _vc = uiNamespace getVariable ["ACME_vent_o2ValCtrl", controlNull];
        if (!isNull _vc) then { _vc ctrlSetBackgroundColor (if (_sel == 0) then {[0, 0, 0.996,1]} else {[0, 0, 0.62,1]}); };
    };
};

// the logbook screen. the dial cycles the visible bottom chevrons. with more than one page, 0 is next, which is
// page down, and 1 is BACK. on a single page there is only BACK. a middle-click activates whichever is
// selected. the highlight of the selected chevron is painted here, and the strip highlight controls are 87757
// for next and 87756 for back.
if (_screen == "logbook") exitWith {
    private _multi = (uiNamespace getVariable ["ACME_vent_logNPages", 1]) > 1;
    disableSerialization;
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    if (_multi) then {
        private _sel = (uiNamespace getVariable ["ACME_vent_selIdx", 0]) + _selDir;
        _sel = ((_sel mod 2) + 2) mod 2;
        uiNamespace setVariable ["ACME_vent_selIdx", _sel];
        if (!isNull _dlg) then {
            (_dlg displayCtrl 87757) ctrlSetBackgroundColor (if (_sel == 0) then {[0, 0.988, 0.992,1]} else {[0,0,0,0]});
            (_dlg displayCtrl 87756) ctrlSetBackgroundColor (if (_sel == 1) then {[0, 0.988, 0.992,1]} else {[0,0,0,0]});
        };
    } else {
        // only BACK exists, so keep it selected and a middle-click always exits.
        uiNamespace setVariable ["ACME_vent_selIdx", 1];
        if (!isNull _dlg) then { (_dlg displayCtrl 87756) ctrlSetBackgroundColor [0, 0.988, 0.992,1]; };
    };
};

// the graph screen. the dial cycles through three positions: 0 is the PRESSURE view, 1 is the FLOW view and 2 is
// BACK. landing on 0 or 1 switches the shown waveform, so rotating still switches between pressure and flow,
// and landing on 2 highlights the back chevron so a middle-click can exit. this is the only screen where you
// would otherwise be stuck.
if (_screen == "graph") exitWith {
    private _sel = (uiNamespace getVariable ["ACME_vent_selIdx", 0]) + _selDir;
    _sel = ((_sel mod 3) + 3) mod 3;
    uiNamespace setVariable ["ACME_vent_selIdx", _sel];
    disableSerialization;
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    if (_sel < 2) then {
        private _newType = ["PRESSURE","FLOW"] select _sel;
        private _oldType = uiNamespace getVariable ["ACME_vent_graphType", "PRESSURE"];
        uiNamespace setVariable ["ACME_vent_graphType", _newType];
        // switching PRESSURE and FLOW changes the whole plot: the scale numbers, 40, 20, 0, -20 and -40 against 20, 10
        // and 0, the gridline count, five against three, and the baseline, the center against the floor. the screen
        // router builds those, so the graph screen is rebuilt on the switch instead of only re-labeling the title.
        // otherwise the numbers and gridlines only changed when you exited and re-entered.
        if (_newType != _oldType) exitWith {
            // keep the sweep running across the rebuild. changing which trace you are watching is not a reason for the arm
            // to jump back to the left edge, and it is not a reason to re-zero the sensors either.
            uiNamespace setVariable ["ACME_vent_graphKeepSweep", true];
            ["graph"] call ACME_fnc_ventPanelShowScreen;
            uiNamespace setVariable ["ACME_vent_selIdx", _sel];  // preserve the dial position across the rebuild.
        };
    };
    if (!isNull _dlg) then {
        (_dlg displayCtrl 87800) ctrlSetText (uiNamespace getVariable ["ACME_vent_graphType", "PRESSURE"]);
        (_dlg displayCtrl 87756) ctrlSetBackgroundColor (if (_sel == 2) then {[0, 0.988, 0.992,1]} else {[0,0,0,0]});
    };
};

// list and menu screens. it is a single continuous selection loop across the rows plus the visible nav chevrons
// in order.
if (_screen in ["weight","mode","interface","connect","menu","params","advset","ventdisp","tech","tech2","alerts","alerts2","ie","peep"]) exitWith {
    private _n = uiNamespace getVariable ["ACME_vent_listCount", 0];
    private _navList = uiNamespace getVariable ["ACME_vent_navList", []];
    private _nStrip = count _navList;  // exactly the chevrons that are actually shown.
    private _total = _n + _nStrip;
    if (_total <= 0) exitWith {};
    private _sel = (uiNamespace getVariable ["ACME_vent_selIdx", 0]) + _selDir;
    _sel = ((_sel mod _total) + _total) mod _total;  // wrap through the rows and then the chevrons, back to row 0.
    uiNamespace setVariable ["ACME_vent_selIdx", _sel];
    uiNamespace setVariable ["ACME_vent_listSel", (_sel min (_n - 1)) max 0];
    // one painter for every list screen, ALERTS included. the rows carry the labels, the value fields carry the
    // highlight, and the same code paints the nav chevrons. that is why the strip highlights work on the ALERTS
    // pages now: the custom painter that forgot the strip is gone.
    [] call ACME_fnc_ventPanelListRefresh;
};

// the live screen. it is a single continuous loop across the BPM and vt value fields plus the strip buttons,
// left to right.
if (_screen == "live") exitWith {
    private _nFields = 2;  // BPM and vt.
    private _nStrip = 4;
    private _total = _nFields + _nStrip;
    private _editing = uiNamespace getVariable ["ACME_vent_editing", false];
    if (_editing) exitWith {
        // editing a value. the dial changes the value, which the legacy block below handles.
        [_dir] call ACME_fnc_ventPanelLiveEdit;
    };
    private _sel = (uiNamespace getVariable ["ACME_vent_selIdx", 0]) + _selDir;
    _sel = ((_sel mod _total) + _total) mod _total;
    if (_simple && {_sel == 1}) then { _sel = ((_sel + _selDir + _total) mod _total); };
    uiNamespace setVariable ["ACME_vent_selIdx", _sel];
    [] call ACME_fnc_ventPanelLiveRefresh;
};
