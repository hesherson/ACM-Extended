// this positions every screen control inside the screen cutout of the device face, seeds the panel state, and
// starts the per-frame tick. it runs on dialog load. all screen-child coordinates are computed from the
// on-screen face rectangle and the acme_vent_scr_* cutout fractions, which are kept in sync with the #defines
// in config, so the whole ui moves as one when the cutout is retuned.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};
_dlg setVariable ["ACME_vent_viewer", ACE_player];
private _oldPFH = uiNamespace getVariable ["ACME_vent_pfh", -1];
if (_oldPFH >= 0) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};
uiNamespace setVariable ["ACME_vent_pfh", -1];
// Technician access and confirmations cannot survive a new panel session.
_dlg setVariable ["ACME_vent_techUnlocked", false];
_dlg setVariable ["ACME_vent_techAuthCode", ""];
_dlg setVariable ["ACME_vent_techAuthTarget", objNull];
_dlg setVariable ["ACME_vent_itemConfirmed", []];
_dlg setVariable ["ACME_vent_techPrompt", displayNull];

// the on-screen face rectangle.
// the art is a 2048 square, and the visible device is a wide band in the middle, with a content bbox of x 27 to
// 2048 and y 481 to 1582, so the device aspect is about 1.84:1 wide. the sizing must be done in pixels and then
// converted to ui units per axis with pixelw and pixelh, because ui-x units are not the same scale as ui-y on a
// non-4:3 display. on a 32:9 the ui-x range spans about 3.2 units across the screen while ui-y spans about 1.0,
// so a raw ui-x width looks tiny. pixelw and pixelh give the ui size of one screen pixel in each axis and
// handle that automatically.
getResolution params ["_scrW", "_scrH"];
// the content band fractions of the 2048 square, measured.
private _cW = 0.987;  // the device width as a fraction of the square.
private _cH = 0.538;  // the device height as a fraction of the square.
// the target on-screen device height in screen pixels is 40 percent of the screen height. the square that
// contains the device band is taller, because the device is only _cH of the height of the square.
private _devHpx = 0.40 * _scrH;
private _facePx = _devHpx / _cH;  // the side of the containing square, in pixels.
// convert that pixel square to ui units per axis. this is what makes it visually square on any monitor.
private _faceW = _facePx * pixelW;
private _faceH = _facePx * pixelH;
private _faceX = safezoneX + (safezoneW - _faceW) / 2;
private _faceY = safezoneY + (safezoneH - _faceH) / 2;

// position the face control itself, now that we know the rect.
uiNamespace setVariable ["ACME_vent_faceLit", []];  // force the ambient tint to apply on the first tick.
private _face = _dlg displayCtrl 87701;
_face ctrlSetPosition [_faceX, _faceY, _faceW, _faceH];
_face ctrlCommit 0;

// position the white menu inlay at the same rect, as a full-canvas 1:1 overlay. it carries the white rounded
// screen shape in the right spot, so the ui centers off it automatically through the screen cutout rect
// below.
private _inlay = _dlg displayCtrl 87702;
_inlay ctrlSetPosition [_faceX, _faceY, _faceW, _faceH];
_inlay ctrlCommit 0;

// the knob rotation flash, on the same full-canvas rect. the art places itself over the dial, so this needs no
// geometry of its own beyond matching the face. it starts hidden and stays hidden until a scroll step is
// accepted.
private _knobC = _dlg displayCtrl 87703;
if (!isNull _knobC) then {
    _knobC ctrlSetPosition [_faceX, _faceY, _faceW, _faceH];
    _knobC ctrlCommit 0;
    _knobC ctrlShow false;
};
uiNamespace setVariable ["ACME_vent_knobFlashT", -1];
uiNamespace setVariable ["ACME_vent_knobFlashOn", false];
uiNamespace setVariable ["ACME_vent_knobTexCur", ""];
// the control is created fresh on each open with the config default texture, the white startup inlay. but
// ACME_vent_inlayCur lives in uinamespace and persists across opens, so a previous session could leave it
// saying main cutout inlay while this fresh control actually shows the white one. the router only swaps on
// change, so it would then skip the swap and leave the white inlay up on a connected patient, which was the
// reported bug. re-seed inlaycur to the true current texture, the config default, so the first swap of the
// router always fires.
uiNamespace setVariable ["ACME_vent_inlayCur", "\acm_extended\ui\vent\ventway_sparrow_robust_menu_startup_inlay.paa"];

