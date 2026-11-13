// yankauer suction.
// call it as [] call ACME_fnc_laryngoSuction, per frame, from the tick.
// the tool is a 2048 by 4096 sprite, so it is the one thing in this screen that is not square. the control has to
// be twice as tall as it is wide or keepaspect quietly halves it. it hangs from its distal tip, at uv [0.5703,
// 0.02539], which is the anchor the bundle nominates, and the tubing runs off the bottom of the screen.
// the frame sets run at 110 ms a frame, which is 9.09 fps, the default of the bundle.
// clear is 8 frames, looped, with nothing in the lumen.
// cont_x is 8 frames, looped, actively pulling fluid x.
// out_x is 12 frames, the lumen clearing after the fluid is gone.
// the handoffs are the bundle's, and they matter because the boundary frames are byte identical, so switching on
// any other frame would visibly jump.
// continuous into clearout happens only when the continuous loop is on frame 00.
// clearout into clear happens after clearout frame 11, continuing at clear frame 00.
// clear into fluid plays the clearout backward, 11 to 00, then enters the continuous loop at 00.
// while suction is running, the fill stage of the mouth is walked down in step with the clearout, so what leaves
// the mouth is what appears in the tube.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_laryngo_dlg", displayNull];
if (isNull _dlg) exitWith {};
private _c = _dlg displayCtrl 87916;

// salad. the yankauer is the one exception to holding a single tool: pin it with the middle button and it stays
// where you put it and keeps working while your hands go back to the blade and the tube. that is the whole
// technique, suctioning and intubating at the same time rather than taking turns.
// it is only an exception once it is pinned. loose in the hand it obeys the same rule as everything else, so
// tools still cannot be stacked simply by clicking tray icons.
// the middle button again, or clicking its tray slot, cancels it instantly.
// Provider inventory and the current manual-bag session select the visible device.
// The shared resolver also prevents a pin from keeping unavailable equipment active.
[false] call ACME_fnc_suctionSelectDevice;
if ((uiNamespace getVariable ["ACME_suction_type", -1]) < 0) exitWith {
    _c ctrlSetTextColor [1,1,1,0];
};
if ((uiNamespace getVariable ["ACME_suction_type",-1]) == 1
    && {!([uiNamespace getVariable ["ACME_laryngo_medic",objNull],uiNamespace getVariable ["ACME_laryngo_patient",objNull]]
        call ACME_fnc_equipmentAvailable)}) exitWith {
    _c ctrlSetTextColor [1,1,1,0];
    uiNamespace setVariable ["ACME_laryngo_sucPinned",false];
    if (uiNamespace getVariable ["ACME_laryngo_sucOn",false]) then {
        uiNamespace setVariable ["ACME_laryngo_sucOn",false];
        [uiNamespace getVariable ["ACME_laryngo_medic",objNull]] call ACME_fnc_suctionSfxStop;
        [true] call ACME_fnc_suctionPublish;
    };
    if ((uiNamespace getVariable ["ACME_laryngo_held",""]) == "suction") then {
        uiNamespace setVariable ["ACME_laryngo_held",""];
    };
};

private _pinned = uiNamespace getVariable ["ACME_laryngo_sucPinned", false];
private _inHandSuc = (uiNamespace getVariable ["ACME_laryngo_held", ""]) == "suction";
if (!_pinned && {!_inHandSuc}) exitWith {
    _c ctrlSetTextColor [1,1,1,0];
    if (uiNamespace getVariable ["ACME_laryngo_sucOn", false]) then {
        uiNamespace setVariable ["ACME_laryngo_sucOn", false];
        [uiNamespace getVariable ["ACME_laryngo_medic", ACE_player]] call ACME_fnc_suctionSfxStop;
    };
};

