// screen router for the ventilator panel. it shows exactly one screen at a time, by populating the generic list
// controls, the title, rows and nav strip, or the live-parameters controls, and hiding the rest. the current
// screen is uinamespace "ACME_vent_screen". the screens are boot, weight, mode, interface, connect, live, menu
// and params. the setup flow runs weight, mode, interface, connect, live for every new patient.
// call it as [_screen] call ACME_fnc_ventPanelShowScreen.
params ["_screen"];
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};
// Simple delivery has no weight/mode/interface setup. Keep the saved advanced
// choices intact and go to the physical circuit connection instead.
private _simple = ((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {(!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false]) && {!([uiNamespace getVariable ["ACME_vent_target", objNull]] call ACME_fnc_ventMaskSelected)})});
if (_simple && {_screen in ["weight", "mode", "interface"]}) then {
    private _target = uiNamespace getVariable ["ACME_vent_target", objNull];
    _screen = if (!isNull _target && {_target getVariable ["ACME_vent_configured", false]}) then {"params"} else {"connect"};
    uiNamespace setVariable ["ACME_vent_paramReturn", false];
};
if (_simple && {_screen in ["o2", "ie", "peep"]}) then { _screen = "params"; };
uiNamespace setVariable ["ACME_vent_simpleShown", _simple];
uiNamespace setVariable ["ACME_vent_screen", _screen];
// remember it on the device, so reopening the panel, from the patient button or the self-interaction, which are
// the same machine, puts you back where you were instead of making you walk the whole flow again.
if (hasInterface && {!(_screen in ["boot","selftest"])}) then {
    ACE_player setVariable ["ACME_vent_lastScreen", _screen, false];
};
uiNamespace setVariable ["ACME_vent_listSel", 0];  // reset the row selection on each screen entry.
uiNamespace setVariable ["ACME_vent_selIdx", 0];  // reset the unified dial index on each screen entry.

// control groups.
private _liveCtrls = [87712,87767,87768,87720,87721,87722,87723,87724,87725,87726,87727,87730,87731,87732,87733,87734,87735,87736,87737,87738,87769,87774,87739,87759,87761,87762,87763,87764,87740,87741,87742,87743,87744,87745,87746,87747,87748,87749,87752,87753,87750,87751,87765];
private _listCtrls = [87780,87781,87782,87783,87784,87785,87786,87787,87790,87791,87792,87793,87794,87795,87796,87797,87754,87755,87756,87757];
private _graphCtrls = [87800,87801,87802];
private _navPairs = [[87790,87791],[87792,87793],[87794,87795],[87796,87797]];  // confirm, home, back and next.

// hide everything first. the title bar and the bottom bar stay visible as chrome on all screens.
{ (_dlg displayCtrl _x) ctrlShow false } forEach (_liveCtrls + _listCtrls + _graphCtrls);
// destroy any dynamic waveform bars from a previous graph view.
{ ctrlDelete _x } forEach (uiNamespace getVariable ["ACME_vent_graphBars", []]);
uiNamespace setVariable ["ACME_vent_graphBars", []];
// value fields are standalone ACME_VentBtn controls created by fn_ventpanelvaluefields, not graphbars riders, so
// they must be deleted here rather than only forgotten. clearing the registry alone would orphan the live
// controls: the next screen could not find them to tear them down, and they would hang over it forever. delete
// them, then clear.
{ if (!isNull _x) then { ctrlDelete _x; }; } forEach (uiNamespace getVariable ["ACME_vent_valFields", []]);
uiNamespace setVariable ["ACME_vent_valFields", []];

// screen definitions, as [titletext, rows[], navflags[confirm,home,back,next], prompttext]. rows is a list of
// display strings, and an empty rows list means a message screen, which uses prompttext.
// a screen change tears the level popup down. it is drawn over the screen, so a rebuilt screen would leave its
// controls orphaned on top of the new one. fn_ventlevelwindow re-opens it deliberately where that is wanted.
if (uiNamespace getVariable ["ACME_vent_lvlWinOpen", false]) then {
    { if (!isNull _x) then { ctrlDelete _x; }; } forEach (uiNamespace getVariable ["ACME_vent_lvlWin", []]);
    uiNamespace setVariable ["ACME_vent_lvlWin", []];
    uiNamespace setVariable ["ACME_vent_lvlWinOpen", false];
};

// locked trailing rows. a screen can declare that its last n rows are readouts rather than options, by setting
// ACME_vent_listLocked. they are drawn and excluded from listcount, so the dial steps over them and activate
// cannot reach them. it is cleared here, so a screen that never sets it cannot inherit one that did.
uiNamespace setVariable ["ACME_vent_listLocked", 0];