// keybind hints below the device. it is a dial-only device, so you scroll to move and middle-click to select.
// they are centerd under the face as two icon and label pairs on one line.
private _hintY = _faceY + _faceH * 0.86;
private _hintIcoS = _faceH * 0.045;
private _hintIcoW = _hintIcoS * (pixelH / pixelW);  // a square icon.
// pair 1 is scroll and pair 2 is middle-click, laid out centerd. there are three pairs now, so they are spaced
// across the width rather than sitting at the two-pair positions they had.
private _p1x = _faceX + _faceW * 0.09;
private _p2x = _faceX + _faceW * 0.40;
private _p3x = _faceX + _faceW * 0.72;
// THE KEYBIND HINTS ARE ALWAYS SHOWN. do not put a gate back on them.
// they were hidden behind ACME_ui_helpText, which defaults to false, when that flag was introduced for the IV
// screen in v0.9.999r-30. the IV screen is a pair of hands and a limb and it should not be captioned. this is a
// DEVICE with a dial-only interface: there is no visible affordance anywhere on a picture of a ventilator that
// says scroll to move and middle-click to select, so hiding the line does not make it look more like a real
// machine, it makes it unusable without being told out of band.
// the three pairs are scroll, middle click and the bindable select key.
{ private _hc = _dlg displayCtrl _x; if (!isNull _hc) then { _hc ctrlShow true; }; } forEach [87770, 87771, 87772, 87773, 87776, 87777];
(_dlg displayCtrl 87770) ctrlSetPosition [_p1x, _hintY, _hintIcoW, _hintIcoS];
(_dlg displayCtrl 87770) ctrlCommit 0;
(_dlg displayCtrl 87771) ctrlSetPosition [_p1x + _hintIcoW*1.2, _hintY, _faceW*0.30, _hintIcoS];
(_dlg displayCtrl 87771) ctrlCommit 0;
(_dlg displayCtrl 87772) ctrlSetPosition [_p2x, _hintY, _hintIcoW, _hintIcoS];
(_dlg displayCtrl 87772) ctrlCommit 0;
(_dlg displayCtrl 87773) ctrlSetPosition [_p2x + _hintIcoW*1.2, _hintY, _faceW*0.35, _hintIcoS];
(_dlg displayCtrl 87773) ctrlCommit 0;
// the select hint. a middle-click may not register, which is an engine limitation, so point users to the
// bindable select key.
(_dlg displayCtrl 87773) ctrlSetText "Middle Click: Select";
(_dlg displayCtrl 87776) ctrlSetPosition [_p3x, _hintY, _hintIcoW, _hintIcoS];
(_dlg displayCtrl 87776) ctrlCommit 0;
(_dlg displayCtrl 87777) ctrlSetPosition [_p3x + _hintIcoW*1.2, _hintY, _faceW*0.28, _hintIcoS];
(_dlg displayCtrl 87777) ctrlCommit 0;
[_dlg] call ACME_fnc_ventFlipKeyHint;

// the screen rect is the full inlay extent, measured from the reference: the top white bar, the dark window and
// the bottom white bar together. the existing content layout already places the title and mode on the top band,
// the BPM, vt and gauge readout in the middle window, and the strip on the bottom band, so mapping _place onto
// the full inlay extent lines everything up. the canvas fractions are x 0.334, y 0.4185, w 0.209 and h
// 0.1694.
private _sx = _faceX + _faceW * 0.334;
private _sy = _faceY + _faceH * 0.4185;
private _sw = _faceW * 0.209;
private _sh = _faceH * 0.1694;

// a helper that places a control at fractional coords within the screen rect, [fx,fy,fw,fh].
private _place = {
    params ["_idc", "_fx", "_fy", "_fw", "_fh"];
    private _c = _dlg displayCtrl _idc;
    _c ctrlSetPosition [_sx + _sw*_fx, _sy + _sh*_fy, _sw*_fw, _sh*_fh];
    _c ctrlCommit 0;
    _c
};

// the text scales with the screen height so it fits on both 16:9 and 32:9. the value text is based on the screen
// height, and the labels are a touch smaller.
private _txtVal = _sh * 0.185;
private _txtLbl = _sh * 0.170;
private _txtSmall = _sh * 0.130;
{ (_dlg displayCtrl _x) ctrlSetFontHeight _txtVal; } forEach [87721,87723,87726];
{ (_dlg displayCtrl _x) ctrlSetFontHeight _txtLbl; } forEach [87720,87722,87724];
{ (_dlg displayCtrl _x) ctrlSetFontHeight (_sh * 0.110); } forEach [87727];
{ (_dlg displayCtrl _x) ctrlSetFontHeight _txtSmall; } forEach [87712];

// the screen background fills the cutout.
[87710, 0, 0.135, 1, 0.73] call _place;  // the dark screen fills only the window between the white bars of the inlay.
// the title bar across the top 11 percent or so of the screen.
[87711, 0, 0, 1, 0.11] call _place;
(_dlg displayCtrl 87711) ctrlShow false;  // the old square title bar is hidden, because the menu inlay provides it now, and curved.

