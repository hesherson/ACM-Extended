// init the laryngoscopy mini-game. it is scaled and laid out like the chest-seal and thoracostomy mini-games: a
// large centerd airway view with a tool-slot column to its right, holding the laryngoscope and the et tube, and
// a done button beneath.
// the flow is: grab the laryngoscope, which hangs from the cursor by its blade tip, move it to the mouth, then
// hold left mouse and pull up to open the airway. at full lift it locks open. then grab the et tube, which is
// anchored to the cursor by its tip, and click the center of the vocal cords to pass it.
disableSerialization;
params ["_display"];
uiNamespace setVariable ["ACME_laryngo_dlg", _display];
// blade lamp on. this is a real light on the medic rather than a ui trick, so it lifts the darkness through
// getlightingat exactly like a flashlight would, and it does so everywhere at once rather than only here.
// the lamp is not switched on for you. a laryngoscope with its light already burning the moment you open the
// screen is doing the medic's job for them, and it also means the casualty is lit up at night whether or not
// anyone decided that was a good idea. it goes on the same picker every other minigame uses.
[_display] call ACME_fnc_installLightKey;

// geometry, mirroring fn_chestsealinit.
private _res = getResolution;
private _af = (_res param [1, 1080]) / (_res param [0, 1920]);
if !(_af > 0.05 && {_af < 4}) then { _af = 0.5625 };
private _szX = safeZoneX; private _szY = safeZoneY; private _szW = safeZoneW; private _szH = safeZoneH;
private _cx = _szX + _szW / 2;

// the airway art is square, at 2048 by 2048, and a visually square rect, through pixelw and pixelh, lets the
// keepaspect frames fill it without letterboxing. so the head is large, at the same on-screen scale as the
// chest-seal body.
private _viewH = _szH * 0.78;
private _viewW = _viewH * (pixelW / pixelH);
private _viewX = _cx - _viewW / 2;
private _viewY = _szY + _szH * 0.08;
// zoom. the art is a whole face on a 2048 canvas and the airway is a small feature on it. measured from the
// alpha channels, everything that matters, the teeth, tongue, cords, palate and cavity, lives inside about 15
// percent of the canvas height. drawn one to one, that puts the entire minigame in a small patch of the screen.
// so the layers are drawn on their own rect, scaled by ACME_laryngo_zoom about the mouth, while the mouse
// surface stays on the visible view rect.
// the default zoom is 1.0, which is identical to the previous behavior. raise it to magnify the airway. the
// whole scene scales together and every zone below is in image uv, so nothing needs re-tuning when you do.
// one caveat before you turn it up: the tube art is a separate full-canvas sprite, so it magnifies too, and at a
// high zoom most of its length will sit off screen with only the business end visible. try 2.0 to 2.5 first.
// there are two rects.
// the frame is the visible square the player looks at. instruments are drawn on this and the mouse surface
// covers it.
// the head is the same square pushed down by ACME_laryngo_headOffsetV, so there is room above the face for the
// laryngoscope handle to stick up out of the mouth. measured off the reference composite, the head there sits
// 448 px lower than the raw art on the same 2048 canvas, which is 0.2188. the bottom of the scalp falls outside
// the frame, exactly as it does in the reference.
// the anatomy zones are all expressed in head uv, so they never need re-deriving when the offset changes.
private _zoom = missionNamespace getVariable ["ACME_laryngo_zoom", 1.0];
(missionNamespace getVariable ["ACME_laryngo_focusUV", [0.500, 0.400]]) params ["_focU", "_focV"];
private _fw = _viewW * _zoom;
private _fh = _viewH * _zoom;
// scale about the focus point. at zoom 1 this is exactly the view rect and nothing shifts.
private _fx = _viewX - (_focU * (_fw - _viewW));
private _fy = _viewY - (_focV * (_fh - _viewH));
private _frame = [_fx, _fy, _fw, _fh];
uiNamespace setVariable ["ACME_laryngo_frame", _frame];
uiNamespace setVariable ["ACME_laryngo_viewRect", [_viewX, _viewY, _viewW, _viewH]];

private _headOff = missionNamespace getVariable ["ACME_laryngo_headOffsetV", 0.2188];
private _rect = [_fx, _fy + (_headOff * _fh), _fw, _fh];
uiNamespace setVariable ["ACME_laryngo_rect", _rect];

// the airway this patient actually has. it is read once here, so the whole attempt runs against a fixed grade.
// Trauma still affects difficulty. Neither anatomy nor prior failures prohibit an attempt.
private _patient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
if (!isNull _patient) then {[_patient, "ui:laryngo:" + str clientOwner, true] call ACME_fnc_ecgJostleRequest;};
([_patient] call ACME_fnc_airwayGrade) params ["_mp", "_cl"];
_mp = (round _mp) max 1 min 4;
_cl = (round _cl) max 1 min 4;
// fn_laryngoTick.sqf uses the same grades as this attempt's scene.
uiNamespace setVariable ["ACME_laryngo_mp", _mp];
uiNamespace setVariable ["ACME_laryngo_cl", _cl];

