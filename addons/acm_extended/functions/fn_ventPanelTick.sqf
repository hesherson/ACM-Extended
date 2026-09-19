// per-frame tick. during the boot window it holds the logo and blanks the operational controls. once boot
// elapses it hides the logo, shows the screen, and animates the side gauge with a gentle breath cycle so the
// pressure bar reads as live. fn_ventpanelrefresh sets the live values themselves on change.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};
private _provider = _dlg getVariable ["ACME_vent_viewer", objNull];
if (isNull _provider || {!alive _provider} || {_provider isNotEqualTo ACE_player}
    || {_provider getVariable ["ACE_isUnconscious", false]}
    || {isNull (uiNamespace getVariable ["ACME_vent_target", objNull])}) exitWith {_dlg closeDisplay 2;};
if !([ACE_player, "ventilator", true] call ACME_fnc_procedureAllowed) exitWith {
    [87700] call ACME_fnc_minigameClose;
};
[_dlg] call ACME_fnc_ventFlipKeyHint;
private _custodyTarget = uiNamespace getVariable ["ACME_vent_target", objNull];
private _tgtM = uiNamespace getVariable ["ACME_vent_target", ACE_player];
if (!isNull _custodyTarget && {_custodyTarget isNotEqualTo ACE_player}
    && {!(_custodyTarget getVariable ["ACME_vent_onPatient", false]) || {_custodyTarget getVariable ["ACME_vent_recovering", false]}}) exitWith {
    [87700] call ACME_fnc_minigameClose;
};

// Refresh a visible panel when the synchronized addon option changes. This only
// resets UI edits; advanced device choices remain available when toggled back.
private _simple = missionNamespace getVariable ["ACME_vent_simpleMode", false];
private _effectiveFrame = if (_simple) then {[_custodyTarget] call ACME_fnc_ventEffectiveSettings} else {[]};
if (_simple) then { uiNamespace setVariable ["ACME_vent_bpm", _effectiveFrame select 2]; };
if (_simple != (uiNamespace getVariable ["ACME_vent_simpleShown", _simple])) then {
    uiNamespace setVariable ["ACME_vent_simpleShown", _simple];
    uiNamespace setVariable ["ACME_vent_editing", false];
    uiNamespace setVariable ["ACME_vent_editingParam", -1];
    uiNamespace setVariable ["ACME_vent_editingAlert", -1];
    uiNamespace setVariable ["ACME_vent_editingPeep", false];
    uiNamespace setVariable ["ACME_vent_editingIE", false];
    uiNamespace setVariable ["ACME_vent_editingFio2", false];
    uiNamespace setVariable ["ACME_vent_measBpmNextT", 0];
    private _screen = uiNamespace getVariable ["ACME_vent_screen", "live"];
    if !(_screen in ["boot", "selftest"]) then { [_screen] call ACME_fnc_ventPanelShowScreen; };
};


// slow measured BPM update, on a cadence of about 3 s. fn_ventpanelrefresh reads this stored value only, so
// the live parenthetical no longer re-randomizes every time the operator scrolls the menu, which fires a
// refresh.
// when the vent is driving, the measured value is the real respiration rate of the patient. the drive tick
// pins that to the set BPM in the mandatory modes, and it is the patient's own drive under CPAP.
if (diag_tickTime > (uiNamespace getVariable ["ACME_vent_measBpmNextT", 0])) then {
    private _bpmNow = uiNamespace getVariable ["ACME_vent_bpm", 12];
    // PEEP and i:e row.
    // this row was static config text, "PEEP 5.0   I:E 1:2.0", and was never written at runtime, so it had been
    // lying about the PEEP since the panel was built. it now shows the real numbers, auto-PEEP included. trapped
    // gas from a short expiratory time raises the true end-expiratory pressure above what a medic dialled in, and
    // if the machine did not show that, an inverse ratio would silently strangle the patient behind a reassuring
    // 5.0.
    private _peepSet = if (isNull _tgtM) then {5} else {_tgtM getVariable ["ACME_vent_peep", 5]};
    private _autoP = if (isNull _tgtM) then {0} else {_tgtM getVariable ["ACME_vent_autoPEEP", 0]};
    private _ieCur = if (isNull _tgtM) then {2.0} else {_tgtM getVariable ["ACME_vent_ie", 2.0]};
    if (_simple) then {
        _peepSet = _effectiveFrame select 5;
        _ieCur = _effectiveFrame select 9;
    };
    // three fixed fields. this was one composed string, so the moment auto-PEEP appeared the line grew by six
    // characters and pushed i:e clean off the right of the screen. the auto-PEEP figure now has its own smaller
    // control between them, and i:e sits at a fixed x that nothing can move.
    private _rowP = _dlg displayCtrl 87727;
    private _rowA = _dlg displayCtrl 87767;
    private _rowI = _dlg displayCtrl 87768;
    private _warnCol = if (_autoP > 3) then {[0.95,0.45,0.10,1]} else {[0.80,0.80,0.80,1]};
    if (!isNull _rowP) then {
        _rowP ctrlSetText format ["PEEP %1", _peepSet toFixed 1];
        _rowP ctrlSetTextColor _warnCol;
    };
    if (!isNull _rowA) then {
        // trapped gas is a warning state, so it is colored even when the PEEP figure beside it is not.
        _rowA ctrlSetText (if (_autoP > 0.3) then { format ["(+%1)", _autoP toFixed 1] } else { "" });
        _rowA ctrlSetTextColor _warnCol;
    };
    if (!isNull _rowI) then {
        _rowI ctrlSetText format ["I:E %1", [_ieCur] call ACME_fnc_ventFormatIE];
        _rowI ctrlSetTextColor [0.80,0.80,0.80,1];
    };

    // the alarm count and the status letter live in one box, 87714.
    // the alarm box is the only control in the plug slot. it shows the t, z or c trigger letter when calm, and the
    // red alarm count when something is wrong. the separate status control, 87766, is retired, because two
    // transparent controls on the identical rect was what smeared the gap between the battery and the box shut.
    // its render lives in the alarm-box block below, which reads the same status and alarm state.

    // alarms: the live count beside the bell.
    // the number is the length of ACME_vent_alarms, so it tracks what is actually wrong with the patient and the
    // machine. it turns red the moment anything is active. the bell itself switches to the silenced glyph while
    // the alarm is acknowledged, and fn_ventalarmtick un-silences on any new alarm, so a silence can never deafen
    // you to the next one.
    private _alarms = if (isNull _tgtM) then {[]} else {_tgtM getVariable ["ACME_vent_alarms", []]};
    private _nAlarm = count _alarms;
    private _silUntil = if (isNull _tgtM) then {0} else {_tgtM getVariable ["ACME_vent_alarmSilencedUntil", 0]};
    private _silenced = (_nAlarm > 0) && {CBA_missionTime < _silUntil};
    // keep the retired status control empty and invisible, so it can never paint into the gap again.
    private _stCtrl = _dlg displayCtrl 87766;
    if (!isNull _stCtrl) then { _stCtrl ctrlSetText ""; _stCtrl ctrlShow false; };
    private _cnt = _dlg displayCtrl 87765;
    if (!isNull _cnt) then {
        _cnt ctrlSetText format ["(%1)", _nAlarm];
        _cnt ctrlSetTextColor (if (_nAlarm > 0 && {!_silenced}) then {[0.85,0.12,0.12,1]} else {[0.10,0.10,0.10,1]});
    };
    private _bell = _dlg displayCtrl 87741;
    if (!isNull _bell) then {
        _bell ctrlSetText (if (_silenced) then {"\acm_extended\ui\vent\alarm_silenced_ca.paa"} else {"\acm_extended\ui\vent\alarm_ca.paa"});
        _bell ctrlSetTextColor (if (_nAlarm > 0 && {!_silenced}) then {[0.85,0.12,0.12,1]} else {[0.10,0.10,0.10,1]});
    };

    // the measured BPM parenthetical is driven continuously now, with a visible ramp, in the live-screen block
    // below, rather than on this slow 3 s cadence, which made it look static. this block keeps the PEEP row and
    // the alarm chrome on their cheap 3 s refresh.
    uiNamespace setVariable ["ACME_vent_measBpmNextT", diag_tickTime + 3];
};

private _bootT0 = uiNamespace getVariable ["ACME_vent_bootT0", -1];
private _bootDur = uiNamespace getVariable ["ACME_vent_bootDur", (missionNamespace getVariable ["ACME_vent_blackoutSec", 0.45]) + (missionNamespace getVariable ["ACME_vent_jingleDelaySec", 0.5]) + (missionNamespace getVariable ["ACME_vent_jingleSndLen", 1.675]) + (missionNamespace getVariable ["ACME_vent_bootGapSec", 0.25])];
private _booting = (_bootT0 >= 0) && {(diag_tickTime - _bootT0) < _bootDur};

// B20: the live numeric fields are sensor displays, not edit-only labels. B18 made spontaneous SIMV breaths part
// of ACME_vent_vti/vte/mvDelivered, but the panel only repainted those fields when an operator turned the dial.
// Refresh them at 10 Hz while the live screen is visible. This is UI-local and does no patient writes.
if (!_booting && {(uiNamespace getVariable ["ACME_vent_screen", "live"]) == "live"}) then {
    private _liveTarget = uiNamespace getVariable ["ACME_vent_target", objNull];
    private _liveDriving = !isNull _liveTarget && {_liveTarget getVariable ["ACME_vent_driving", false]};
    private _lastTarget = uiNamespace getVariable ["ACME_vent_mvLastTarget", objNull];
    private _wasDriving = uiNamespace getVariable ["ACME_vent_mvWasDriving", false];
    if (_liveTarget isNotEqualTo _lastTarget || {_liveDriving && {!_wasDriving}}) then {
        private _mvDelay = (missionNamespace getVariable ["ACME_vent_mvSensorDelaySec", 2.0]) max 2.0;
        uiNamespace setVariable ["ACME_vent_mvValidAfter", diag_tickTime + _mvDelay];
        uiNamespace setVariable ["ACME_vent_mvLastTarget", _liveTarget];
    };
    uiNamespace setVariable ["ACME_vent_mvWasDriving", _liveDriving];
    if (diag_tickTime >= (uiNamespace getVariable ["ACME_vent_liveReadoutNext", 0])) then {
        uiNamespace setVariable ["ACME_vent_liveReadoutNext", diag_tickTime + 0.10];
        [] call ACME_fnc_ventPanelRefresh;
    };
};