// header geometry, which applies to every screen.
// the white top bar of the inlay occupies y 0.000 to 0.135 of the screen. both the title text and the battery
// are centerd vertically inside that bar, whose midline is 0.0675, and the title spans the full width with
// centerd alignment, so it sits on the horizontal midline of the screen whatever the battery on the left is
// doing.
// the list screens use the same numbers for their title, see fn_ventpanelshowscreen, so all screens agree.
private _barMid = 0.067;  // the white top bar, measured from the inlay art: 0.002 to 0.132.
private _titleH = 0.090;
[87712, 0.0, _barMid - _titleH/2, 1.0, _titleH] call _place;  // the mode text, centerd both ways.
// the tick renders the t, z or c trigger letter inside the alarm box, 87714, so there is no separate status
// control to position anymore. 87766 is retired and hidden in the router, and leaving it unpositioned keeps it
// off the bar entirely. two controls sharing the plug slot were what closed the battery gap.
// the readout rows are nudged down slightly so the block sits centerd in the box, at y 0.17 to 0.63.
// the content window is measured directly from the inlay art,
// ventway_sparrow_robust_menu_inlay_example_ca.png. the white top bar ends at screen-fraction y 0.132 and the
// white bottom tray begins at 0.873. the previous layout treated the tray as starting at 0.76, which left a
// 0.128-tall dead band of dark screen under the PEEP row, and that was the gap. rows now fill the real window,
// 0.132 to 0.873, with equal padding of 0.018:
// BPM runs 0.150 to 0.335 and VTe runs 0.520 to 0.705.
// m.v runs 0.335 to 0.520 and PEEP runs 0.705 to 0.855, with the tray at 0.873.
// on the right edge, every value and highlight box stops at 0.74, clear of the pressure numerals which start at
// 0.775.
[87720, 0.04, 0.150, 0.26, 0.185] call _place;  // LblBPM.
[87721, 0.32, 0.150, 0.42, 0.185] call _place;  // ValBPM, running 0.32 to 0.74.
[87722, 0.04, 0.335, 0.26, 0.185] call _place;  // LblMV.
[87723, 0.32, 0.335, 0.42, 0.185] call _place;  // ValMV, running 0.32 to 0.74.
[87724, 0.04, 0.520, 0.26, 0.185] call _place;  // LblVT.
[87725, 0.30, 0.520, 0.44, 0.185] call _place;  // ValVTBox, the highlight, running 0.30 to 0.74.
[87726, 0.32, 0.520, 0.42, 0.185] call _place;  // ValVT, running 0.32 to 0.74.
// the bottom parameter row, PEEP and i:e. it spans the full width out to the gauge, spaced.
// the bottom row has three fixed fields, so nothing can push anything else. the auto-PEEP figure gets its own
// smaller control between them, because it appears and disappears, and when it was part of the PEEP string its
// arrival shoved i:e off the right of the screen every time.
// PEEP runs 0.040 to 0.290.
// the (+x.x) figure runs 0.290 to 0.440 and is smaller.
// i:e runs 0.455 to 0.735 and is fixed, so it never moves.
// the widths are sized to the widest string each field can hold, at about 0.31 screen widths per character per
// unit of font height. the first pass guessed and both fields clipped: "PEEP 5.0" needs 0.273 and had 0.250, so
// the trailing zero went, and "(+1.2)" needs 0.167 and had 0.150, so the closing bracket went.
// "PEEP 5.0" is 8 characters at 0.110, so 0.273, in a field of 0.280.
// "(+1.2)" is 6 characters at 0.090, so 0.167, in a field of 0.175.
// "i:e 1:2.0" is 9 characters at 0.105, so 0.293, in a field of 0.300, ending at 0.795 against a gauge frame at
// 0.870.
// i:e ended at 0.850 in an earlier build and was crowding the bar. it is pulled back to 0.795, which leaves
// 0.075 of clear screen between the text and the gauge instead of 0.020.
[87727, 0.040, 0.705, 0.280, 0.150] call _place;
[87767, 0.325, 0.722, 0.175, 0.128] call _place;
[87768, 0.495, 0.705, 0.300, 0.150] call _place;
(_dlg displayCtrl 87767) ctrlSetFontHeight (_sh * 0.090);  // smaller than the row it sits in.
(_dlg displayCtrl 87768) ctrlSetFontHeight (_sh * 0.105);
// the side gauge on the right edge. it runs from the value rows all the way down to the white tray, the same
// bottom edge the PEEP row uses, instead of stopping two thirds of the way down and leaving dead screen under
// it.
[87730, 0.87, 0.150, 0.09, 0.705] call _place;  // 0.150 to 0.855, hard against the tray at 0.873.
// the pressure scale, 0 to 50 cmH2O, down the left side of the gauge: a numeral plus a short tick at each 10.
// the gauge bar spans screen-fractions y 0.15 to 0.62, and the bar itself renders between 5 percent and 95
// percent of that height, from the tick's 0.05 plus 0.90 times frac, so the scale must anchor to that same
// usable band or the numbers will not line up with the bar.
private _gsTop = 0.150; private _gsBot = 0.855;
private _gsH = _gsBot - _gsTop;
// seven steps now: 60 at the head down to 0 at the foot. six left the bar with no zero mark under it, so the
// bottom of the scale had nothing to read against.
private _lblIdc = [87769,87733,87734,87735,87736,87737,87738];  // the text is set below from _v, not from config.
private _tckIdc = [87774,87739,87759,87761,87762,87763,87764];
{
    // seven labels, 60 down to 0. the full scale is 60 cmH2O, because a stiff lung under pressure control runs past
    // 50 regularly and the bar was pinning at the top with no headroom left to read.
    private _v = 60 - (_forEachIndex * 10);  // 60 down to 0.
    private _frac = _v / 60;  // 0 to 1 of the gauge span.
    // match the mapping of the bar itself: the bottom of the bar is 5 percent of the height and the top is 95
    // percent.
    private _yFrac = _gsBot - (_gsH * (0.05 + 0.90 * _frac));
    private _lblH = 0.075;
    // set the text from the same _v that sets the position. the label strings were hardcoded in config as 50, 40,
    // 30, 20, 10 and 0, so changing the scale here moved every label to its new position while it still read the
    // old number. the position and the text now come from one source and cannot disagree again.
    (_dlg displayCtrl (_lblIdc select _forEachIndex)) ctrlSetText (str _v);
    [(_lblIdc select _forEachIndex), 0.760, _yFrac - _lblH/2, 0.090, _lblH] call _place;
    [(_tckIdc select _forEachIndex), 0.852, _yFrac - 0.004, 0.018, 0.008] call _place;
} forEach [0,0,0,0,0,0,0];
{ (_dlg displayCtrl _x) ctrlSetFontHeight (_sh * 0.075); } forEach _lblIdc;
[87731, 0.87, 0.705, 0.09, 0.150] call _place;  // green, the lower one.
[87732, 0.87, 0.555, 0.09, 0.150] call _place;  // blue, the upper one.
// the top bar, measured off the new menu inlay art.
// the inlay paints the top bar itself now, so these controls are placed on it rather than drawing it.
// the white bar runs y 0.000 to 0.130.
// the battery block runs x 0.025 to 0.235. it is a black field, and the battery and plug glyph rides on it.
// the alarm square runs x 0.341 to 0.424. it is black by default and red whenever an alarm is up.
// the title field runs x 0.426 to 1.000. it is white, and the title is centerd at 0.713 rather than left
// aligned.
private _barY = 0.012; private _barH = 0.130;  // the bar is 0.130 of the screen, measured off the reference.