// pin every scene layer to the head rect and set the grade-specific textures. the draw order is fixed in the
// dialog: pharynx, larynx, palate, cavity, five tongue states, teeth, lips, blade, light and tube. the cords,
// meaning the pharynx and larynx, are chosen by cormack-lehane, and the five tongue states, rest through s4, by
// mallampati. the shared palate, cavity, teeth and lips, and the blade, light and tube, keep their config
// textures. fn_laryngoframes owns the tongue opacities, and the blade, light and tube start hidden and are
// faded in by state in the tick.
{
    (_display displayCtrl _x) ctrlSetPosition _rect;
    (_display displayCtrl _x) ctrlCommit 0;
} forEach [87803,87804,87805,87806, 87801,87851,87852,87853, 87915, 87807,87878,87808];
// the blade, lamp and tube live on the frame and are moved every tick by whatever is holding them.
{
    (_display displayCtrl _x) ctrlSetPosition _frame;
    (_display displayCtrl _x) ctrlCommit 0;
} forEach [87802,87811,87812,87911,87912,87913,87809, 87900,87901,87902,87903,87904,87905,87906,87907,87908, 87909,87910];
(_display displayCtrl 87803) ctrlSetText format ["\acm_extended\ui\laryngo\cl%1_pharynx.paa", _cl];
(_display displayCtrl 87804) ctrlSetText format ["\acm_extended\ui\laryngo\cl%1_larynx.paa", _cl];
{
    _x params ["_idc","_frameIdx"];
    (_display displayCtrl _idc) ctrlSetText format ["\acm_extended\ui\laryngo\tongue_mp%1_%2.paa", _mp, _frameIdx];
} forEach [[87801,1],[87851,2],[87852,3],[87853,4]];
// the last tongue state needs a per-grade nudge. the bundle ships state_4_vertical_tuning_pixels for exactly
// this and it was never applied: 0, -41, -22 and 0 px for mallampati 1 to 4 on the 2048 canvas. without it the
// grade 2 s4 sits at v 0.141 to 0.156 while grade 1 sits at 0.117 to 0.133, so on a mallampati 2 the final
// tongue frame lands squarely over the cords and the airway never opens however far you lever. measuring the
// installed art independently gave 0, -48, -16 and 0, which agrees inside the resolution of the check.
// it is clamped. fn_airwaygrade should only ever return 1 to 4, and indexing an array off the back of an
// unexpected value throws, and a thrown error here would take the whole dialog down mid-procedure.
private _s4Tune = ([0, -41, -22, 0] select (((_mp - 1) max 0) min 3)) / 2048;
(_display displayCtrl 87853) ctrlSetPosition [_rect select 0, (_rect select 1) + (_s4Tune * (_rect select 3)), _rect select 2, _rect select 3];
(_display displayCtrl 87853) ctrlCommit 0;
[_display, 0] call ACME_fnc_laryngoFrames;
(_display displayCtrl 87802) ctrlSetTextColor [1,1,1,0];
(_display displayCtrl 87811) ctrlSetTextColor [1,1,1,0];
(_display displayCtrl 87812) ctrlSetTextColor [1,1,1,0];
(_display displayCtrl 87809) ctrlSetTextColor [1,1,1,0];
{ (_display displayCtrl _x) ctrlSetTextColor [1,1,1,0]; } forEach [87814, 87817, 87818, 87878, 87909, 87910, 87915, 87911, 87912, 87913, 87916];
(_display displayCtrl 87816) ctrlSetText "";
// the tube stage layers, 87900 to 87905, start hidden from their config alpha. the tick calls
// fn_laryngotubeframes once the tube is in hand.

// the held-tool footprint, a square at about 22 percent of the view, and its anchor offsets. see the tick.
// the scope was too small for the head. at 22 percent of the view it read like a toy held up next to a face
// rather than a blade you are about to put down someone's throat. it is sized against the head now, not against
// the panel.
private _toolS = _viewH * (missionNamespace getVariable ["ACME_laryngo_toolScale", 0.44]);
uiNamespace setVariable ["ACME_laryngo_toolS", _toolS];

// the tool-slot column to the right of the view, in the chest-seal layout.
// the tray slot was the wrong shape, and that is the whole reason the icons were tiny.
// the head rect above correctly uses _viewW = _viewH * (pixelw / pixelh), which is the real ratio for a visually
// square box. this slot used _slotH * _af instead, where _af is resy over resx. that is a completely different
// number: on a 5120x1440 it is 0.28, so the slot came out about three and a half times too narrow, and
// RscPictureKeepAspect then did exactly what it is supposed to do and shrank the art down to fit that sliver.
// the icons were never small by choice. the box was wrong and the art was obeying it.
// it is sized to fit rather than guessed. four slots plus their counts, the gaps between them and the done
// button all have to live inside the view height, so the slot height is solved for rather than picked. with
// four slots the old fixed 0.26 ran a long way off the bottom of the screen.
private _nSlots  = 5;
private _countH  = _szH * 0.026;
private _slotGap = _szH * 0.012;
private _doneH   = _szH * 0.045;
private _topPad  = _viewH * 0.03;
private _doneGap = _szH * 0.015;
private _slotH   = ((_viewH - _topPad - (_nSlots * _countH) - ((_nSlots - 1) * _slotGap) - _doneGap - _doneH) / _nSlots) max (_szH * 0.04);
private _sqr = 1;
if (pixelH != 0) then { _sqr = pixelW / pixelH; };
private _slotW = _slotH * _sqr;
// the same trap as the slot. this is a horizontal distance, so it needs the square-in-pixels ratio rather than
// resy over resx. with the old _af the gap between the head and the tray was about a quarter of what it was
// meant to be.
private _gap   = (_viewH * 0.05) * _sqr;
private _colX  = _viewX + _viewW + _gap;
private _colY  = _viewY + _topPad;
private _inset = _slotH * 0.10;
private _place2 = {
    params ["_bg","_logo","_cnt","_clk","_y"];
    (_display displayCtrl _bg)  ctrlSetPosition [_colX, _y, _slotW, _slotH];               (_display displayCtrl _bg)  ctrlCommit 0;
    (_display displayCtrl _clk) ctrlSetPosition [_colX, _y, _slotW, _slotH];               (_display displayCtrl _clk) ctrlCommit 0;
    // the icon is a centerd square inside the slot. handing keepaspect a non-square box and expecting a square icon
    // to sit neatly in it is how these ended up spilling over their boxes.
    private _icoH = (_slotH - (2 * _inset));
    private _icoW = _icoH * _sqr;
    if (_icoW > (_slotW - (2 * _inset))) then { _icoW = _slotW - (2 * _inset); _icoH = _icoW / (_sqr max 1e-5); };
    (_display displayCtrl _logo) ctrlSetPosition [_colX + ((_slotW - _icoW) / 2), _y + ((_slotH - _icoH) / 2), _icoW, _icoH];
    (_display displayCtrl _logo) ctrlCommit 0;
    (_display displayCtrl _cnt) ctrlSetPosition [_colX, _y + _slotH, _slotW, _countH];     (_display displayCtrl _cnt) ctrlCommit 0;
};
// four slots, all in the same column. the syringe and collar were declared in config with their own hardcoded
// safezone positions and never placed here, which is why the syringe ended up on its own out to the right while
// the other two were laid out properly. everything goes through _place2 now.
private _step = _slotH + _countH + _slotGap;
[87860,87861,87862,87863, _colY] call _place2;  // the laryngoscope.
private _tubeY = _colY + _step;
[87864,87865,87866,87867, _tubeY] call _place2;  // the et tube.
// the syringe then the collar, in the order they are used: the cuff goes up first, then the tube is secured. the
// tray reads top to bottom as the procedure runs.
private _syrY  = _colY + (_step * 2);
[87870,87871,87872,87873, _syrY] call _place2;  // the cuff syringe.
private _colrY = _colY + (_step * 3);
[87874,87875,87876,87877, _colrY] call _place2;  // the securing collar.
private _sucY  = _colY + (_step * 4);
[87880,87881,87882,87883, _sucY] call _place2;  // the yankauer suction.
// the done button under the tool column, in the chest-seal layout.
private _doneY = _sucY + _slotH + _countH + _doneGap;
(_display displayCtrl 87868) ctrlSetPosition [_colX, _doneY, _slotW, _doneH];
(_display displayCtrl 87868) ctrlCommit 0;

