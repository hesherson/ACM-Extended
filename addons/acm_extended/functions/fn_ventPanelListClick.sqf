// activate a list row. ventPanelActivateSel calls it through a middle-click, and the dial is the only input. the
// blue selection bar already shows which row the dial is on, and this acts on it. the behavior per screen is:
// setup, meaning weight, mode and interface, commits the selection and advances the flow to the next screen.
// menu, params and tech activate the row, opening the sub-screen or performing the action.
// the blue bar is the persistent cursor and is never cleared here.
params ["_row"];
if !([ACE_player, "ventilator", true] call ACME_fnc_procedureAllowed) exitWith {};
playSound "ACME_VentClick";
private _n = uiNamespace getVariable ["ACME_vent_listCount", 0];
if (_row >= _n) exitWith {};
private _screen = uiNamespace getVariable ["ACME_vent_screen", ""];
if (((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])}) && {
    _screen in ["weight", "mode", "interface", "params", "o2", "ie", "peep"]
    || {_screen == "alerts" && {_row == 2}}
}) exitWith {};

// keep the cursor on the activated row.
uiNamespace setVariable ["ACME_vent_selIdx", _row];
uiNamespace setVariable ["ACME_vent_listSel", _row];
[] call ACME_fnc_ventPanelListRefresh;

// the weight screen: 70 kg and above, the last row, is the only functional option, and the rest are inert and
// cosmetic.
if (_screen == "weight") exitWith {
    if (_row == (_n - 1)) then {
        ["confirm"] call ACME_fnc_ventPanelNavClick;  // it commits 70 kg and advances to mode.
    } else {
        ["Only 70 kg+ is selectable on this ventilator.", 1.5] call ace_common_fnc_displayTextStructured;
    };
};

// the o2 enrichment screen: the single row is the value. a middle-click toggles edit mode, exactly like the BPM
// field on the live screen, so in edit the dial changes the value and clicking again commits.
if (_screen == "peep") exitWith {
    private _ed = uiNamespace getVariable ["ACME_vent_editingPeep", false];
    uiNamespace setVariable ["ACME_vent_editingPeep", !_ed];
    [] call ACME_fnc_ventPanelListRefresh;
};

if (_screen == "ie") exitWith {
    private _ed = uiNamespace getVariable ["ACME_vent_editingIE", false];
    uiNamespace setVariable ["ACME_vent_editingIE", !_ed];
    [] call ACME_fnc_ventPanelListRefresh;
};

if (_screen == "alerts") exitWith {
    private _tA = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    if (_row == 4) exitWith {
        // INV i:e is a toggle rather than a dial, so flip it on the spot.
        private _inv = _tA getVariable ["ACME_vent_alertInvIE", true];
        _tA setVariable ["ACME_vent_alertInvIE", !_inv, true];

        // a pre-existing bug, found while splitting the rows. this only ever called ventPanelListRefresh, which repaints
        // the selection colors and nothing else, and never touched the text. so flipping INV i:e flipped the variable,
        // the vent honored it, and the screen carried on saying whatever it said before, until you left the screen and
        // came back. you could toggle it three times and watch it not change.
        [4, if (!_inv) then {"ON"} else {"OFF"}] call ACME_fnc_ventPanelSetValue;
        ["ALERT", format ["Inv I:E alarm: %1", if (!_inv) then {"ON"} else {"OFF"}]] call ACME_fnc_ventLogbookAdd;

        playSound "ACME_VentClick";
        [] call ACME_fnc_ventPanelListRefresh;
    };
    // the other four are dialled values. a middle-click enters edit on this row and a middle-click again commits.
    private _ed = uiNamespace getVariable ["ACME_vent_editingAlert", -1];
    // committing this row, because it was being edited: log the new limit value.
    if (_ed == _row) then {
        private _lbl = ["Low RR", "High RR", "Press. limit", "Press. alert"] select _row;
        private _vv = switch (_row) do {
            case 0: { _tA getVariable ["ACME_vent_alertRRLow", 6] };
            case 1: { _tA getVariable ["ACME_vent_alertRRHigh", 25] };
            case 2: { _tA getVariable ["ACME_vent_alertPLimit", 40] };
            default { _tA getVariable ["ACME_vent_alertPAlert", 40] };
        };
        ["ALERT", format ["%1: %2", _lbl, _vv]] call ACME_fnc_ventLogbookAdd;
    };
    uiNamespace setVariable ["ACME_vent_editingAlert", (if (_ed == _row) then {-1} else {_row})];
    [] call ACME_fnc_ventPanelListRefresh;
};

