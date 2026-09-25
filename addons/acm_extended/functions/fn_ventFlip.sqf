// the reverse of the device: everything you cannot do from the front, which is the power and the battery hatch.
// ["toggle"] call ACME_fnc_ventFlip turns the machine round.
// ["apply"] call ACME_fnc_ventFlip re-applies the current side, after a screen rebuild.
// ["power"] call ACME_fnc_ventFlip presses the power button.
// ["swap"] call ACME_fnc_ventFlip presses the battery hatch.
// ["tick"] call ACME_fnc_ventFlip runs per frame, for the hover tooltips and the swap countdown.
// on why there is a side at all: the power button and the battery compartment are on the back of the real
// sparrow, and there is no honest way to reach them from a picture of the front. turning the device round is
// also the only point at which the screen legitimately disappears, which is what makes powering it off feel
// like an act rather than a menu item.
// on the per-battery charge: two charges exist and they swap places rather than resetting.
// the fitted one is ACME_vent_battery on the casualty, or on the medic when nothing is connected.
// the spare is ACME_vent_spareBattery on the medic, at 100 for a fresh item.
// pressing the hatch exchanges them, so a half-flat battery you pulled earlier goes back in half flat. a swap
// that always produced 100 percent would make the whole endurance model free.

#define REV_TEX "\acm_extended\ui\vent\ventway_sparrow_robust_rev_ca.paa"
#define FRONT_TEX "\acm_extended\ui\vent\ventway_sparrow_robust_ca.paa"

// the hit zones, measured off the annotated reference at 2048 and expressed as canvas fractions. the face art is
// a full-canvas 1:1 overlay, so these need no correction.
#define BATT_X0 0.4697
#define BATT_X1 0.8975
#define BATT_Y0 0.5127
#define BATT_Y1 0.6309
#define PWR_X0  0.7588
#define PWR_X1  0.8408
#define PWR_Y0  0.4023
#define PWR_Y1  0.4844

#define SWAP_SECS 4.375

params [["_mode", "apply"]];
disableSerialization;

private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};
private _tgt = uiNamespace getVariable ["ACME_vent_target", objNull];

if (_mode isEqualTo "toggle") exitWith {
    // a swap in progress owns the device. turning it round mid-swap would leave the banner orphaned on a face nobody
    // is looking at, and the battery would land with no indication that it had.
    if ((uiNamespace getVariable ["ACME_vent_swapUntil", -1]) > 0) exitWith {};
    uiNamespace setVariable ["ACME_vent_flipped", !(uiNamespace getVariable ["ACME_vent_flipped", false])];
    ["apply"] call ACME_fnc_ventFlip;
};

if (_mode isEqualTo "apply") exitWith {
    private _rev = uiNamespace getVariable ["ACME_vent_flipped", false];

    private _face = _dlg displayCtrl 87701;
    if (!isNull _face) then {
        private _want = if (_rev) then { REV_TEX } else { FRONT_TEX };
        if ((uiNamespace getVariable ["ACME_vent_faceTexCur", ""]) != _want) then {
            _face ctrlSetText _want;
            uiNamespace setVariable ["ACME_vent_faceTexCur", _want];
        };
    };

    // the screen only exists on the front. hiding the inlay and the screen substrate is what does it, because every
    // readout is drawn inside that window, so with the window gone there is nothing to leak through. the brightness
    // veil goes with them, because there is no lit screen left to dim.
    {
        private _c = _dlg displayCtrl _x;
        if (!isNull _c) then { _c ctrlShow (!_rev); };
    } forEach [87702, 87710, 87703];
    {
        if (!isNull _x) then { _x ctrlShow (!_rev); };
    } forEach (uiNamespace getVariable ["ACME_vent_veilCtls", []]);

    // the reverse-side controls exist only while the back is showing.
    {
        private _c = _dlg displayCtrl _x;
        if (!isNull _c) then { _c ctrlShow _rev; };
    } forEach [87778, 87779];
    // blanked and hidden. these have dark backgrounds, and an empty one that is still shown is a black bar.
    { private _c = _dlg displayCtrl _x; if (!isNull _c) then { _c ctrlSetText ""; _c ctrlShow false; }; } forEach [88000, 88001];

    if (_rev) then {
        // the screen content is torn down by the router when it rebuilds, and here it is only hidden, because flipping
        // back must restore exactly the screen the medic left rather than reset them to the top of the menus.
        [] call ACME_fnc_ventPanelHideScreen;
    } else {
        // mid-boot, do not rebuild. calling the router during the boot chain or the self test re-creates that screen
        // from scratch, which restarts the progress ring and replays its sound. turning the device round to watch the
        // sequence was therefore starting it over every time, and the pieces landed on top of each other. while the
        // machine is still coming up the tick owns the screen. it times everything from ACME_vent_bootT0 and paints the
        // right frame on its own, so flipping back simply reveals the sequence part way through instead of restarting
        // it.
        private _bT0 = uiNamespace getVariable ["ACME_vent_bootT0", -1];
        private _dur = uiNamespace getVariable ["ACME_vent_bootDur", 3];
        private _coming = (_bT0 >= 0) && {(diag_tickTime - _bT0) < (_dur + 12)};
        private _scrNow = uiNamespace getVariable ["ACME_vent_screen", "live"];
        // not while it is booting. pressing power calls this to restore whatever the off branch hid, and it was
        // repainting the last screen in full before the boot chain had a chance to blank anything. that is the weight
        // screen flashing up for a few frames either side of the power press: the panel was being told to draw its old
        // screen and then told to go dark, in that order. a booting machine has nothing to restore.
        private _bT0 = uiNamespace getVariable ["ACME_vent_bootT0", -1];
        private _bDur = uiNamespace getVariable ["ACME_vent_bootDur", 2.4];
        if (_bT0 >= 0 && {(diag_tickTime - _bT0) < _bDur}) exitWith {};

        if (_coming || {_scrNow isEqualTo "selftest"}) then {
            // reveal what already exists rather than rebuilding it. the self-test ring and its percentage are dynamic
            // controls that hidescreen hid on the way out, and without showing them again the test ran to completion behind
            // a blank panel and the ring never came back.
            (_dlg displayCtrl 87710) ctrlShow true;
            [] call ACME_fnc_ventPanelShowDyn;
        } else {
            [_scrNow] call ACME_fnc_ventPanelShowScreen;
        };
    };
};