// interaction zones, as fractions of the view, with the glottis measured from the cords art.
// the mouth zone is generous, because it is contact rather than aim. the cords zone is the target the tube must
// be placed in, and it is where cormack-lehane is felt: a good view is a big open slit you can hardly miss, and
// a poor one is a small slit tucked further back behind the tongue.
// these are measured from the art rather than inherited. every value here used to date from the old jaw frames
// and was never re-measured when the bundle art arrived, so the zones were pointing at empty canvas. the old
// cords zone sat at v 0.42 while the real glottis is at v 0.86 on the upright art. measured from the alpha
// channels:
// the upper dental arch runs v 0.753 to 0.790, a distinct band with a clear gap before the lower arch.
// the lower dental arch runs v 0.800 to 0.903.
// the palate runs v 0.759 to 0.822 and the cavity runs v 0.822 to 0.895.
// the larynx runs v 0.839 to 0.879, with the glottic aperture centerd at v 0.858 and a radius of about 0.016.
// the tongue at mp1 s1 runs v 0.818 to 0.881, and s4 runs v 0.857 to 0.883.
// everything is on the midline at u 0.498.
// on orientation: the head art is rotated 180 degrees and the instruments are not, so each of those is mirrored
// here, with v = 1 - v_upright and u = 1 - u. that was verified rather than assumed. the 128x128 and smaller
// mips inside a paa are stored uncompressed, so they were decoded and compared, and all 28 anatomical layers
// matched the rotated source. the revert path, if the head is ever set upright again, is to mirror every v
// back, at v = 1 - v.
uiNamespace setVariable ["ACME_laryngo_mouthZone", [0.502, 0.172, 0.16]];
// measured off the installed rotated art rather than carried over. decoding the larynx layer and finding the
// dark glottic aperture puts it at u 0.4978 and v 0.1367 with a radius of about 0.0165 on every grade. the art
// is the same, and cormack-lehane changes how much of it the pharynx layer leaves visible rather than where it
// is.
// the radius here is the target, and it is drawn a little wider than the visible aperture, because the medic is
// aiming a tube tip at it rather than clicking a pixel.
// for reference, the dark glottic slit was located at full resolution in each grade's larynx art and mirrored
// for the rotated head. the old radii were smaller than the opening actually drawn, where cl4 was 0.009 against
// a real half-extent of 0.0195, so the target was smaller than the thing you could see and aim at.
// cl1 has a center of [0.5023, 0.1415] and a half-extent of 0.0195.
// cl2 has a center of [0.5020, 0.1423] and a half-extent of 0.0193.
// cl3 has a center of [0.5018, 0.1357] and a half-extent of 0.0168.
// cl4 has a center of [0.5022, 0.1411] and a half-extent of 0.0195.
// Wider targets, with a visible-aperture floor for the most difficult anatomy.
private _radius = (([0.032, 0.026, 0.019, 0.015] select (_cl - 1)) * 1.25) max 0.022;
uiNamespace setVariable ["ACME_laryngo_cordsZone", [0.4978, 0.1367, _radius]];
private _dbHalf = [0.10, 0.085, 0.065, 0.05] select (_mp - 1);
uiNamespace setVariable ["ACME_laryngo_depthBand", [0.60 - _dbHalf, 0.60 + _dbHalf]];
// Every grade can reach the final tongue frame. Harder grades need more lift and finer depth/aim.
private _maxReveal = 1;
private _restReveal = [0.12, 0.09, 0.06, 0.03] select (_mp - 1);
private _liftThresh = (([0.50, 0.68, 0.85, 0.95] select (_cl - 1)) + ((_mp - 1) * 0.03)) min 0.98;
uiNamespace setVariable ["ACME_laryngo_maxReveal", _maxReveal];
uiNamespace setVariable ["ACME_laryngo_restReveal", _restReveal];
uiNamespace setVariable ["ACME_laryngo_liftThresh", _liftThresh];
uiNamespace setVariable ["ACME_laryngo_missLatched", false];
uiNamespace setVariable ["ACME_laryngo_fluidSeen", []];
uiNamespace setVariable ["ACME_LG_JerkExposure", 0];