// operational controls are hidden while booting. that is the live readouts and the list-screen controls. the
// screen background and the title and bottom bars stay as chrome, and the screen router owns per-screen
// visibility once boot completes.
// it includes the graph controls, 87800 to 87802, and the nav-highlight boxes, 87754 to 87757. GraphField,
// 87801, has a near-black background and sits at its config placeholder until the graph screen positions it,
// so if it is not hidden during boot it paints a black rectangle over the boot logo until the screen router
// runs.
private _opCtrls = [87712,87713,87716,87767,87768,87720,87721,87722,87723,87724,87725,87726,87727,87730,87731,87732,87733,87734,87735,87736,87737,87738,87769,87774,87739,87759,87761,87762,87763,87764,87740,87741,87742,87743,87744,87745,87746,87747,87748,87749,87752,87753,87750,87751,87780,87781,87782,87783,87784,87785,87786,87787,87790,87791,87792,87793,87794,87795,87796,87797,87754,87755,87756,87757,87800,87801,87802,87765,87766];

// the 4-second MMB power-off hold. it is measured here because the panel tick is the only thing running while
// the panel is open, and the hold only means anything while the panel is open.
[] call ACME_fnc_ventHoldTick;

// ambient light on the device body.
// the ventilator is a physical object sitting in the world, so it should be lit like one. the face texture was
// drawn at full brightness whatever the hour, which made the machine glow like a lightbox at midnight while
// everything around it was black.
// ace_common_fnc_ambientBrightness returns 0 to 1 from the sun, the moon and the overcast, which is exactly the
// quantity wanted and is already the number the rest of ACE lights things by. it is applied through colortext,
// which on a picture control multiplies the texture rather than drawing over it, so the art keeps its own
// shading and simply gets darker.
// there is no flashlight option, deliberately. this device carries its own light source, and a medic reading a
// lit screen does not also need a torch on the bezel around it.
// the screen lights its own bezel. the brightness setting adds a small amount back, because a panel turned up
// genuinely spills light onto the housing around it. nothing is added at level 1, because that setting exists
// to make the machine hard to see and having it brighten the case would defeat the point.
private _ambFace = _dlg displayCtrl 87701;
if (!isNull _ambFace) then {
    // 1. sky. the sun, the moon and the overcast, the same number the rest of ACE lights by.
    private _amb = 1;
    if (!isNil "ace_common_fnc_ambientBrightness") then { _amb = [] call ace_common_fnc_ambientBrightness; };
    private _dark = missionNamespace getVariable ["ACME_vent_ambientMin", 0.30];
    private _r = linearConversion [0, 1, _amb, _dark, 1, true];
    private _g = _r; private _b = _r;

    // 2. local light, with its color.
    // arma will not tell a script what color an arbitrary light is, so this does the two halves separately. the
    // intensity comes from ACE's own lightintensityfromobject, which already understands weapon lights, vehicle
    // lights and burning objects, and is what ACE lights everything else by. the color is matched for the sources
    // that genuinely have one and can be identified by type, which are chemlights and flares. everything else
    // contributes as white, which is the honest answer rather than a guess.
    private _cx = 0; private _cy = 0; private _cz = 0; private _cw = 0;
    private _rad = missionNamespace getVariable ["ACME_vent_lightRadius", 18];
    {
        private _src = _x;
        private _i = 0;
        if (!isNil "ace_common_fnc_lightIntensityFromObject") then {
            _i = [ACE_player, _src] call ace_common_fnc_lightIntensityFromObject;
        };
        if (_i > 0.01) then {
            // a distance falloff on top of the intensity, so a lamp across the road tints less than one at arm's reach.
            private _d = ACE_player distance _src;
            private _f = _i * (1 - ((_d / _rad) min 1));
            if (_f > 0.005) then {
                private _t = typeOf _src;
                private _col = switch (true) do {
                    case (_t find "Chemlight_red"    >= 0 || {_t find "Flare_red"    >= 0}): { [1.00, 0.18, 0.14] };
                    case (_t find "Chemlight_green"  >= 0 || {_t find "Flare_green"  >= 0}): { [0.22, 1.00, 0.30] };
                    case (_t find "Chemlight_blue"   >= 0):                                  { [0.24, 0.42, 1.00] };
                    case (_t find "Chemlight_yellow" >= 0 || {_t find "Flare_yellow" >= 0}): { [1.00, 0.90, 0.25] };
                    case (_t find "Flare_white"      >= 0):                                  { [1.00, 0.98, 0.92] };
                    default { [1, 1, 1] };  // an unknown source. it contributes brightness, not a hue.
                };
                _cx = _cx + (_col select 0) * _f;
                _cy = _cy + (_col select 1) * _f;
                _cz = _cz + (_col select 2) * _f;
                _cw = _cw + _f;
            };
        };
    } forEach (ACE_player nearObjects _rad);

    if (_cw > 0) then {
        // the local light adds to the sky rather than replacing it, so a chemlight at night tints a dark machine
        // instead of washing it to white, and adds almost nothing in daylight where nobody would notice it.
        private _room = (1 - _r) max 0;
        private _k = (_cw min 1) * _room;
        _r = (_r + (_cx / _cw) * _k) min 1;
        _g = (_g + (_cy / _cw) * _k) min 1;
        _b = (_b + (_cz / _cw) * _k) min 1;
    };

    // 3. the spill from the screen itself, on the front only.
    // the screen faces away when the device is turned round, so it cannot light the back. flipping in poor light
    // therefore darkens the machine slightly, which is the correct behavior and a useful cue that the screen now
    // points at the casualty rather than at you.
    private _revF = uiNamespace getVariable ["ACME_vent_flipped", false];
    if (!_revF && {uiNamespace getVariable ["ACME_vent_powered", false]}) then {
        private _blF  = (round (uiNamespace getVariable ["ACME_vent_brightness", 3])) max 1 min 4;
        private _glow = missionNamespace getVariable ["ACME_vent_ambientGlow", 0.16];
        private _add  = _glow * ((_blF - 1) / 3);
        _r = (_r + _add) min 1; _g = (_g + _add) min 1; _b = (_b + _add) min 1;
    };

    private _curL = uiNamespace getVariable ["ACME_vent_faceLit", []];
    private _now = [_r, _g, _b];
    private _chg = (count _curL) != 3;
    if (!_chg) then { { if (abs ((_curL select _forEachIndex) - _x) > 0.006) then { _chg = true; }; } forEach _now; };
    if (_chg) then {
        _ambFace ctrlSetTextColor [_r, _g, _b, 1];
        _ambFace ctrlCommit 0;
        private _kc3 = _dlg displayCtrl 87703;
        if (!isNull _kc3) then { _kc3 ctrlSetTextColor [_r, _g, _b, 1]; _kc3 ctrlCommit 0; };
        uiNamespace setVariable ["ACME_vent_faceLit", _now];
    };
};

// reverse side. while the device is turned round there is no screen to draw, so the whole front-face pipeline
// below is skipped and the back runs instead: hover tooltips, the swap countdown, and nothing else.
["tick"] call ACME_fnc_ventFlip;
// there is no early exit while flipped. bailing out here paused the boot, because the sequence stopped
// counting and its audio stopped queueing until a medic turned the device back round. the machine keeps
// running with its back to you, exactly as a real one would, and what changes is only whether you can see it.
// fn_ventflip owns the visibility and the end of fn_ventpanelshowscreen enforces it, so everything below
// paints into hidden controls and costs nothing but a few wasted writes.
// the facing enforcement used to sit here, at the top. that was the wrong end, because every branch below it
// that shows something, the boot chain, the battery indicator and the power-off substrate, ran afterwards and
// undid it in the same frame. it is the last thing the tick does now, so it always has the final word. see the
// end of this file.