if (_mode isEqualTo "power") exitWith {
    if ((uiNamespace getVariable ["ACME_vent_swapUntil", -1]) > 0) exitWith {};
    playSound "ACME_VentPower";
    private _on = uiNamespace getVariable ["ACME_vent_powered", false];
    // it is written through to the machine as well as the ui, or the state would evaporate the moment the panel
    // closed.
    private _pwrH = uiNamespace getVariable ["ACME_vent_powerHolder", objNull];
    if (isNull _pwrH) then { _pwrH = if (isNull _tgt) then { ACE_player } else { _tgt }; };
    if (_on) then {
        // off. the machine stops driving immediately, because a ventilator that is off is not ventilating, and the
        // casualty is on whatever the medic does next.
        // it also forgets the casualty. a machine that loses power does not pick the patient back up on its own, so
        // the operator repeats the whole first-time sequence: power on, boot, self test, settings and connect.
        // fn_ventstophard owns all of that, and the battery hatch below calls the same function.
        ["Ventilator powered OFF"] call ACME_fnc_ventStopHard;
    } else {
        // on. it goes straight into the boot sequence, whichever way the device happens to be facing. flip to the front
        // and the self test is already running, exactly as it would be on the real unit.
        uiNamespace setVariable ["ACME_vent_powered", true];
        uiNamespace setVariable ["ACME_vent_booted", false];
        if (local _pwrH) then {
            _pwrH setVariable ["ACME_vent_powerOn", true, true];
            _pwrH setVariable ["ACME_vent_hasBooted", true, true];  // this press is the boot.
        } else {
            private _custody = _pwrH getVariable ["ACME_vent_custodyId", ""];
            [_pwrH, "ventPowerState", [ACE_player, true, true, _custody]] call ACME_fnc_ownerDispatch;
        };
        ACE_player setVariable ["ACME_vent_booted", true];
        // the real boot chain, not just a flag. acme_vent_boott was being set here and nothing reads it, because the
        // tick times boot from ACME_vent_bootT0, which only fn_ventpanelinit was ever setting. that is why pressing
        // power dropped straight onto the settings screen with no blackout, splash or jingle.
        // boot first, then restore. ventBootStart stamps the boot window, and apply reads it and knows not to repaint the
        // old screen. doing these the other way round is what let the previous screen flash up.
        [] call ACME_fnc_ventBootStart;
        ["apply"] call ACME_fnc_ventFlip;  // restore the chrome only. the guard above skips the screen repaint.
    };
};