// ALERTS page 2 of 2 and PARAMS: the same edit-by-row-index model and the same custom-screen highlight refresh.
// every row on page 2 is a dialled value, and on PARAMS only row 0, p.SUPPORT, is, while rows 1 to 3 route on to
// their sub-screens.
if (_screen == "alerts2") exitWith {
    private _t2 = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    private _ed = uiNamespace getVariable ["ACME_vent_editingAlert", -1];
    // committing this row, because it was being edited: log the new value.
    if (_ed == _row) then {
        private _lbl = ["Low TVe", "Leak", "Apnea time", "MV low", "MV high", "PEEP alert"] select _row;
        private _vv = switch (_row) do {
            case 0: { format ["%1%2", _t2 getVariable ["ACME_vent_alertLowTVe", 85], "%"] };
            case 1: { format ["%1%2", _t2 getVariable ["ACME_vent_alertLeak", 100], "%"] };
            case 2: { format ["%1 s", _t2 getVariable ["ACME_vent_alertApnea", 30]] };
            case 3: { format ["%1 L/min", (([_t2] call ACME_fnc_ventMVLimits) select 0) toFixed 1] };
            case 4: { format ["%1 L/min", (([_t2] call ACME_fnc_ventMVLimits) select 1) toFixed 1] };
            default { format ["%1 cmH2O", _t2 getVariable ["ACME_vent_alertPEEP", 5.0]] };
        };
        ["ALERT", format ["%1: %2", _lbl, _vv]] call ACME_fnc_ventLogbookAdd;
    };
    uiNamespace setVariable ["ACME_vent_editingAlert", (if (_ed == _row) then {-1} else {_row})];
    playSound "ACME_VentClick";
    [] call ACME_fnc_ventPanelListRefresh;
};

// PARAMS: rows 0 to 2, o2, i:e and PEEP, edit in place, so a middle-click enters edit on this row, the dial
// changes the value and a middle-click commits. rows 3 to 5, VENT. MODE, PAT. INT. and PAT. WEIGHT, navigate to
// their sub-screen, with a flag so the sub-screen returns here when you pick something instead of dumping you on
// the live screen.
if (_screen == "params") exitWith {
    private _nav = uiNamespace getVariable ["ACME_vent_paramsNav", [false,false,false,false,false]];  // a safe fallback: never fire a sub-screen off a stale value.
    private _isNav = (_row < count _nav) && {_nav select _row};
    if (_isNav) then {
        playSound "ACME_VentClick";
        uiNamespace setVariable ["ACME_vent_editingParam", -1];
        uiNamespace setVariable ["ACME_vent_paramReturn", true];  // a sub-screen, so come back to PARAMS.
        // page 2 is exactly the three sub-screen rows, in order.
        switch (_row) do {
            case 0: { ["mode"] call ACME_fnc_ventPanelShowScreen; };
            case 1: { ["interface"] call ACME_fnc_ventPanelShowScreen; };
            case 2: { ["weight"] call ACME_fnc_ventPanelShowScreen; };
        };
    } else {
        // in-place editable, so toggle edit on this row.
        private _ed = uiNamespace getVariable ["ACME_vent_editingParam", -1];
        // committing this row, because it was being edited: log the new value.
        if (_ed == _row) then {
            private _tP2 = uiNamespace getVariable ["ACME_vent_target", ACE_player];
            private _entry = switch (_row) do {
                case 0: { format ["O2 enrichment: %1%2", (if (isNull _tP2) then {uiNamespace getVariable ["ACME_vent_fio2", 21]} else {_tP2 getVariable ["ACME_vent_fio2", 21]}), "%"] };
                case 1: { format ["I:E ratio: %1", [(if (isNull _tP2) then {2.0} else {_tP2 getVariable ["ACME_vent_ie", 2.0]})] call ACME_fnc_ventFormatIE] };
                case 2: { format ["PEEP: %1 cmH2O", (if (isNull _tP2) then {5} else {_tP2 getVariable ["ACME_vent_peep", 5]})] };
                case 3: { format ["Pressure support: %1 cmH2O", (if (isNull _tP2) then {10} else {_tP2 getVariable ["ACME_vent_psup", 10]})] };
                default { format ["Trigger sensitivity: %1", (missionNamespace getVariable ["ACME_vent_trigSensCmH2O", -2])] };
            };
            ["USER", _entry] call ACME_fnc_ventLogbookAdd;
        };
        uiNamespace setVariable ["ACME_vent_editingParam", (if (_ed == _row) then {-1} else {_row})];
        [] call ACME_fnc_ventPanelListRefresh;
    };
};

if (_screen == "o2") exitWith {
    private _ed = uiNamespace getVariable ["ACME_vent_editingFio2", false];
    uiNamespace setVariable ["ACME_vent_editingFio2", !_ed];
    [] call ACME_fnc_ventPanelListRefresh;
};

// ADV. SETTINGS: BRIGHTNESS, ALARM VOLUME and TECH MODE, which is the main MENU into ADV SETTINGS level of the
// manual. _row is the real dial position, unlike the branch this replaced.
if (_screen == "advset") exitWith {
    switch (_row) do {
        // brightness and volume open as popups over the current screen rather than as screens of their own, because both
        // change something you are judging while you set it, so the panel behind has to stay visible.
        case 0: { ["brightness"] call ACME_fnc_ventLevelWindow; };
        case 1: { ["alarmvol"]   call ACME_fnc_ventLevelWindow; };
        case 2: { ["ventdisp"]   call ACME_fnc_ventPanelShowScreen; };
        case 3: { ["tech"]       call ACME_fnc_ventPanelShowScreen; };
    };
};

// VENT. DISPLAY: pick which tidal volume the live readout reports, then go back where you came from.
if (_screen == "ventdisp") exitWith {
    uiNamespace setVariable ["ACME_vent_dispType", (["VTI","VTE"] select (_row min 1))];
    ["advset"] call ACME_fnc_ventPanelShowScreen;
};

// every other screen with rows: activating a row commits and advances, in setup, or acts, in menu, params and
// tech.
["confirm"] call ACME_fnc_ventPanelNavClick;