private _def = switch (_screen) do {
    // weight is a custom two-column grid, see fn_ventcustomlayout: 15, 20, 30 and 40 down column one, then 50, 60
    // and 70+ down column two, in exactly that dial order, then the tray. only 70+ commits, and the others hint.
    case "weight":    { ["WEIGHT", [], [false,true,false,true], ""] };
    // vent mode, matching the list of the real sparrow: SIMV vc ps, IMV vc (CPR), SIMV pc and CPAP ps.
    // IMV vc (CPR) is not a cosmetic entry. it is the only mode that ventilates correctly during compressions. see
    // fn_ventdrivetick for what it does and what every other mode costs you during an arrest.
    case "mode":      { ["VENT. MODE", ["SIMV VC PS","IMV VC (CPR)","SIMV PC","CPAP PS HF"], [false,true,true,false], ""] };
    case "interface": { ["PAT. INT.", ["INVASIVE","NON INVASIVE","NEBULIZER"], [false,true,true,false], ""] };
    case "connect":   { ["CONNECT", [], [true,true,true,false], "CONNECT PATIENT<br/>AND PRESS OK"] };
    case "menu":      {
        // the first item toggles: STOP VENT when running, START VENT when stopped.
        private _running = (uiNamespace getVariable ["ACME_vent_target", ACE_player]) getVariable ["ACME_vent_connected", false];
        private _startStop = if (_running) then { "STOP VENT" } else { "START VENT" };
        [ "MENU", [_startStop,"NEW PATIENT","VENT. PARAMS","ALERT SETTINGS","ADV. SETTINGS"], [false,true,true,false], "" ]
    };
    case "params":    {
        // params, page 1 of 2, and device-accurate: six right-aligned rows built by fn_ventcustomlayout. o2, i:e and
        // PEEP edit in place, so the dial changes the value on this very page. VENT. MODE, PAT. INT. and PAT. WEIGHT
        // open their sub-screens and return here. a params page that does not show you the params is a menu, and this
        // is a readout you can steer.
        uiNamespace setVariable ["ACME_vent_editingParam", -1];
        [format ["PARAMS  (%1/2)", (uiNamespace getVariable ["ACME_vent_paramsPage", 0]) + 1], [], [false,true,true,true], ""]
    };
    case "peep": {
        // PEEP. it is the single most therapeutic dial on this machine and the most dangerous one on an undecompressed
        // chest. it runs 0 to 20 cmH2O.
        private _tP = uiNamespace getVariable ["ACME_vent_target", ACE_player];
        private _pv = _tP getVariable ["ACME_vent_peep", 5];
        uiNamespace setVariable ["ACME_vent_editingPeep", false];
        [ "PEEP", [format ["PEEP   %1 cmH2O", _pv]], [false,true,true,false], "" ]
    };
    case "ie": {
        // i:e ratio. dial through the ladder, then middle-click to enter edit and to commit, exactly like o2.
        // the inverse steps, 2:1 and 3:1, are reachable only when INV i:e is on in the ALERTS screen, which is what
        // that toggle is for. an inverse ratio recruits a stiff lung and gas-traps a healthy one.
        private _tI2 = uiNamespace getVariable ["ACME_vent_target", ACE_player];
        private _ieV = _tI2 getVariable ["ACME_vent_ie", 2.0];
        uiNamespace setVariable ["ACME_vent_editingIE", false];
        [ "I:E RATIO", [format ["I:E   %1", [_ieV] call ACME_fnc_ventFormatIE]], [false,true,true,false], "" ]
    };
    case "alerts": {
        // alerts, page 1 of 2, and device-accurate: 6 < rr < 25 BPM on one line with both bounds editable, a PRESSURE
        // header, LIMIT and ALERT indented under it, and the INV i:e toggle. fn_ventcustomlayout builds it, and every
        // number is a registered value field, so the knob, commit and highlight machinery is the standard one. these
        // are not cosmetic: the rr bounds and the pressure ALERT drive fn_ventalarmtick directly, and the drive engine
        // enforces the pressure LIMIT.
        uiNamespace setVariable ["ACME_vent_editingAlert", -1];  // always enter the screen not editing.
        [ "ALERTS  (1/2)", [], [false,true,true,true], "" ]
    };
    case "alerts2": {
        // alerts, page 2 of 2, and device-accurate: LOW TVe, LEAK, APNEA t., the mv window on one line with both bounds
        // editable, and PEEP. it uses the same editingalert machinery as page 1 and the same standard painter.
        uiNamespace setVariable ["ACME_vent_editingAlert", -1];  // always enter the screen not editing.
        ["ALERTS  (2/2)", [], [false,true,true,false], ""]
    };
    case "o2":        {
        // o2 enrichment. it is a single value row driven exactly like the BPM field: middle-click the row to enter
        // edit, dial to change it between 21 and 100 percent, then middle-click again to commit. room air, at 21
        // percent, is the default.
        private _tgtO = uiNamespace getVariable ["ACME_vent_target", ACE_player];
        private _f = if (isNull _tgtO) then { uiNamespace getVariable ["ACME_vent_fio2", 21] } else { _tgtO getVariable ["ACME_vent_fio2", (uiNamespace getVariable ["ACME_vent_fio2", 21])] };
        // clamp on entry. a value saved before the 95 percent ceiling existed would otherwise display as unreachable,
        // with the dial only able to bring it down and never back.
        _f = (_f max 21) min 95;
        uiNamespace setVariable ["ACME_vent_fio2", _f];
        uiNamespace setVariable ["ACME_vent_editingFio2", false];  // always enter the screen not editing.
        [ "O2 ENRICH.", [format ["O2 ENRICHMENT   %1%2", _f, "%"]], [false,true,true,false], "" ]
    };
    case "advset":    {
        // main MENU and ADV SETTINGS, per the ventway manual. BRIGHTNESS, ALARM VOLUME and TECH MODE are siblings here.
        // tech was previously reached directly from MENU, which skipped this level entirely.
        [ "ADV. SETTINGS", ["BRIGHTNESS","ALARM VOLUME","VENT. DISPLAY","TECH MODE"], [false,true,true,false], "" ]
    };
    // VENT. DISPLAY. this is which tidal volume the live screen reports. VTi is what the machine delivered and VTe
    // is what came back out, and they are genuinely different numbers here, because fn_ventdrivetick derives VTi
    // from the mode and the lung compliance, and VTe from VTi minus leak. which one you want on the readout is a
    // real preference, so it is a setting rather than a fixed choice.
    // the BRIGHTNESS and ALARM VOLUME screens were removed here. both are popups now, drawn by fn_ventlevelwindow
    // over whatever screen you are on.
    case "ventdisp":  {
        private _dt = uiNamespace getVariable ["ACME_vent_dispType", "VTE"];
        [ "VENT. DISPLAY", ["VTI","VTE"], [false,true,true,false], "" ]
    };
    case "tech":      { ["TECH  (1/2)", ["SET TIME","CALIBRATION","WORK HOURS","SELF TEST","LOGBOOK"], [false,true,true,true], ""] };
    case "tech2":     {
        // altitude is a readout rather than an option: the real height above sea level, updated every time this screen
        // is drawn, and locked out of the selection so the dial steps over it. fn_altitudetrue is the same source the
        // altitude physiology model uses, so the number on the tech page and the number driving the pao2 of the
        // casualty can never disagree.
        // fn_altitudetrue takes the object whose altitude is wanted. the machine is on the casualty, so read theirs.
        // with no casualty bound, which is presetting a carried machine, read the medic holding it.
        private _altObj = uiNamespace getVariable ["ACME_vent_target", objNull];
        if (isNull _altObj) then { _altObj = ACE_player; };
        private _altM = round ([_altObj] call ACME_fnc_altitudeTrue);
        uiNamespace setVariable ["ACME_vent_listLocked", 1];
        ["TECH  (2/2)", ["EXPORT LOG","SW VERSION","SW UPDATE","SYSTEM MODE", format ["ALTITUDE  %1 M", _altM]], [false,true,true,false], ""]
    };
    // SELF TEST and LOGBOOK draw their own bodies and must not draw their own titles. each used to create a header
    // of its own, at 0.11 and 0.10 font against the standard 0.085, spanning the full screen width and therefore
    // running straight across the black block. declaring the title here routes both through the single title
    // control, so they inherit its size, its left pad and its lack of a shadow automatically.
    case "selftest":  { ["SELF TEST", [], [false,false,false,false], ""] };
    case "logbook":   { ["LOGBOOK",   [], [false,false,true,false], ""] };
    default { ["", [], [false,false,false,false], ""] };
};
// changing screen cancels any power-off hold in progress. the hold ui lives over the screen, and a bar left
// floating over a screen it no longer belongs to is worse than no bar at all.
[] call ACME_fnc_ventHoldClear;
uiNamespace setVariable ["ACME_vent_mmbDown", -1];

// which inlay, the square and the title.
// there are two inlays, and which one is up is decided by whether this screen has alarm triggers to show.
// the live screen uses ..._battery_cutout_w_trigger_ca.paa, the battery block plus the small trigger square.
// every other screen uses ..._battery_cutout_ca.paa, the battery block only.
// the power-on splash uses ..._menu_startup_inlay.paa, plain white, set in fn_ventpanelinit.
// measured off the art, screen-local, these are identical in both files except for the square:
// the battery block runs 0.0023 to 0.3264.
// the white bar runs 0.3287 to 1.0000, on the no-trigger inlay.
// the trigger square runs 0.3402 to 0.4230, on the with-trigger inlay only, and the white resumes at 0.4253.
// the square exists purely to give the alarm trigger letter somewhere to live, so it is wanted on the one screen
// that has alarms to report. both inlays carry the battery block, so the charge state stays visible on every
// screen, which is the thing that was missing before.
private _tgtI = uiNamespace getVariable ["ACME_vent_target", objNull];
private _liveConnected = (_screen == "live") && {!isNull _tgtI} && {_tgtI getVariable ["ACME_vent_connected", false]};
private _wantTrigger = (_screen == "live");

private _inlayC = _dlg displayCtrl 87702;
if (!isNull _inlayC) then {
    private _want = if (_wantTrigger) then {
        "\acm_extended\ui\vent\ventway_sparrow_robust_menu_inlay_battery_cutout_w_trigger_ca.paa"
    } else {
        "\acm_extended\ui\vent\ventway_sparrow_robust_menu_inlay_battery_cutout_ca.paa"
    };
    if ((uiNamespace getVariable ["ACME_vent_inlayCur", ""]) != _want) then {
        _inlayC ctrlSetText _want;  // on change only, because ctrlSetText is a texture reload.
        uiNamespace setVariable ["ACME_vent_inlayCur", _want];
    };
};