// a powered-off device uses the dark inlay. a dead device is not a hole where the screen used to be. the bezel
// is still physically there and simply unlit, and this draws that bezel dark over the black substrate.
// the veil still goes, because there is no backlight to dim, and dimming an already dark panel would only make
// the brightness setting appear to do something while the machine is off. the boot branch further down picks
// the machine up the moment the power button, or a battery swap, sets ACME_vent_powered back to true.
if !(uiNamespace getVariable ["ACME_vent_powered", false]) exitWith {
    { private _c = _dlg displayCtrl _x; if (!isNull _c) then { _c ctrlShow false; }; } forEach _opCtrls;
    [] call ACME_fnc_ventPanelHideScreen;
    private _offInlay = "\acm_extended\ui\vent\ventway_sparrow_robust_menu_inlay_blk_ca.paa";
    private _inlOff = _dlg displayCtrl 87702;
    if (!isNull _inlOff) then {
        if ((uiNamespace getVariable ["ACME_vent_inlayCur", ""]) != _offInlay) then {
            _inlOff ctrlSetText _offInlay;  // on change only, because ctrlSetText is a texture reload.
            uiNamespace setVariable ["ACME_vent_inlayCur", _offInlay];
        };
        _inlOff ctrlShow (!(uiNamespace getVariable ["ACME_vent_flipped", false]));
    };
    { if (!isNull _x) then { _x ctrlShow false; }; } forEach (uiNamespace getVariable ["ACME_vent_veilCtls", []]);
    private _sbg = _dlg displayCtrl 87710;
    // THE DARK PANEL USES THE MEASURED WINDOW, NOT THE ONE IT INHERITED.
    // this branch only ever set the colour, so the substrate kept whatever rect was last written, which is the
    // 0.132 to 0.873 operating rect from the post-boot restore below. in screen-rect units that bottom edge lands
    // at 0.14746 of the face while the bezel bar of the art starts at 0.14795, so it stopped 0.00049 short and
    // left a hairline of lighter case showing between the black square and the black frame.
    // 0.8780 lands at 0.14871 and overlaps the bar, which is the same number and the same reason the boot splash
    // and the power-off splash already use. the 0.006 side bleed carries the black out to the bezel rather than
    // stopping a pixel or two inside it.
    // the operating rect below is deliberately left alone. the inlay covers that edge while the machine is
    // running, and only this branch draws the substrate with nothing on top of it.
    // the screen rect is read here rather than taken from _scrX and friends, because those are unpacked further
    // down the tick and this branch exits well before them.
    (uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]]) params ["_offX","_offY","_offW","_offH2"];
    // the top and the bottom are knobs, because this is a two pixel judgement against the bezel of the art and it
    // is quicker to nudge in game than to rebuild for.
    // THE BOTTOM IS DERIVED FROM THE ART, NOT NUDGED. see the note on the knobs in fn_postInit.
    // fn_ventPanelInit:377 records both measurements: the screen rect is y 0.4185 to 0.5879 of the face and the
    // opaque extent of the inlay art is y 0.41846 to 0.58887. so the art bottom is at screen-rect fraction
    // 1.00573, which is PAST THE END OF THE RECT. every hand-nudged value, 0.8705, 0.8780 and 0.8900, was inside
    // the rect and could never have reached the frame however far it was pushed.
    // overshooting costs nothing here, because the bezel is black and this branch draws the substrate with
    // nothing on top of it.
    private _offTop = missionNamespace getVariable ["ACME_vent_offScreenTop", 0.1347];
    private _offBot = missionNamespace getVariable ["ACME_vent_offScreenBottom", 0.8900];
    private _offH = _offBot - _offTop;
    private _offBleed = missionNamespace getVariable ["ACME_vent_offScreenBleed", 0.006];
    _sbg ctrlSetPosition [_offX - _offW*_offBleed, _offY + _offH2*_offTop, _offW*(1 + 2*_offBleed), _offH2*_offH];
    _sbg ctrlSetBackgroundColor [0,0,0,1];
    // only if the front is facing you. this branch runs after the facing enforcement above, so an unconditional
    // ctrlshow true here put the dark glass back on screen the moment it had been hidden, and an off machine
    // viewed from the back showed a black rectangle floating on its own case. the battery fill has to go for the
    // same reason: it is chrome on a screen that is not facing the operator.
    private _revOff = uiNamespace getVariable ["ACME_vent_flipped", false];
    _sbg ctrlShow (!_revOff);
    { private _c = _dlg displayCtrl _x; if (!isNull _c) then { _c ctrlShow false; }; } forEach [87713, 87716];
    [] call ACME_fnc_ventFaceGate;  // exitwith skips the end of the tick, so the gate runs here too.
};

// the brightness veil, every frame. fn_ventveilraise re-creates it whenever it is no longer the topmost
// control, which is what keeps it above everything built with ctrlcreate: the self-test ring, the ALERTS and
// PARAMS layouts, the logbook, the graph, the alarm window and the level popup. a static control could not do
// that, because ctrlcreate always appends above the static ones.
[] call ACME_fnc_ventVeilRaise;

// knob rotation flash, cleanup. the handler only ever toggles on a step, so the last step of a scroll can leave
// the overlay up. clear it once the dial has been still for a moment. the window is longer than the scroll
// cooldown, 0.065, so it cannot blink out between two steps of a continuous turn.
private _kFlashT = uiNamespace getVariable ["ACME_vent_knobFlashT", -1];
if (_kFlashT >= 0 && {(diag_tickTime - _kFlashT) > 0.18}) then {
    private _kc2 = _dlg displayCtrl 87703;
    if (!isNull _kc2) then { _kc2 ctrlShow false; };
    uiNamespace setVariable ["ACME_vent_knobFlashOn", false];
    uiNamespace setVariable ["ACME_vent_knobFlashT", -1];
};

// top bar: the battery and the alarm square.
// the battery and plug icon. the machine does run flat, in fn_ventbatterytick, so this icon reports the machine
// rather than a guess about the medic. it used to read ACME_vent_batteryState, which nothing in the addon ever
// writes, and then fall back to whether the player is in a vehicle. so it showed plugged for a medic sitting
// in a truck holding a ventilator running on its own cells, and never once showed charging. the icon is on
// every screen now, so it has to be right.
// external power and not yet full gives charging.
// external power and full gives plugged.
// running on its own cells gives the default.
// it reads from the bound target, because the battery belongs to the machine on that casualty. with no target,
// which is presetting a carried machine, there is nothing to read, so the old vehicle heuristic stands in.
private _battTgt = uiNamespace getVariable ["ACME_vent_target", objNull];
private _battIco = switch (missionNamespace getVariable ["ACME_vent_batteryState", ""]) do {
    case "charging": { "vent_battery_charging" };
    case "plugged":  { "vent_battery_plugged" };
    case "default":  { "vent_battery_default" };
    default {
        if (!isNull _battTgt && {_battTgt getVariable ["ACME_vent_configured", false]}) then {
            private _ext = _battTgt getVariable ["ACME_vent_battExternal", false];
            private _pct = _battTgt getVariable ["ACME_vent_battery", 100];
            if (_ext) then {
                if (_pct < 99.5) then { "vent_battery_charging" } else { "vent_battery_plugged" }
            } else { "vent_battery_default" };
        } else {
            // no machine is bound yet, so fall back to whether the medic is under external power.
            if (!isNull objectParent ACE_player) then { "vent_battery_plugged" } else { "vent_battery_default" }
        };
    };
};
private _battC = _dlg displayCtrl 87713;
if (!isNull _battC) then {
    private _want = format ["\acm_extended\ui\vent\%1_ca.paa", _battIco];
    if ((uiNamespace getVariable ["ACME_vent_battIcoCur", ""]) != _want) then {
        _battC ctrlSetText _want;  // on change only. a ctrlSetText every frame is a texture
        uiNamespace setVariable ["ACME_vent_battIcoCur", _want];  // reload, and it will flicker.
    };
};

// charge fill.
// the art is a hollow outline now, so the bar inside it is drawn here. it shrinks as the charge falls and
// shifts color as it goes. the color is not decorative. it tracks the alarm bands the machine already uses,
// so the bar says the same thing the alarm list would:
// above 25 percent is cyan, which is healthy with no alarm.
// 25 percent down to 10 percent runs cyan to amber, which is the low battery band.
// 10 percent down to 0 runs amber to red, which is the battery critical band.
// holding cyan until 25 percent matters. a bar that starts warming at 80 percent tells you something is wrong
// when nothing is, and a medic learns to ignore it.
private _bFill = _dlg displayCtrl 87716;
if (!isNull _bFill) then {
    private _bfRect = uiNamespace getVariable ["ACME_vent_battFillRect", []];
    if (count _bfRect == 4) then {
        _bfRect params ["_bfX","_bfY","_bfW","_bfH"];
        // the same holder the swap writes to. the fitted battery lives on the casualty when one is connected and on
        // the medic when a medic carries the machine, so reading only the casualty meant a battery swapped on an
        // unconnected machine showed the old charge until it was hooked up.
        private _battHolder = if (isNull _battTgt) then { ACE_player } else { _battTgt };
        private _pctB = _battHolder getVariable ["ACME_vent_battery", 100];
        _pctB = (_pctB max 0) min 100;

        private _lowAt  = missionNamespace getVariable ["ACME_vent_batteryLowPct", 25];
        private _critAt = missionNamespace getVariable ["ACME_vent_batteryCritPct", 10];

        private _cyan  = [0.000, 0.988, 0.992];  // #00fcfd.
        private _amber = [0.898, 0.714, 0.333];  // #e5b655.
        private _red   = [0.839, 0.239, 0.153];  // #d63d27.
        private _mix = {
            params ["_a","_b","_t"];
            _t = (_t max 0) min 1;
            [ (_a select 0) + ((_b select 0) - (_a select 0)) * _t,
              (_a select 1) + ((_b select 1) - (_a select 1)) * _t,
              (_a select 2) + ((_b select 2) - (_a select 2)) * _t ]
        };
        private _rgb = switch (true) do {
            case (_pctB > _lowAt):  { _cyan };
            case (_pctB > _critAt): { [_cyan, _amber, 1 - ((_pctB - _critAt) / ((_lowAt - _critAt) max 1))] call _mix };
            default                 { [_amber, _red, 1 - (_pctB / (_critAt max 1))] call _mix };
        };

        // below critical the bar stops being a gauge and becomes a warning. it holds a small red sliver and blinks
        // rather than shrinking to nothing, because a bar that has vanished looks the same as a bar that was never
        // there. it keeps blinking until the machine actually stops.
        private _frac = _pctB / 100;
        private _show = true;
        if (_pctB <= _critAt) then {
            _frac = (missionNamespace getVariable ["ACME_vent_battSliverFrac", 0.14]);
            private _hz = missionNamespace getVariable ["ACME_vent_battBlinkHz", 2];
            _show = ((floor (diag_tickTime * _hz * 2)) mod 2) isEqualTo 0;
        };
        if (_pctB <= 0) then { _show = false; };

        private _w = (_bfW * _frac) max 0;
        _bFill ctrlSetPosition [_bfX, _bfY, _w, _bfH];
        _bFill ctrlSetBackgroundColor [_rgb select 0, _rgb select 1, _rgb select 2, 1];
        _bFill ctrlCommit 0;
        _bFill ctrlShow _show;
    };
};