// position: it is held by the distal tip and drawn at 1:2.
(uiNamespace getVariable ["ACME_laryngo_frame", [0,0,0.2,0.2]]) params ["_fx","_fy","_fw","_fh"];
(uiNamespace getVariable ["ACME_Laryngo_ShakeBase_off", [0,0]]) params ["_sDx","_sDy"];
_fx = _fx + _sDx; _fy = _fy + _sDy;
(uiNamespace getVariable ["ACME_laryngo_cur", [_fx + _fw/2, _fy + _fh/2]]) params ["_cx","_cy"];
// pinned, it holds its place, because the mouse is needed elsewhere.
// a pinned device is parked in the pharynx, so it moves with the head like everything else that is physically in
// the casualty. it is held as a fraction of the frame and turned back into a screen position against the shaken
// frame each tick.
if (_pinned) then {
    private _pr = uiNamespace getVariable ["ACME_laryngo_sucPinRel", []];
    if ((count _pr) >= 2) then {
        _cx = _fx + ((_pr select 0) * _fw);
        _cy = _fy + ((_pr select 1) * _fh);
    };
};
// the device profile. the art path, anchor, scale and aspect all come from fn_suctiondevice, so the screen has no
// idea which device it is running and a second one is a data change rather than a code change.
private _dev = uiNamespace getVariable ["ACME_suction_device", ([1] call ACME_fnc_suctionDevice)];

// there are two device models, and this driver only knows one.
// everything below animates a lumen, with cont_, out_ and clear_ frames per fluid type, which is what a yankauer
// on a vacuum reservoir does. the suction bag is a bulb feeding a collection bag, so what animates is the bulb
// compressing and the bag filling: twenty squeeze cycles of twelve frames plus twenty-one fill levels, with
// completely different filenames.
// rather than let it request cont_v_03.paa from a folder that has no such file and draw nothing, it says so. the
// bulb driver is the next piece of work and the assets and profile are in place for it.
// the bulb has its own driver, because what it animates is the bulb and the bag rather than a lumen. everything
// below this line is the wand model and does not apply to it.
// the sprite is positioned from the profile first, for BOTH devices.
// this used to sit below the bulb exit, so the suction bag never got positioned at all and sat at the placeholder
// rect the dialog config carries, which the config itself says only exists to keep the control valid before
// onload. combined with the control being left at alpha zero, the bag was invisible AND in the wrong place.
// the profile already carries tipuv, scale and aspect for both devices, so the same three lines serve both and
// there is no second layout to keep in step.
(_dev getOrDefault ["tipUV", [0.5703, 0.02539]]) params ["_tu","_tv"];
private _sc0 = _dev getOrDefault ["scale", 0.55];
private _cw0 = _fw * _sc0;
private _ch0 = _fh * _sc0 * (_dev getOrDefault ["aspect", 2]);
_c ctrlSetPosition [_cx - (_tu * _cw0), _cy - (_tv * _ch0), _cw0, _ch0];
_c ctrlCommit 0;

// whether the tip is in the mouth is decided for both devices, here, above the bulb exit.
// it is the same test and the same zone the wand uses further down. it used to sit below this exit, so in bag
// mode nothing ever computed it. fn_suctionbulb reads ACME_laryngo_sucInMouth and nothing wrote it, so it was
// always false and a squeeze drew nothing at all, however well the medic aimed.
(uiNamespace getVariable ["ACME_laryngo_rect", [0,0,0.2,0.2]]) params ["_prx","_pry","_prw","_prh"];
_prx = _prx + _sDx; _pry = _pry + _sDy;
(uiNamespace getVariable ["ACME_laryngo_mouthZone", [0.502, 0.172, 0.16]]) params ["_pmzx","_pmzy","_pmzr"];
private _pmzr2 = _pmzr * (missionNamespace getVariable ["ACME_laryngo_sucZoneMult", 0.85]);
private _phu = (_cx - _prx) / (_prw max 1e-5);
private _phv = (_cy - _pry) / (_prh max 1e-5);
uiNamespace setVariable ["ACME_laryngo_sucInMouth",
    ((((_phu - _pmzx)^2) + ((_phv - _pmzy)^2)) <= (_pmzr2 * _pmzr2))];