// the top-bar chrome follows the inlay.
// the battery, 87713, is shown always, because both inlays have the block it sits in.
// the alarm box, 87714, is shown only where the trigger square exists. drawn on an inlay without one it would
// sit on the white bar, which is how a red alarm ended up as a box floating beside the title.
(_dlg displayCtrl 87713) ctrlShow true;
(_dlg displayCtrl 87714) ctrlShow _wantTrigger;
(_dlg displayCtrl 87766) ctrlShow false;  // retired for good.

(uiNamespace getVariable ["ACME_vent_scrRect", [0,0,1,1]]) params ["_tsx","_tsy","_tsw","_tsh"];

_def params ["_title", "_rows", "_nav", "_prompt"];

// the title.
// there is one padding value, applied to whichever inlay is up. the field is no longer a hand-tuned number per
// inlay. it is the point where the white of that inlay actually begins, plus the same pad either side. both are
// measured off the art rather than estimated:
// with the trigger, the white resumes at 0.4253, past the trigger square.
// with no trigger, the white starts at 0.3287, past the battery block.
// the left edge is guaranteed by alignment rather than by arithmetic. the title control is left-aligned, at
// style 0 in config, so its first glyph sits exactly _titlepad past where the white begins, on every inlay and
// whatever the title says. centring plus a width estimate was the previous approach and it kept failing:
// measuring a 13-character title twice gave 0.47 and 0.59 screen widths per character per unit of font height,
// so any single constant was going to bury something.
// the auto-fit is kept and now only protects the right edge from clipping. 0.60 is the larger of the two
// measured factors, so it errs toward shrinking slightly early rather than clipping.
// there is one placement for every title, on every screen and both inlays, rather than two fields keyed to which
// inlay is up. it is the same x, the same width and the same size everywhere.
// x is set past the widest obstruction either inlay has, which is the with-trigger square ending at 0.4230, so
// a title cannot reach black on either one. measured off the art:
// the battery block runs 0.0000 to 0.3264 on both inlays.
// the trigger square runs 0.3402 to 0.4230 on the with-trigger inlay only.
// the font matches the MENU rows near enough. rows are 0.13 and titles are 0.125, a hair under, which is what a
// title bar wants against the list beneath it.
// the character-width factor was re-derived from the menu rows themselves rather than from a single title
// measurement, because the earlier figure was badly off and it is what kept the titles small. measured off a
// screenshot at font 0.13:
// ALARM VOLUME is 12 characters and 0.478 wide, so 0.306 per char per unit font.
// TECH MODE is 9 characters and 0.345 wide, so 0.295.
// VENT. DISPLAY is 13 characters and 0.443 wide, so 0.262, because of narrow glyphs, a period and a space.
// so it is about 0.31 for a normal mix, against the 0.40 previously assumed. at 0.125 the longest title in the
// addon is 13 times 0.31 times 0.125, which is 0.504, inside the 0.545 field with room to spare, and it still
// fits at the worst measured factor. this is the size every title uses, the mode on the live screen
// included.
#define VENT_TITLE_X    0.450
#define VENT_TITLE_W    0.545
#define VENT_TITLE_FONT 0.125
// the live mode title, SIMV vc ps, is placed and scaled correctly and is left exactly as it is. every other
// title sits on the inlay without the trigger square, which frees the space that square occupies, so they move
// further right into it. it is the same font and the same right edge, with a later start.
// they are left aligned off the battery block. every screen except the live one uses the inlay without the
// trigger square, so the only thing in the way is the battery block, which ends at 0.3264. the title starts a
// pad past that at 0.345 and runs to the right edge, which is a lot further left than it was and gives the
// longest title 0.650 of field for the 0.504 it needs.
#define VENT_TITLE_X2   0.345
#define VENT_TITLE_W2   0.650

private _tFieldX = VENT_TITLE_X;
private _tFieldW = VENT_TITLE_W;

private _tCtl = _dlg displayCtrl 87712;
if (!isNull _tCtl) then {
    // one size, every title, every screen. the auto-fit that used to live here is removed, because it sized each
    // title to its own field, so screens ended up with visibly different title sizes, and its width estimate was
    // unreliable in both directions anyway. a single constant is what all the same actually means.
    _tCtl ctrlSetFontHeight (_tsh * VENT_TITLE_FONT);
    _tCtl ctrlSetPosition [_tsx + _tsw * _tFieldX, _tsy + _tsh * 0.004, _tsw * _tFieldW, _tsh * 0.125];
    _tCtl ctrlCommit 0;
};

// Custom screens own their value fields. Generic lists have no value-pair producer.

if (_screen == "live") exitWith {
    // live parameters screen. it shows the live controls and refreshes the values and the selection colors. the
    // positional loop in postinit handles the running-vent sound, which plays near any actively ventilated patient,
    // rather than this function.
    { (_dlg displayCtrl _x) ctrlShow true } forEach _liveCtrls;
    // the title shows the actual selected mode. it was hardcoded to SIMV vc ps.
    private _tgtM = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    private _modeM = if (isNull _tgtM) then { "SIMV VC PS" } else { _tgtM getVariable ["ACME_vent_mode", "SIMV VC PS"] };
    // spaced out so the mode spans the width of the bar, from the alarm box to the end of the inlay, the way the
    // device prints it. it is done by widening the gaps between the words rather than by stretching the glyphs:
    // each single space becomes three, which is what turns "SIMV VC PS" into a title that fills its strip.
    (_dlg displayCtrl 87712) ctrlSetText ([_modeM] call ACME_fnc_ventModeTitle);
    [] call ACME_fnc_ventPanelRefresh;
    [] call ACME_fnc_ventPanelLiveRefresh;
};

if (_screen == "selftest") exitWith {
    // automatic power-on self-test. it has a SELF TEST header, a solid dot-ring that fills clockwise in discrete
    // steps of about 12.5 percent, at 12, 25, 37 and so on to 100, like the real device, and a centerd percentage.
    // the tick drives the stepping and the vent sound, and routes to ACME_vent_postSelfTest at 100 percent. the
    // controls are created dynamically and stored under ACME_vent_graphBars, so the router tears them down.
    private _sr = uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]];
    _sr params ["_sx","_sy","_sw","_sh"];
    private _dyn = [];
    // the title. it went missing when this screen stopped drawing its own header, because the shared title control
    // is written near the bottom of this function, well past the exitwith above, so a screen that returns early
    // never reaches it. SELF TEST was declared correctly in the screen table and simply never got applied.
    // it is drawn here instead, centerd, and on exactly the field, padding and font size every other title uses, so
    // it lines up with them rather than being its own size in its own place like the header that was removed.
    private _stT = _dlg ctrlCreate ["ACME_VentTextC", -1];
    _stT ctrlSetPosition [_sx + _sw*VENT_TITLE_X2, _sy + _sh*0.004, _sw*VENT_TITLE_W2, _sh*0.125];
    _stT ctrlSetFontHeight (_sh * VENT_TITLE_FONT);
    _stT ctrlSetText "SELF TEST";
    _stT ctrlSetTextColor ([[0.05, 0.05, 0.05, 1]] call ACME_fnc_ventColor);  // dark ink on the white bar.
    _stT ctrlSetBackgroundColor [0,0,0,0];
    _stT ctrlCommit 0; _stT ctrlShow true;
    _dyn pushBack _stT;
    // dense touching ring segments, circular in pixels through pixelw and pixelh, so it reads as a solid ring. it is
    // centerd in the window between the white bars of the inlay, 0.132 to 0.873 with a midline of 0.5025, on both
    // axes.
    private _cx = _sx + _sw*0.5; private _cy = _sy + _sh*0.5025;
    private _rY = _sh*0.30; private _rX = _rY * (pixelW / pixelH);
    private _segY = _sh*0.05; private _segX = _segY * (pixelW / pixelH);
    private _N = 64;
    private _dots = [];
    for "_i" from 0 to (_N - 1) do {
        private _ang = -90 + (_i / _N) * 360;
        private _d = _dlg ctrlCreate ["RscText", -1];
        _d ctrlSetPosition [_cx + _rX*(cos _ang) - _segX/2, _cy + _rY*(sin _ang) - _segY/2, _segX, _segY];
        _d ctrlSetBackgroundColor ([[0.14,0.18,0.24,1]] call ACME_fnc_ventColor);
        _d ctrlCommit 0; _d ctrlShow true;
        _dots pushBack _d; _dyn pushBack _d;
    };
    uiNamespace setVariable ["ACME_vent_stDots", _dots];
    private _pct = _dlg ctrlCreate ["RscStructuredText", -1];
    _pct ctrlSetPosition [_cx - _rX*0.85, _cy - _rY*0.30, _rX*1.7, _rY*0.6];
    _pct ctrlSetFontHeight (_sh * 0.16);
    _pct ctrlSetStructuredText parseText "<t align='center' color='#e6f2ff'>0%</t>";
    _pct ctrlCommit 0; _pct ctrlShow true;
    uiNamespace setVariable ["ACME_vent_stPct", _pct];
    _dyn pushBack _pct;
    uiNamespace setVariable ["ACME_vent_graphBars", _dyn];  // the router cleanup path.
    // stepped progress state, in 8 discrete steps. the startup clip is armed to play on the first tick of the
    // screen by clearing its once-guard, and the tick plays it exactly once per self-test.
    uiNamespace setVariable ["ACME_vent_stStep", 0];
    // the step interval is derived from the audio rather than randomised. the ring used to advance every 0.8 to 1.3
    // s, so eight steps landed anywhere between 6.9 and 10.9 s, while the queued audio, startup then running,
    // always runs a fixed 8.04 s. on a fast test the spool-down therefore fired with well over a second of the
    // running hum still sounding, and playSound3D cannot be stopped once started. pacing the ring off the clip
    // lengths means it reaches 100 percent just as the hum ends, so the shutdown lands on silence instead of on top
    // of it.