// battery. the art is a full-canvas 1:1 overlay like the inlay, so it takes the face rect and positions itself.
// that deletes the whole aspect-correction block that used to live here: a width in screen fractions, a height
// derived through pixelw and pixelh to keep it square, and a magic 0.4715 offset to drag the glyph back onto
// the bar midline. none of it was ever going to be exactly right, which is why it had been retuned twice and
// still needed a keep-aspect style to stop the icon distorting.
// for reference, the art is the authority and was measured off the canvas itself, a 512 square.
// the battery body runs canvas x 0.000 to 0.633.
// the letter gap runs canvas x 0.633 to 0.695, which is the t, z or c slot. see the status box above.
// the plug glyph runs canvas x 0.695 to 1.000.
// the glyph band runs canvas y 0.363 to 0.580, with a band center at 0.4715.
// the plugged variant spans the full canvas width, so the canvas is mapped so its right edge lands just left of
// the alarm square rather than across it. the alarm square, at screen x 0.232 to 0.320, is reserved for alarms
// only, and the battery body and the plug glyph both sit to its left. the block previously spanned x 0.005 to
// 0.326, which put the plug glyph, the right 30 percent or so of the texture, directly on top of the alarm
// square. that was the encroachment. the block ends at 0.226 now, a hair left of the square, so the whole
// battery and plug indicator clears it.
private _battC0 = _dlg displayCtrl 87713;
_battC0 ctrlSetPosition [_faceX, _faceY, _faceW, _faceH];
_battC0 ctrlCommit 0;

// the charge fill, inside the outline. it is measured off the decoded art: the hollow interior runs canvas x
// 0.33740 to 0.36768 and y 0.42480 to 0.43408. because both the art and this rect are canvas fractions of the
// same face, they cannot drift apart.
// it is inset so the bar sits centerd inside the outline with a black margin all round, rather than filling the
// hollow edge to edge and touching the walls. that is two canvas pixels each side, measured on the same 2048
// grid the interior was measured on, so 2/2048 or 0.000977.
private _bfIn = 0.000977;
private _bfX = _faceX + _faceW * (0.33740 + _bfIn);
private _bfY = _faceY + _faceH * (0.42480 + _bfIn);
private _bfW = _faceW * (0.03027 - 2*_bfIn);
private _bfH = _faceH * (0.00928 - 2*_bfIn);
uiNamespace setVariable ["ACME_vent_battFillRect", [_bfX, _bfY, _bfW, _bfH]];
private _bfC = _dlg displayCtrl 87716;
if (!isNull _bfC) then {
    _bfC ctrlSetPosition [_bfX, _bfY, _bfW, _bfH];
    _bfC ctrlCommit 0;
};

// the alarm square. it is transparent, black on black and invisible, when all is well, and red with the alarm
// letter the moment anything is wrong.
// it sits in the square the with-trigger inlay cuts for it. measured off that art the square is 0.3402 to
// 0.4230, so 0.341 wide by 0.083 lands inside it with a pixel to spare on each side. it is shown on the live
// screen only, because that is the only inlay with the square, and fn_ventpanelshowscreen gates it.
// this briefly lived at 0.238, after the addon's copy of the inlay turned out to be a version with the trigger
// square missing and the battery block running the full 0.0000 to 0.3264. that was the asset being wrong rather
// than the placement, and both are correct now.
[87714, 0.336, 0.014, 0.083, 0.106] call _place;  // nudged 0.005 left, so the letter reads centerd in the square.
(_dlg displayCtrl 87714) ctrlSetBackgroundColor ([[0, 0, 0, 0]] call ACME_fnc_ventColor);  // idle is transparent. the tick turns it red on an alarm.

// the title, centerd in the white field the inlay leaves for it. the field starts at 0.45, comfortably clear of
// the black block which ends at 0.3264, measured off the inlay art rather than estimated. the font came down
// from 0.11, because at that size a 13-character title rendered about 0.67 screen widths wide, which is wider
// than the field it is centerd in. the overflow went out both sides and the left half disappeared under the
// black block, which is why ADV. SETTINGS read as "DV. SETTINGS".
[87712, 0.45, _barY, 0.55, _barH] call _place;
(_dlg displayCtrl 87712) ctrlSetFontHeight (_sh * 0.085);
(_dlg displayCtrl 87712) ctrlSetTextColor ([[0.05, 0.05, 0.05, 1]] call ACME_fnc_ventColor);  // black ink on the white bar.
(_dlg displayCtrl 87712) ctrlSetBackgroundColor ([[0, 0, 0, 0]] call ACME_fnc_ventColor);

(_dlg displayCtrl 87711) ctrlShow false;  // the old drawn title bar. the inlay provides it now.