// the bulb has its own driver, because what it animates is the bulb and the bag rather than a lumen. everything
// below this line is the wand model and does not apply to it.
if ((_dev getOrDefault ["model", "wand"]) isEqualTo "bulb") exitWith {
    ["tick"] call ACME_fnc_suctionBulb;
};
private _sc = _dev getOrDefault ["scale", 0.55];
private _cw = _fw * _sc;
private _ch = _fh * _sc * (_dev getOrDefault ["aspect", 2]);
_c ctrlSetPosition [_cx - (_tu * _cw), _cy - (_tv * _ch), _cw, _ch];
_c ctrlCommit 0;
_c ctrlSetTextColor [1,1,1,1];

// is the tip in the mouth, and is it being worked?
// holding the trigger down with the yankauer parked over someone's forehead should not empty their airway. two
// things have to be true for anything to actually come out.
// 1. the tip is in the mouth. it is tested against the same mouth zone everything else uses, in head uv, because
// the cursor is the tip: the sprite hangs off it.
// 2. it is being swept. suctioning is not pointing, it is sweeping the pooled fluid out from the gutters and the
// back of the pharynx. so lateral travel is accumulated and a stroke is only counted on a direction reversal,
// which is what distinguishes working the tip side to side from drifting it across in one go. the rate does not
// matter, only that it keeps happening: each stroke buys a short grace window, and letting the sweep stop lets
// suction lapse until it starts again.
// published above, for both devices. read it rather than recompute it, so the wand and the bag can never
// disagree about where the mouth is.
private _inMouth = uiNamespace getVariable ["ACME_laryngo_sucInMouth", false];

private _nowS = diag_tickTime;
private _lastX = uiNamespace getVariable ["ACME_laryngo_sucLastX", -999];
private _dir   = uiNamespace getVariable ["ACME_laryngo_sucSweepDir", 0];
private _amp   = uiNamespace getVariable ["ACME_laryngo_sucSweepAmp", 0];
if (_lastX > -900) then {
    private _dx = _cx - _lastX;
    private _minStroke = _fw * (missionNamespace getVariable ["ACME_laryngo_sucStroke", 0.045]);
    if ((abs _dx) > 1e-5) then {
        private _nd = if (_dx > 0) then {1} else {-1};
        if (_nd == _dir || {_dir == 0}) then {
            _amp = _amp + (abs _dx);
            _dir = _nd;
        } else {
            // a reversal. if the leg just finished was long enough, that is one honest sweep.
            if (_amp >= _minStroke) then {
                uiNamespace setVariable ["ACME_laryngo_sucSweepUntil",
                    _nowS + (missionNamespace getVariable ["ACME_laryngo_sucSweepGrace", 0.9])];
            };
            _dir = _nd;
            _amp = abs _dx;
        };
    };
};
uiNamespace setVariable ["ACME_laryngo_sucLastX", _cx];
uiNamespace setVariable ["ACME_laryngo_sucSweepDir", _dir];
uiNamespace setVariable ["ACME_laryngo_sucSweepAmp", _amp];
private _sweeping = _nowS < (uiNamespace getVariable ["ACME_laryngo_sucSweepUntil", 0]);
// a pinned tool is parked in the pool and left running, so it does not have to be swept. that is what pinning it
// means. held in the hand, it still has to be worked.
private _working = _inMouth && {_pinned || _sweeping};

// suction runs while the button is held, and there is no timer. the release is handled where the button release
// is.
private _now = diag_tickTime;
private _on  = uiNamespace getVariable ["ACME_laryngo_sucOn", false];
// pinning is what runs it. the sound is an engine-looped source, so it simply keeps playing for as long as the
// pin lasts rather than needing to be retriggered when it reaches the end.
if (_pinned && {!_on}) then {
    _on = true;
    uiNamespace setVariable ["ACME_laryngo_sucOn", true];
    private _med = uiNamespace getVariable ["ACME_laryngo_medic", ACE_player];
    [_med, uiNamespace getVariable ["ACME_laryngo_patient", objNull]] call ACME_fnc_suctionSfxStart;
};