private _stFirst = 0.5;
// the total audible length of the queued pair, accounting for the crossfade. the running clip starts one overlap
// before the startup clip ends, so the pair finishes an overlap earlier than their raw sum. the ring is paced to
// land on 100 percent exactly there, so the spool-down begins as the hum ends rather than over the top of it.
private _stOv = missionNamespace getVariable ["ACME_vent_sndOverlap", 0.11];
private _stAudio = (missionNamespace getVariable ["ACME_vent_startupSndLen", 2.324])
                 + (missionNamespace getVariable ["ACME_vent_runningSndLen", 5.721])
                 - _stOv;
uiNamespace setVariable ["ACME_vent_stStepInt", (((_stAudio - _stFirst) / 8) max 0.25)];
uiNamespace setVariable ["ACME_vent_stStepNextT", diag_tickTime + _stFirst];
    uiNamespace setVariable ["ACME_vent_stStartupPlayed", false];  // re-arm the startup clip for this self-test,
    uiNamespace setVariable ["ACME_vent_stRunPlayed", false];  // the running clip that follows it,
    uiNamespace setVariable ["ACME_vent_stShutPlayed", false];  // and the spool-down fired at 100 percent.

    [] call ACME_fnc_ventFaceGate;  // exitwith skips the gate at the end of this function.
};

if (_screen == "logbook") exitWith {
    // the logbook. it is a chronological record of what the machine did: the alarms and alerts that fired, and the
    // operator's own interactions, such as settings changed and actions taken. the newest is at the top. it reads
    // from the per-device buffer on the operator, see fn_ventlogbookadd, pages through it with the dial, and steps
    // back to the tech screen. it is read-only, because a logbook you can edit is not a logbook.
    private _sr = uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]];
    _sr params ["_sx","_sy","_sw","_sh"];
    private _dyn = [];

    // the standard title control draws the title, and this screen contributes only its body.

    private _log = ACE_player getVariable ["ACME_vent_logbook", []];
    private _perPage = 6;
    private _nPages = (ceil ((count _log) / _perPage)) max 1;
    private _page = (uiNamespace getVariable ["ACME_vent_logPage", 0]) min (_nPages - 1) max 0;
    uiNamespace setVariable ["ACME_vent_logPage", _page];

    if (_log isEqualTo []) then {
        // an empty logbook. say so plainly rather than showing a blank field.
        private _empty = _dlg ctrlCreate ["RscStructuredText", -1];
        _empty ctrlSetPosition [_sx + _sw*0.06, _sy + _sh*0.40, _sw*0.88, _sh*0.14];
        _empty ctrlSetFontHeight (_sh * 0.075);
        _empty ctrlSetStructuredText parseText "<t align='center' color='#8a929c'>No events logged.</t>";
        _empty ctrlCommit 0; _empty ctrlShow true;
        _dyn pushBack _empty;
    } else {
        // rows for this page. each row has the clock on the left, a small colored category tag, and the text to the
        // right of it.
        private _rowH = 0.108;
        private _y0 = 0.150;
        private _start = _page * _perPage;
        private _end = ((_start + _perPage) min (count _log)) - 1;
        private _fRow = 0.082;  // it was 0.070, the smallest text on the device and the hardest to read at a glance.
        for "_i" from _start to _end do {
            (_log select _i) params ["_clock", "_cat", "_text"];
            private _rowY = _y0 + (_i - _start) * _rowH;
            // category color: alarms are red, alerts amber, user actions blue and system gray.
            private _tagRGBA = switch (_cat) do {
                case "ALARM": { [0.886, 0.227, 0.227, 1] };
                case "ALERT": { [0.878, 0.627, 0.125, 1] };
                case "USER":  { [0.353, 0.784, 0.941, 1] };
                default       { [0.604, 0.635, 0.675, 1] };
            };
            // the clock, roughly monospaced, on the left.
            private _tc = _dlg ctrlCreate ["RscText", -1];
            _tc ctrlSetPosition [_sx + _sw*0.05, _sy + _sh*_rowY, _sw*0.16, _sh*_rowH];
            _tc ctrlSetText _clock;
            _tc ctrlSetFontHeight (_sh * _fRow);
            _tc ctrlSetTextColor ([[0.80, 0.84, 0.90, 1]] call ACME_fnc_ventColor);
            _tc ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
            _tc ctrlCommit 0; _tc ctrlShow true;
            _dyn pushBack _tc;
            // a small square category swatch.
            private _sw2 = _dlg ctrlCreate ["RscText", -1];
            private _swSz = (0.045 * _sh) / pixelH;
            _sw2 ctrlSetPosition [_sx + _sw*0.225, _sy + _sh*(_rowY + _rowH*0.28), _swSz*pixelW, _swSz*pixelH];
            _sw2 ctrlSetBackgroundColor _tagRGBA;
            _sw2 ctrlCommit 0; _sw2 ctrlShow true;
            _dyn pushBack _sw2;
            // the event text, filling the rest of the row.
            private _txc = _dlg ctrlCreate ["RscText", -1];
            _txc ctrlSetPosition [_sx + _sw*0.29, _sy + _sh*_rowY, _sw*0.66, _sh*_rowH];
            _txc ctrlSetText _text;
            _txc ctrlSetFontHeight (_sh * _fRow);
            _txc ctrlSetTextColor ([[0.93, 0.93, 0.93, 1]] call ACME_fnc_ventColor);
            _txc ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
            _txc ctrlCommit 0; _txc ctrlShow true;
            _dyn pushBack _txc;
        };
        // the page indicator, such as "(2/3)", bottom left, and only when there is more than one page.
        if (_nPages > 1) then {
            private _pg = _dlg ctrlCreate ["RscText", -1];
            _pg ctrlSetPosition [_sx + _sw*0.05, _sy + _sh*0.885, _sw*0.30, _sh*0.09];
            _pg ctrlSetText format ["(%1/%2)", _page + 1, _nPages];
            _pg ctrlSetFontHeight (_sh * 0.065);
            _pg ctrlSetTextColor ([[0.20, 0.20, 0.20, 1]] call ACME_fnc_ventColor);
            _pg ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
            _pg ctrlCommit 0; _pg ctrlShow true;
            _dyn pushBack _pg;
        };
    };

    uiNamespace setVariable ["ACME_vent_graphBars", _dyn];  // the router teardown path.
    uiNamespace setVariable ["ACME_vent_logNPages", _nPages];

    // nav strip: next, which is page down and dial-cyclable when multi-page, and BACK. it is modeled on the
    // back-only strip of the graph screen, and keeps the down-chevron for next when there is more than one page.
    private _navY = 0.885; private _navH = 0.10;
    private _icoPx = (_navH * _sh) / pixelH * 0.85;
    private _icoW = _icoPx * pixelW; private _icoH = _icoPx * pixelH;
    private _place2 = { params ["_idc","_fx","_fy","_fw","_fh"]; private _c = _dlg displayCtrl _idc; _c ctrlSetPosition [_sx + _sw*_fx, _sy + _sh*_fy, _sw*_fw, _sh*_fh]; _c ctrlCommit 0; _c };
    { (_dlg displayCtrl (_x select 0)) ctrlShow false; (_dlg displayCtrl (_x select 1)) ctrlShow false; } forEach _navPairs;
    { (_dlg displayCtrl _x) ctrlShow false; } forEach [87754,87755,87756,87757];

    // the BACK chevron, in the right slot, and its highlight, 87756.
    [87794, 0.86, _navY, 0.14, _navH] call _place2;
    private _backCx = _sx + _sw*(0.86 + 0.07); private _icoYabs = _sy + _sh*(_navY + 0.005);
    (_dlg displayCtrl 87795) ctrlSetPosition [_backCx - _icoW/2, _icoYabs, _icoW, _icoH];
    (_dlg displayCtrl 87795) ctrlCommit 0;
    (_dlg displayCtrl 87794) ctrlShow true; (_dlg displayCtrl 87795) ctrlShow true;
    private _hlPad = _icoW*0.25;
    (_dlg displayCtrl 87756) ctrlSetPosition [_backCx - _icoW/2 - _hlPad, _icoYabs - _icoH*0.15, _icoW + 2*_hlPad, _icoH*1.3];
    (_dlg displayCtrl 87756) ctrlCommit 0; (_dlg displayCtrl 87756) ctrlShow true;

    // the next chevron, a down arrow in the second slot, and its highlight, 87757, only when multi-page.
    if (_nPages > 1) then {
        [87796, 0.72, _navY, 0.14, _navH] call _place2;
        private _nextCx = _sx + _sw*(0.72 + 0.07);
        (_dlg displayCtrl 87797) ctrlSetPosition [_nextCx - _icoW/2, _icoYabs, _icoW, _icoH];
        (_dlg displayCtrl 87797) ctrlCommit 0;
        (_dlg displayCtrl 87796) ctrlShow true; (_dlg displayCtrl 87797) ctrlShow true;
        (_dlg displayCtrl 87757) ctrlSetPosition [_nextCx - _icoW/2 - _hlPad, _icoYabs - _icoH*0.15, _icoW + 2*_hlPad, _icoH*1.3];
        (_dlg displayCtrl 87757) ctrlCommit 0; (_dlg displayCtrl 87757) ctrlShow true;
    };

    // the default dial selection is BACK, so a single middle-click always exits. selidx 1 is BACK in the knob
    // map.
    uiNamespace setVariable ["ACME_vent_selIdx", 1];
    (_dlg displayCtrl 87756) ctrlSetBackgroundColor ([[0, 0.988, 0.992,1]] call ACME_fnc_ventColor);

    [] call ACME_fnc_ventFaceGate;  // exitwith skips the gate at the end of this function.
};