// state.
// it runs idle, then scopeheld with the blade in hand and out, then inserted with the blade in the mouth, then
// lifting while levering up, then exposed with the view locked, then tubeheld with the tube in hand and out,
// then tubing with the tube in the mouth, then done.
uiNamespace setVariable ["ACME_laryngo_state", "idle"];
uiNamespace setVariable ["ACME_laryngo_held", ""];  // "" or "scope" or "tube".
uiNamespace setVariable ["ACME_laryngo_lift", 0];  // 0 to 1 of exposure progress. a drag zeroes it on a snatch.
uiNamespace setVariable ["ACME_laryngo_reveal", 0];  // 0 to 1 of shown mouth-open amount, which drives the flipbook.
uiNamespace setVariable ["ACME_laryngo_holding", false];
uiNamespace setVariable ["ACME_laryngo_cur", [_viewX + _viewW/2, _viewY + _viewH/2]];
uiNamespace setVariable ["ACME_laryngo_done", false];
uiNamespace setVariable ["ACME_laryngo_tubeDepth", 0];  // 0 to 1 of how far the tube is pushed in, which drives f1 through f6.
uiNamespace setVariable ["ACME_laryngo_migrationSyncNext", 0];
uiNamespace setVariable ["ACME_laryngo_migrationSyncLast", [-1, -1, false]];
uiNamespace setVariable ["ACME_laryngo_tubeAim", ""];  // "" or "cords" or "esoph", locked at the push-start click.
// technique scoring. see fn_laryngotick.
uiNamespace setVariable ["ACME_laryngo_pryPressure", 0];  // the integrated off-axis load on the incisors.
uiNamespace setVariable ["ACME_laryngo_pryReveal", 0];  // the view lost to prying. it decays back when you stop.
uiNamespace setVariable ["ACME_laryngo_pryWarned", false];  // a rising-edge latch for the creak warning.
uiNamespace setVariable ["ACME_laryngo_creakNext", 0];
// depth, on the wheel, the re-grip rhythm and the cuff.
uiNamespace setVariable ["ACME_laryngo_depth", 0.5];  // 0 to 1 of how far the blade is in.
uiNamespace setVariable ["ACME_laryngo_depthQual", 1];  // 1 in the vallecula, falling off on both sides.
uiNamespace setVariable ["ACME_laryngo_liftPending", 0];
uiNamespace setVariable ["ACME_laryngo_regripHeld", false];
uiNamespace setVariable ["ACME_laryngo_airwayOpen", false];
uiNamespace setVariable ["ACME_laryngo_gripStr", 0];
uiNamespace setVariable ["ACME_laryngo_tubeGrip", false];
uiNamespace setVariable ["ACME_laryngo_bladeYaw", 0];
uiNamespace setVariable ["ACME_laryngo_liftVel", 0];
uiNamespace setVariable ["ACME_laryngo_fulcUnsafe", false];
uiNamespace setVariable ["ACME_laryngo_tubeBalkUntil", 0];
uiNamespace setVariable ["ACME_laryngo_relSince", -1];
uiNamespace setVariable ["ACME_laryngo_collarSnapped", false];
uiNamespace setVariable ["ACME_laryngo_tubeInHand", false];
uiNamespace setVariable ["ACME_laryngo_tubeCanFeed", false];
uiNamespace setVariable ["ACME_laryngo_cuffSnap", false];
uiNamespace setVariable ["ACME_laryngo_cuffStart", 0];
uiNamespace setVariable ["ACME_laryngo_tubeAimLock", ""];
uiNamespace setVariable ["ACME_laryngo_cuffDone", false];
uiNamespace setVariable ["ACME_laryngo_bladePic", 0];
uiNamespace setVariable ["ACME_laryngo_fulcNext", 0];
// how far the handle has to come back before the last of the view opens up. it is rolled per patient, because
// some airways give it up on a small lever and some want most of the range, and the medic finds out by doing
// it.
// the range is 1 to 5. some airways give it up on a single click of the handle and some want the whole range.
// overshoot loses it again, so it is a search rather than a ratchet.
// this belongs to the airway rather than to whoever happens to have the screen open. it was re-rolled on every
// open, so the same casualty wanted a different lever each time and two medics on one patient were solving two
// different problems. it is cached on them now, exactly the way fn_airwaygrade caches mallampati and
// cormack-lehane.
private _stableAirwayDraw = {
    params ["_p", "_salt", "_count", "_base"];
    if (!isMultiplayer) exitWith {_base + floor (random _count)};
    private _key = if (isPlayer _p) then {getPlayerUID _p} else {netId _p};
    if (_key == "") then {_key = netId _p;};
    if (_key == "") then {_key = format ["%1:%2:%3", typeOf _p, vehicleVarName _p, str _p];};
    private _h = 0;
    { _h = ((_h * 139) + _x + ((_forEachIndex + 1) * 23)) % 9973; } forEach (toArray (_key + _salt));
    _base + (_h % _count)
};
private _fulcNeed = _patient getVariable ["ACME_laryngo_fulcNeed", -1];
private _needFulcCache = _fulcNeed < 1;
if (_needFulcCache) then {_fulcNeed = [_patient, ":laryngo:fulcrum", 5, 1] call _stableAirwayDraw;};
uiNamespace setVariable ["ACME_laryngo_fulcNeed", _fulcNeed];

// how deep this particular airway wants the tube. trachea length varies, so a depth that sits perfectly in one
// casualty is down the right main bronchus in the next. it is rolled at 5 to 8 of the eight frames and cached on
// them, exactly like the mallampati grade and the fulcrum: some need the full length of the tube, and some want
// it two or three frames short of maximum.
// sink it past this and it goes down the right main bronchus, because that bronchus is the straighter of the
// two. one lung then gets everything and the other gets nothing.
private _ideal = _patient getVariable ["ACME_ETT_IdealFrame", -1];
private _needIdealCache = _ideal < 1;
if (_needIdealCache) then {_ideal = [_patient, ":laryngo:depth", 4, 5] call _stableAirwayDraw;};
if (_needFulcCache || {_needIdealCache}) then {
    // Same deterministic answer on every medic client; only the casualty owner persists it for saves/AAR/reopens.
    [_patient, "laryngoAnatomy", [_fulcNeed, _ideal]] call ACME_fnc_ownerDispatch;
};
uiNamespace setVariable ["ACME_laryngo_idealFrame", _ideal];
// Do not accept the tube at the old shallow frame 4. Most airways now require frame 5-7 before the tube is
// considered seated, based on one frame proximal to that patient's mainstem threshold.
private _seatFrame = ((_ideal - 1) max (missionNamespace getVariable ["ACME_ETT_MinSeatFrame", 5])) min _ideal;
uiNamespace setVariable ["ACME_laryngo_requiredSeatFrame", _seatFrame];
uiNamespace setVariable ["ACME_laryngo_fulcOK", false];
uiNamespace setVariable ["ACME_laryngo_gagMisses", 0];
uiNamespace setVariable ["ACME_laryngo_gagNext", 0];
uiNamespace setVariable ["ACME_laryngo_fluidKind", ""];
uiNamespace setVariable ["ACME_laryngo_fluidStage", 0];
uiNamespace setVariable ["ACME_laryngo_fluidPhase", 0];
uiNamespace setVariable ["ACME_laryngo_fluidMode", "rest"];
uiNamespace setVariable ["ACME_laryngo_sucMode", "clear"];
uiNamespace setVariable ["ACME_laryngo_sucFrame", 0];
uiNamespace setVariable ["ACME_laryngo_sucOn", false];
uiNamespace setVariable ["ACME_laryngo_sucNext", 0];
uiNamespace setVariable ["ACME_laryngo_sucDrainNext", 0];
uiNamespace setVariable ["ACME_laryngo_sucLastX", -999];
uiNamespace setVariable ["ACME_laryngo_sucSweepDir", 0];
uiNamespace setVariable ["ACME_laryngo_sucSweepAmp", 0];
uiNamespace setVariable ["ACME_laryngo_sucSweepUntil", 0];
uiNamespace setVariable ["ACME_suction_bagMl", 0];
uiNamespace setVariable ["ACME_suction_sqT0", -1];
uiNamespace setVariable ["ACME_suction_sqBand", ["0000","0050"]];
uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
uiNamespace setVariable ["ACME_laryngo_sucPinRel", []];
uiNamespace setVariable ["ACME_laryngo_fluidCap", 10];
uiNamespace setVariable ["ACME_laryngo_fluidPersist", false];
uiNamespace setVariable ["ACME_laryngo_syringeUsed", false];
uiNamespace setVariable ["ACME_laryngo_collarUsed", false];
uiNamespace setVariable ["ACME_laryngo_fluidReturnAt", 0];
uiNamespace setVariable ["ACME_laryngo_sucHint", 0];
uiNamespace setVariable ["ACME_laryngo_fluidPhaseNext", 0];
uiNamespace setVariable ["ACME_laryngo_fluidFillNext", 0];
uiNamespace setVariable ["ACME_laryngo_bladeLocked", false];
// a different casualty is a clean airway. the persisted state below is keyed to the patient, so opening the
// screen on someone new reads their own record, which is empty, rather than carrying the last one's mess
// across.
// damage and mess live on the casualty. broken teeth, a soiled airway and how many times it has been provoked
// are facts about them rather than about the operator, so a second medic arriving finds the airway as the first
// one left it rather than a clean slate.
// this is derived from the count on the casualty, which is what fn_laryngoteeth maintains. anything above zero
// means they have already lost something and the fractured art should be showing.
uiNamespace setVariable ["ACME_laryngo_teethBroken", ((_patient getVariable ["ACME_laryngo_teethBroken", 0]) > 0)];
// Shared owner pool, not stale B11 close-time snapshots.


