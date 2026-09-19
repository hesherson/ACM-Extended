// the nav-strip actions, confirm, home, back and next, that drive the setup flow and menu navigation.
// the flow order is weight, mode, interface, connect, live. home jumps to live once configured, or stays in the
// flow. back steps to the previous screen. confirm and next commit the current selection and advance. the
// selections are stored on the player, so they persist and are available to the later clinical wiring, where an
// interface of "INVASIVE" is the et-tube branch.
// the controls are on the front. with the device turned round the operator is pressing the power button or the
// battery hatch, and this function must not also run the logic of the front screen underneath them. it used to:
// the select key fired this, it acted on whatever screen the machine had been left on, and pressing the battery
// hatch produced the WEIGHT screen's refusal that only 70 kg is selectable, with no way out of it.
// the two reverse controls carry their own ButtonClick handlers and are unaffected by this exit.
if (uiNamespace getVariable ["ACME_vent_flipped", false]) exitWith {};
// a dead machine has nothing to activate either.
if !(uiNamespace getVariable ["ACME_vent_powered", false]) exitWith {};


params ["_action"];
if !([ACE_player, "ventilator", true] call ACME_fnc_procedureAllowed) exitWith {};
private _custodyTarget = uiNamespace getVariable ["ACME_vent_target", objNull];
if (!isNull _custodyTarget && {_custodyTarget isNotEqualTo ACE_player}
    && {!(_custodyTarget getVariable ["ACME_vent_onPatient", false]) || {_custodyTarget getVariable ["ACME_vent_recovering", false]}}) exitWith {};
private _vTgt = uiNamespace getVariable ["ACME_vent_target", ACE_player]; if (isNull _vTgt) then { _vTgt = ACE_player; };
playSound "ACME_VentClick";
private _screen = uiNamespace getVariable ["ACME_vent_screen", ""];
// A live addon-setting change may arrive before the panel tick rebuilds setup.
if (missionNamespace getVariable ["ACME_vent_simpleMode", false] && {_screen in ["weight", "mode", "interface", "o2", "ie", "peep"]}) exitWith {
    [_screen] call ACME_fnc_ventPanelShowScreen;
};
// the selection comes from the unified dial index, clamped to the row range for row-commit purposes.
private _n = uiNamespace getVariable ["ACME_vent_listCount", 0];
private _sel = (uiNamespace getVariable ["ACME_vent_selIdx", 0]) min ((_n - 1) max 0);

// commit the selection of the current screen to the player.
private _commit = {
    params ["_screen", "_sel"];
    switch (_screen) do {
        case "weight": {
            // 70 kg and above is the only functional weight, and the others are inert.
            // this fixes a bug. _sel above is the dial index clamped into the row range, and when the dial was parked on the
            // next chevron, at an index past the last row, that clamp pulled it back down onto the last row, which is
            // exactly the 70 kg entry. so hitting next always looked like a valid 70 kg selection and the screen advanced
            // on its own. it tests the raw dial index instead, so the operator must actually be on the 70 kg row to
            // proceed.
            private _weights = [15,20,30,40,50,60,70];
            private _rawSel = uiNamespace getVariable ["ACME_vent_selIdx", 0];
            if (_rawSel != ((count _weights) - 1)) exitWith {
                uiNamespace setVariable ["ACME_vent_weightInert", true];  // signal: no advance.
            };
            _vTgt setVariable ["ACME_vent_weight", 70, true];
            uiNamespace setVariable ["ACME_vent_weightInert", false];
            ["USER", "Patient weight: 70 kg"] call ACME_fnc_ventLogbookAdd;
        };
        case "mode": {
            private _modes = ["SIMV VC PS","IMV VC (CPR)","SIMV PC","CPAP PS HF"];
            private _newMode = _modes select _sel;
            _vTgt setVariable ["ACME_vent_mode", _newMode, true];
            if (_newMode == "SIMV PC") then {
                private _peep = _vTgt getVariable ["ACME_vent_peep", 5];
                private _vt = _vTgt getVariable ["ACME_vent_vt", 500];
                private _floor = 11 max (_peep + 1);
                private _defaultPinsp = (round (8 + (12 * (_vt / 500)))) max _floor min 60;
                if (isNil {_vTgt getVariable "ACME_vent_pinsp"}) then { _vTgt setVariable ["ACME_vent_pinsp", _defaultPinsp, true]; };
                uiNamespace setVariable ["ACME_vent_pinsp", (_vTgt getVariable ["ACME_vent_pinsp", _defaultPinsp]) max _floor min 60];
            };
            ["USER", format ["Mode: %1", _newMode]] call ACME_fnc_ventLogbookAdd;
        };
        case "interface": {
            private _ifaces = ["INVASIVE","NON INVASIVE","NEBULIZER"];
            _vTgt setVariable ["ACME_vent_iface", _ifaces select _sel, true];
            ["USER", format ["Interface: %1", _ifaces select _sel]] call ACME_fnc_ventLogbookAdd;
            // the nebulizer is cosmetic in this sim, because only INVASIVE drives ventilation through the et tube. it still
            // selects and advances like the real device, and it does not ventilate.
            if (_sel == 2) then { ["Nebulizer mode is cosmetic in this trainer.", 1.5] call ace_common_fnc_displayTextStructured; };
        };
    };
};