// the white bottom bar, matching the title bar, carrying the button strip.
[87715, 0, 0.76, 1, 0.11] call _place;
(_dlg displayCtrl 87715) ctrlShow false;  // the old square bottom bar is hidden, because the menu inlay provides it now, and curved.
// the bottom button strip on the white bar. the icons are placed square, so the icon w and h in ui units must
// match the pixelw and pixelh ratio, because the ui-x and ui-y scales of the cutout differ, and that keeps the
// glyphs from stretching.
// the bottom white bar occupies screen-fraction y of about 0.87 to 1.0, measured from the inlay, so the strip is
// placed inside that band and the icons sit on the white bar rather than above it.
private _stripY = 0.885; private _stripH = 0.10;
// a square icon. choose a pixel size from the bar height and convert to ui per axis, sized to fit inside the
// bar.
// the icon size is a fraction of the bar height. it was 0.72, which left the glyphs small enough to be hard to
// read at a glance on a device you are meant to check without stopping what you are doing. the highlight boxes
// and the alarm count are both derived from this, so they grow with it and the strip stays proportioned.
private _icoFrac = missionNamespace getVariable ["ACME_vent_trayIconFrac", 0.88];
private _icoPx = (_stripH * _sh) / pixelH * _icoFrac;
private _icoW = _icoPx * pixelW;  // the ui-x width for a square icon.
private _icoH = _icoPx * pixelH;  // the ui-y height for a square icon.
private _hlMap = [87748, 87749, 87752, 87753];  // highlight boxes for alarm, graph, breath and menu.
// the live alarm count sits immediately right of the bell, in column 0. it is a real control because the number
// has to change: it is the length of ACME_vent_alarms. a count baked into the icon art is a picture of a zero,
// and it will read zero while the patient is dying.
private _cntIco = _icoW * 0.75;
{
    _x params ["_btnIdc", "_icoIdc", "_col"];
    private _cx = 0.03 + _col * 0.235;
    [_btnIdc, _cx, _stripY, 0.20, _stripH] call _place;
    // center the square icon within the cell, vertically centerd in the bar.
    private _cellCx = _sx + _sw*(_cx + 0.10);  // the cell center x, absolute.
    private _icoY = _sy + _sh*_stripY + (_sh*_stripH - _icoH)/2;  // vertically centerd in the bar cell.
    private _ico = _dlg displayCtrl _icoIdc;
    // a per-icon scale. the manual-breath glyph, in column 2, carries more internal padding than the others, so at
    // the shared size it reads noticeably smaller than the bell or the menu icon beside it. it is scaled up on its
    // own.
    // it is capped so it stays inside its selection box. the highlight is _icoW times 1.5 wide and _icoH times 1.3
    // tall, so 1.22 keeps the icon within the box on both axes and leaves the light blue still visibly framing
    // it.
    private _sc = if (_col == 2) then { missionNamespace getVariable ["ACME_vent_breathIconScale", 1.22] } else { 1 };
    private _iw = _icoW * _sc;
    private _ih = _icoH * _sc;
    _ico ctrlSetPosition [_cellCx - _iw/2, _icoY - ((_ih - _icoH)/2), _iw, _ih];
    _ico ctrlCommit 0;
    // the selection highlight box behind the icon, a touch larger than the icon so the light blue frames it.
    if (_col == 0) then {
        private _cnt = _dlg displayCtrl 87765;
        // the live alarm count sits tight to the bell and reads at nearly the height of the icon itself. it was offset
        // 0.60 of an icon width away at 0.72 height, which left it small and floating clear of the symbol it belongs
        // to. it is pulled in and scaled up, so the pair reads as one unit.
        private _cntOff = missionNamespace getVariable ["ACME_vent_alarmCountOffset", 0.42];
        private _cntFrac = missionNamespace getVariable ["ACME_vent_alarmCountFrac", 0.95];
        _cnt ctrlSetPosition [_cellCx + _icoW*_cntOff, _icoY, _icoW * 1.9, _icoH];
        _cnt ctrlSetFontHeight (_icoH * _cntFrac);
        _cnt ctrlCommit 0;
    };
    private _hlIdc = _hlMap select _col;
    private _hlPad = _icoW * 0.25;
    private _hl = _dlg displayCtrl _hlIdc;
    _hl ctrlSetPosition [_cellCx - _icoW/2 - _hlPad, _icoY - (_icoH*0.15), _icoW + 2*_hlPad, _icoH*1.3];
    _hl ctrlCommit 0;
} forEach [[87740,87741,0],[87742,87743,1],[87744,87745,2],[87746,87747,3]];
// direct-click hit targets over the BPM and vt rows.
[87750, 0.02, 0.150, 0.72, 0.185] call _place;  // HitBPM. it stops at 0.74, clear of the scale.
[87751, 0.02, 0.520, 0.72, 0.185] call _place;  // HitVT. it stops at 0.74, clear of the scale.
// the boot logo: a clean centerd square on the dark screen, with no letterbox background box. it is sized off
// the screen height, with a square width derived through the pixel ratio, then centerd in the screen rect.
private _blH = _sh * 0.55;
private _blW = _blH * (pixelW / pixelH);  // a visually square footprint. it was pixelh over pixelw, which is inverted, and that caused the stretch.
private _blC = _dlg displayCtrl 87760;
_blC ctrlSetPosition [_sx + (_sw - _blW)/2, _sy + _sh*0.18, _blW, _blH];
_blC ctrlCommit 0;
// the graph controls are never positioned here, because the graph screen sizes them on entry. they default to
// visible at their config placeholder, and GraphField, 87801, is near-black, so they are hidden now to avoid a
// black box over the boot logo before the screen router takes over.
{ (_dlg displayCtrl _x) ctrlShow false } forEach [87800,87801,87802];