if (_screen == "o2") exitWith {
    // o2 enrichment, laid out like the device: an instruction line, then "OXYGEN: NN%" with the number in a
    // highlight box you dial. middle-click toggles edit, through ACME_vent_editingFio2, the dial changes it from 21
    // to 100 while editing, and the back chevron steps out. the title bar shows "O2 ENRICHMENT".
    private _sr = uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]];
    _sr params ["_sx","_sy","_sw","_sh"];
    private _dyn = [];

    private _tgtO2 = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    private _f = if (isNull _tgtO2) then { uiNamespace getVariable ["ACME_vent_fio2", 21] } else { _tgtO2 getVariable ["ACME_vent_fio2", (uiNamespace getVariable ["ACME_vent_fio2", 21])] };
    uiNamespace setVariable ["ACME_vent_fio2", _f];

    // the title on the bar.
    (_dlg displayCtrl 87712) ctrlSetText "O2 ENRICHMENT";

    // instruction text, left aligned in the upper area. it is three short lines, like the reference.
    {
        private _il = _dlg ctrlCreate ["RscText", -1];
        _il ctrlSetPosition [_sx + _sw*0.06, _sy + _sh*(0.17 + _forEachIndex*0.115), _sw*0.90, _sh*0.11];
        _il ctrlSetText _x;
        _il ctrlSetFontHeight (_sh * 0.078);
        _il ctrlSetFont "PuristaMedium";
        _il ctrlSetTextColor ([[0.92,0.92,0.92,1]] call ACME_fnc_ventColor);
        _il ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
        _il ctrlCommit 0; _il ctrlShow true;
        _dyn pushBack _il;
    } forEach ["ADJUST TO EXTERNAL", "OXYGEN SUPPLY"];

    // the "OXYGEN:" label and the value in a highlight box, in the lower area.
    private _lblO = _dlg ctrlCreate ["RscText", -1];
    _lblO ctrlSetPosition [_sx + _sw*0.06, _sy + _sh*0.615, _sw*0.42, _sh*0.13];
    _lblO ctrlSetText "OXYGEN:";
    _lblO ctrlSetFontHeight (_sh * 0.095);
    _lblO ctrlSetFont "PuristaBold";
    _lblO ctrlSetTextColor ([[0.95,0.95,0.95,1]] call ACME_fnc_ventColor);
    _lblO ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
    _lblO ctrlCommit 0; _lblO ctrlShow true;
    _dyn pushBack _lblO;

    private _editing = uiNamespace getVariable ["ACME_vent_editingFio2", false];
    private _valBox = _dlg ctrlCreate ["ACME_VentTextC", -1];
    _valBox ctrlSetPosition [_sx + _sw*0.44, _sy + _sh*0.615, _sw*0.28, _sh*0.13];
    _valBox ctrlSetText format ["%1%2", _f, "%"];
    _valBox ctrlSetFontHeight (_sh * 0.095);
    _valBox ctrlSetFont "PuristaBold";
    // the highlight when editing is a dark box with light text, and idle is a light box with dark text, like the
    // reference.
    if (_editing) then {
        _valBox ctrlSetTextColor ([[1,1,1,1]] call ACME_fnc_ventColor);
        _valBox ctrlSetBackgroundColor ([[0, 0, 0.996,1]] call ACME_fnc_ventColor);
    } else {
        _valBox ctrlSetTextColor ([[1,1,1,1]] call ACME_fnc_ventColor);
        _valBox ctrlSetBackgroundColor ([[0, 0, 0.996,1]] call ACME_fnc_ventColor);
    };
    _valBox ctrlCommit 0; _valBox ctrlShow true;
    _dyn pushBack _valBox;
    uiNamespace setVariable ["ACME_vent_o2ValCtrl", _valBox];  // the knob updates this.

    uiNamespace setVariable ["ACME_vent_graphBars", _dyn];  // the router teardown path.

    // nav strip: back only, in the right slot, modeled on the graph screen.
    private _navY = 0.885; private _navH = 0.10;
    private _icoPx = (_navH * _sh) / pixelH * 0.85;
    private _icoW = _icoPx * pixelW; private _icoH = _icoPx * pixelH;
    private _place2 = { params ["_idc","_fx","_fy","_fw","_fh"]; private _c = _dlg displayCtrl _idc; _c ctrlSetPosition [_sx + _sw*_fx, _sy + _sh*_fy, _sw*_fw, _sh*_fh]; _c ctrlCommit 0; _c };
    { (_dlg displayCtrl (_x select 0)) ctrlShow false; (_dlg displayCtrl (_x select 1)) ctrlShow false; } forEach _navPairs;
    { (_dlg displayCtrl _x) ctrlShow false; } forEach [87754,87755,87756,87757];
    [87794, 0.86, _navY, 0.14, _navH] call _place2;
    private _backCx = _sx + _sw*(0.86 + 0.07); private _icoYabs = _sy + _sh*(_navY + 0.005);
    (_dlg displayCtrl 87795) ctrlSetPosition [_backCx - _icoW/2, _icoYabs, _icoW, _icoH];
    (_dlg displayCtrl 87795) ctrlCommit 0;
    (_dlg displayCtrl 87794) ctrlShow true; (_dlg displayCtrl 87795) ctrlShow true;
    private _hlPad = _icoW*0.25;
    (_dlg displayCtrl 87756) ctrlSetPosition [_backCx - _icoW/2 - _hlPad, _icoYabs - _icoH*0.15, _icoW + 2*_hlPad, _icoH*1.3];
    (_dlg displayCtrl 87756) ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
    (_dlg displayCtrl 87756) ctrlCommit 0; (_dlg displayCtrl 87756) ctrlShow true;
};