if (_mode isEqualTo "swap") exitWith {
    if ((uiNamespace getVariable ["ACME_vent_swapUntil", -1]) > 0) exitWith {};

    // the hatch is refused while the machine comes up or goes down. a battery pull during either one cuts the
    // clip that is playing and lays the next one over the top of it, and playsound3d cannot be stopped once it
    // starts.
    // the window is the boot splash plus the self test that follows it. the splash is timed from the boot stamp,
    // the same pair the screen-repaint guard above uses, and the self test that follows has no stamp of its own, so
    // it is recognised by the screen it draws. the powered test closes the one hole in that: a machine switched off
    // part way through a self test leaves the screen name behind, and an unpowered machine has no sequence to
    // protect.
    private _bT0s = uiNamespace getVariable ["ACME_vent_bootT0", -1];
    private _bDurS = uiNamespace getVariable ["ACME_vent_bootDur", 2.4];
    private _scrS = uiNamespace getVariable ["ACME_vent_screen", ""];
    private _upS = uiNamespace getVariable ["ACME_vent_powered", false];
    private _bootingS = _upS && {(_bT0s >= 0 && {(diag_tickTime - _bT0s) < _bDurS}) || {_scrS isEqualTo "selftest"}};
    private _shuttingS = (uiNamespace getVariable ["ACME_vent_shutT0", -1]) >= 0;
    if (_bootingS || {_shuttingS}) exitWith {
        (_dlg displayCtrl 88001) ctrlSetText "BUSY";
        (_dlg displayCtrl 88001) ctrlShow true;
        uiNamespace setVariable ["ACME_vent_swapMsgUntil", diag_tickTime + 2];
    };

    // Hold the selected physical spare during the hatch animation. Another viewer cannot
    // swap the same patient's spare, and closing before completion returns that exact donor.
    if ((uiNamespace getVariable ["ACME_vent_batterySwapRequest", ""]) != ""
        || {!((uiNamespace getVariable ["ACME_vent_batterySupply", []]) isEqualTo [])}) exitWith {};
    private _supply = [ACE_player, _tgt, ["ACME_VentBattery"]] call ACME_fnc_treatmentSupplyTake;
    if (_supply isEqualTo []) exitWith {
        (_dlg displayCtrl 88001) ctrlSetText "NO SPARE BATTERY";
        (_dlg displayCtrl 88001) ctrlShow true;
        uiNamespace setVariable ["ACME_vent_swapMsgUntil", diag_tickTime + 2];
    };
    uiNamespace setVariable ["ACME_vent_batterySupply", _supply];
    playSound "ACME_VentBattSwap";
    uiNamespace setVariable ["ACME_vent_swapUntil", diag_tickTime + SWAP_SECS];

    // the battery leaves the machine on this press, so the machine dies on this press. it does not run on for the
    // length of the swap animation and then notice.
    // fn_ventstophard clears the drive flag, and the server sound engine plays the spool-down clip off that flag.
    // the swap runs 4.375 s and the spool-down clip runs 2.324 s, so the clip finishes inside the swap and nothing
    // lands on top of it.
    ["Battery removed"] call ACME_fnc_ventStopHard;

    (_dlg displayCtrl 88001) ctrlSetText "SWAPPING...";
    (_dlg displayCtrl 88001) ctrlShow true;
};