// seed the panel state.
// the functional settings persist on the target, which is the patient being ventilated, or the medic in preset
// mode, so a running vent drives the ventilation of that patient. read the current values or the defaults.
private _target = uiNamespace getVariable ["ACME_vent_target", ACE_player];
if (isNull _target) then { _target = ACE_player; };
private _bpm  = _target getVariable ["ACME_vent_bpm", 12];
private _vt   = _target getVariable ["ACME_vent_vt", 500];
private _peepSeed = _target getVariable ["ACME_vent_peep", 5];
private _pinspFloor = (11 max (_peepSeed + 1));
private _pinspDefault = round (8 + (12 * (_vt / 500)));
private _pinsp = (_target getVariable ["ACME_vent_pinsp", _pinspDefault]) max _pinspFloor min 60;
private _psup = (_target getVariable ["ACME_vent_psup", 10]) max 0 min 50;
private _trig = _target getVariable ["ACME_vent_trigSensCmH2O", missionNamespace getVariable ["ACME_vent_trigSensCmH2O", -2]];
private _fio2 = _target getVariable ["ACME_vent_fio2", 21];
if (isNil {_target getVariable "ACME_vent_pinsp"}) then { _target setVariable ["ACME_vent_pinsp", _pinsp, true]; };
if (isNil {_target getVariable "ACME_vent_psup"}) then { _target setVariable ["ACME_vent_psup", _psup, true]; };
if (isNil {_target getVariable "ACME_vent_trigSensCmH2O"}) then { _target setVariable ["ACME_vent_trigSensCmH2O", _trig, true]; };
uiNamespace setVariable ["ACME_vent_bpm", _bpm];
uiNamespace setVariable ["ACME_vent_vt", _vt];
uiNamespace setVariable ["ACME_vent_pinsp", _pinsp];
uiNamespace setVariable ["ACME_vent_fio2", _fio2];
uiNamespace setVariable ["ACME_vent_sel", "none"];  // the selected field: none, bpm or vt.
uiNamespace setVariable ["ACME_vent_editing", false];  // in edit, so knob turns change the value.
uiNamespace setVariable ["ACME_vent_scrRect", [_sx, _sy, _sw, _sh]];

// the brightness veil is created dynamically by fn_ventveilraise rather than here, because it has to sit above
// controls that do not exist yet, so it is built after them and rebuilt whenever anything new appears.
// the veil rect covers the inlay art rather than the screen rect. those are not the same thing: the screen rect
// is x 0.334 to 0.543 and y 0.4185 to 0.5879 of the face, while the opaque extent of the art, measured off the
// decoded texture, is x 0.33203 to 0.54443 and y 0.41846 to 0.58887. the art is wider on both sides and taller
// at the foot, so a veil on the screen rect left uncovered slivers of white bar showing round the edges: 0.00197
// on the left, 0.00143 on the right and 0.00097 at the bottom, in canvas fractions.
// fn_ventflip works in face canvas fractions, because the reverse art is a full-canvas 1:1 overlay just like the
// front. publishing the rect keeps the hit zones and the art in the same coordinate space by construction.
uiNamespace setVariable ["ACME_vent_faceRect", [_faceX, _faceY, _faceW, _faceH]];

// reverse side hit zones, from the annotated reference. they are hidden until the device is turned round.
{
    _x params ["_idc","_x0","_x1","_y0","_y1"];
    private _c = _dlg displayCtrl _idc;
    if (!isNull _c) then {
        _c ctrlSetPosition [_faceX + _faceW*_x0, _faceY + _faceH*_y0, _faceW*(_x1-_x0), _faceH*(_y1-_y0)];
        _c ctrlCommit 0;
        _c ctrlShow false;
    };
} forEach [
    [87778, 0.4697, 0.8975, 0.5127, 0.6309],  // the battery hatch.
    [87779, 0.7588, 0.8408, 0.4023, 0.4844]  // the power button.
];
(_dlg displayCtrl 87778) ctrlAddEventHandler ["ButtonClick", { ["swap"]  call ACME_fnc_ventFlip; }];
(_dlg displayCtrl 87779) ctrlAddEventHandler ["ButtonClick", { ["power"] call ACME_fnc_ventFlip; }];
// hidden, not merely blanked. both carry a dark background, so leaving them shown with empty text parked them at
// their config position as black bars across the world. clearing the text was never going to be enough.
{ private _c = _dlg displayCtrl _x; if (!isNull _c) then { _c ctrlSetText ""; _c ctrlShow false; _c ctrlCommit 0; }; } forEach [88000, 88001];
uiNamespace setVariable ["ACME_vent_flipped", false];
// this is not set here. fn_ventpanelopen reads the machine's own persisted power state before the dialog is
// created, and forcing true here would switch on any device the moment its panel was opened.
uiNamespace setVariable ["ACME_vent_swapUntil", -1];
uiNamespace setVariable ["ACME_vent_swapMsgUntil", -1];
uiNamespace setVariable ["ACME_vent_faceTexCur", ""];

uiNamespace setVariable ["ACME_vent_veilRect", [
    _faceX + _faceW * 0.33203,
    _faceY + _faceH * 0.41846,
    _faceW * 0.21240,
    _faceH * 0.17041
]];
uiNamespace setVariable ["ACME_vent_veilCtls", []];
uiNamespace setVariable ["ACME_vent_veilC", []];