uiNamespace setVariable ["ACME_laryngo_gagMisses",   (_patient getVariable ["ACME_laryngo_gagMisses", 0])];
uiNamespace setVariable ["ACME_laryngo_tubeAnchored", false];
uiNamespace setVariable ["ACME_laryngo_tubeVel", 0];
uiNamespace setVariable ["ACME_laryngo_tubeAnchorRel", []];
{ uiNamespace setVariable [_x, false]; } forEach ["ACME_laryngo_kUp","ACME_laryngo_kDown","ACME_laryngo_kLeft","ACME_laryngo_kRight","ACME_laryngo_kFulcBack","ACME_laryngo_kFulcFwd"];
uiNamespace setVariable ["ACME_laryngo_overPressure", 0];  // taps driven into an airway that has stopped giving.
uiNamespace setVariable ["ACME_laryngo_regripLast", -99];
uiNamespace setVariable ["ACME_laryngo_tubeCatch", -1];  // the clicks left to work the cuff past the cords.
uiNamespace setVariable ["ACME_laryngo_tubeClicks", []];  // the advance-rate window.
uiNamespace setVariable ["ACME_laryngo_tubeRammed", false];
uiNamespace setVariable ["ACME_laryngo_tubePassed", false];
uiNamespace setVariable ["ACME_laryngo_cuffAmt", 0];
uiNamespace setVariable ["ACME_laryngo_cuffGrab", false];
uiNamespace setVariable ["ACME_laryngo_tubeTipPos", []];
uiNamespace setVariable ["ACME_laryngo_tubeAng", 0];
uiNamespace setVariable ["ACME_laryngo_tubeAngVel", 0];

// the per-attempt apnea clock. it latches on when the blade first enters the mouth, runs until the tube passes
// or the attempt fails, and abandons as no view if it runs out. the tooth baseline is what the trauma check
// measures this attempt's damage against.
uiNamespace setVariable ["ACME_laryngo_attemptStarted", false];
uiNamespace setVariable ["ACME_laryngo_attemptClock", 0];
uiNamespace setVariable ["ACME_laryngo_teethAtStart", (if (isNull _patient) then {0} else {_patient getVariable ["ACME_laryngo_teethBroken", 0]})];

// a drag state reset, so a fresh open does not inherit the velocity or trail of the last attempt.
uiNamespace setVariable ["ACME_LG_DragPt", []];
uiNamespace setVariable ["ACME_LG_DragLast", -1];
uiNamespace setVariable ["ACME_LG_LastVel", 0];
uiNamespace setVariable ["ACME_LG_Yaw", 0];
uiNamespace setVariable ["ACME_LG_ToothContact", false];
uiNamespace setVariable ["ACME_laryngo_jerkTripped", false];

// the interaction surface, transparent and over the view, plus its handlers.
private _surface = _display displayCtrl 87830;
// one cursor source, covering the whole screen.
// an earlier build added a second, display-level tracker so tools would not freeze off the head. that was the
// wrong fix. the MouseMoving of a control and the MouseMoving of a display do not report in the same coordinate
// basis, so with both installed the cursor variable was being rewritten twice a frame with two different
// answers. the springs were then chasing a point that teleported back and forth every frame, which is exactly
// the flinging: violent near the edges and calm over the head, where the two happened to agree closely.
// the surface simply covers the entire screen instead. it is declared before the tray buttons, so they still
// draw over it and still take their own clicks.
_surface ctrlSetPosition [safeZoneXAbs, safeZoneY, safeZoneWAbs, safeZoneH];
_surface ctrlCommit 0; _surface ctrlEnable true; _surface ctrlShow true;
private _fnTrack = {
    params ["_c", "_ex", "_ey"];
    if ((_ex isEqualType 0) && {_ey isEqualType 0} && {finite _ex} && {finite _ey}) then {
        uiNamespace setVariable ["ACME_laryngo_cur", [_ex, _ey]];
    };
};
_surface ctrlAddEventHandler ["MouseMoving", _fnTrack];
_surface ctrlAddEventHandler ["MouseHolding", _fnTrack];

// one mouse handler, all buttons. registering a second MouseButtonDown for the middle button relied on both
// handlers being called, and whichever way the engine resolves that, the pin was not happening. it is
// dispatched inside the single handler now.
_display displayAddEventHandler ["MouseButtonDown", {
    if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true}; _this call ACME_fnc_laryngoClick }];
// the middle button pins the suction. pressing it with the yankauer in hand parks it where it is and starts it
// running, and pressing it again cancels instantly. that is what makes salad possible, because the tool stays
// working while both hands go back to the blade and the tube.