if (_mode isEqualTo "tick") exitWith {
    private _rev = uiNamespace getVariable ["ACME_vent_flipped", false];
    if (!_rev) exitWith {};

    (uiNamespace getVariable ["ACME_vent_faceRect", [0,0,1,1]]) params ["_fx","_fy","_fw","_fh"];
    private _tip = _dlg displayCtrl 88000;
    private _ban = _dlg displayCtrl 88001;

    // the swap completes when the sound does. it is held to the exact length of the file rather than a guessed
    // number, so the battery lands on the last of the clicks instead of before or after them.
    private _until = uiNamespace getVariable ["ACME_vent_swapUntil", -1];
    if (_until > 0 && {diag_tickTime >= _until}) then {
        uiNamespace setVariable ["ACME_vent_swapUntil", -1];

        // An exchange, not a reset. If the device is on another casualty, the casualty owner atomically swaps the
        // fitted charge and returns the old charge to this provider. This also serializes simultaneous viewers.
        private _holder = if (isNull _tgt) then { ACE_player } else { _tgt };
        private _supply = uiNamespace getVariable ["ACME_vent_batterySupply", []];
        uiNamespace setVariable ["ACME_vent_batterySupply", []];
        if (_supply isEqualTo []) exitWith {};
        private _source = if (isNull (_supply select 2)) then {_supply select 0} else {_supply select 2};
        private _spare = _source getVariable ["ACME_vent_spareBattery", 100];
        if (local _holder) then {
            private _fitted = _holder getVariable ["ACME_vent_battery", 100];
            _holder setVariable ["ACME_vent_battery", _spare, true];
            _holder setVariable ["ACME_vent_battWarned", 0, true];
            _source setVariable ["ACME_vent_spareBattery", _fitted, true];
            [_supply] call ACME_fnc_treatmentSupplyRefund;
        } else {
            private _seq = 1 + (uiNamespace getVariable ["ACME_vent_batterySwapSeq", 0]);
            uiNamespace setVariable ["ACME_vent_batterySwapSeq", _seq];
            private _requestId = format ["%1:%2:%3", clientOwner, _seq, diag_frameNo];
            uiNamespace setVariable ["ACME_vent_batterySwapRequest", _requestId];
            uiNamespace setVariable ["ACME_vent_batterySwapSupply", _supply];
            [_holder, "ventBatteryExchange", [ACE_player, _requestId, _spare, serverTime]] call ACME_fnc_ownerDispatch;
        };

        // the fresh battery does not start the machine. the machine died when the old one came out, at the hatch
        // press above, and it stays dark until a medic presses power.
        // an earlier version started it here and argued that a battery device does not sit dark waiting to be asked.
        // that argument is dropped. a power source that is removed and replaced is a cold start, and a cold start on
        // this device is a deliberate act: power on, boot, self test, settings and connect. a machine that walked
        // itself back up also walked itself back onto the casualty, which is exactly what must not happen.
        // nothing is cleared here, because fn_ventstophard already cleared all of it on the press.

        // OFF reports the new state, because the fresh battery no longer starts the machine.
        // the banner is a fixed sizeex control on a fixed box, and the tick never resizes its font, so the string is
        // held to 16 characters. NO SPARE BATTERY above is 16 and is known to fit.
        if (local _holder) then {
            _ban ctrlSetText format ["BATTERY %1%2 OFF", round _spare, "%"];
            _ban ctrlShow true;
            uiNamespace setVariable ["ACME_vent_swapMsgUntil", diag_tickTime + 2.5];
        } else {
            _ban ctrlSetText "VERIFYING SWAP";
            _ban ctrlShow true;
            uiNamespace setVariable ["ACME_vent_swapMsgUntil", diag_tickTime + 6];
        };
    };

    private _msgUntil = uiNamespace getVariable ["ACME_vent_swapMsgUntil", -1];
    if (_msgUntil > 0 && {diag_tickTime >= _msgUntil}) then {
        _ban ctrlSetText ""; _ban ctrlShow false;
        uiNamespace setVariable ["ACME_vent_swapMsgUntil", -1];
    };
    private _swapping = (uiNamespace getVariable ["ACME_vent_swapUntil", -1]) > 0;
    if (!isNull _ban) then {
        _ban ctrlSetPosition [_fx + _fw*0.30, _fy + _fh*0.30, _fw*0.40, _fh*0.055];
        _ban ctrlCommit 0;
    };

    // the hover tooltip. it uses ctrlposition and the cursor rather than a mouse-moving handler on each button,
    // because two controls do not justify two more event handlers running every frame.
    if (!isNull _tip) then {
        private _mp = getMousePosition;
        private _mx = _mp select 0; private _my = _mp select 1;
        private _in = {
            params ["_x0","_x1","_y0","_y1"];
            (_mx >= (_fx + _fw*_x0)) && {_mx <= (_fx + _fw*_x1)}
              && {_my >= (_fy + _fh*_y0)} && {_my <= (_fy + _fh*_y1)}
        };
        private _txt = "";
        if (!_swapping) then {
            if ([BATT_X0, BATT_X1, BATT_Y0, BATT_Y1] call _in) then { _txt = "Swap Battery"; };
            if ([PWR_X0, PWR_X1, PWR_Y0, PWR_Y1] call _in) then {
                _txt = if (uiNamespace getVariable ["ACME_vent_powered", false]) then { "Power Off" } else { "Power On" };
            };
        };
        if ((ctrlText _tip) != _txt) then { _tip ctrlSetText _txt; };
        _tip ctrlShow (_txt != "");
        if (_txt != "") then {
            // it sits just under the cursor, clamped so it cannot run off the right of the device.
            private _tw = _fw * 0.22;
            private _tx = (_mx - _tw/2) min ((_fx + _fw) - _tw) max _fx;
            _tip ctrlSetPosition [_tx, _my + _fh*0.030, _tw, _fh*0.040];
            _tip ctrlCommit 0;
        };
    };
};