// the alarm box, on the plug slot, right of the battery. it is the one box in that corner. it carries the t, z
// or c trigger letter when the machine is calm, and when something is wrong it carries the letter code of the
// highest priority active alarm on a red field. it is a letter rather than a count, so a medic reads what is
// wrong at a glance: P for pressure, A for apnea, DC for a disconnect, the way they read a rhythm.
private _alarmBox = _dlg displayCtrl 87714;
if (!isNull _alarmBox) then {
    private _tgtA = uiNamespace getVariable ["ACME_vent_target", objNull];
    private _anyA = if (isNull _tgtA) then {[]} else {_tgtA getVariable ["ACME_vent_alarms", []]};
    private _statA = if (isNull _tgtA) then {""} else {_tgtA getVariable ["ACME_vent_status", ""]};
    private _silA = if (isNull _tgtA) then {0} else {_tgtA getVariable ["ACME_vent_alarmSilencedUntil", 0]};
    private _showRed = (count _anyA > 0) && {CBA_missionTime >= _silA};
    if (_showRed) then {
        // the highest-priority active alarm wins the box. severity 3, HIGH, beats 2, which beats 1, and within a tier
        // the first in the list wins. its letter goes on the red field.
        private _top = _anyA select 0;
        private _topSev = [_top] call ACME_fnc_ventAlarmSeverity;
        {
            private _s = [_x] call ACME_fnc_ventAlarmSeverity;
            if (_s > _topSev) then { _top = _x; _topSev = _s; };
        } forEach _anyA;
        private _letter = [_top] call ACME_fnc_ventAlarmLetter;
        _alarmBox ctrlSetBackgroundColor ([[0.86, 0.08, 0.08, 1]] call ACME_fnc_ventColor);
        _alarmBox ctrlSetText _letter;
        _alarmBox ctrlSetTextColor ([[1, 1, 1, 1]] call ACME_fnc_ventColor);
        _alarmBox ctrlSetFont "PuristaSemibold";
        // a two-character code gets a slightly smaller glyph, so it still fits the one-slot box. the box is
        // center-aligned, at style=2 in config, so the letter sits in the middle of the red square.
        _alarmBox ctrlSetFontHeight ((ctrlPosition _alarmBox) select 3) * (if (count _letter > 1) then {0.66} else {0.92});
    } else {
        // calm. the field is transparent, so the black block shows through, and the t, z or c trigger letter is white.
        // it is blank when there is no trigger, so the corner stays quiet until the machine has something to say.
        _alarmBox ctrlSetBackgroundColor ([[0, 0, 0, 0]] call ACME_fnc_ventColor);
        _alarmBox ctrlSetText _statA;
        _alarmBox ctrlSetTextColor ([[1, 1, 1, 1]] call ACME_fnc_ventColor);
        _alarmBox ctrlSetFont "PuristaSemibold";
        _alarmBox ctrlSetFontHeight ((ctrlPosition _alarmBox) select 3) * 0.86;
    };
};
private _scr = uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]];
_scr params ["_scrX","_scrY","_scrW","_scrH"];
// shutdown sequence.
// this is the startup sequence run again on the way out: the same white window, the same logo, half the
// duration, and POWERING OFF... across the top. reusing the boot controls rather than building a second screen
// means the two can never drift apart. if the boot art or the window inset changes, the shutdown follows it
// for free.
// it sits above the boot branch and exits, so a shutdown always wins over anything else the panel wanted to
// draw.
private _shutT0 = uiNamespace getVariable ["ACME_vent_shutT0", -1];
if (_shutT0 >= 0) exitWith {
    private _shutDur = uiNamespace getVariable ["ACME_vent_shutDur", 1.2];
    private _elapsed = diag_tickTime - _shutT0;

    { (_dlg displayCtrl _x) ctrlShow false } forEach _opCtrls;
    // the same facing rule as the power-off branch. a shutdown animation playing on the back of the device is a
    // black rectangle on its case.
    (_dlg displayCtrl 87710) ctrlShow (!(uiNamespace getVariable ["ACME_vent_flipped", false]));

    // the identical window inset boot uses, measured from the inlay art, so the white lands inside the rounded
    // corners of the screen instead of poking out through them.
    // measured off the inlay art, its transparent window runs y 0.1347 to 0.8682. the old 0.132 to 0.873 overshot
    // it at both ends, so the white poked into the white bars. the 0.006 side bleed carries the white out to the
    // bezel instead of stopping a pixel or two short of the frame.
    // the width and the left edge are unchanged. only the bottom moves.
    // the splash is placed in screen-rect units, which are 0.16940 of the face tall, and the bottom bar it has to
    // meet belongs to the art at 0.17041. so a bottom of 0.8705 landed at 0.14746 of the face while the bar starts
    // at 0.14795, a gap of 0.00049, which is the dark line. 0.8780 lands at 0.14871 and overlaps it.
    private _sTop = 0.1347; private _sH = 0.8780 - 0.1347;
    private _sBleed = 0.006;
    (_dlg displayCtrl 87710) ctrlSetPosition [_scrX - _scrW*_sBleed, _scrY + _scrH*_sTop, _scrW*(1 + 2*_sBleed), _scrH*_sH];
    (_dlg displayCtrl 87710) ctrlSetBackgroundColor [1,1,1,1];  // substrate: pure white, literal.
    (_dlg displayCtrl 87710) ctrlCommit 0;
    (_dlg displayCtrl 87760) ctrlShow true;  // the boot logo, again.

    // POWERING OFF... across the top of the white window. it is created once and torn down with the panel.
    private _st = uiNamespace getVariable ["ACME_vent_shutTitle", controlNull];
    if (isNull _st) then {
        _st = _dlg ctrlCreate ["RscText", -1];
        _st ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
        _st ctrlSetTextColor ([[0.06, 0.06, 0.06, 1]] call ACME_fnc_ventColor);  // black ink, because the window is white here.
        _st ctrlSetText "POWERING OFF...";
        uiNamespace setVariable ["ACME_vent_shutTitle", _st];
    };
    _st ctrlSetPosition [_scrX, _scrY + _scrH * (_sTop + 0.015), _scrW, _scrH * 0.10];
    _st ctrlSetFontHeight (_scrH * 0.085);
    _st ctrlCommit 0;
    _st ctrlShow true;

    if (_elapsed < _shutDur) exitWith {};

    // the sequence is complete, so the machine now stops.
    uiNamespace setVariable ["ACME_vent_shutT0", -1];
    [] call ACME_fnc_ventPowerDown;
    [] call ACME_fnc_ventFaceGate;  // exitwith skips the end of the tick.
};