// boot sequence gating.
private _doBoot = uiNamespace getVariable ["ACME_vent_doBoot", true];
// THE DISPLAY BRIGHTNESS RESETS ON EVERY START, WITHOUT EXCEPTION.
// this is the SECOND boot path. fn_ventBootStart handles a press of the power button on the reverse face and a
// restart after a battery swap, and this one handles a panel opening onto a machine that has not booted yet. both
// mean the machine is starting, so both reset, or a cold open would come up carrying whatever the last operator
// left on the dial.
// it is gated on _doBoot, so reopening the panel on a machine that is already running leaves the setting alone.
// that is not a restart and the operator's choice should survive it.
// see the note in fn_ventBootStart for why level 3 and not level 1.
if (_doBoot) then {
    uiNamespace setVariable ["ACME_vent_brightness", (missionNamespace getVariable ["ACME_vent_brightDefault", 3])];
};
uiNamespace setVariable ["ACME_vent_bootT0", if (_doBoot) then { diag_tickTime } else { -1 }];
// B20: live flow-derived readouts need a short sensor-settle window on every fresh panel open. The respiratory
// mechanics are already running; this only withholds the displayed minute-volume value while the rolling flow
// estimate settles, which prevents a stale/high first sample from flashing before the current breaths dominate.
private _mvDelay = (missionNamespace getVariable ["ACME_vent_mvSensorDelaySec", 2.0]) max 2.0;
uiNamespace setVariable ["ACME_vent_mvValidAfter", diag_tickTime + _mvDelay];
uiNamespace setVariable ["ACME_vent_mvLastTarget", _target];
uiNamespace setVariable ["ACME_vent_mvWasDriving", _target getVariable ["ACME_vent_driving", false]];
uiNamespace setVariable ["ACME_vent_liveReadoutNext", 0];
// boot runs in three phases, and the screen follows the audio rather than the other way round.
// 1. blackout: a dead black panel, with no inlay, no logo and nothing else. this is the half-beat between
// pressing the power button and the device actually waking. without it the panel snapped straight to a lit
// splash, which read as already on rather than just switched on.
// 2. splash: a white screen with the sparrow mark. the jingle fires a beat into this.
// 3. handover: a short gap, then the self-test takes over.
// all four numbers are tunables, so re-cutting the audio only means updating one of them.
private _blackout    = missionNamespace getVariable ["ACME_vent_blackoutSec", 0.45];
private _jingleDelay = missionNamespace getVariable ["ACME_vent_jingleDelaySec", 0.5];
private _jingleLen   = missionNamespace getVariable ["ACME_vent_jingleSndLen", 1.675];
private _bootGap     = missionNamespace getVariable ["ACME_vent_bootGapSec", 0.25];
uiNamespace setVariable ["ACME_vent_bootDur", _blackout + _jingleDelay + _jingleLen + _bootGap];
uiNamespace setVariable ["ACME_vent_blackoutUntil", (diag_tickTime + _blackout)];
if (_doBoot) then {
    private _bT0 = uiNamespace getVariable ["ACME_vent_bootT0", -1];

    // phase 1, dead black. hide the logo and blank the inlay, so nothing is lit at all.
    (_dlg displayCtrl 87760) ctrlShow false;
    (_dlg displayCtrl 87702) ctrlSetText "";
    (_dlg displayCtrl 87714) ctrlShow false;
    (_dlg displayCtrl 87710) ctrlSetBackgroundColor [0,0,0,1];  // substrate: literal, and never through ventcolor.
    (_dlg displayCtrl 87710) ctrlCommit 0;

    // phase 2, the screen wakes. both this and the jingle are stamped with the boot t0 they belong to and re-check
    // the dialog, so closing the panel mid-boot drops them rather than firing into a dead display or landing on top
    // of a second, fresher boot.
    [{
        params ["_bT0", "_dlg"];
        if ((uiNamespace getVariable ["ACME_vent_bootT0", -1]) isEqualTo _bT0
            && {!isNull (uiNamespace getVariable ["ACME_vent_dlg", displayNull])}) then {
            (_dlg displayCtrl 87760) ctrlShow true;
            // explicitly set the startup inlay. boot does not call ventPanelShowScreen, because the router and its inlay
            // rule only run once boot elapses, so without this the splash shows whatever the control was created with, and
            // a stale inlaycur from a previous open could leave the cutout inlay on screen.
            (_dlg displayCtrl 87702) ctrlSetText "\acm_extended\ui\vent\ventway_sparrow_robust_menu_startup_inlay.paa";
            uiNamespace setVariable ["ACME_vent_inlayCur", "\acm_extended\ui\vent\ventway_sparrow_robust_menu_startup_inlay.paa"];
            (_dlg displayCtrl 87714) ctrlShow false;  // there is no alarm square on the startup inlay.
        };
    }, [_bT0, _dlg], _blackout] call CBA_fnc_waitAndExecute;

    // the power-on jingle, a beat into the lit splash. it is distinct from ventilator_startup_sfx, which is the
    // mechanical spin-up on the self-test screen, and from the running loop.
    [{
        params ["_bT0"];
        if ((uiNamespace getVariable ["ACME_vent_bootT0", -1]) isEqualTo _bT0
            && {!isNull (uiNamespace getVariable ["ACME_vent_dlg", displayNull])}) then {
            playSound3D ["acm_extended\sound\vent_jingle_sfx.ogg", ACE_player, false, getPosASL ACE_player, 3, 1, 30];
        };
    }, [_bT0], (_blackout + _jingleDelay)] call CBA_fnc_waitAndExecute;
} else {
    // no boot on this open, so route straight to the correct screen now.
    (_dlg displayCtrl 87760) ctrlShow false;
    private _configured = _target getVariable ["ACME_vent_configured", false];
    // resume where you left off. fn_ventpanelopen already decided: a fresh casualty forces WEIGHT, because you are
    // not getting a mode picked for you, and anything else picks up on the last screen you were looking at.
    private _start = uiNamespace getVariable ["ACME_vent_startScreen", ""];
    if (_start isEqualTo "") then { _start = if (_configured) then {"live"} else {"weight"}; };
    [_start] call ACME_fnc_ventPanelShowScreen;
};