if (_screen == "graph") exitWith {
    // graph screen. it is a real swept waveform monitor. a cursor sweeps left to right, writing live samples of the
    // pressure or flow waveform, derived from BPM and vt, into filled columns and overwriting the previous sweep.
    // it is the same technique as the megacode ecg. the dial cycles PRESSURE, FLOW and BACK, and the knob toggles
    // the back highlight, 87756.
    private _sr = uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]];
    _sr params ["_sx","_sy","_sw","_sh"];
    private _place = { params ["_idc","_fx","_fy","_fw","_fh"]; private _c = _dlg displayCtrl _idc; _c ctrlSetPosition [_sx + _sw*_fx, _sy + _sh*_fy, _sw*_fw, _sh*_fh]; _c ctrlCommit 0; _c };
    private _which = uiNamespace getVariable ["ACME_vent_graphType", "PRESSURE"];
    (_dlg displayCtrl 87800) ctrlSetText _which;
    // the same size and the same field as every other title. it was 0.11 across the full width, which both made it
    // the largest title on the device and ran it straight over the black block.
    (_dlg displayCtrl 87800) ctrlSetFontHeight (_sh * VENT_TITLE_FONT);
    [87800, VENT_TITLE_X2, 0.004, VENT_TITLE_W2, 0.10] call _place;
    [87801, 0.135, 0.16, 0.840, 0.56] call _place;  // the plot field, dark, moved right for the scale.
    (_dlg displayCtrl 87802) ctrlShow false;  // the old single zero-axis line is retired, because the gridlines replace it.
    { (_dlg displayCtrl _x) ctrlShow true } forEach [87800,87801];
    // plot geometry, in abs ui, plus a fresh set of filled column controls across it.
    private _fieldX = _sx + _sw*0.135; private _fieldW = _sw*0.840;
    private _fieldY = _sy + _sh*0.16; private _fieldH = _sh*0.56;
    // a per-type baseline. FLOW is bidirectional about the midline, with 0 in the center, and PRESSURE rises from
    // the bottom, with 0 at the floor. the waveform and the undrawn baseline both key off this, so there is no
    // diagonal.
    private _flow = (_which == "FLOW");
    private _axisY  = if (_flow) then { _fieldY + _fieldH*0.5 } else { _fieldY + _fieldH };
    // gridlines, created before the columns so the waveform draws on top of them. FLOW has five levels, 40, 20, 0,
    // -20 and -40, giving four bands, and PRESSURE has three, 20, 10 and 0, giving two bands. they are a faint
    // blue-gray, like the device.
    private _gridN = if (_flow) then {5} else {3};
    private _gridCtrls = [];
    for "_g" from 0 to (_gridN - 1) do {
        private _gy = _fieldY + (_g / (_gridN - 1)) * _fieldH;
        private _gl = _dlg ctrlCreate ["RscText", -1];
        _gl ctrlSetPosition [_fieldX, _gy, _fieldW, pixelH];
        // the 0 line, the center for flow and the floor for pressure, is a touch brighter than the intermediate
        // lines.
        private _isZero = if (_flow) then {_g == 2} else {_g == (_gridN - 1)};
        _gl ctrlSetBackgroundColor (if (_isZero) then {[0.95, 0.97, 1,0.85]} else {[0.95, 0.97, 1,0.45]});
        _gl ctrlCommit 0; _gl ctrlShow true;
        _gridCtrls pushBack _gl;
    };
    uiNamespace setVariable ["ACME_vent_graphGrid", _gridCtrls];
    private _N = 140;  // a higher column count gives a smoother, tighter waveform.
    private _colW = _fieldW / _N;
    private _cols = [];
    for "_i" from 0 to (_N - 1) do {
        private _c = _dlg ctrlCreate ["RscText", -1];
        _c ctrlSetBackgroundColor ([[0, 0, 0.996,1]] call ACME_fnc_ventColor);  // waveform blue.
        // start every column as an empty sliver on the baseline, so the undrawn part of the plot is blank, a flat line
        // on the baseline, and never a diagonal hatch of stale heights.
        _c ctrlSetPosition [_fieldX + _i*_colW, _axisY, _colW + 0.0006, 0.0012];
        _c ctrlCommit 0; _c ctrlShow true;
        _cols pushBack _c;
    };
    // white outline caps: one thin white sliver per column, riding the top of each waveform column, like the fine
    // white line the device draws over the blue fill. they are kept as a parallel array that the tick moves in
    // lockstep.
    private _caps = [];
    for "_i" from 0 to (_N - 1) do {
        private _cap = _dlg ctrlCreate ["RscText", -1];
        _cap ctrlSetBackgroundColor ([[0.95,0.97,1,1]] call ACME_fnc_ventColor);
        _cap ctrlSetPosition [_fieldX + _i*_colW, _axisY, _colW + 0.0006, pixelH];
        _cap ctrlCommit 0; _cap ctrlShow true;
        _caps pushBack _cap;
    };
    uiNamespace setVariable ["ACME_vent_graphCaps", _caps];
    // dressing, per the real device, from the FLOW screen photo.
    // there is a white outline marking the plot bounds, a scale on the left, a light-blue sweeper at the write
    // position, and the tidal volume readout along the bottom: VTE for what came out and i for what went in. the
    // gap between those two numbers is a clinical instrument in its own right, because a VTe far below VTi means
    // the gas is going somewhere it should not, which on this table means an air leak.
    // the graph dressing is white. the scale numbers, the plot border, the gridlines and the sweeper are the rule
    // markings of the instrument rather than part of the trace, and drawing them in the same blue family as the
    // waveform made the plot read as one blue object. white separates the measurement from the paper it is drawn
    // on, which is what a real device does.
    private _lineBlue = [0.95, 0.97, 1, 1];
    private _px1 = pixelW * 1.5; private _py1 = pixelH * 1.5;

    // a white border of four thin rects. there is no draw rectangle for 2d ui, only filled boxes.
    {
        _x params ["_bx", "_by", "_bw", "_bh"];
        private _b = _dlg ctrlCreate ["RscText", -1];
        _b ctrlSetPosition [_bx, _by, _bw, _bh];
        _b ctrlSetBackgroundColor ([[0.95, 0.97, 1, 1]] call ACME_fnc_ventColor);
        _b ctrlCommit 0; _b ctrlShow true;
        _cols pushBack _b;  // it rides the same cleanup list as the columns.
    } forEach [
        [_fieldX - _px1,          _fieldY - _py1,           _fieldW + 2*_px1, _py1],  // top.
        [_fieldX - _px1,          _fieldY + _fieldH,        _fieldW + 2*_px1, _py1],  // bottom.
        [_fieldX - _px1,          _fieldY - _py1,           _px1,             _fieldH + 2*_py1],  // left.
        [_fieldX + _fieldW,       _fieldY - _py1,           _px1,             _fieldH + 2*_py1]  // right.
    ];

    // the left scale, aligned to the gridlines and sitting just left of the plot. FLOW is symmetric about the mid
    // axis, at 40, 20, 0, -20 and -40 top to bottom, and PRESSURE reads from the floor, at 20, 10 and 0. it is
    // right-aligned, so the numbers sit flush to the left of the box, never under it and never clipped.
    private _labels = if (_which == "FLOW") then {["40","20","0","-20","-40"]} else {["20","10","0"]};
    private _nLab = count _labels;
    // the label field was 0.070 wide against a "-40" that needs about 0.067 at this font, so the minus sign was
    // clipped off the left every time. the plot moved right to 0.135 and the field widened to 0.105, which leaves
    // real margin instead of a rounding error.
    private _scaleRight = 0.128;  // the right edge of the label field, just left of the plot at 0.135.
    private _scaleW = 0.105;  // comfortably wider than "-40" needs.
    {
        private _ly = _fieldY + (_forEachIndex / (_nLab - 1)) * _fieldH - (_sh * 0.042);
        private _l = _dlg ctrlCreate ["ACME_VentTextR", -1];  // a right-aligned base, at style 1.
        _l ctrlSetPosition [_sx + _sw * (_scaleRight - _scaleW), _ly, _sw * _scaleW, _sh * 0.084];
        _l ctrlSetText _x;
        _l ctrlSetFontHeight (_sh * 0.072);
        _l ctrlSetTextColor _lineBlue;
        _l ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
        _l ctrlCommit 0; _l ctrlShow true;
        _cols pushBack _l;
    } forEach _labels;

    // the no-input hatch, one control per column. from the manual, diagonal lines mean the sensors are reporting
    // nothing. that is a property of each moment in time rather than of the whole plot, so it is drawn column by
    // column as the sweep passes: a column with no input gets hatch marks, a column with input gets its waveform,
    // and the sweep overwrites one with the other as it goes.
    // the previous version was a static overlay of long diagonal strokes across the whole plot. it could only be
    // all on or all off, so it could not show input returning, and its lines were far too widely spaced.
    // two of the three marks in a column reuse the column and cap controls, which are free precisely because that
    // column is not drawing a waveform. this third array is the extra one that gets the density right.
    private _hatch = [];
    for "_i" from 0 to (_N - 1) do {
        private _hc = _dlg ctrlCreate ["RscText", -1];
        _hc ctrlSetPosition [_fieldX + _i*_colW, _axisY, _colW, 0.0012];
        _hc ctrlCommit 0; _hc ctrlShow true;
        _hatch pushBack _hc;
        _cols pushBack _hc;
    };
    uiNamespace setVariable ["ACME_vent_graphHatch", _hatch];

    // the sweeper. it is a vertical light-blue line standing at the write position, exactly like the device. the
    // tick moves it, because it knows the cursor and we only give it the control. it is stored under its own key so
    // the tick can find it, and pushed onto the cleanup list so the router cannot leak it.
    private _sweep = _dlg ctrlCreate ["RscText", -1];
    _sweep ctrlSetPosition [_fieldX, _fieldY, pixelW * 2, _fieldH];
    _sweep ctrlSetBackgroundColor _lineBlue;
    _sweep ctrlCommit 0; _sweep ctrlShow true;
    uiNamespace setVariable ["ACME_vent_graphSweep", _sweep];
    _cols pushBack _sweep;

    // the readout, "VTE 0394 I 0385", zero-padded like the device. the values come from the drive tick, which has
    // been publishing real VTi and VTe all along, and the tick refreshes this line as they change.
    private _vtRow = _dlg ctrlCreate ["RscText", -1];
    _vtRow ctrlSetPosition [_fieldX, _fieldY + _fieldH + _py1 * 2, _fieldW, _sh * 0.10];
    _vtRow ctrlSetFontHeight (_sh * 0.085);
    _vtRow ctrlSetTextColor _lineBlue;
    _vtRow ctrlSetBackgroundColor ([[0, 0, 0, 0]] call ACME_fnc_ventColor);
    _vtRow ctrlSetText "VTE ----  I ----";
    _vtRow ctrlCommit 0; _vtRow ctrlShow true;
    uiNamespace setVariable ["ACME_vent_graphVtRow", _vtRow];
    _cols pushBack _vtRow;

    // fold the white caps and the gridlines into the same teardown list, so the router deletes them on any screen
    // change. they were created as separate controls and would otherwise leak.
    { _cols pushBack _x; } forEach (uiNamespace getVariable ["ACME_vent_graphCaps", []]);
    { _cols pushBack _x; } forEach (uiNamespace getVariable ["ACME_vent_graphGrid", []]);
    uiNamespace setVariable ["ACME_vent_graphBars", _cols];  // the same key the router deletes on a screen change.
    uiNamespace setVariable ["ACME_vent_graphBuf", []];
    uiNamespace setVariable ["ACME_vent_graphGeo", [_fieldX,_fieldY,_fieldW,_fieldH,_axisY,_flow]];
    uiNamespace setVariable ["ACME_vent_graphN", _N];
    // sweeper continuity. switching PRESSURE to FLOW rebuilds the plot, and the rebuild used to slam the cursor back
    // to zero, so the arm jumped to the left edge every time you changed trace. on a real device the sweep does not
    // care what you are looking at, because it keeps running. the knob sets this flag before it rebuilds, so a type
    // switch keeps the cursor and the sample clock while a fresh entry to the screen still starts clean.
    if (uiNamespace getVariable ["ACME_vent_graphKeepSweep", false]) then {
        uiNamespace setVariable ["ACME_vent_graphKeepSweep", false];
    } else {
        uiNamespace setVariable ["ACME_vent_graphCursor", 0];
        uiNamespace setVariable ["ACME_vent_graphColAcc", 0];
        uiNamespace setVariable ["ACME_vent_graphSampT", diag_tickTime];
        // sensor zeroing. per the manual, the machine zeroes its sensors on entry and draws diagonal lines across the
        // plot while it has no input to show. it happens on a genuine entry only, not on a trace switch.
        uiNamespace setVariable ["ACME_vent_graphZeroUntil", diag_tickTime + (missionNamespace getVariable ["ACME_vent_graphZeroSecs", 3])];
    };
    // nav strip: back only, at dial position 2. hide the other nav highlights, then place and arm the back
    // highlight.
    private _navY = 0.885; private _navH = 0.10;
    private _icoPx = (_navH * _sh) / pixelH * 0.85;
    private _icoW = _icoPx * pixelW; private _icoH = _icoPx * pixelH;
    { (_dlg displayCtrl (_x select 0)) ctrlShow false; (_dlg displayCtrl (_x select 1)) ctrlShow false; } forEach _navPairs;
    { (_dlg displayCtrl _x) ctrlShow false; } forEach [87754,87755,87757];
    [87794, 0.86, _navY, 0.14, _navH] call _place;  // the back button slot, on the right.
    private _cellCx = _sx + _sw*(0.86 + 0.07); private _icoYabs = _sy + _sh*(_navY + 0.005);
    (_dlg displayCtrl 87795) ctrlSetPosition [_cellCx - _icoW/2, _icoYabs, _icoW, _icoH];
    (_dlg displayCtrl 87795) ctrlCommit 0;
    (_dlg displayCtrl 87794) ctrlShow true; (_dlg displayCtrl 87795) ctrlShow true;
    private _hlPad = _icoW*0.25;
    (_dlg displayCtrl 87756) ctrlSetPosition [_cellCx - _icoW/2 - _hlPad, _icoYabs - _icoH*0.15, _icoW + 2*_hlPad, _icoH*1.3];
    (_dlg displayCtrl 87756) ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
    (_dlg displayCtrl 87756) ctrlCommit 0; (_dlg displayCtrl 87756) ctrlShow true;

    [] call ACME_fnc_ventFaceGate;  // exitwith skips the gate at the end of this function.
};