switch (_action) do {
    case "next";
    case "confirm": {
        // next on the tech screen pages to tech2, through the down-chevron. on other screens next equals confirm.
        if (_action == "next" && {_screen == "tech"}) exitWith {
            ["tech2"] call ACME_fnc_ventPanelShowScreen;
        };
        // next on PARAMS flips between its two pages, wrapping, the same way the logbook pages. the six rows used to be
        // crammed onto one page in a smaller font, and they are three per page at the standard size now.
        if (_action == "next" && {_screen == "params"}) exitWith {
            uiNamespace setVariable ["ACME_vent_paramsPage", (((uiNamespace getVariable ["ACME_vent_paramsPage", 0]) + 1) % 2)];
            ["params"] call ACME_fnc_ventPanelShowScreen;
        };
        // next on the logbook pages down through the entries, wrapping at the end.
        if (_action == "next" && {_screen == "logbook"}) exitWith {
            private _np = uiNamespace getVariable ["ACME_vent_logNPages", 1];
            private _pg = (uiNamespace getVariable ["ACME_vent_logPage", 0]) + 1;
            if (_pg >= _np) then { _pg = 0; };
            uiNamespace setVariable ["ACME_vent_logPage", _pg];
            ["logbook"] call ACME_fnc_ventPanelShowScreen;
        };
        switch (_screen) do {
            case "alerts":    {
                // the down-chevron pages on to the status page. the row click handles the rows themselves.
                ["alerts2"] call ACME_fnc_ventPanelShowScreen;
            };
            case "alerts2":   { ["alerts"] call ACME_fnc_ventPanelShowScreen; };
            case "weight":    {
                [_screen, _sel] call _commit;
                if (uiNamespace getVariable ["ACME_vent_paramReturn", false] && {!(uiNamespace getVariable ["ACME_vent_weightInert", false])}) exitWith {
                    uiNamespace setVariable ["ACME_vent_paramReturn", false];
                    ["params"] call ACME_fnc_ventPanelShowScreen;  // it came from PARAMS, so go back there.
                };
                if !(uiNamespace getVariable ["ACME_vent_weightInert", false]) then { ["mode"] call ACME_fnc_ventPanelShowScreen; } else { ["Only 70 kg+ is selectable on this ventilator.", 1.5] call ace_common_fnc_displayTextStructured; };
            };
            case "mode":      {
                [_screen, _sel] call _commit;
                // opened from PARAMS. commit the mode and return to PARAMS, rather than the setup chain or live.
                if (uiNamespace getVariable ["ACME_vent_paramReturn", false]) exitWith {
                    uiNamespace setVariable ["ACME_vent_paramReturn", false];
                    ["params"] call ACME_fnc_ventPanelShowScreen;
                };
                // two different journeys arrive at this screen, and they should leave it differently.
                // in setup, no patient is connected yet. mode is one step in the preset chain, so continue down it: weight,
                // mode, interface, connect.
                // on the fly, a patient is already on the vent and the medic came here to change the mode mid-treatment.
                // switching to IMV vc (CPR) as compressions start is exactly this. they did not come to re-run the setup chain,
                // and routing them into INTERFACE and CONNECT would re-walk configuration on a patient who is already
                // configured. so commit and drop straight back to the live screen: the BPM, the VTe, the gauge, the machine
                // they were using.
                private _tgtM = uiNamespace getVariable ["ACME_vent_target", objNull];
                private _connM = (!isNull _tgtM) && {_tgtM getVariable ["ACME_vent_connected", false]};
                if (_connM) then {
                    ["live"] call ACME_fnc_ventPanelShowScreen;
                } else {
                    ["interface"] call ACME_fnc_ventPanelShowScreen;
                };
            };
            case "interface": {
                [_screen, _sel] call _commit;
                if (uiNamespace getVariable ["ACME_vent_paramReturn", false]) exitWith {
                    uiNamespace setVariable ["ACME_vent_paramReturn", false];
                    ["params"] call ACME_fnc_ventPanelShowScreen;  // it came from PARAMS, so go back there.
                };
                ["connect"] call ACME_fnc_ventPanelShowScreen;
            };
            case "connect":   {
                if !([ACE_player, "ventilator"] call ACME_fnc_procedureAllowed) exitWith {};
                if (!isNull _vTgt && {_vTgt getVariable ["ACME_vent_recovering", false]}) exitWith {};
                // Setup and START share the same physical circuit reach. Presetting
                // a carried machine does not connect a patient and needs no leash.
                private _preset = uiNamespace getVariable ["ACME_vent_presetMode", false];
                private _leash = missionNamespace getVariable ["ACME_vent_leash", 2.5];
                if (!_preset && {(objectParent ACE_player) isNotEqualTo (objectParent _vTgt)
                    || {(ACE_player distance _vTgt) > _leash}}) exitWith {
                    ["Out of range of the patient. Move closer to connect the circuit.", 2.5] call ace_common_fnc_displayTextStructured;
                };
                // with a patient connected, mark configured and connected, which is running, register into the circulation loop
                // so the vent-drive tick runs on them, then go live.
                _vTgt setVariable ["ACME_vent_configured", true, true];
                // never connect a circuit to the medic. presetting configures the machine and does not attach it to a chest.
                // this is precisely the line that used to make you your own ventilated patient.
                if (uiNamespace getVariable ["ACME_vent_presetMode", false]) exitWith {
                    ["Machine configured. Connect it on a casualty.", 2] call ace_common_fnc_displayTextStructured;
                    ["menu"] call ACME_fnc_ventPanelShowScreen;
                };
                _vTgt setVariable ["ACME_vent_connected", true, true];
                _vTgt setVariable ["ACME_vent_operator", ACE_player, true];  // tie the circuit to this medic, as the leash origin.
                if (!isNil "ACME_circ_activePatients") then { ACME_circ_activePatients pushBackUnique _vTgt; };
                ["live"] call ACME_fnc_ventPanelShowScreen;
            };
            case "menu": {
                switch (_sel) do {
                    case 0: {  // the STOP and START VENT toggle.
                        private _running = _vTgt getVariable ["ACME_vent_connected", false];
                        if (_running) then {
                            // STOP VENT. fully halt the stage-3 vent drive on the patient. the drive tick releases the BVM vars next pass,
                            // because connected is now false.
                            _vTgt setVariable ["ACME_vent_connected", false, true];
                            ["USER", "Ventilation stopped"] call ACME_fnc_ventLogbookAdd;
                            ["Ventilation stopped.", 1.5] call ace_common_fnc_displayTextStructured;
                        } else {
                            // START VENT. resume driving the patient, who is still configured and intubated.
                            if !([ACE_player, "ventilator"] call ACME_fnc_procedureAllowed) exitWith {};
                            // never connect a circuit to the medic. presetting configures the machine and does not attach it to a chest.
                            // this is precisely the line that used to make you your own ventilated patient.
                if (uiNamespace getVariable ["ACME_vent_presetMode", false]) exitWith {
                    ["Machine configured. Connect it on a casualty.", 2] call ace_common_fnc_displayTextStructured;
                    ["menu"] call ACME_fnc_ventPanelShowScreen;
                };
                // the leash guard. you cannot start ventilating a patient you are not next to, because the circuit only reaches
                // so far. this is the fix for stopping the vent, walking 50 m into a vehicle, hitting START and having it run
                // again. START now checks you are actually within circuit range of the casualty, and in the same vehicle,
                // before it re-ties the machine to them.
                private _leash = missionNamespace getVariable ["ACME_vent_leash", 2.5];
                if (isNull _vTgt
                    || {(objectParent ACE_player) isNotEqualTo (objectParent _vTgt)}
                    || {(ACE_player distance _vTgt) > _leash}) exitWith {
                    ["Out of range of the patient. Move closer to connect the circuit.", 2.5] call ace_common_fnc_displayTextStructured;
                    ["menu"] call ACME_fnc_ventPanelShowScreen;
                };
                _vTgt setVariable ["ACME_vent_connected", true, true];
                _vTgt setVariable ["ACME_vent_operator", ACE_player, true];  // tie, or re-tie, the circuit to this medic.
                            if (!isNil "ACME_circ_activePatients") then { ACME_circ_activePatients pushBackUnique _vTgt; };
                            ["USER", "Ventilation started"] call ACME_fnc_ventLogbookAdd;
                            ["Ventilation started.", 1.5] call ace_common_fnc_displayTextStructured;
                        };
                        ["live"] call ACME_fnc_ventPanelShowScreen;
                    };
                    case 1: {  // NEW PATIENT.
                        // gray in the manual. a full reset is not something you do to a machine that is currently ventilating somebody,
                        // so it is refused until ventilation is stopped.
                        if !(["gray", "NEW PATIENT"] call ACME_fnc_ventItemGate) exitWith {};
                        // a full reset. stop ventilation, clear all config, re-arm boot and restart the flow.
                        ["USER", "New patient (reset)"] call ACME_fnc_ventLogbookAdd;
                        _vTgt setVariable ["ACME_vent_configured", false, true];
                        _vTgt setVariable ["ACME_vent_connected", false, true];
                        _vTgt setVariable ["ACME_vent_driving", false, true];
                        ACE_player setVariable ["ACME_vent_booted", false, true];
                        ["weight"] call ACME_fnc_ventPanelShowScreen;  // restart the flow.
                    };
                    case 2: { uiNamespace setVariable ["ACME_vent_paramReturn", false]; ["params"] call ACME_fnc_ventPanelShowScreen; };  // VENT. PARAMS.
                    case 3: { ["alerts"] call ACME_fnc_ventPanelShowScreen; };  // ALERT SETTINGS.
                    case 4: { ["advset"] call ACME_fnc_ventPanelShowScreen; };  // ADV. SETTINGS opens its own screen, with BRIGHTNESS, ALARM VOLUME and TECH MODE, per the manual.
                };
            };
            case "tech": {
                // TECH page 1, with the manual's colors enforced. CALIBRATION is red, so it is password protected and not
                // available while ventilating. SELF TEST is gray, so it is not available while ventilating. the rest are plain.
                // row 4 is LOGBOOK and opens the real logbook, and the others remain display-only stubs, and they now refuse for
                // the right reason rather than being uniformly inert.
                switch (_sel) do {
                    case 1: { if (["red", "CALIBRATION"] call ACME_fnc_ventItemGate) then {
                                  ["Calibration is display-only in this build.", 1.5] call ace_common_fnc_displayTextStructured;
                              }; };
                    case 3: { if (["gray", "SELF TEST"] call ACME_fnc_ventItemGate) then {
                                  uiNamespace setVariable ["ACME_vent_stStep", 0];
                                  ["selftest"] call ACME_fnc_ventPanelShowScreen;
                              }; };
                    case 4: {
                        uiNamespace setVariable ["ACME_vent_logPage", 0];
                        ["logbook"] call ACME_fnc_ventPanelShowScreen;
                    };
                    default {
                        ["This technician screen is display-only in this build.", 1.5] call ace_common_fnc_displayTextStructured;
                    };
                };
            };
            case "tech2": {
                // sw UPDATE, row 2, is red in the manual: password protected and not available while ventilating.
                if (_sel == 2) then {
                    if (["red", "SW UPDATE"] call ACME_fnc_ventItemGate) then {
                        ["Software update is display-only in this build.", 1.5] call ace_common_fnc_displayTextStructured;
                    };
                } else {
                    ["This technician screen is display-only in this build.", 1.5] call ace_common_fnc_displayTextStructured;
                };
            };
            case "params": {
                // fn_ventpanellistclick handles row activation on PARAMS, deciding between editing in place and opening a
                // sub-screen. there is no confirm chevron on this page, so nothing routes from here.
            };
        };
    };
    case "back": {
        // on PARAMS page 2, BACK steps to page 1 first rather than leaving the screen outright.
        if (_screen == "params" && {(uiNamespace getVariable ["ACME_vent_paramsPage", 0]) > 0}) exitWith {
            uiNamespace setVariable ["ACME_vent_paramsPage", 0];
            ["params"] call ACME_fnc_ventPanelShowScreen;
        };
        // if we drilled into a sub-screen from PARAMS, backing out returns to PARAMS whatever the default back route of
        // that screen is, and clears the flag. choosing nothing still comes home.
        if (uiNamespace getVariable ["ACME_vent_paramReturn", false] && {_screen in ["mode","interface","weight"]}) exitWith {
            uiNamespace setVariable ["ACME_vent_paramReturn", false];
            ["params"] call ACME_fnc_ventPanelShowScreen;
        };
        switch (_screen) do {
            case "mode":      {
                // backing out goes where you came from, derived from the connection. a connected patient means this was an
                // on-the-fly change from a running vent, so it goes back to live, and no patient means the setup chain, so it
                // goes back to weight. it is the same rule as the confirm route above, for the same reason.
                private _tgtB = uiNamespace getVariable ["ACME_vent_target", objNull];
                if ((!isNull _tgtB) && {_tgtB getVariable ["ACME_vent_connected", false]}) then {
                    ["live"] call ACME_fnc_ventPanelShowScreen;
                } else {
                    ["weight"] call ACME_fnc_ventPanelShowScreen;
                };
            };
            case "interface": { ["mode"] call ACME_fnc_ventPanelShowScreen; };
            case "connect":   { [if (missionNamespace getVariable ["ACME_vent_simpleMode", false]) then {"menu"} else {"interface"}] call ACME_fnc_ventPanelShowScreen; };
            case "menu":      { ["live"] call ACME_fnc_ventPanelShowScreen; };
            case "params":    { uiNamespace setVariable ["ACME_vent_editingParam", -1]; ["menu"] call ACME_fnc_ventPanelShowScreen; };
            case "o2":        { uiNamespace setVariable ["ACME_vent_editingFio2", false]; ["params"] call ACME_fnc_ventPanelShowScreen; };
            case "ie":        { uiNamespace setVariable ["ACME_vent_editingIE", false]; ["params"] call ACME_fnc_ventPanelShowScreen; };
            case "peep":      { uiNamespace setVariable ["ACME_vent_editingPeep", false]; ["params"] call ACME_fnc_ventPanelShowScreen; };
            case "alerts":    { uiNamespace setVariable ["ACME_vent_editingAlert", -1]; ["menu"] call ACME_fnc_ventPanelShowScreen; };
            case "alerts2":   { ["alerts"] call ACME_fnc_ventPanelShowScreen; };
            // ADV. SETTINGS and everything under it. without these three the switch fell through to its default, which is
            // live, so backing out of any of them threw the operator all the way to the main screen instead of up one
            // level.
            // TECH MODE is reached from ADV. SETTINGS rather than from MENU. the menu is START VENT, NEW PATIENT, VENT.
            // PARAMS, ALERT SETTINGS and ADV. SETTINGS, and TECH sits inside the last of those. backing out of it to MENU
            // skipped a level, even though it did not look like a bug from the main screen.
            case "advset":    { ["menu"]   call ACME_fnc_ventPanelShowScreen; };
            case "ventdisp":  { ["advset"] call ACME_fnc_ventPanelShowScreen; };
            case "tech":      { ["advset"] call ACME_fnc_ventPanelShowScreen; };
            case "tech2":     { ["tech"] call ACME_fnc_ventPanelShowScreen; };
            case "logbook":   { uiNamespace setVariable ["ACME_vent_logPage", 0]; ["tech"] call ACME_fnc_ventPanelShowScreen; };
            case "graph":     { ["live"] call ACME_fnc_ventPanelShowScreen; };
            default { ["live"] call ACME_fnc_ventPanelShowScreen; };
        };
    };
    case "home": {
        // home is the running ventilation screen. it is not the menu, because home on this device means the screen you
        // actually watch the patient on, the one carrying the BPM, mv, VTi and the pressure row. sending it to the menu
        // made it a go-up-one-level key, which is what BACK is for. from any depth it lands on live in one press.
        uiNamespace setVariable ["ACME_vent_paramsPage", 0];
        uiNamespace setVariable ["ACME_vent_paramReturn", false];
        if (ACE_player getVariable ["ACME_vent_configured", false]) then {
            ["live"] call ACME_fnc_ventPanelShowScreen;
        } else {
            // nothing is configured yet, so there is no live screen to show. the menu is the only sensible landing.
            ["menu"] call ACME_fnc_ventPanelShowScreen;
        };
    };
};