// the frame clock.
private _mode = uiNamespace getVariable ["ACME_laryngo_sucMode", "clear"];  // clear, intake, cont or out.
private _fr   = uiNamespace getVariable ["ACME_laryngo_sucFrame", 0];
private _kind = uiNamespace getVariable ["ACME_laryngo_fluidKind", ""];
private _stage = uiNamespace getVariable ["ACME_laryngo_fluidStage", 0];

if (_now >= (uiNamespace getVariable ["ACME_laryngo_sucNext", 0])) then {
    private _fps = _dev getOrDefault ["frameMs", 110];
    uiNamespace setVariable ["ACME_laryngo_sucNext", _now + ((_fps * (0.9 + (random 0.2))) / 1000)];

    switch (_mode) do {
        case "clear": {
            _fr = (_fr + 1) % 8;
            // suction is running with fluid still in the mouth, so draw it in. the clearout runs backward to get there,
            // because that is the only join the bundle guarantees is seamless.
            if (_on && {_working} && {_kind != ""} && {_stage > 0}) then {
                _mode = "intake"; _fr = 11;
            };
        };
        case "intake": {
            // the clearout played backward, 11 down to 00, then straight into the continuous loop at 00.
            _fr = _fr - 1;
            if (_fr <= 0) then { _mode = "cont"; _fr = 0; };
        };
        case "cont": {
            _fr = (_fr + 1) % 8;
            // only ever leave the continuous loop on frame 00, where the boundary is byte identical.
            if (_fr == 0 && {(!_on) || {!_working} || {_kind == ""} || {_stage <= 0}}) then { _mode = "out"; _fr = 0; };
        };
        case "out": {
            _fr = _fr + 1;
            if (_fr > 11) then { _mode = "clear"; _fr = 0; };
        };
    };
    uiNamespace setVariable ["ACME_laryngo_sucMode", _mode];
    uiNamespace setVariable ["ACME_laryngo_sucFrame", _fr];
}
;

// the mouth empties in step with the tube.
if (_on && {_working} && {_mode in ["cont","intake"]} && {_kind != ""} && {_stage > 0}) then {
    if (_now >= (uiNamespace getVariable ["ACME_laryngo_sucDrainNext", 0])) then {
        private _g = switch (_kind) do {
            case "v": { [420, 620] };
            case "b": { [240, 360] };
            default   { [120, 200] };
        };
        _g params ["_lo","_hi"];
        private _dm = _dev getOrDefault ["drainMult", 1];
        _lo = _lo * _dm; _hi = _hi * _dm;
        uiNamespace setVariable ["ACME_laryngo_sucDrainNext", _now + ((_lo + (random (_hi - _lo))) / 1000)];
        [1] call ACME_fnc_laryngoFluidDrain;
        _stage = uiNamespace getVariable ["ACME_laryngo_fluidStage", 0];

    };
};

if (_on && {_inMouth} && {!_sweeping} && {_kind != ""} && {_stage > 0}
    && {_nowS >= (uiNamespace getVariable ["ACME_laryngo_sucHint", 0])}) then {
    uiNamespace setVariable ["ACME_laryngo_sucHint", _nowS + 3];
};

private _dp = _dev getOrDefault ["path", "\acm_extended\ui\laryngo\suction\"];
private _ff = if (_fr < 10) then { format ["0%1", _fr] } else { str _fr };
private _tex = switch (_mode) do {
    case "cont":   { format ["%1cont_%2_%3.paa", _dp, _kind, _ff] };
    case "intake": { format ["%1out_%2_%3.paa",  _dp, _kind, _ff] };
    case "out":    { format ["%1out_%2_%3.paa",  _dp, _kind, _ff] };
    default        { format ["%1clear_%2.paa", _dp, _ff] };
};
if ((_kind == "") && {_mode != "clear"}) then { _tex = format ["%1clear_0%2.paa", _dp, _fr min 7]; };
_c ctrlSetText _tex;