if (_booting) then {
    { (_dlg displayCtrl _x) ctrlShow false } forEach _opCtrls;
    { (_dlg displayCtrl _x) ctrlShow true } forEach [87710];  // screen background. the inlay provides the bars now.
    // startup sequence. the white background fills the window between the white bars of the inlay, from 0.132 to
    // 0.873, measured from the inlay art. it used to span the full screen rect, 0 to 1, and because this is a
    // square control while the screen of the device is rounded, its sharp corners overshot the rounded corners of
    // the bezel and cut into them. insetting it to the real window means it sits exactly between the bars, so the
    // corners land inside the rounding instead of poking out through it.
    // the bottom only, exactly as the shutdown splash above. the width and the left edge are untouched.
    private _bootTop = 0.1347; private _bootH = 0.8780 - 0.1347;
    private _sBleed = 0.006;
    (_dlg displayCtrl 87710) ctrlSetPosition [_scrX - _scrW*_sBleed, _scrY + _scrH*_bootTop, _scrW*(1 + 2*_sBleed), _scrH*_bootH];
    // blackout phase. for the first fraction of a second the panel is dead black, with no white, no logo and no
    // inlay. this branch runs every frame while booting, so without this check it would re-light the splash
    // immediately and the blackout set up in ventPanelInit would never be seen.
    if (diag_tickTime < (uiNamespace getVariable ["ACME_vent_blackoutUntil", 0])) then {
        (_dlg displayCtrl 87710) ctrlSetBackgroundColor [0,0,0,1];  // substrate: a literal blackout.
        (_dlg displayCtrl 87710) ctrlCommit 0;
        (_dlg displayCtrl 87760) ctrlShow false;
    } else {
        (_dlg displayCtrl 87710) ctrlSetBackgroundColor [1,1,1,1];  // substrate: pure white, literal.
        (_dlg displayCtrl 87710) ctrlCommit 0;
        (_dlg displayCtrl 87760) ctrlShow true;
    };
} else {
    if (_bootT0 >= 0) then {
        // boot just finished. clear the flag, restore the normal dark screen, both the rect and the color, and run the
        // automatic self-test before routing to the real first screen. read configured from the bound target, the
        // patient the panel is bound to, and not from ACE_player, so it decides live against setup correctly.
        uiNamespace setVariable ["ACME_vent_bootT0", -1];
        (_dlg displayCtrl 87760) ctrlShow false;
        (_dlg displayCtrl 87710) ctrlSetPosition [_scrX, _scrY + _scrH*0.132, _scrW, _scrH*0.741];  // the measured window runs 0.132 to 0.873.
        (_dlg displayCtrl 87710) ctrlSetBackgroundColor [0.02,0.03,0.04,1];  // substrate: literal. back to black for everything else.
        (_dlg displayCtrl 87710) ctrlCommit 0;
        private _target = uiNamespace getVariable ["ACME_vent_target", ACE_player];
        private _configured = _target getVariable ["ACME_vent_configured", false];
        uiNamespace setVariable ["ACME_vent_postSelfTest", if (_configured) then {"live"} else {"weight"}];
        ["selftest"] call ACME_fnc_ventPanelShowScreen;
    };

    // self-test ring, on the self-test screen only. it uses discrete steps of about 12.5 percent, plus the startup
    // sound.
    // there is also a stale middle-click watchdog. a button-down stamp only ever legitimately lives for the length
    // of a hold, which is 4 s to power off. if one is still sitting there well past that, the matching button-up
    // was never delivered, which happens when focus is lost mid-click. left alone it wedges the next select. it is
    // cleared here, so the panel always recovers by itself rather than needing to be closed and reopened.
private _mmbT = uiNamespace getVariable ["ACME_vent_mmbDown", -1];
if (_mmbT > 0 && {(diag_tickTime - _mmbT) > (missionNamespace getVariable ["ACME_vent_mmbStaleSec", 8])}) then {
    uiNamespace setVariable ["ACME_vent_mmbDown", -1];
    uiNamespace setVariable ["ACME_vent_mmbFired", false];
    [] call ACME_fnc_ventHoldClear;
};

// alarm indicator flash, at the rates the device manual specifies.
// LOW is yellow and constant on, at 0 hz with a duty of 100 percent.
// medium is yellow at 0.45 hz with a duty of 50 percent.
// HIGH is red at 2 hz with a duty of 50 percent.
// a 50 percent duty cycle means the indicator is lit for half of each period, so the phase test is simply the
// first half of the cycle. the field is toggled between its fill color and white rather than being hidden,
// because the window frame is white on this device and blinking to white is what reads as the indicator going
// dark.
// it gates on the window actually being open. without this the driver kept running after a medic dismissed the
// alarm window. the controls of the window are deleted on close, and ACME_vent_alarmFillCtrl still held that
// handle, and arma recycles control handles. so the flash carried on recoloring whatever control had since
// inherited the number, which is the blinking box that appeared off in the corner whenever the panel was open.
// the flash driver was painting an innocent bystander.
private _flashHz = uiNamespace getVariable ["ACME_vent_alarmFlashHz", 0];
private _fillCtrl = uiNamespace getVariable ["ACME_vent_alarmFillCtrl", controlNull];
if ((uiNamespace getVariable ["ACME_vent_alarmWinOpen", false])
    && {!isNull _fillCtrl} && {_flashHz > 0}) then {
    private _period = 1 / _flashHz;
    private _on = ((diag_tickTime % _period) < (_period * 0.5));  // a duty cycle of 50 percent.
    private _col = if (_on) then {
        uiNamespace getVariable ["ACME_vent_alarmFillCol", [0.93,0.78,0.10,1]]
    } else {
        [1,1,1,1]
    };
    _fillCtrl ctrlSetBackgroundColor _col;
};

if ((uiNamespace getVariable ["ACME_vent_screen", "live"]) == "selftest") then {
        // self-test audio, queued as one sequence: startup, then the running clip underneath the test as it counts up,
        // then shutdown the moment the ring reaches 100 percent. each clip is one-shot through playSound3D and guarded
        // by its own flag, so nothing retriggers or overlaps itself. all three flags are re-armed in
        // fn_ventpanelshowscreen when a medic enters the self-test screen, so every power-on plays the full sequence.
        // this is the panel's own sequence and is deliberately independent of the server-side sound engine, which
        // handles a vent that is actually ventilating a casualty.
        if !(uiNamespace getVariable ["ACME_vent_stStartupPlayed", false]) then {
            uiNamespace setVariable ["ACME_vent_stStartupPlayed", true];
            playSound3D ["acm_extended\sound\ventilator_startup_sfx.ogg", ACE_player, false, getPosASL ACE_player, 3, 1, 30];

            // both following clips are scheduled off this moment, not off the progress ring. the shutdown used to be fired
            // by the step that filled the ring, which meant its timing depended on how the ring happened to advance.
            // playSound3D cannot be stopped once started, so any drift showed up as the running hum still sounding
            // underneath the spool-down. scheduling both from one anchor makes the audio exact and leaves the ring free to
            // be purely cosmetic.
            private _ov   = missionNamespace getVariable ["ACME_vent_sndOverlap", 0.11];
            private _sLen = missionNamespace getVariable ["ACME_vent_startupSndLen", 2.324];
            private _rLen = missionNamespace getVariable ["ACME_vent_runningSndLen", 5.721];
            private _runAt  = (_sLen - _ov) max 0;  // it starts one overlap under the startup tail,
            private _shutAt = _runAt + ((_rLen - _ov) max 0);  // and the spool-down starts one overlap under the hum tail.

            [{
                if ((uiNamespace getVariable ["ACME_vent_screen", ""]) != "selftest") exitWith {};
                if (uiNamespace getVariable ["ACME_vent_stRunPlayed", false]) exitWith {};
                uiNamespace setVariable ["ACME_vent_stRunPlayed", true];
                playSound3D ["acm_extended\sound\ventilator_running_sfx.ogg", ACE_player, false, getPosASL ACE_player, 3, 1, 30];
            }, [], _runAt] call CBA_fnc_waitAndExecute;

            [{
                if ((uiNamespace getVariable ["ACME_vent_screen", ""]) != "selftest") exitWith {};
                if (uiNamespace getVariable ["ACME_vent_stShutPlayed", false]) exitWith {};
                uiNamespace setVariable ["ACME_vent_stShutPlayed", true];
                playSound3D ["acm_extended\sound\ventilator_shutdown_sfx.ogg", ACE_player, false, getPosASL ACE_player, 3, 1, 30];
            }, [], _shutAt] call CBA_fnc_waitAndExecute;
        };
        if (diag_tickTime >= (uiNamespace getVariable ["ACME_vent_stStepNextT", 0])) then {
            private _step = uiNamespace getVariable ["ACME_vent_stStep", 0];
            if (_step < 8) then {
                _step = _step + 1;
                uiNamespace setVariable ["ACME_vent_stStep", _step];
                uiNamespace setVariable ["ACME_vent_stStepNextT", diag_tickTime + (uiNamespace getVariable ["ACME_vent_stStepInt", 0.943])];
                // the spool-down is no longer fired here. it is scheduled off the start of the self-test, so its timing cannot
                // drift with the ring. the ring is cosmetic and paced to land alongside it.
                private _dots = uiNamespace getVariable ["ACME_vent_stDots", []];
                private _n = count _dots;
                private _filled = round (_n * _step / 8);
                for "_i" from 0 to (_n - 1) do {
                    (_dots select _i) ctrlSetBackgroundColor (if (_i < _filled) then {[0.35,0.75,0.95,1]} else {[0.14,0.18,0.24,1]});
                };
                private _pct = uiNamespace getVariable ["ACME_vent_stPct", controlNull];
                if (!isNull _pct) then { _pct ctrlSetStructuredText parseText format ["<t align='center' color='#e6f2ff'>%1%2</t>", floor (_step / 8 * 100), "%"]; };
            } else {
                // it is held one interval at 100 percent, then routes on to the real first screen.
                [uiNamespace getVariable ["ACME_vent_postSelfTest", "weight"]] call ACME_fnc_ventPanelShowScreen;
            };
        };
    };

    // live gauge animation, on the live screen only.
    if ((uiNamespace getVariable ["ACME_vent_screen", "live"]) == "live") then {
    private _sr = uiNamespace getVariable ["ACME_vent_scrRect", [0,0,0.2,0.18]];
    _sr params ["_sx","_sy","_sw","_sh"];
    private _bpm = uiNamespace getVariable ["ACME_vent_bpm", 12];
    private _period = 60 / (_bpm max 1);
    private _phase = (diag_tickTime mod _period) / _period;  // 0 to 1 within a breath.
    // airway pressure over the breath, as a fraction of the gauge span. it is continuous: it rises from the PEEP
    // baseline and falls back to it, so there is no discontinuity at the wrap. the old curve started at 0 and
    // ended at 0.12, which snapped every breath.
    private _peep = 0.12;
    // scale the gauge to the real peak pressure from the drive engine, across the 0 to 50 cmH2O span, so a stiff
    // lung under volume control visibly pegs the bar instead of every breath looking identical.
    private _vTgP = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    private _pipReal = if (isNull _vTgP) then { 20 } else { _vTgP getVariable ["ACME_vent_pip", 20] };
    if (_simple) then { _peep = (_effectiveFrame select 5) / 60; };

    // smoothed peak. the drive engine recomputes PIP whenever anything feeding it changes, so turning the vt or BPM
    // dial stepped the peak to a new value between one frame and the next and the bar jumped rather than moved. a
    // real gauge cannot do that, because the pressure it shows is a physical quantity with mass behind it.
    // the displayed peak now eases toward the computed one at a fixed rate per second, so a dial turn is a ramp
    // across roughly a second instead of a jump, and holding the dial gives a continuous sweep rather than a
    // staircase. the waveform shape below is unchanged, and only the height it is scaled against is smoothed.
    private _pipShown = uiNamespace getVariable ["ACME_vent_pipShown", -1];
    if (_pipShown < 0) then { _pipShown = _pipReal; };  // first frame. adopt the value rather than ramping from zero.
    private _rate = missionNamespace getVariable ["ACME_vent_gaugeEaseRate", 2.2];  // per second.
    private _kEase = ((diag_deltaTime * _rate) max 0) min 1;
    _pipShown = _pipShown + ((_pipReal - _pipShown) * _kEase);
    uiNamespace setVariable ["ACME_vent_pipShown", _pipShown];

    private _pipFrac = ((_pipShown / 60) max 0.15) min 1;  // full scale is 60 cmH2O.
    private _pNow = switch (true) do {
        case (_phase < 0.35): { _peep + (_pipFrac - _peep) * (_phase / 0.35) };  // rise from PEEP to PIP.
        case (_phase < 0.55): { _pipFrac };  // plateau at PIP.
        default { _peep + (_pipFrac - _peep) * ((1 - ((_phase - 0.55) / 0.45)) max 0) };  // fall back to PEEP.
    };

    // manual breath excursion. the machine's own cycle only runs in a mandatory mode, so on CPAP, or on a vent
    // that is connected and not driving, a manual breath would move real gas while the gauge sat flat and the
    // operator saw nothing happen. the breath is overlaid here as a rise, a plateau and a fall over its own short
    // window, and it takes whichever pressure is higher, so it also reads correctly when it lands on top of a
    // machine breath.
    // a cough spikes the airway pressure and the gauge must show it, or "C" is a letter with no consequence. the
    // patient fighting the tube drives the needle up exactly as the machine would, which is the point: an
    // unsedated intubated casualty is barotraumatising themselves, and you can watch them do it.
    private _coughUntil = if (isNull _tgtM) then {0} else {_tgtM getVariable ["ACME_vent_coughUntilT", 0]};
    if (CBA_missionTime < _coughUntil) then {
        private _cPIP = if (isNull _tgtM) then {0} else {_tgtM getVariable ["ACME_vent_coughPIP", 0]};  // full scale is 60 cmH2O.
        private _cFrac = (_cPIP / 60) min 1;  // full scale is 60 cmH2O
        _pNow = _pNow max _cFrac;
    };

    private _mbT = uiNamespace getVariable ["ACME_vent_manualGaugeT", -999];
    private _mbDur = missionNamespace getVariable ["ACME_vent_manualGaugeDur", 1.4];
    private _mbEl = diag_tickTime - _mbT;
    if (_mbEl >= 0 && {_mbEl < _mbDur}) then {
        private _mbPhase = _mbEl / _mbDur;
        private _mbP = switch (true) do {
            case (_mbPhase < 0.35): { _peep + (_pipFrac - _peep) * (_mbPhase / 0.35) };
            case (_mbPhase < 0.55): { _pipFrac };
            default { _peep + (_pipFrac - _peep) * ((1 - ((_mbPhase - 0.55) / 0.45)) max 0) };
        };
        _pNow = _pNow max _mbP;
    };
    // held peak. it never snap-resets at the wrap, which made the blue bar vanish and reappear. instead the peak
    // decays gently toward the current pressure, so as the green rises the blue shrinks to nothing, and as the
    // green falls the blue grows back in behind it. it is continuous in both directions.
    private _peak = uiNamespace getVariable ["ACME_vent_gaugePeak", 0];
    // the peak decay must be much slower than the rate the green falls, or the peak chases the green down and the
    // blue gap never opens. that is exactly what happened: at 0.55/s the green falls at about 0.12/s, so the peak
  // span per second.
    private _decay = missionNamespace getVariable ["ACME_vent_gaugePeakDecay", 0.04];  // span per second
    _peak = (_peak - (_decay * diag_deltaTime)) max _pNow;
    uiNamespace setVariable ["ACME_vent_gaugePeak", _peak];
    uiNamespace setVariable ["ACME_vent_gaugeLastPhase", _phase];
    // the gauge frame occupies screen fractions x 0.87 to 0.96 and y 0.15 to 0.62, ending above the white bottom
    // bar.
    private _gx = _sx + _sw*0.87; private _gw = _sw*0.09;
    // this must match the gauge frame and scale placed in fn_ventpanelinit, at 0.150 to 0.855. it was kept in step
    // by hand, at the old bottom, so the bars were drawn against a different bottom edge than the frame and the
    // numerals were. that is half of why the bar did not line up with the ticks.
    private _gTop = _sy + _sh*0.150; private _gBot = _sy + _sh*0.855;
    private _gFullH = _gBot - _gTop;
    // the gauge color reflects the airway pressure state from the drive engine. green is safe, amber is caution
    // at about 30 cmH2O or more, and red is danger at about 35 or more. at danger the lung is accumulating
    // barotrauma, and the fix is to drop to SIMV pc, which caps pressure, or to back the vt down.
    private _vTg = uiNamespace getVariable ["ACME_vent_target", ACE_player];
    private _pipState = if (isNull _vTg) then { 0 } else { _vTg getVariable ["ACME_vent_pipState", 0] };  // danger: red.
    private _greenCol = switch (_pipState) do {  // caution: amber.
        case 2: { [0.95,0.25,0.20,1] };  // safe: green.
        case 1: { [0.98,0.72,0.15,1] };  // caution: amber
        default { [0.35,0.85,0.45,1] };  // safe: green
    };
    private _peakCol = switch (_pipState) do {
        case 2: { [0.70,0.15,0.15,1] };  // a normal peak. the pressure bar keeps its own blue, unchanged.
        case 1: { [0.75,0.50,0.10,1] };
        default { [0.28,0.55,0.92,1] };  // normal peak: the pressure bar keeps its own blue, unchanged
    };
    (_dlg displayCtrl 87731) ctrlSetBackgroundColor _greenCol;
    (_dlg displayCtrl 87732) ctrlSetBackgroundColor _peakCol;
    // green is the current pressure, which rises and falls each breath. blue is the space the green vacates as it
    // decays, from the green top up to the held peak, so the peak reads as a shrinking green plus a growing blue
    // that together always reach the peak line of this breath.
    // the bar must start at the zero tick, not at the bottom of the frame.
    // the scale maps a value onto 0.05 plus 0.90 times frac of the frame height, so 0 cmH2O is 5 percent above the
    // bottom edge of the frame. the bar, though, was drawn from the frame bottom upward, so it always carried a 5
    // percent pedestal hanging below the 0 mark and its foot never sat on zero. it is anchored to the zero line
  // the y of the 0 cmH2O tick.
  // 0 gives zero height, sitting exactly on the 0 tick.
    private _zeroY  = _gBot - (_gFullH * 0.05);  // y of the 0 cmH2O tick
    private _greenH = _gFullH * 0.90 * _pNow;  // 0 -> zero height, sitting exactly on the 0 tick
    private _peakH  = _gFullH * 0.90 * _peak;
    // green fills from the bottom to the current level.
    (_dlg displayCtrl 87731) ctrlSetPosition [_gx, _zeroY - _greenH, _gw, _greenH];
    (_dlg displayCtrl 87731) ctrlCommit 0;  // the gap between the current pressure and the held peak.
    // blue fills the gap between the current green top and the peak top.
    private _blueSegH = (_peakH - _greenH) max 0;  // the gap between current pressure and the held peak
    (_dlg displayCtrl 87732) ctrlSetPosition [_gx, _zeroY - _peakH, _gw, _blueSegH];
    (_dlg displayCtrl 87732) ctrlCommit 0;

    // live measured breaths. the parenthetical in "20 (18)" is the actual respiration rate of the patient, and it
    // must track in real time. change the set rate and you watch the breaths of the patient move toward it, with
    // no interaction needed. the true rate the vent enforces is instant, which is correct for gas exchange, and a
    // number that teleports reads as broken. so the displayed value ramps toward the real rate a step per tick,
    // which is what makes it visibly slide to the new setting. it refreshes every tick, rather than on a 3 s timer
    // or only when the operator scrolls, and it is skipped while a medic edits the BPM field, so the set number is
    // not stomped.
    private _bpmSet = uiNamespace getVariable ["ACME_vent_bpm", 12];
    // a nan is type SCALAR, so isEqualType 0 does not catch it. detect it the only way sqf can: nan is the one
    // value not equal to itself. any non-number or nan falls back to a safe default. this is the real cause of the
    // empty "()". a nan respiration rate seeded _shown, and nan <= 0 and nan > 0 are both false, so the digit
    // builder skipped its zero-guard, ran a loop that never appended, and returned an empty string.
    if (!(_bpmSet isEqualType 0) || {_bpmSet != _bpmSet}) then { _bpmSet = 12; };
    private _selL = uiNamespace getVariable ["ACME_vent_sel", "none"];
    private _editL = uiNamespace getVariable ["ACME_vent_editing", false];
    if (!(_selL == "bpm" && {_editL})) then {
        // measured rate source. read the ventilator's own published delivered rate. going through the
        // ACM_breathing_RespirationRate of the patient meant the readout only updated when ACM's breathing loop
        // happened to call updateRespirationRate, which it may never do for a paralyzed apneic casualty, so the
        // parenthetical sat at 0 while the machine was plainly cycling. ACME_vent_measRR is written every drive tick
        // by the vent itself. -1 means the vent is not driving, in which case fall back to the patient's own
        // spontaneous rate, which is the right number under CPAP and when disconnected, and finally to the set rate.
        // the measured rate is a count, not a model, and it is shown as it is.
        // everything that used to sit here was fallback. if the vent published nothing, take the casualty's own rate.
        // if that was zero and the machine was in a mandatory mode, take the set rate as a floor. the reasoning was
        // that a machine in a mandatory mode cannot be delivering zero. that is true of a machine that is running and
        // exactly backwards for one that has stopped, and it meant a disconnected ventilator displayed its set rate
        // and looked perfectly healthy.
        // fn_ventdrivetick now counts real delivered breaths over a rolling sixty seconds, manual ones included, and
        // stops adding to that window the moment it stops driving. so the number falls away on its own when the
        // machine stops, which is the reading that matters. there is no floor and no substitution.
        private _rrRaw = if (isNull _tgtM) then { 0 } else {
            private _vm = _tgtM getVariable ["ACME_vent_measRR", -1];
            if (_vm isEqualType 0 && {_vm >= 0}) then {
                _vm
            } else {
                // it was never driven on this casualty, so there is no window to read. show what they are doing themselves,
                // which is what the flow sensor of the circuit would pick up.
                private _own = _tgtM getVariable ["ACM_breathing_RespirationRate", 0];
                if (_own isEqualType 0 && {_own > 0}) then { round _own } else { 0 }
            };
        };

  // belt and suspenders after the arithmetic.
        if (!(_rrRaw isEqualType 0) || {_rrRaw != _rrRaw}) then { _rrRaw = _bpmSet };
        private _rrTarget = (round _rrRaw) max 0;
        if (_rrTarget != _rrTarget) then { _rrTarget = _bpmSet };  // belt and suspenders after the arithmetic
        // ramp the shown value toward the target, up to a few breaths per second, so it slides rather than snaps.
        private _shown = uiNamespace getVariable ["ACME_vent_measBpm", _rrTarget];
        if (!(_shown isEqualType 0) || {_shown != _shown}) then { _shown = _rrTarget };
        private _dt2 = diag_deltaTime;
        if (!(_dt2 isEqualType 0) || {_dt2 != _dt2} || {_dt2 < 0}) then { _dt2 = 0 };
        private _rate = (missionNamespace getVariable ["ACME_vent_measBpmRampPerSec", 6]) * _dt2;  // if the ramp math ever went nan, reset to the target.
        private _delta = _rrTarget - _shown;  // snap the last fraction so it settles cleanly.
        _shown = _shown + ((_delta max (-_rate)) min _rate);
        if (_shown != _shown) then { _shown = _rrTarget };  // if the ramp math ever went nan, reset to target
        if (abs _delta < 0.6) then { _shown = _rrTarget; };  // snap the last fraction so it settles cleanly
        uiNamespace setVariable ["ACME_vent_measBpm", _shown];
        // build the readout from raw digits. coerce to a clean, nan-free, non-negative integer first.
        private _setInt  = round (parseNumber (str _bpmSet));  if (_setInt  != _setInt)  then { _setInt  = 0 };
        private _measInt = round (parseNumber (str _shown));   if (_measInt != _measInt) then { _measInt = 0 };
        _setInt  = _setInt  max 0;
        _measInt = _measInt max 0;
        private _digits = ["0","1","2","3","4","5","6","7","8","9"];  // a nan-safe zero guard.
        private _toStr = {
            params ["_n"];
            if (!(_n isEqualType 0) || {_n != _n} || {_n <= 0}) exitWith {"0"};  // nan-safe zero guard
            private _s = "";
            while {_n > 0} do { _s = (_digits select (_n mod 10)) + _s; _n = floor (_n / 10); };
            _s
        };
        private _setStr  = [_setInt]  call _toStr;
        private _measStr = [_measInt] call _toStr;
        // a final belt. whatever happened upstream, neither half can be blank. an empty string here is the only way
        // the readout can show "()", so force a literal "0" if either builder ever returns nothing.
        if (_setStr  isEqualTo "") then { _setStr  = "0"; };
        if (_measStr isEqualTo "") then { _measStr = "0"; };
        private _txt = _setStr + " (" + _measStr + ")";
        (_dlg displayCtrl 87721) ctrlSetText _txt;
    };
    };

    // graph waveform sweep, on the graph screen only.
    // a cursor advances at a fixed time-base, writing live samples of the pressure or flow morphology into filled
    // columns and blanking a small gap ahead of it, like a real monitor sweep. pressure is positive only, running
    // from the PEEP baseline to the PIP plateau and then falling. flow is bidirectional, with a decelerating
    // inspiration and an expiratory dip.
    if ((uiNamespace getVariable ["ACME_vent_screen", "live"]) == "graph") then {
        private _cols = uiNamespace getVariable ["ACME_vent_graphBars", []];
        private _N = uiNamespace getVariable ["ACME_vent_graphN", 0];
        if (_N > 0 && {count _cols >= _N}) then {
            (uiNamespace getVariable ["ACME_vent_graphGeo", [0,0,0.2,0.18,0.1,false]]) params ["_fx","_fy","_fw","_fh","_axisY","_flow"];
            private _caps = uiNamespace getVariable ["ACME_vent_graphCaps", []];
            private _haveCaps = (count _caps >= _N);
            private _colW = _fw / _N;
            private _which = uiNamespace getVariable ["ACME_vent_graphType", "PRESSURE"];
            // derive the baseline from the live graph type, not the stored geo. if graphtype and geo ever disagree, such as
            // after a switch that has not rebuilt geo yet, trusting the stored _axisY drew the negative dip of the flow
            // waveform downward from the pressure floor, straight out of the bottom of the plot. recomputing here keeps
            // the waveform math and its baseline locked together whatever happens.
            _flow = (_which == "FLOW");
            _axisY = if (_flow) then { _fy + _fh*0.5 } else { _fy + _fh };  // a vt-scaled excursion.
            private _bpm = uiNamespace getVariable ["ACME_vent_bpm", 12];  // a finer time base to match the denser columns, giving a window of about 5.6 s.
            private _vt  = uiNamespace getVariable ["ACME_vent_vt", 500];
            if (_simple) then {
                private _graphTarget = uiNamespace getVariable ["ACME_vent_target", objNull];
                _vt = if (isNull _graphTarget) then {500} else {_graphTarget getVariable ["ACME_vent_vti", 500]};
            };
            private _period = 60 / (_bpm max 1);
            private _amp = ((0.6 + 0.4 * ((_vt - 300) / 500)) max 0.5) min 1.15;  // vt-scaled excursion
            private _colSecs = missionNamespace getVariable ["ACME_vent_graphColSecs", 0.04];  // finer time base to match the denser columns (~5.6 s window)
            private _acc = (uiNamespace getVariable ["ACME_vent_graphColAcc", 0]) + (diag_deltaTime / _colSecs);
            private _steps = (floor _acc) min _N;
            _acc = _acc - (floor _acc);
            private _cursor = uiNamespace getVariable ["ACME_vent_graphCursor", 0];
            // sample clock. each column represents _colSecs of time, so it must advance per column. sampling diag_tickTime
            // once per step would give every column in the same frame an identical phase and flatten the trace at high
            // column counts.
            // no input. two things mean the sensors have nothing to report: the zeroing window just after the screen
            // opens, and a machine that is not driving a patient. either way the sweep keeps moving and draws hatch
            // instead of a waveform, so the trace records that there was no input at that moment rather than pretending
            // there was a flat breath.
            private _zeroUntil = uiNamespace getVariable ["ACME_vent_graphZeroUntil", -1];
            private _zeroing = (_zeroUntil > 0) && {diag_tickTime < _zeroUntil};
            private _tgtG = uiNamespace getVariable ["ACME_vent_target", objNull];
            private _driving = (!isNull _tgtG)
                && {_tgtG getVariable ["ACME_vent_connected", false]}
                && {_tgtG getVariable ["ACME_vent_driving", false]};
            private _noInput = _zeroing || {!_driving};
            private _hatch = uiNamespace getVariable ["ACME_vent_graphHatch", []];
            private _haveHatch = (count _hatch) >= _N;
  // 1/40.
            // that is what makes it read as a continuous diagonal field rather than dots, and it is the density the
            // reference shows. the pattern is keyed to the column index, so it stays locked to the plot as the sweep wraps
            // instead of crawling.
            private _hSlope = missionNamespace getVariable ["ACME_vent_graphHatchSlope", 0.025];  // 1/40
            private _hCol = [[0.55, 0.70, 0.88, 0.85]] call ACME_fnc_ventColor;
            private _waveCol = [[0, 0, 0.996,1]] call ACME_fnc_ventColor;  // the thickness of the white outline cap.
            private _capCol  = [[0.95,0.97,1,1]] call ACME_fnc_ventColor;

            private _sampT = uiNamespace getVariable ["ACME_vent_graphSampT", diag_tickTime];
            private _capH = pixelH * 1.4;  // thickness of the white outline cap
            for "_s" from 1 to _steps do {
                _sampT = _sampT + _colSecs;
                private _phase = (_sampT mod _period) / _period;
                private _val = 0;
                private _c = _cols select _cursor;
                private _cap = if (_haveCaps) then { _caps select _cursor } else { controlNull };
                // a no-input column: three hatch marks instead of a waveform. the column and cap controls are free here,
  // a slight overlap, so neighboring columns join up.
                // array supplies the third.
                if (_noInput) then {
                    private _hx = _fx + _cursor*_colW;
                    private _hw = _colW * 1.8;  // slight overlap so neighboring columns join up
                    private _hh = pixelH * 1.6;
                    // the direction is flipped, so the pattern climbs left to right instead of falling. subtracting the column term
                    // rather than adding it mirrors the slope without touching the spacing, so the density that was already right
                    // is preserved exactly.
                    private _base = (1 - ((_cursor * _hSlope) mod 1)) mod 1;
                    private _marks = [_c, _cap, (if (_haveHatch) then {_hatch select _cursor} else {controlNull})];
                    {
                        if (!isNull _x) then {
                            private _yf = (_base + (_forEachIndex / 3)) mod 1;
                            _x ctrlSetPosition [_hx, _fy + _fh * _yf, _hw, _hh];
                            _x ctrlSetBackgroundColor _hCol;
                            _x ctrlCommit 0;
                        };
                    } forEach _marks;
                } else {
                // input present. the hatch mark for this column collapses and the waveform overwrites it.
                if (_haveHatch) then {
                    private _hc2 = _hatch select _cursor;
                    if (!isNull _hc2) then {
                        _hc2 ctrlSetPosition [_fx + _cursor*_colW, _axisY, _colW, 0.0012];
                        _hc2 ctrlCommit 0;
                    };
                };
                _c ctrlSetBackgroundColor _waveCol;
                if (!isNull _cap) then { _cap ctrlSetBackgroundColor _capCol; };

                if (_which == "PRESSURE") then {
                    // real pressure waveform.
                    // the old trace was a trapezoid: a linear ramp, a flat top and a linear fall. that is not what a ventilator
                    // draws, and every clinically useful feature was missing from it. a real pressure-time curve has four parts,
                    // and each one tells you something.
                    // 1. the PEEP baseline, where the airway sits between breaths.
                    // 2. the inspiratory rise, steep and curving over as flow meets resistance.
                    // 3. the peak and then the plateau. the drop between them is the resistive component. flow stops, the
                    // resistive pressure dissipates, and what is left is the pressure actually distending the lung. a rising PIP
                    // minus pplat means resistance, and a rising pplat itself means compliance.
                    // 4. the expiratory decay, exponential rather than linear, with a time constant tau of r times c.
                    // it is driven from the machine rather than from a synthetic amplitude: the real PEEP and the real PIP in
                    // cmH2O against the plot's own 0 to 50 scale, and the real i:e ratio for how much of the cycle is inspiration.
                    // so the trace changes shape when the settings or the lung change, which is the only reason to draw it at
                    // all.
                    private _scale  = missionNamespace getVariable ["ACME_vent_graphScaleCmH2O", 50];
                    private _tgtW   = uiNamespace getVariable ["ACME_vent_target", objNull];
                    private _peepC  = if (isNull _tgtW) then { 5 } else { _tgtW getVariable ["ACME_vent_peep", 5] };
                    if (_simple) then { _peepC = _effectiveFrame select 5; };
                    private _pipC   = if (isNull _tgtW) then { 20 } else { _tgtW getVariable ["ACME_vent_pip", 20] };
                    if (_pipC <= _peepC) then { _pipC = _peepC + 10 };
                    // the resistive drop, which is the step from peak to plateau. it is a fraction of the driving pressure rather
                    // than a fixed number, so it scales with how hard the machine is pushing.
                    private _resF   = missionNamespace getVariable ["ACME_vent_graphResistFrac", 0.22];
                    private _platC  = _peepC + (_pipC - _peepC) * (1 - _resF);

                    private _peep = (_peepC / _scale) max 0 min 1;
                    private _pip  = (_pipC  / _scale) max 0 min 1;
                    private _plat = (_platC / _scale) max 0 min 1;

                    // the inspiratory fraction of the cycle from the real i:e. 1:2 gives a ti of 1/3.
                    private _ieR = if (isNull _tgtW) then { 2.0 } else { _tgtW getVariable ["ACME_vent_ie", 2.0] };
                    if (_simple) then { _ieR = _effectiveFrame select 9; };
                    private _ti  = (1 / (1 + (_ieR max 0.2))) max 0.12 min 0.7;  // 0 to 1 within inspiration.
  // the rise occupies the first 30 percent of ti.
                    _val = if (_phase < _ti) then {
                        private _u = _phase / _ti;  // 0..1 within inspiration
                        private _riseF = 0.30;  // rise occupies the first 30% of ti
                        if (_u < _riseF) then {
                            // steep, curving over into the peak rather than arriving at a corner. sin takes degrees in sqf, so 0 to 90 is a
                            // quarter turn: fast off the baseline and rounded on top.
                            _peep + (_pip - _peep) * (sin ((_u / _riseF) * 90))
                        } else {
                            private _k = (_u - _riseF) / (1 - _riseF);
                            if (_k < 0.18) then {
                                // flow stops and the resistive pressure falls away. it is quick, and eased so it reads as a settle rather than
                                // a step.
                                private _kk = _k / 0.18;
                                _pip - (_pip - _plat) * (1 - ((1 - _kk) * (1 - _kk)))
                            } else {
                                // plateau, drifting down very slightly. real lungs stress-relax, and a dead flat line looks synthetic.
                                _plat - (_plat - _peep) * 0.05 * ((_k - 0.18) / 0.82)
                            };
                        };
                    } else {
                        // expiration. it is passive and exponential, because the lung empties through the circuit against its own time
                        // constant. a linear fall is the single most obviously wrong thing the old trace did, because the shape of
                        // this decay is how you read gas trapping.
                        private _u = (_phase - _ti) / (1 - _ti);
                        private _tau = missionNamespace getVariable ["ACME_vent_graphExpTau", 3.2];
                        _peep + (_plat - _peep) * (exp (-(_u * _tau)))
                    };
                    // clamped to the box. a peak past full scale flattens at the top rail instead of drawing out through the white
                    // border, which is what a real display does when it runs out of scale. it tells you the value is off the top
                    // and does not draw outside the instrument.
                    // a patient fighting the machine. every breath they take of their own collides with a delivered one, and the
                    // machine feels each collision as a pressure spike. it reads from the same dyssynchrony value the capnograph
                    // cleft and the alarm use, so all three instruments agree about what is happening rather than telling three
                    // different stories.
                    // it is irregular on purpose, because the efforts of a patient do not land on the schedule of the
                    // ventilator.
                    private _dysP = if (isNull _tgtW) then { 0 } else { _tgtW getVariable ["ACME_vent_dyssync", 0] };
                    if (_dysP > 0.05) then {
                        private _k = (sin ((_sampT * 430) + (_phase * 260))) * (sin (_sampT * 137));
                        _val = _val + (_k * 0.26 * _dysP);
                    };
                    _val = (_val max 0) min 1;
                    // pressure fills from the floor, where axisy is the plot bottom, upward.
                    private _h = _fh * _val;
                    private _topY = (_fy + _fh) - _h;
                    _c ctrlSetPosition [_fx + _cursor*_colW, _topY, _colW + 0.0006, _h max 0.0012];
                    _c ctrlCommit 0;
                    if (!isNull _cap) then {
                        _cap ctrlSetPosition [_fx + _cursor*_colW, _topY, _colW + 0.0006, _capH];
                        _cap ctrlCommit 0;
                    };
                } else {
                    _val = switch (true) do {
                        case (_phase < 0.02): { _amp * (_phase / 0.02) };
                        case (_phase < 0.35): { _amp * (1 - ((_phase - 0.02) / 0.33)) };
                        case (_phase < 0.40): { 0 };
                        case (_phase < 0.44): { -0.85 * _amp * ((_phase - 0.40) / 0.04) };
                        case (_phase < 0.62): { -0.85 * _amp * (1 - ((_phase - 0.44) / 0.18)) };
                        default { 0 };
                    };
                    // clamped both ways. flow is bidirectional, so a big inspiratory peak and a big expiratory dip both flatten at
                    // their rail rather than running out through the border.
                    _val = (_val max -1) min 1;
                    // flow is bidirectional about the midline, axisy. positive is above and negative is below.
                    private _half = _fh * 0.5;
                    private _topY = 0;
                    if (_val >= 0) then {
                        private _h = _half * _val;
                        _topY = _axisY - _h;
                        _c ctrlSetPosition [_fx + _cursor*_colW, _topY, _colW + 0.0006, _h max 0.0012];  // it grows downward, and the cap rides the top edge of the dip, which is the axis.
                    } else {
                        private _h = _half * (-_val);
                        _topY = _axisY;  // grows downward; the cap rides the top edge (== axis) of the dip
                        _c ctrlSetPosition [_fx + _cursor*_colW, _axisY, _colW + 0.0006, _h max 0.0012];
                    };
                    _c ctrlCommit 0;
                    if (!isNull _cap) then {
                        // the cap rides the outer edge of the excursion: the top of a positive column, or the bottom of a dip.
                        private _capY = if (_val >= 0) then { _topY } else { _axisY + (_half * (-_val)) - _capH };
                        _cap ctrlSetPosition [_fx + _cursor*_colW, _capY, _colW + 0.0006, _capH];
                        _cap ctrlCommit 0;
                    };
                };
                };
                // blank a small gap just ahead of the cursor, which is the sweep erase bar. the fill, its cap and the hatch
                // mark all collapse to a sliver on the baseline, so the region the sweep has not reached stays blank whichever
                // of the two it was last drawing.
                private _gap = (_cursor + 2) mod _N;
                private _gc = _cols select _gap;
                _gc ctrlSetPosition [_fx + _gap*_colW, _axisY, _colW + 0.0006, 0.0012];
                _gc ctrlCommit 0;
                if (_haveCaps) then {
                    private _gcap = _caps select _gap;
                    _gcap ctrlSetPosition [_fx + _gap*_colW, _axisY, _colW + 0.0006, 0.0012];
                    _gcap ctrlCommit 0;
                };
                if (_haveHatch) then {
                    private _ghc = _hatch select _gap;
                    if (!isNull _ghc) then {
                        _ghc ctrlSetPosition [_fx + _gap*_colW, _axisY, _colW, 0.0012];
                        _ghc ctrlCommit 0;
                    };
                };
                _cursor = (_cursor + 1) mod _N;
            };
            uiNamespace setVariable ["ACME_vent_graphCursor", _cursor];

            // the sweeper rides the write position, one column ahead of the freshest sample, like the device.
            private _sweep = uiNamespace getVariable ["ACME_vent_graphSweep", controlNull];
            if (!isNull _sweep) then {
                private _sn = uiNamespace getVariable ["ACME_vent_graphN", 140];
                _sweep ctrlSetPosition [_fx + ((_cursor mod _sn) / _sn) * _fw, _fy, pixelW * 2, _fh];
                _sweep ctrlCommit 0;
            };

            // VTE and i readout, zero-padded to four digits like the device. the values are real, from the drive tick. a
            // VTe sitting far below VTi is the cousin of the capnograph: the gas is leaving through a hole.
            private _vtRow = uiNamespace getVariable ["ACME_vent_graphVtRow", controlNull];
            if (!isNull _vtRow) then {
                private _tgtV = uiNamespace getVariable ["ACME_vent_target", ACE_player];
                if (!isNull _tgtV) then {
                    private _vti = _tgtV getVariable ["ACME_vent_vti", -1];
                    private _vte = _tgtV getVariable ["ACME_vent_vte", -1];
                    private _fmt = { params ["_v"]; if (_v < 0) exitWith {"----"}; private _t = str round _v; while {count _t < 4} do { _t = "0" + _t }; _t };
                    _vtRow ctrlSetText format ["VTE %1  I %2", [_vte] call _fmt, [_vti] call _fmt];
                };
            };
            uiNamespace setVariable ["ACME_vent_graphColAcc", _acc];
            uiNamespace setVariable ["ACME_vent_graphSampT", _sampT];
        };
    };
};


// facing, the last word.
// this is the final act of every frame. everything above is free to show whatever it likes, and if the device
// is turned round, none of it survives. putting this at the top instead, which is where it started, meant
// every later branch quietly re-showed its own piece. the boot splash, the battery indicator and the off-state
// substrate each reappeared on the back of the machine that way, one at a time, as each was reported.
[] call ACME_fnc_ventFaceGate;