// list and message screen layout.
private _sr = uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]];
_sr params ["_sx","_sy","_sw","_sh"];
private _place = {
    params ["_idc","_fx","_fy","_fw","_fh"];
    private _c = _dlg displayCtrl _idc;
    _c ctrlSetPosition [_sx + _sw*_fx, _sy + _sh*_fy, _sw*_fw, _sh*_fh];
    _c ctrlCommit 0;
    _c
};

// the title, on the white title bar.
(_dlg displayCtrl 87780) ctrlSetText _title;
// the title height is set here at runtime, which overrides the sizeex in the config class. it is nudged up from
// 0.11 so the heading reads a little larger without changing its weight, because the bold experiment looked
// wrong on this device.
(_dlg displayCtrl 87780) ctrlSetFontHeight (_sh * VENT_TITLE_FONT);
// the same header geometry as the live screen, in fn_ventpanelinit. the white top bar is y 0 to 0.135, so the
// title is centerd on its midline at 0.0675 and spans the full width with centerd alignment. every screen
// agrees.
[87780, VENT_TITLE_X2, 0.067 - 0.045, VENT_TITLE_W2, 0.090] call _place;  // shifted right. live keeps VENT_TITLE_X.
(_dlg displayCtrl 87780) ctrlShow true;

// rows, or a prompt, or a device-accurate custom layout for the screens that have one.
private _customScreens = ["params", "alerts", "alerts2", "weight"];
if (_screen in _customScreens) then {
    // fn_ventcustomlayout builds the statics, riding graphbars for teardown, registers every editable number as a
    // standard value field, and sets listcount itself. the rows and the prompt stay hidden.
    [_screen] call ACME_fnc_ventCustomLayout;
} else {
if (count _rows > 0) then {
    private _rowIdc = [87781,87782,87783,87784,87785,87786];
    // five rows per page, always. the pitch used to be the window divided by however many rows the screen happened
    // to have, so a three-row page had tall rows, a five-row page had short ones, and the panel changed shape as
    // you moved between menus. the pitch is fixed at a fifth of the span on every screen now. a page with fewer
    // than five rows leaves the remaining positions empty instead of stretching to fill them, which is also what
    // stops a single row becoming a full-screen highlight. no screen exceeds five rows.
    private _perPage = 5;
    private _n = (count _rows) min _perPage;
    // two exemptions: VENT. MODE and the first layer of ADV. SETTINGS. both are short pick-lists rather than pages
    // of settings, so they read better filling the window than sitting in the top three fifths of it. every other
    // list screen keeps the fixed pitch.
    private _fillScreens = ["mode", "advset", "interface"];
    private _fillWindow = _screen in _fillScreens;
    // rows fill the real content window, measured from the inlay art. the white top bar ends at 0.132 and the white
    // bottom tray begins at 0.873. with equal padding of 0.018 each side, rows span 0.150 to 0.855, hard up against
    // the tray with no dead band underneath.
    private _rowTop = 0.150;
    private _rowSpan = 0.705;
    private _rowH = if (_fillWindow && {_n > 0}) then { _rowSpan / _n } else { _rowSpan / _perPage };

    for "_i" from 0 to (_n - 1) do {
        private _c = _dlg displayCtrl (_rowIdc select _i);
        _c ctrlSetText (_rows select _i);
        _c ctrlSetFontHeight (_sh * 0.13);
        [_rowIdc select _i, 0.06, _rowTop + _i*_rowH, 0.80, _rowH*0.92] call _place;
        _c ctrlShow true;
        _c ctrlEnable true;
    };
    // locked trailing rows are drawn and not selectable, and they are grayed so they read as readouts.
    private _locked = uiNamespace getVariable ["ACME_vent_listLocked", 0];
    if (_locked > 0) then {
        for "_i" from (_n - _locked) to (_n - 1) do {
            if (_i >= 0) then {
                (_dlg displayCtrl (_rowIdc select _i)) ctrlSetTextColor ([[0.45,0.48,0.52,1]] call ACME_fnc_ventColor);
            };
        };
    };
    uiNamespace setVariable ["ACME_vent_listCount", (_n - _locked) max 0];
    // B18: entering VENT. MODE must highlight the mode that is actually configured. Resetting to row zero
    // made an otherwise innocent confirm rewrite SIMV PC to SIMV VC PS while the header could still show PC.
    if (_screen == "mode") then {
        private _modesNow = ["SIMV VC PS","IMV VC (CPR)","SIMV PC","CPAP PS HF"];
        private _modeTarget = uiNamespace getVariable ["ACME_vent_target", objNull];
        private _modeNow = if (isNull _modeTarget) then {"SIMV VC PS"} else {_modeTarget getVariable ["ACME_vent_mode", "SIMV VC PS"]};
        private _modeIdx = _modesNow find _modeNow;
        if (_modeIdx < 0) then { _modeIdx = 0; };
        uiNamespace setVariable ["ACME_vent_listSel", _modeIdx];
        uiNamespace setVariable ["ACME_vent_selIdx", _modeIdx];
    };
} else {
    // message screen, for connect. center the prompt. it is structured text, so <br/> renders as a real line break
    // and long copy wraps to the screen width instead of clipping off both ends.
    private _p = _dlg displayCtrl 87787;
    _p ctrlSetStructuredText parseText _prompt;
    [87787, 0.04, 0.34, 0.92, 0.28] call _place;
    _p ctrlShow true;
    uiNamespace setVariable ["ACME_vent_listCount", 0];
};
};

// the nav strip on the bottom bar, with confirm, home, back and next, showing the flagged ones only. build an
// ordered list of the visible chevrons, so the dial traverses exactly them rather than a phantom 4-wide strip,
// and so activating a strip position fires the right nav action. each entry is [action, btnidc, hlidc].
[_nav] call ACME_fnc_ventNavStrip;

// highlight the initially selected row.
// build the value fields after the rows have been positioned, because the fields are sized from the rect of each
// row, and before the highlight is painted, because the highlight now lands on the field and the field has to
// exist first.
// the custom-layout screens have already registered their own fields, and running the generic builder over them
// would tear them down, because its first act is deleting whatever is registered. so it runs for list screens
// only.
if !(_screen in _customScreens) then {
    [[]] call ACME_fnc_ventPanelValueFields;
};

[] call ACME_fnc_ventPanelListRefresh;

// facing.
// this is the last word on visibility. any screen the router builds is hidden again if the device is turned
// round. the router is called from a dozen places, several of them timed, and chasing a flip check into each
// one would leave exactly one path that lights the screen through the back of the machine. one gate at the end
// instead.
[] call ACME_fnc_ventFaceGate;