// start the tick.
private _pfh = [{
    params ["_args", "_id"];
    private _display = _args select 0;
    if (isNull _display || {_display isNotEqualTo (uiNamespace getVariable ["ACME_vent_dlg", displayNull])}
        || {_id != (uiNamespace getVariable ["ACME_vent_pfh", -1])}) exitWith {[_id] call CBA_fnc_removePerFrameHandler;};
    [] call ACME_fnc_ventPanelTick;
}, 0, [_dlg]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_vent_pfh", _pfh];

// knob emulation. the mouse wheel turns the knob. for MouseZChanged, _this is [display, scroll], and a scroll
// above 0 is up, or clockwise.
_dlg displayAddEventHandler ["MouseZChanged", {
    if ([_this,"wheel"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_d", "_scroll"];
    [[1,-1] select (_scroll < 0)] call ACME_fnc_ventPanelKnob;
    true
}];

// middle-click is the only select method. it is a dial-only device, so the mouse never changes the selection and
// middle-click only activates the current dial selection. the problem with a single handler on the background
// is that the strip buttons, rows and field-hit controls sit on top of it and intercept the mouse, so the
// background never sees the click. the fix is to attach the same MouseButtonDown handler to every interactive
// control, and to the background, so wherever the cursor is, a middle-click activates whatever the dial
// currently has selected. the handler ignores which control was clicked. it never moves the selection, it only
// activates selidx.
// MMB is a long press now: tap to select, hold for 4 seconds to power off.
// arma has no held-for-n-seconds event, and, this is the part that shapes the whole design, no way to poll
// whether a mouse button is currently down. so a hold has to be assembled from the edges: stamp the time on
// button-down, measure it from the panel tick, and clear it on button-up.
// that forces select to move from down to up. it is not a compromise, it is how every long press on every device
// works, because you cannot know a press was short until it ends. the latency is a few milliseconds and nobody
// will feel it.
// the failure mode is real and worth naming. if the button-up is never delivered, such as an alt-tab mid-hold,
// the stamp is left behind and the tick would power the vent off on its own. there are three guards, in order
// of how much they buy.
// the tick fires once at 4 s and clears the stamp, so a stale hold cannot fire repeatedly.
// the stamp is cleared on panel close and on screen change, so it cannot survive the panel that made it.
// and the filling bar is the real protection: an accidental hold is visible for four full seconds, in the middle
// of the screen, saying what is about to happen, and letting go cancels it.
private _midClickEH = {
    if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_ctrl", "_button"];
    if (_button == 2) then {
        uiNamespace setVariable ["ACME_vent_mmbDown", diag_tickTime];
        uiNamespace setVariable ["ACME_vent_mmbFired", false];
    };
    false
};

// button-up. a short press is a select. a press that already powered the machine off is not, so it is
// consumed.
private _midUpEH = {
    if ([_this,"up"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_ctrl", "_button"];
    if (_button == 2) then { [] call ACME_fnc_ventMmbUp; };
    false
};
{
    private _c = _dlg displayCtrl _x;
    if (!isNull _c) then {
        _c ctrlAddEventHandler ["MouseButtonDown", _midClickEH];
        _c ctrlAddEventHandler ["MouseButtonUp",   _midUpEH];
    };
} forEach [
    87709,  // the full-screen background.
    87740,87742,87744,87746,  // the strip buttons.
    87750,87751,  // the live field hit controls, BPM and vt.
    87781,87782,88000,88001,87785,87786,  // the list rows.
    87790,87792,87794,87796  // the nav chevron buttons.
];
// a display-level fallback. it also catches the middle button at the display level, so even if a control
// consumes or misses it, the activation still fires. that is belt and suspenders for reliable middle-click
// selection.
// the middle-click state is reset on every open. the select is assembled from a button-down stamp and a
// button-up edge, see the long-press notes above, which means it has state that lives in uinamespace between
// openings. if an up is never delivered, and alt-tabbing mid-click is the usual way while closing the panel on
// a held button is the other, that state is left behind and the next press can be swallowed by it. that is the
// symptom where middle click stopped selecting anything. nothing here is expensive, so all of it is cleared
// unconditionally on every open rather than trying to work out which of the three variables was left dirty.
uiNamespace setVariable ["ACME_vent_mmbDown", -1];
uiNamespace setVariable ["ACME_vent_mmbFired", false];
uiNamespace setVariable ["ACME_vent_mmbUpFrame", -1];
[] call ACME_fnc_ventHoldClear;

_dlg displayAddEventHandler ["MouseButtonDown", {
    if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_d", "_button"];
    if (_button == 2) then {
        uiNamespace setVariable ["ACME_vent_mmbDown", diag_tickTime];
        uiNamespace setVariable ["ACME_vent_mmbFired", false];
    };
    false
}];
_dlg displayAddEventHandler ["MouseButtonUp", {
    if ([_this,"up"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_d", "_button"];
    if (_button == 2) then { [] call ACME_fnc_ventMmbUp; };  // the same choke point, because the frame gate dedupes.
    false
}];
