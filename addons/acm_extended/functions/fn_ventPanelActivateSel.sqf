// activate whatever the unified selection index, selidx, currently points at, on a list or menu screen. if the
// index is within the row range it activates that row, through ventPanelListClick, and if it is in the strip
// range it activates that strip button, through ventPanelStripClick. this is what middle-click calls, as the
// primary select.
// there is a debounce. both a control-level and a display-level MouseButtonDown handler can fire for one physical
// click, so a second activation within a short window is ignored, which prevents double-advancing screens.
// the controls are on the front. with the device turned round the operator is pressing the power button or the
// battery hatch, and this function must not also run the logic of the front screen underneath them. it used to:
// the select key fired this, it acted on whatever screen the machine had been left on, and pressing the battery
// hatch produced the WEIGHT screen's refusal that only 70 kg is selectable, with no way out of it.
// the two reverse controls carry their own ButtonClick handlers and are unaffected by this exit.
if (uiNamespace getVariable ["ACME_vent_flipped", false]) exitWith {
    // a middle click works the back too. the whole panel is operated with the middle button, so the power button and
    // the battery hatch answer to the same press rather than being the only two things on the device that need a
    // left click. the zones are tested against the cursor here, in the same canvas fractions the art uses, instead
    // of leaning on ButtonClick, which only ever fires on left.
    (uiNamespace getVariable ["ACME_vent_faceRect", [0,0,1,1]]) params ["_fx","_fy","_fw","_fh"];
    private _mp = getMousePosition;
    private _mx = _mp select 0; private _my = _mp select 1;
    private _in = {
        params ["_x0","_x1","_y0","_y1"];
        (_mx >= (_fx + _fw*_x0)) && {_mx <= (_fx + _fw*_x1)}
          && {_my >= (_fy + _fh*_y0)} && {_my <= (_fy + _fh*_y1)}
    };
    if ([0.4697, 0.8975, 0.5127, 0.6309] call _in) exitWith { ["swap"]  call ACME_fnc_ventFlip; };
    if ([0.7588, 0.8408, 0.4023, 0.4844] call _in) exitWith { ["power"] call ACME_fnc_ventFlip; };
};
// a dead machine has nothing to activate either.
if !(uiNamespace getVariable ["ACME_vent_powered", false]) exitWith {};


private _now = diag_tickTime;
private _lastAct = uiNamespace getVariable ["ACME_vent_lastActivate", -1];
if (_lastAct >= 0 && {(_now - _lastAct) < 0.15}) exitWith {};
uiNamespace setVariable ["ACME_vent_lastActivate", _now];

private _screen = uiNamespace getVariable ["ACME_vent_screen", "live"];
private _n = uiNamespace getVariable ["ACME_vent_listCount", 0];
private _selIdx = uiNamespace getVariable ["ACME_vent_selIdx", 0];

// an open level popup takes precedence over everything. its only control is ok, so any activate confirms and
// closes. the level is already committed live by the dial, so there is nothing to write here.
if (uiNamespace getVariable ["ACME_vent_lvlWinOpen", false]) exitWith {
    playSound "ACME_VentClick";
    ["close"] call ACME_fnc_ventLevelWindow;
    ["advset"] call ACME_fnc_ventPanelShowScreen;
};

// an open alarm window takes precedence. a middle-click fires the selected button: x, at 0, silences and closes,
// and next, at 1, pages to the next alarm. this is what makes the window actually operable on a dial-only
// device.
if (uiNamespace getVariable ["ACME_vent_alarmWinOpen", false]) exitWith {
    playSound "ACME_VentClick";
    private _asel = uiNamespace getVariable ["ACME_vent_alarmSel", 0];
    if (_asel == 1) then {
        [true] call ACME_fnc_ventAlarmWindow;  // next: page.
    } else {
        [] call ACME_fnc_ventAlarmSilence;  // x: silence and close.
        uiNamespace setVariable ["ACME_vent_alarmWinOpen", false];
    };
};
// note that the selftest screen has no branch below, so a middle-click is intentionally inert during the roughly
// 8 s power-on self-test. that is expected rather than a fault.

// note that every list-style screen must be in this list, or a middle-click is a silent no-op on it and the
// operator cannot select anything or back out. that is exactly what happened to alerts, alerts2, ie and peep:
// they were built, they rendered, they dialled, and the select button did nothing at all.
// the ADV SETTINGS rows are routed through ventPanelListClick with every other list screen, so the nav chevrons on
// it stay live. it used to have its own branch here that read ACME_vent_sel, which is the field selector of the
// live screen and holds a string, none, bpm or vt, switched against numeric cases. nothing ever matched, and the
// early exit also killed home and BACK on this screen.

if (_screen in ["weight","mode","interface","connect","menu","params","advset","ventdisp","tech","tech2","alerts","alerts2","ie","peep"]) exitWith {
    if (_selIdx < _n) then {
        [_selIdx] call ACME_fnc_ventPanelListClick;
    } else {
        // a strip position is a visible nav chevron, so fire its action: confirm, home, back or next.
        private _navList = uiNamespace getVariable ["ACME_vent_navList", []];
        private _navIdx = _selIdx - _n;
        if (_navIdx >= 0 && {_navIdx < count _navList}) then {
            playSound "ACME_VentClick";
            [((_navList select _navIdx) select 0)] call ACME_fnc_ventPanelNavClick;
        };
    };
};

if (_screen == "o2") exitWith {
    if (((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])})) exitWith {
        ["params"] call ACME_fnc_ventPanelShowScreen;
    };
    // the dial map: 0 is the OXYGEN value, where a middle-click toggles edit, and 1 is BACK. while editing, the dial
    // changes the value, which the knob handles, and a middle-click commits by toggling edit off.
    playSound "ACME_VentClick";
    private _editing = uiNamespace getVariable ["ACME_vent_editingFio2", false];
    if (_editing || {_selIdx == 0}) then {
        uiNamespace setVariable ["ACME_vent_editingFio2", !_editing];
        ["o2"] call ACME_fnc_ventPanelShowScreen;  // rebuild with the new edit highlight.
    } else {
        ["back"] call ACME_fnc_ventPanelNavClick;
    };
};

if (_screen == "live") exitWith {
    private _nFields = 2;
    if (_selIdx < _nFields) then {
        [["bpm","vt"] select _selIdx] call ACME_fnc_ventPanelFieldClick;
    } else {
        [_selIdx - _nFields] call ACME_fnc_ventPanelStripClick;
    };
};

if (_screen == "graph") exitWith {
    // dial position 2 is BACK, so exit to the live screen. positions 0 and 1, PRESSURE and FLOW, only view and take no
    // action.
    if (_selIdx == 2) then {
        playSound "ACME_VentClick";
        ["back"] call ACME_fnc_ventPanelNavClick;
    };
};

if (_screen == "logbook") exitWith {
    // the dial map: 0 is next, which is page down, and 1 is BACK. single-page logbooks pin selidx to 1, BACK, so a
    // middle-click always exits.
    playSound "ACME_VentClick";
    if (_selIdx == 0 && {(uiNamespace getVariable ["ACME_vent_logNPages", 1]) > 1}) then {
        ["next"] call ACME_fnc_ventPanelNavClick;
    } else {
        ["back"] call ACME_fnc_ventPanelNavClick;
    };
};