_display displayAddEventHandler ["MouseButtonUp", {
    if ([_this,"up"] call ACME_fnc_minigameInputMouse) exitWith {true};
    // releasing the right button stops a deflation in progress, because a partial pull is not a deflated cuff.
    if (((_this param [1, -1]) isEqualTo 1)) then { ["stop"] call ACME_fnc_laryngoCuffDeflate; };
    params ["_d", "_button"];
    if (_button == 0) then {
        // this releases the tube, not the laryngoscope. the laryngoscope is on the grip key. letting go also frees the
        // tube to follow the cursor again, so it can be re-aimed and re-committed.
        uiNamespace setVariable ["ACME_laryngo_tubeGrip", false];
        ["release"] call ACME_fnc_laryngoCuff;
        // releasing stops a hand-held suction dead, and deleting the sound source is the only instant stop there is. a
        // pinned one keeps running, because that is what pinning is for.
        if ((uiNamespace getVariable ["ACME_laryngo_sucOn", false])
            && {!(uiNamespace getVariable ["ACME_laryngo_sucPinned", false])}) then {
            uiNamespace setVariable ["ACME_laryngo_sucOn", false];
            [uiNamespace getVariable ["ACME_laryngo_medic", ACE_player]] call ACME_fnc_suctionSfxStop;
        };
        if ((uiNamespace getVariable ["ACME_laryngo_tubeDepth", 0]) <= 0.001) then {
            uiNamespace setVariable ["ACME_laryngo_tubeAnchored", false];
        };

    };
}];
// the wheel is the third axis. it is blade depth while the blade is live, and tube advance once the tube is in
// hand. MouseZChanged on the surface control is reliable in dialogs, unlike the middle button.
_surface ctrlAddEventHandler ["MouseZChanged", {
    if ([_this,"wheel"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_c", "_scroll"];
    if (_scroll == 0) exitWith {};
    [(if (_scroll > 0) then {1} else {-1})] call ACME_fnc_laryngoScroll;
}];
_display displayAddEventHandler ["MouseZChanged", {
    if ([_this,"wheel"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_d", "_scroll"];
    if (_scroll == 0) exitWith {};
    [(if (_scroll > 0) then {1} else {-1})] call ACME_fnc_laryngoScroll;
}];

// the control scheme, on the dialog itself.
// these are display handlers rather than CBA keybinds, because CBA installs its handlers on the mission display,
// and an open dialog takes keyboard focus away from it, so a CBA keybind simply never fires in here. the dialog
// gets the keys instead, and returning true consumes them, which is also what stops the arrow keys walking
// through the dialog's own controls.
// rebind by dik code with no rebuild, for example ACME_laryngo_keyUp = 17. the defaults are:
// grip is left ctrl at 29, and right ctrl at 157 is also accepted. up is w at 17 and down is s at 31.
// left is a at 30 and right is d at 32. the fulcrum is back on up at 200 and forward on down at 208.
private _keys = [
    ["ACME_laryngo_keyUp",        17,  "ACME_laryngo_kUp"],
    ["ACME_laryngo_keyDown",      31,  "ACME_laryngo_kDown"],
    ["ACME_laryngo_keyLeft",      30,  "ACME_laryngo_kLeft"],
    ["ACME_laryngo_keyRight",     32,  "ACME_laryngo_kRight"],
    ["ACME_laryngo_keyFulcBack",  200, "ACME_laryngo_kFulcBack"],
    ["ACME_laryngo_keyFulcFwd",   208, "ACME_laryngo_kFulcFwd"]
];
uiNamespace setVariable ["ACME_laryngo_keyTable", _keys];

_display displayAddEventHandler ["KeyDown", {
    if (_this call ACME_fnc_minigameInput) exitWith {true};
    params ["_d", "_key"];
    private _grip = missionNamespace getVariable ["ACME_laryngo_keyGrip", 29];
    if (_key == _grip || {_key == 157}) exitWith {
        // KeyDown repeats while a key is held, so a fresh grip is only counted on the real press.
        if (!(uiNamespace getVariable ["ACME_laryngo_regripHeld", false])) then {
            uiNamespace setVariable ["ACME_laryngo_regripHeld", true];
            uiNamespace setVariable ["ACME_laryngo_holding", true];
            uiNamespace setVariable ["ACME_laryngo_gripStr", 1];
            call ACME_fnc_laryngoRegrip;
        };
        true
    };
    private _hit = false;
    {
        _x params ["_var", "_def", "_flag"];
        if (_key == (missionNamespace getVariable [_var, _def])) then {
            uiNamespace setVariable [_flag, true];
            _hit = true;
        };
    } forEach (uiNamespace getVariable ["ACME_laryngo_keyTable", []]);
    _hit
}];

_display displayAddEventHandler ["KeyUp", {
    if ((_this + [true]) call ACME_fnc_minigameInput) exitWith {true};
    params ["_d", "_key"];
    private _grip = missionNamespace getVariable ["ACME_laryngo_keyGrip", 29];
    if (_key == _grip || {_key == 157}) exitWith {
        uiNamespace setVariable ["ACME_laryngo_regripHeld", false];
        uiNamespace setVariable ["ACME_laryngo_holding", false];
        true
    };
    private _hit = false;
    {
        _x params ["_var", "_def", "_flag"];
        if (_key == (missionNamespace getVariable [_var, _def])) then {
            uiNamespace setVariable [_flag, false];
            _hit = true;
        };
    } forEach (uiNamespace getVariable ["ACME_laryngo_keyTable", []]);
    _hit
}];

// Preserve an already opened manual bag only across the flashlight rebuild.
private _suctionResume = uiNamespace getVariable ["ACME_suction_resume", []];
uiNamespace setVariable ["ACME_suction_resume", []];
if (count _suctionResume == 6 && {
    (_suctionResume select 0) isEqualTo (uiNamespace getVariable ["ACME_laryngo_medic", objNull])
} && {(_suctionResume select 1) isEqualTo _patient}) then {
    _suctionResume params ["", "", "_bagOwner", "_bagMl", "_totalMl", "_standalone"];
    uiNamespace setVariable ["ACME_suction_bagOwner", _bagOwner];
    uiNamespace setVariable ["ACME_suction_bagMl", _bagMl];
    uiNamespace setVariable ["ACME_suction_totalMl", _totalMl];
    uiNamespace setVariable ["ACME_suction_standalone", _standalone];
};
[true] call ACME_fnc_suctionSelectDevice;
[] call ACME_fnc_laryngoRefreshSlots;
(_display displayCtrl 87810) ctrlSetText "Grab the laryngoscope from the tray.";
// no helper text. the minigames give the medic the instruments and the casualty and nothing else, in the same
// way ACM and ACE do. every prompt behind this still runs harmlessly, so ACME_ui_helpText true puts them all
// back without touching a call site.
if (!(missionNamespace getVariable ["ACME_ui_helpText", false])) then { (_display displayCtrl 87810) ctrlShow false; };

// reopened on a tube that is already seated and secured. everything is locked, and suction still works, which is
// the main reason to come back in.
if (uiNamespace getVariable ["ACME_laryngo_reopenSecured", false]) then {
    uiNamespace setVariable ["ACME_laryngo_state", "complete"];
    uiNamespace setVariable ["ACME_laryngo_airwayOpen", false];
    (_display displayCtrl 87810) ctrlSetText "Airway secured. Suction is available; nothing else can be moved.";

    // draw what is actually in the patient.
    // the restore used to set the status line and nothing else, so a screen reopened on a secured airway said the
    // airway was secured and showed an empty mouth with no tube and no collar. the state was right and the picture
    // was not.
    // both are replayed from the same numbers the procedure itself uses, so the reopened screen is identical to the
    // one the medic closed rather than an approximation of it.
    [{
        params ["_dsp"];
        if (isNull _dsp) exitWith {};
        (uiNamespace getVariable ["ACME_laryngo_frame", [0,0,0.2,0.2]]) params ["_fx","_fy","_fw","_fh"];

        // the tube, seated, exactly as the procedure leaves it.
        // showing frame 8 is only half of it. fn_laryngotubeframes decides WHICH frame is visible and
        // fn_laryngotubepose decides WHERE it sits, and the first attempt at this restore did only the former. so
        // the correct frame was drawn at whatever rect the control happened to hold, which put a long tube shaft
        // down the middle of the face.
        // this is the same pair of calls fn_laryngopasstube makes when the tube seats, reading the same stored tip
        // position, at angle 0 because a seated tube hangs straight and is held by the airway rather than by
        // fingers. the reopened screen is then identical to the one the medic closed, which is the whole point.
        uiNamespace setVariable ["ACME_laryngo_tubeAng", 0];
        uiNamespace setVariable ["ACME_laryngo_tubeAngVel", 0];
        private _restorePatient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
        private _savedDepth = if (isNull _restorePatient) then {1} else {_restorePatient getVariable ["ACME_ETT_Depth", 1]};
        _savedDepth = (_savedDepth max 0) min 1;
        uiNamespace setVariable ["ACME_laryngo_tubeDepth", _savedDepth];
        [_dsp, _savedDepth] call ACME_fnc_laryngoTubeFrames;
        // where the medic actually seated it, converted back into this screen's layout.
        private _tf = if (isNull _restorePatient) then {[]} else {_restorePatient getVariable ["ACME_ETT_TipFrac", []]};
        private _tpR = if ((count _tf) >= 2) then {
            [_fx + ((_tf select 0) * _fw), _fy + ((_tf select 1) * _fh)]
        } else {
            // nothing stored, from a tube placed before this build. fall back to the authored tip anchor, which is
            // the measured center of the tube art, so it lands correctly even if not exactly where they left it.
            (missionNamespace getVariable ["ACME_laryngo_tubeTipUV", [0.5035, 0.2749]]) params ["_au", "_av"];
            [_fx + (_au * _fw), _fy + (_av * _fh)]
        };
        [_dsp, _tpR select 0, _tpR select 1, 0] call ACME_fnc_laryngoTubePose;

        // the collar, fastened, at its measured resting place. the loose one stays hidden.
        (missionNamespace getVariable ["ACME_laryngo_collarUV", [0.4991, 0.4925]]) params ["_coU", "_coV"];
        (missionNamespace getVariable ["ACME_laryngo_collarTarget", [0.4991, 0.3558]]) params ["_ctU", "_ctV"];
        (_dsp displayCtrl 87909) ctrlSetTextColor [1,1,1,0];
        private _cc = _dsp displayCtrl 87910;
        _cc ctrlSetPosition [_fx + ((_ctU - _coU) * _fw), _fy + ((_ctV - _coV) * _fh), _fw, _fh];
        _cc ctrlCommit 0;
        _cc ctrlSetTextColor [1,1,1,1];
    }, [_display], 0.1] call CBA_fnc_waitAndExecute;
};

// coming back to a tube that has moved.
// the tube is already in and has just worked its way out. it starts in hand at the depth it reached, so the job
// is to feed it back to seated and then tie it down.
if (uiNamespace getVariable ["ACME_laryngo_resume", false] && {!isNull _patient}) then {
    private _savedDepth = ((_patient getVariable ["ACME_ETT_Depth", 1]) max 0) min 1;
    private _cuffUp = _patient getVariable ["ACME_ETT_CuffInflated", false];
    uiNamespace setVariable ["ACME_laryngo_tubeDepth", _savedDepth];
    uiNamespace setVariable ["ACME_laryngo_tubeAnchored", true];
    uiNamespace setVariable ["ACME_laryngo_tubeAimLock", "cords"];
    uiNamespace setVariable ["ACME_laryngo_airwayOpen", true];

    // Removing the collar does not make the tube teleport out of the airway. With the cuff still inflated the
    // correct next task is cuff deflation; with the cuff down the tube is adjustable/removable at its stored depth.
    if (_cuffUp) then {
        uiNamespace setVariable ["ACME_laryngo_state", "cuff"];
        uiNamespace setVariable ["ACME_laryngo_tubeInHand", false];
        uiNamespace setVariable ["ACME_laryngo_held", ""];
        (_display displayCtrl 87810) ctrlSetText "The tube is unsecured. Use the syringe to deflate the cuff before moving it.";
    } else {
        uiNamespace setVariable ["ACME_laryngo_state", "migrated"];
        uiNamespace setVariable ["ACME_laryngo_tubeInHand", true];
        uiNamespace setVariable ["ACME_laryngo_held", "tube"];
        (_display displayCtrl 87810) ctrlSetText "The unsecured tube can be adjusted or removed.";
    };

    // Restore both frame/depth and screen position immediately. The old reopen path restored only the numeric
    // depth, so the sprite kept its default rect and appeared almost completely outside the mouth.
    [{
        params ["_dsp", "_pat", "_depth"];
        if (isNull _dsp || {isNull _pat}) exitWith {};
        (uiNamespace getVariable ["ACME_laryngo_frame", [0,0,0.2,0.2]]) params ["_fx","_fy","_fw","_fh"];
        uiNamespace setVariable ["ACME_laryngo_tubeAng", 0];
        uiNamespace setVariable ["ACME_laryngo_tubeAngVel", 0];
        [_dsp, _depth] call ACME_fnc_laryngoTubeFrames;
        private _tf = _pat getVariable ["ACME_ETT_TipFrac", []];
        private _tip = if ((count _tf) >= 2) then {
            [_fx + ((_tf select 0) * _fw), _fy + ((_tf select 1) * _fh)]
        } else {
            (missionNamespace getVariable ["ACME_laryngo_tubeTipUV", [0.5035, 0.2749]]) params ["_au", "_av"];
            [_fx + (_au * _fw), _fy + (_av * _fh)]
        };
        uiNamespace setVariable ["ACME_laryngo_tubeTipPos", _tip];
        private _anchorRel = if ((count _tf) >= 2) then {+_tf} else {
            [((_tip select 0) - _fx) / (_fw max 1e-5), ((_tip select 1) - _fy) / (_fh max 1e-5)]
        };
        uiNamespace setVariable ["ACME_laryngo_tubeAnchorRel", _anchorRel];
        [_dsp, _tip select 0, _tip select 1, 0] call ACME_fnc_laryngoTubePose;
    }, [_display, _patient, _savedDepth], 0.05] call CBA_fnc_waitAndExecute;
};

// suction mode.
// it is the same screen running one tool. there is no laryngoscope, no tube and no tray, because the device is
// in your hand the moment it opens, which is what taking the action meant. the controls are identical to
// suctioning inside an intubation on purpose, so it is not a second skill to learn.
if (uiNamespace getVariable ["ACME_suction_standalone", false]) then {
    uiNamespace setVariable ["ACME_laryngo_state", "suctionOnly"];
    uiNamespace setVariable ["ACME_laryngo_held", "suction"];
    {
        private _c = _display displayCtrl _x;
        if (!isNull _c) then { _c ctrlShow false; _c ctrlEnable false; };
    } forEach [87860,87861,87862,87863, 87864,87865,87866,87867, 87870,87871,87872,87873,
               87874,87875,87876,87877, 87880,87881,87882,87883];
    {
        private _c = _display displayCtrl _x;
        if (!isNull _c) then { _c ctrlSetTextColor [1,1,1,0]; };
    } forEach [87802,87811,87812,87911,87912,87913,87809, 87900,87901,87902,87903,87904,87905,87906,87907,87908, 87909,87910,87814,87817,87818];
    // B13: only the local in-progress NV rebuild may restore a pin; an old patient flag cannot.
    (_display displayCtrl 87810) ctrlSetText "Hold left mouse to suction. Middle click pins it in place.";
};

// motion. the airway view rides in the same helicopter as everything else, so it moves with it. the rest
// position of every control is captured once here and the shake is applied against that base each frame, which
// is how the chest seal, iv and thoracostomy screens already do it.
uiNamespace setVariable ["ACME_Laryngo_ShakeBase", []];
uiNamespace setVariable ["ACME_Laryngo_ShakeBase_off", [0, 0]];

// coming back from ACE's interaction menu.
// ACE destroys this display to show its own menu, so the panel is rebuilt afterwards. everything above has just
// reset the screen to idle, which is correct for a fresh open and wrong for a rebuild, because the medic was
// halfway through an intubation when they reached for the flashlight. put the procedure back exactly as they
// left it.
private _snap = uiNamespace getVariable ["ACME_laryngo_snap", []];
if ((count _snap) >= 14) then {
    uiNamespace setVariable ["ACME_laryngo_snap", []];
    _snap params ["_sState","_sHeld","_sLift","_sRev","_sPic","_sLock","_sOpen",
                  "_sTIH","_sDepth","_sAnch","_sAnchP","_sAim","_sPin","_sPinP",
                  ["_sPassed", false, [false]]];
    uiNamespace setVariable ["ACME_laryngo_state", _sState];
    uiNamespace setVariable ["ACME_laryngo_held", _sHeld];
    uiNamespace setVariable ["ACME_laryngo_lift", _sLift];
    uiNamespace setVariable ["ACME_laryngo_reveal", _sRev];
    uiNamespace setVariable ["ACME_laryngo_bladePic", _sPic];
    uiNamespace setVariable ["ACME_laryngo_bladeLocked", _sLock];
    uiNamespace setVariable ["ACME_laryngo_airwayOpen", _sOpen];
    uiNamespace setVariable ["ACME_laryngo_tubeInHand", _sTIH];
    uiNamespace setVariable ["ACME_laryngo_tubeDepth", _sDepth];
    uiNamespace setVariable ["ACME_laryngo_tubeAnchored", _sAnch];
    uiNamespace setVariable ["ACME_laryngo_tubeAnchorRel", _sAnchP];
    uiNamespace setVariable ["ACME_laryngo_tubeAimLock", _sAim];
    uiNamespace setVariable ["ACME_laryngo_sucPinned", _sPin];
    uiNamespace setVariable ["ACME_laryngo_sucPinRel", _sPinP];
    // Appended field keeps old 14-field snapshots valid without inventing
    // successful passage from a depth or animation state.
    uiNamespace setVariable ["ACME_laryngo_tubePassed", _sPassed];
    [] call ACME_fnc_laryngoRefreshSlots;
};

// Reconcile tray occupancy after secured/migrated/rebuild state has been restored.
[] call ACME_fnc_laryngoRefreshSlots;
// Capture the existing tube before the first render/input. This is the comparison baseline for a close
// immediately after an adjustment, and identifies the insertion if a replacement occurs in transit.
uiNamespace setVariable ["ACME_laryngo_migrationTubeTime", if (isNull _patient) then {-1} else {_patient getVariable ["ACME_ETT_Time", -1]}];
if (!isNull _patient && {_patient getVariable ["ACME_ETT_Inserted", false]}) then {
    private _migrationDepth = _patient getVariable ["ACME_ETT_Depth", 1];
    uiNamespace setVariable ["ACME_laryngo_migrationSyncLast", [_migrationDepth,
        _patient getVariable ["ACME_ETT_Frame", 1 + round (_migrationDepth * 7)],
        _patient getVariable ["ACME_ETT_Mainstem", false]]];
};
private _pfh = [{ [] call ACME_fnc_laryngoTick; }, 0, []] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_laryngo_pfh", _pfh];


// B13: a display-scoped capability, independent of saved airway/trauma state.
private _suctionSerial = (missionNamespace getVariable ["ACME_suctionSessionSerial", 0]) + 1;
missionNamespace setVariable ["ACME_suctionSessionSerial", _suctionSerial];
private _suctionToken = format ["suctionSession:%1:%2", clientOwner, _suctionSerial];
uiNamespace setVariable ["ACME_suctionToken", _suctionToken];
uiNamespace setVariable ["ACME_suctionPublishSeq", 0];
uiNamespace setVariable ["ACME_suctionEpoch", [_patient] call ACME_fnc_clinicalEpoch];
uiNamespace setVariable ["ACME_suctionNextPublish", 0];
uiNamespace setVariable ["ACME_suctionLastMode", ""];
uiNamespace setVariable ["ACME_suctionBagBase", uiNamespace getVariable ["ACME_suction_bagMl", 0]];
uiNamespace setVariable ["ACME_suctionTotalBase", uiNamespace getVariable ["ACME_suction_totalMl", 0]];
private _sMedic = uiNamespace getVariable ["ACME_laryngo_medic", objNull];
private _sPatient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
if (!isNull _sMedic && {(uiNamespace getVariable ["ACME_suction_bagOwner", []]) isEqualTo [_sMedic, _sPatient]}) then {
    _sMedic setVariable ["ACME_suctionManualSession", [_sPatient, _suctionToken, uiNamespace getVariable ["ACME_suctionBagBase", 0]], true];
};
(_display displayCtrl 87883) ctrlSetTooltip "ACCUVAC: take suction, move into mouth, middle-click to park for SALAD. Middle-click again to remove.";
