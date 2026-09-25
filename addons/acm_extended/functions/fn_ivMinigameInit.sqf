// the iv mini-game dialog init. it frames a limb, lays out a compact right-side slot column, with BAND on top
// then the 14, 16 and 18 g needles, loads all three band and vein sites for the limb so the held band snaps
// magnetically to the nearest, wires the ultrawide-safe cursor calibration and a display-level click router, and
// starts the tick.
disableSerialization;
params ["_display"];
// Retained on the owning display so an obsolete unload cannot close a newer session.
_display setVariable ["ACME_IV_Session", +(uiNamespace getVariable ["ACME_IV_Session", []])];
_display setVariable ["ACME_IV_ReturnMenu", +(uiNamespace getVariable ["ACME_IV_ReturnMenu", []])];
uiNamespace setVariable ["ACME_IV_DLG", _display];
uiNamespace setVariable ["ACME_minigame_open", true];

private _bodyPart = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
private _site     = uiNamespace getVariable ["ACME_IV_Site", "lower"];
private _patient  = uiNamespace getVariable ["ACME_IV_Patient", objNull];
if (!isNull _patient) then {[_patient, "ui:iv:" + str clientOwner, true] call ACME_fnc_ecgJostleRequest;};

// load all three sites for this limb, so the band can snap between upper, middle and lower. each site can use a
// different view, because the basilic and popliteal are rear, and we render one view at a time. we pick the
// starting view from the launched site, and only allow snapping between sites that share that view.
private _isEJ = (toLower _bodyPart == "ej");
private _siteOrder = if (_isEJ) then { ["left", "right"] } else { ["lower", "middle", "upper"] };
private _allSites = createHashMap;
private _startView = "";
{
    private _d = [_bodyPart, _x] call ACME_fnc_ivSiteData;
    if !(_d isEqualTo []) then {
        _d params ["_vTex", "_bTex", "_bU", "_bV", "_vU", "_vV", "_lbl"];
        _allSites set [_x, [_vTex, _bTex, _bU, _bV, _vU, _vV, _lbl]];
    };
} forEach _siteOrder;

private _data = _allSites getOrDefault [_site, []];
if (_data isEqualTo []) exitWith {
    // A failed site lookup closes the display and leaves a local notice.
    [format ["No IV site data for %1 (%2).", _bodyPart, _site], 2] call ace_common_fnc_displayTextStructured;
    [86500] call ACME_fnc_minigameClose;
};
_data params ["_viewTex", "_bandTex", "_bandU", "_bandV", "_veinU", "_veinV", "_label"];
uiNamespace setVariable ["ACME_IV_View", _viewTex];

// persist the full per-site list, as a plain array of [site, view, bandu, bandv, veinu, veinv, label], so the flip
// button can rebuild the snap set for the other view.
private _siteList = [];
{
    _y params ["_vTex", "_bTex", "_bU", "_bV", "_vU", "_vV", "_lbl"];
    _siteList pushBack [_x, _vTex, _bU, _bV, _vU, _vV, _lbl, _bTex];
} forEach _allSites;
uiNamespace setVariable ["ACME_IV_SiteList", _siteList];

// A site on the launched view is a snap target. A rear-only site is not a target on a front view.
// AN OCCUPIED LOCATION IS STILL A SNAP TARGET.
// r-26 to r-31 removed an occupied location from this set. That stopped the medic from putting the band back
// on a limb that already holds an IV. The band is a tool and not a permission.
// The medic applies the band, removes the band, and adds an IV at any time.
private _snapSites = [];
{
    _y params ["_vTex", "_bTex", "_bU", "_bV", "_vU", "_vV", "_lbl"];
    if (_vTex == _viewTex) then {
        _snapSites pushBack [_x, _bU, _bV, _vU, _vV, _lbl, _bTex];
    };
} forEach _allSites;
uiNamespace setVariable ["ACME_IV_SnapSites", _snapSites];
// The dialog opens at the launched site. An occupied location no longer moves the opening site,
// because an occupied location is still a valid target for the band and for a new stick.

// the active site state, starting at the launched site.
uiNamespace setVariable ["ACME_IV_Site", _site];  // physical BOA site
uiNamespace setVariable ["ACME_IV_ProbeSite", _site];  // independent vein currently under the provider
uiNamespace setVariable ["ACME_IV_BandUV", [_bandU, _bandV]];
uiNamespace setVariable ["ACME_IV_VeinUV", [_veinU, _veinV]];
// the candidate veins at this site. outside the antecubital fossa this is the single strip it always was.
if (_isEJ) then {
    // the EJ resolves its own two veins per frame in fn_ivMinigameTick, so it gets an EMPTY set and the
    // nearest-vein call falls back to the single-strip measurement against whatever that block chose.
    uiNamespace setVariable ["ACME_IV_VeinSet", []];
} else {
    uiNamespace setVariable ["ACME_IV_VeinSet",
        [(uiNamespace getVariable ["ACME_IV_Patient", objNull]),
     (uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"]),
         _site, _veinU, _veinV] call ACME_fnc_ivVeinSet];
};
uiNamespace setVariable ["ACME_IV_BandTex", _bandTex];
uiNamespace setVariable ["ACME_IV_Label", _label];
// THE SITE CAPTION IS OFF. it named the vein in blue across the top of the panel, which told the medic the
// answer to the thing the panel is asking them to find by feel.
// the text is still written, and fn_ivMinigameClick, fn_ivMinigameFlip and fn_ivMinigameRestoreState still keep
// it current, so bringing it back is deleting the ctrlShow line below and nothing else.
(_display displayCtrl 86504) ctrlSetText _label;
(_display displayCtrl 86504) ctrlShow false;
uiNamespace setVariable ["ACME_IV_Stage", "ready"];  // a BOA improves palpability; it is never an IV permission gate.
uiNamespace setVariable ["ACME_IV_BandOn", false];
uiNamespace setVariable ["ACME_IV_Held", "none"];
uiNamespace setVariable ["ACME_IV_Gauge", 16];
// There is no puncture yet. Therefore there is no site.
// fn_ivMinigameRestoreState can set this value again below.
uiNamespace setVariable ["ACME_IV_InsSite", ""];
uiNamespace setVariable ["ACME_IV_SnapUV", [_bandU, _bandV]];  // where the held band currently snaps.

// ej mode: no band on the neck. both jugulars are live, and the active side tracks the cursor in the tick.
if (_isEJ) then {
    private _lE = _allSites getOrDefault ["left", []];
    private _rE = _allSites getOrDefault ["right", []];
    if (count _lE >= 6) then { uiNamespace setVariable ["ACME_IV_EJVeinL", [_lE select 4, _lE select 5]]; };
    if (count _rE >= 6) then { uiNamespace setVariable ["ACME_IV_EJVeinR", [_rE select 4, _rE select 5]]; };
    uiNamespace setVariable ["ACME_IV_EJMode", true];
    uiNamespace setVariable ["ACME_IV_EJSide", "right"];  // anatomical side; legacy alias, not an art direction.
    uiNamespace setVariable ["ACME_IV_EJAnatomicalSide", "right"];  // the patient side, for the ACM iv registration.
    uiNamespace setVariable ["ACME_IV_BandOn", true];  // bypass the band gate. palpation and the stick are always live.
    uiNamespace setVariable ["ACME_IV_Stage", "ready"];  // there is no needband stage.
    // the ej is a fat, superficial target, so it is a touch more forgiving than a peripheral stick. all of it is
    // tunable.
    // feelradius is kept modest, so the palpable zone stays on the neck, from the chin down to above the collarbone,
    // rather than spilling up toward the mouth. the ej also gets its own shorter strip length, set after the global
    // striphalf below, so the vein reads as a neck-length vertical rather than a long limb vein.
    uiNamespace setVariable ["ACME_IV_Patency", 1];
    uiNamespace setVariable ["ACME_IV_FeelRadius", 0.018];
    uiNamespace setVariable ["ACME_IV_HitRadius", 0.013];
    uiNamespace setVariable ["ACME_IV_MaxHot", 1.0];
} else {
    uiNamespace setVariable ["ACME_IV_EJMode", false];
    uiNamespace setVariable ["ACME_IV_EJAnatomicalSide", ""];
};

// the aspect fix.
private _finite = { params ["_v"]; (_v isEqualType 0) && {finite _v} };
private _af = 0.5625;
private _pw = pixelW; private _ph = pixelH;
if (([_pw] call _finite) && {[_ph] call _finite} && {_pw > 0} && {_ph > 0}) then {
    private _c = _pw / _ph;
    if (([_c] call _finite) && {_c > 0.05} && {_c < 4}) then { _af = _c; };
};
uiNamespace setVariable ["ACME_IV_AspectFix", _af];

// The body rect: a framed limb, centered.
private _szX = safeZoneX; private _szY = safeZoneY; private _szW = safeZoneW; private _szH = safeZoneH;
private _cx = _szX + (_szW / 2);
// ACME_iv_uiScaleV3 enlarges the limb. it CANNOT change the difficulty, and that is by construction rather than by
// care: fn_ivVeinDist returns its distance in BODY-WIDTH FRACTIONS, and fn_ivSiteDifficulty returns feel and hit
// radii in the same fractions. the vein, the tolerance and the safe radii all scale with the rect together, so
// the ratio the stick is judged on is identical at any size. what does change is pixels per fraction, so the
// same tolerance covers more screen and is easier to aim at with a mouse. that is the point of making it bigger.
// V3 rebases the user-facing scale: new 1.00 is exactly the former 1.10 visual size.
// A new setting key intentionally resets saved V2 preferences so an old saved 1.10 does not become 1.21.
// The lower setting limit is reduced by the same factor so the previous absolute minimum remains available.
// Geometry, input, marks and instruments all read this one body rectangle.
private _zoomSetting = missionNamespace getVariable ["ACME_iv_uiScaleV3", 1];
if (!(_zoomSetting isEqualType 0) || {!finite _zoomSetting}) then {_zoomSetting = 1;};
_zoomSetting = (_zoomSetting max ((0.66 / 0.925) / 1.10)) min 1.5;
private _zoom = _zoomSetting * 1.10;
// Match the old tray at the preserved minimum and then grow with the same physical
// scale as the patient. Its independent fit always keeps the final tray slot reachable.
private _k = if (_zoom < 1) then {
    linearConversion [0.66 / 0.925, 1, _zoom, 1, 1.6, true]
} else {1.6 * _zoom};
private _bodyH = _szH * 0.925 * _zoom;
private _bodyW = _bodyH * _af;
private _bodyX = _cx - (_bodyW / 2);
private _bodyY = _szY + (_szH * 0.5075) - (_bodyH / 2);
// Larger views may crop transparent canvas/body ends. Up/Down pans the entire
// patient layer so every site and old puncture remains reachable at full zoom.
uiNamespace setVariable ["ACME_IV_BodyRect", [_bodyX, _bodyY, _bodyW, _bodyH]];
uiNamespace setVariable ["ACME_IV_BodyRectBase", [_bodyX, _bodyY, _bodyW, _bodyH]];  // unshaken. see fn_motionshake.

private _limb = _display displayCtrl 86501;
_limb ctrlSetText _viewTex;
_limb ctrlSetPosition [_bodyX, _bodyY, _bodyW, _bodyH];
_limb ctrlCommit 0;

// This static background group sits between skin and every placed mark/band.
// It stays in screen space; child redness controls receive one motion offset.
private _prepLayer = _display displayCtrl 86508;
_prepLayer setVariable ["ACME_UI_NoShake", true];
_prepLayer ctrlEnable false;

private _band = _display displayCtrl 86502;
_band ctrlSetText _bandTex;
_band ctrlSetPosition [_bodyX, _bodyY, _bodyW, _bodyH];
_band ctrlSetTextColor [1, 1, 1, 1];
_band ctrlCommit 0;
_band ctrlShow false;

(_display displayCtrl 86503) ctrlSetText "";
// no helper text. the minigames give the medic the instruments and the casualty and nothing else, in the same
// way ACM and ACE do. every prompt still runs harmlessly behind this, so setting ACME_ui_helpText true puts
// them all back without touching a call site.
if (!(missionNamespace getVariable ["ACME_ui_helpText", false])) then { (_display displayCtrl 86503) ctrlShow false; };

// a compact slot column on the right: BAND, PAD, the 14, 16 and 18 g needles, then the saline line, each with a
// label under it.
// the slot size comes from the screen width, which is what it always did and what looks right on 16 by 9. that
// many rows of it do not fit the height of a 32 by 9 screen, which pushed the bottom slot off the panel.
// so the column is measured first and shrunk only if it does not fit. a screen with room is untouched.
// THE COUNT MUST MATCH THE ROWS ACTUALLY DRAWN. it is the band, the pad, one row per needle gauge, and the line
// slot when it is on. the 20g added a fourth gauge at v0.9.999r-44, so this went from 5 and 6 to 6 and 7. a
// count left behind is a column that runs off the bottom of an ultrawide screen and nowhere else, which is the
// worst kind of thing to leave behind.
private _rows  = 6;  // band, pad, 14g, 16g, 18g, 20g.
if (missionNamespace getVariable ["ACME_iv_lineSlot", false]) then { _rows = 7; };
// the tray takes the SAME physical scale the limb takes, so ACME_iv_uiScaleV3 grows the panel as one thing rather than
// growing the casualty and leaving the instruments the size they were. the fit check below still shrinks the
// column when it does not fit the screen height, so a large scale on a short screen degrades instead of
// overflowing.
private _slotW = _szW * 0.066 * _k;
private _slotH = _slotW * _af * 0.92;
private _lblH  = _szH * 0.024;
private _gap   = _szH * 0.012;
private _colY  = _szY + (_szH * 0.115);
private _avail = (_szY + (_szH * 0.97)) - _colY;
private _need  = (_slotH + _lblH + _gap) * _rows;
if (_need > _avail && {_need > 0}) then {
    private _k = _avail / _need;
    _slotW = _slotW * _k;
    _slotH = _slotH * _k;
    _lblH  = _lblH  * _k;
    _gap   = _gap   * _k;
};
private _step = _slotH + _lblH + _gap;
// anchor the column by its right edge, so a shrunk slot does not drift away from the panel edge.
private _colX = _szX + (_szW * 0.961) - _slotW;

// the band slot, row 0.
private _bandY = _colY;
(_display displayCtrl 86530) ctrlSetPosition [_colX, _bandY, _slotW, _slotH]; (_display displayCtrl 86530) ctrlCommit 0;
(_display displayCtrl 86531) ctrlSetPosition [_colX + _slotW*0.10, _bandY + _slotH*0.10, _slotW*0.80, _slotH*0.80]; (_display displayCtrl 86531) ctrlCommit 0;
(_display displayCtrl 86533) ctrlSetPosition [_colX, _bandY + _slotH, _slotW, _lblH]; (_display displayCtrl 86533) ctrlCommit 0;  // the BAND label.
(_display displayCtrl 86532) ctrlSetPosition [_colX, _bandY, _slotW, _slotH]; (_display displayCtrl 86532) ctrlCommit 0;
uiNamespace setVariable ["ACME_IV_BandSlotRect", [_colX, _bandY, _slotW, _slotH]];
(_display displayCtrl 86532) ctrlAddEventHandler ["MouseEnter", {["band",0,true] call ACME_fnc_ivTrayHover;}];
(_display displayCtrl 86532) ctrlAddEventHandler ["MouseExit",  {["band",0,false] call ACME_fnc_ivTrayHover;}];

// the pad slot, row 1.
private _padY = _colY + _step;
(_display displayCtrl 86535) ctrlSetPosition [_colX, _padY, _slotW, _slotH]; (_display displayCtrl 86535) ctrlCommit 0;
(_display displayCtrl 86536) ctrlSetPosition [_colX + _slotW*0.12, _padY + _slotH*0.16, _slotW*0.76, _slotH*0.68]; (_display displayCtrl 86536) ctrlCommit 0;
(_display displayCtrl 86538) ctrlSetPosition [_colX, _padY + _slotH, _slotW, _lblH]; (_display displayCtrl 86538) ctrlCommit 0;  // the PAD label.
(_display displayCtrl 86537) ctrlSetPosition [_colX, _padY, _slotW, _slotH]; (_display displayCtrl 86537) ctrlCommit 0;
uiNamespace setVariable ["ACME_IV_PadSlotRect", [_colX, _padY, _slotW, _slotH]];
(_display displayCtrl 86537) ctrlAddEventHandler ["MouseEnter", {["pad",0,true] call ACME_fnc_ivTrayHover;}];
(_display displayCtrl 86537) ctrlAddEventHandler ["MouseExit",  {["pad",0,false] call ACME_fnc_ivTrayHover;}];

// hide the old needle header, which is unused now.
(_display displayCtrl 86539) ctrlShow false;

// four needle slots, rows 2 to 5, then the saline line on row 6.
// Tray-only textures are cropped, centered and already horizontal. Avoid ctrlSetAngle here: its native
// transform can distort images at 90 degrees under custom FOV (BI T136844). All five stock poses were baked
// from the same source pixels, so hover only moves/scales square canvases and never stretches the catheter.
private _nY0 = _colY + (_step * 2);
private _iconScale = missionNamespace getVariable ["ACME_iv_trayIconScale", 2.45];
if (!(_iconScale isEqualType 0) || {!finite _iconScale}) then {_iconScale = 2.45;};
_iconScale = (_iconScale max 0.5) min 3;
private _gauges = [[86540,86541,86542,86543,14], [86544,86545,86546,86547,16], [86548,86549,86550,86551,18],
                   [86556,86557,86558,86559,20]];
private _needleRects = [];
{
    _x params ["_bgIdc", "_logoIdc", "_lblIdc", "_clickIdc", "_g"];
    private _ry = _nY0 + (_forEachIndex * _step);
    // Leave room for the 1.06 hover enlargement and the full upward fan on narrow/ultrawide trays.
    private _iconH = ((_slotH * _iconScale) min ((_slotW * 0.90) / _af)) min (_slotH * 1.95);
    // _af is pixelW / pixelH. For a physically square PAA canvas:
    //     width / pixelW == height / pixelH
    // therefore width = height * (pixelW / pixelH).
    private _iconW = _iconH * _af;

    private _iconX = _colX + (_slotW / 2) - (_iconW / 2);

    // Keep the existing height preference, bounded by the actual fan footprint. This also safely brings old
    // saved 0.34 defaults down from the top without overwriting the player's stored preference.
    private _iconBias = missionNamespace getVariable ["ACME_iv_trayIconBias", 0.66];
    if (!(_iconBias isEqualType 0) || {!finite _iconBias}) then {_iconBias = 0.66;};
    private _minBias = 0.12 + (0.27 * _iconH / _slotH);
    private _maxBias = 0.90 - (0.065 * _iconH / _slotH);
    _iconBias = (_iconBias max _minBias) min _maxBias;
    private _iconY = _ry + (_slotH * _iconBias) - (_iconH / 2);
    (_display displayCtrl _bgIdc) ctrlSetPosition [_colX, _ry, _slotW, _slotH]; (_display displayCtrl _bgIdc) ctrlCommit 0;
    private _logo = _display displayCtrl _logoIdc;
    _logo ctrlSetText format ["\acm_extended\ui\iv\tray\iv_tray_%1g_0_ca.paa", _g];
    _logo ctrlSetPosition [_iconX, _iconY, _iconW, _iconH];
    _logo ctrlCommit 0;
    (_display displayCtrl _lblIdc) ctrlSetPosition [_colX, _ry + _slotH, _slotW, _lblH]; (_display displayCtrl _lblIdc) ctrlCommit 0;
    private _click = _display displayCtrl _clickIdc;
    _click ctrlSetPosition [_colX, _ry, _slotW, _slotH];
    _click ctrlCommit 0;
    _click ctrlAddEventHandler ["MouseEnter", compile format ["['needle',%1,true] call ACME_fnc_ivTrayHover",_g]];
    _click ctrlAddEventHandler ["MouseExit",  compile format ["['needle',%1,false] call ACME_fnc_ivTrayHover",_g]];
    _needleRects pushBack [_g, [_colX, _ry, _slotW, _slotH], [_iconX,_iconY,_iconW,_iconH], _logoIdc];
} forEach _gauges;
uiNamespace setVariable ["ACME_IV_NeedleRects", _needleRects];

// the saline line slot is off. what the mini-game called a line is a capped extension set rather than an
// administration set, and the transfusion menu already owns hanging a bag, so the slot is hidden until that is
// settled. set ACME_iv_lineSlot true to bring it back.
private _lineSlotOn = missionNamespace getVariable ["ACME_iv_lineSlot", false];
if (!_lineSlotOn) then {
    { private _lc = _display displayCtrl _x; if (!isNull _lc) then { _lc ctrlShow false; }; } forEach [86552, 86553, 86554, 86555];
};

// the saline line slot, row 6. its art is a loop of tubing rather than a needle, so it takes its own scale.
// the multiplier follows the count of needle rows above it. it was 3 for three gauges and it is 4 for four.
private _lineY = _nY0 + (_step * (count _gauges));
private _lIconH = _slotH * (missionNamespace getVariable ["ACME_iv_trayLineScale", 1.9]);
// Same physical-pixel-square rule as the catheter icons above.
private _lIconW = _lIconH * _af;
(_display displayCtrl 86552) ctrlSetPosition [_colX, _lineY, _slotW, _slotH]; (_display displayCtrl 86552) ctrlCommit 0;
(_display displayCtrl 86553) ctrlSetPosition [_colX + (_slotW / 2) - (_lIconW / 2), _lineY + (_slotH / 2) - (_lIconH / 2), _lIconW, _lIconH]; (_display displayCtrl 86553) ctrlCommit 0;
(_display displayCtrl 86554) ctrlSetPosition [_colX, _lineY + _slotH, _slotW, _lblH]; (_display displayCtrl 86554) ctrlCommit 0;
(_display displayCtrl 86555) ctrlSetPosition [_colX, _lineY, _slotW, _slotH]; (_display displayCtrl 86555) ctrlCommit 0;

// the interaction surface, which is the mouse-move source, plus the cursor calibration.
uiNamespace setVariable ["ACME_IV_EvtUI", []];
uiNamespace setVariable ["ACME_IV_EvtUITime", -1];
uiNamespace setVariable ["ACME_IV_CalXminG",  1e9];
uiNamespace setVariable ["ACME_IV_CalXmaxG", -1e9];
uiNamespace setVariable ["ACME_IV_CalYminG",  1e9];
uiNamespace setVariable ["ACME_IV_CalYmaxG", -1e9];
uiNamespace setVariable ["ACME_IV_CalXminU", 0];
uiNamespace setVariable ["ACME_IV_CalXmaxU", 0];
uiNamespace setVariable ["ACME_IV_CalYminU", 0];
uiNamespace setVariable ["ACME_IV_CalYmaxU", 0];

private _surface = _display displayCtrl 86510;
_surface ctrlSetPosition [_bodyX, _bodyY, _bodyW, _bodyH];
_surface ctrlCommit 0;
_surface ctrlEnable true;
_surface ctrlShow true;

private _fnTrack = {
    params ["_ctrl", "_ex", "_ey"];
    if !((_ex isEqualType 0) && {_ey isEqualType 0} && {finite _ex} && {finite _ey}) exitWith {};
    uiNamespace setVariable ["ACME_IV_EvtUI", [_ex, _ey]];
    uiNamespace setVariable ["ACME_IV_EvtUITime", diag_tickTime];
    private _gmp = getMousePosition; _gmp params ["_gx", "_gy"];
    if !((_gx isEqualType 0) && {_gy isEqualType 0} && {finite _gx} && {finite _gy}) exitWith {};
    if (_gx < (uiNamespace getVariable ["ACME_IV_CalXminG",  1e9]))  then { uiNamespace setVariable ["ACME_IV_CalXminG", _gx]; uiNamespace setVariable ["ACME_IV_CalXminU", _ex]; };
    if (_gx > (uiNamespace getVariable ["ACME_IV_CalXmaxG", -1e9])) then { uiNamespace setVariable ["ACME_IV_CalXmaxG", _gx]; uiNamespace setVariable ["ACME_IV_CalXmaxU", _ex]; };
    if (_gy < (uiNamespace getVariable ["ACME_IV_CalYminG",  1e9]))  then { uiNamespace setVariable ["ACME_IV_CalYminG", _gy]; uiNamespace setVariable ["ACME_IV_CalYminU", _ey]; };
    if (_gy > (uiNamespace getVariable ["ACME_IV_CalYmaxG", -1e9])) then { uiNamespace setVariable ["ACME_IV_CalYmaxG", _gy]; uiNamespace setVariable ["ACME_IV_CalYmaxU", _ey]; };
};
_surface ctrlAddEventHandler ["MouseMoving", _fnTrack];
_surface ctrlAddEventHandler ["MouseHolding", _fnTrack];

// a display-level click router, like the chest seal. it resolves the cursor and routes: slot rects go to grab and
// the limb goes to apply band or stick. Right click removes an applied band or
// retracts the needle elsewhere. Left MouseButtonUp clears the palpate/wipe hold.
_display displayAddEventHandler ["MouseButtonDown", {
    if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true}; _this call ACME_fnc_ivMinigameClick; }];
_display displayAddEventHandler ["MouseButtonUp", {
    if ([_this,"up"] call ACME_fnc_minigameInputMouse) exitWith {true}; _this call ACME_fnc_ivMinigameRelease; }];

// the wheel threads the catheter off the needle.
// a display level MouseZChanged does not fire while the cursor sits over a control, and the limb picture covers
// most of the panel, so the handler goes on the controls as well. fn_ivminigamescroll ignores a notch that
// changes nothing, so overlapping handlers cannot double-step.
private _fnc_ivScroll = {
    if ([_this,"wheel"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_c", "_scroll"];
    if (_scroll == 0) exitWith { false };
    [(if (_scroll > 0) then {1} else {-1})] call ACME_fnc_ivMinigameScroll;
};
{
    if (!isNull _x) then { _x ctrlAddEventHandler ["MouseZChanged", _fnc_ivScroll]; };
} forEach (allControls _display);
_display displayAddEventHandler ["MouseZChanged", _fnc_ivScroll];

// the middle button needs the same treatment as the wheel. a display level MouseButtonDown does not see it while
// the cursor sits over a control, which is most of the panel, so it never reached the click router.
private _fnc_ivMB = {
    if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_c", "_button"];
    // Use the same hit-test as the display, including controls layered over the
    // band. The router consumes duplicate delivery before any second action.
    if !(_button in [1, 2]) exitWith { false };
    _this call ACME_fnc_ivMinigameClick
};
private _fnc_ivMBUp = {
    _this call ACME_fnc_ivMinigameRelease
};
// on every control, not a chosen few. the six named ones were a guess at what sits under the cursor, and the
// cursor is on the catheter sprite during the thread, which is a control created at runtime and was not in the
// list. whatever the pointer is over now carries the handler.
{
    if (!isNull _x) then {
        _x ctrlAddEventHandler ["MouseButtonDown", _fnc_ivMB];
        _x ctrlAddEventHandler ["MouseButtonUp", _fnc_ivMBUp];
    };
} forEach (allControls _display);
uiNamespace setVariable ["ACME_IV_MBHandler", _fnc_ivMB];
uiNamespace setVariable ["ACME_IV_MBUpHandler", _fnc_ivMBUp];
// CBA's fallback is attached to the MAIN display, not the IV dialog. Adapt its
// source before routing: the dialog/session guard correctly rejects display 46.
// Pair down/up on that same dialog so the shared input bridge releases rebinding
// state even when a picture consumes the normal dialog event. Both are removed
// on close, and only middle presses may cross this main-display adapter.
private _mbId = ["MouseButtonDown", {
    params ["_d", "_button"];
    if (_button != 2) exitWith { false };
    private _dialog = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
    if (isNull _dialog || {!([] call ACME_fnc_ivUiValid)}) exitWith { false };
    private _event = +_this;
    _event set [0, _dialog];
    _event call ACME_fnc_ivMinigameClick
}] call CBA_fnc_addDisplayHandler;
uiNamespace setVariable ["ACME_IV_MBDisplayHandler", _mbId];
private _mbUpId = ["MouseButtonUp", {
    params ["_d", "_button"];
    if (_button != 2) exitWith { false };
    private _dialog = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
    if (isNull _dialog || {!([] call ACME_fnc_ivUiValid)}) exitWith { false };
    private _event = +_this;
    _event set [0, _dialog];
    _event call ACME_fnc_ivMinigameRelease
}] call CBA_fnc_addDisplayHandler;
uiNamespace setVariable ["ACME_IV_MBUpDisplayHandler", _mbUpId];
uiNamespace setVariable ["ACME_IV_ScrollHandler", _fnc_ivScroll];

// the needle withdraw is the middle button, handled in fn_ivminigameclick.
// dialogs do not always deliver the middle button, which is why the laryngoscope uses the wheel instead of it.
// so a key does the same job. it is space by default and it rebinds by dik code with no rebuild, for example
// ACME_iv_keyWithdraw = 57.
_display displayAddEventHandler ["KeyDown", {
    if (_this call ACME_fnc_minigameInput) exitWith {true};
    params ["_d", "_key"];
    if (_key in [200, 208]) exitWith {
        [if (_key == 200) then {1} else {-1}] call ACME_fnc_ivMinigamePan;
        true
    };
    private _want = missionNamespace getVariable ["ACME_iv_keyWithdraw", 57];
    if (_key != _want) exitWith { false };
    [] call ACME_fnc_ivMinigameRetract
}];

// the hold, palpate and wipe state.
uiNamespace setVariable ["ACME_IV_Dragging", false];
uiNamespace setVariable ["ACME_IV_StripHalf", ([0.045, 0.085] select _isEJ)];  // EJ spans below the chin through the lateral neck/traps, stopping above the clavicles.
uiNamespace setVariable ["ACME_IV_Palpated", false];
uiNamespace setVariable ["ACME_IV_PalpTimer", 0];
uiNamespace setVariable ["ACME_IV_Cleaned", false];
uiNamespace setVariable ["ACME_IV_HoldCum", 0];
uiNamespace setVariable ["ACME_IV_PrepCtrls", []];
uiNamespace setVariable ["ACME_IV_PrepPts", []];
uiNamespace setVariable ["ACME_IV_PrepTotal", 0];
uiNamespace setVariable ["ACME_IV_PrepSum", [0, 0]];
uiNamespace setVariable ["ACME_IV_PrepLast", []];
uiNamespace setVariable ["ACME_IV_PrepCells", createHashMap];
// the prep bruise is one control that grows with the wiped area. it is deleted with the dabs, because it belongs
// to the scrub that made it.
private _pb = uiNamespace getVariable ["ACME_IV_PrepBruise", controlNull];
if (!isNull _pb) then { ctrlDelete _pb; };
uiNamespace setVariable ["ACME_IV_PrepBruise", controlNull];
uiNamespace setVariable ["ACME_IV_HoldLast", -1e9];
uiNamespace setVariable ["ACME_IV_WipeSwipes", 0];
uiNamespace setVariable ["ACME_IV_WipeDir", 0];
uiNamespace setVariable ["ACME_IV_WipeLastX", -1e9];
uiNamespace setVariable ["ACME_IV_WipeTravel", 0];
uiNamespace setVariable ["ACME_IV_CleanCtrl", controlNull];
uiNamespace setVariable ["ACME_IV_CleanTime", -1];

// the feel dot, small and pinpoint. it is created once.
private _dot = _display ctrlCreate ["ACME_IV_Dot", -1];
_dot ctrlShow false;
uiNamespace setVariable ["ACME_IV_DotCtrl", _dot];

// the cursor-following item sprites show the real art while held, the band or the needle, like the chest seal.
// they are dialog controls, 86505 for the band and 86506 for the needle, positioned each tick.
(_display displayCtrl 86505) ctrlShow false;
(_display displayCtrl 86506) ctrlShow false;

uiNamespace setVariable ["ACME_IV_PipCtrl", controlNull];

// the remove-mode and persistent-mark state, then draw any iv sites already on this limb and view. they live on
// the patient, so reopening or flipping the limb keeps them.
uiNamespace setVariable ["ACME_IV_PullIdx", -1];  // any pull in progress is abandoned here.
uiNamespace setVariable ["ACME_IV_MarkCtrls", []];
// the rotated-catheter frames: the tip, or insertion-point, anchor for each, measured off the art, with the pivot
// at the canvas center. they are keyed by frame suffix, where "" is the straight base. the tick, stick and
// render use them, so the needle tip stays under the cursor at every angle.
// the insertion point of each catheter orientation, as a fraction of the sprite canvas. the held cursor, the
// seat and the persistent hub all put this point under the mouse.
// the supercath art is authored against a pinned insertion plane. the assembly advances into a clip at that
// plane, so the leading end does not move between frames 01 and 14, and only the visible length changes. one
// anchor per orientation is therefore correct for the whole sequence, and it also holds the connected line art.
// these were measured off the 2048 mip of the frame 14 hub, being the topmost opaque pixel for the needle-up
// orientations and the bottommost for the ej, which points down into the neck. the extreme row is averaged by
// alpha, so a two pixel bevel still resolves to a point.
// do not hand-edit these. re-run tools/measure_iv.py if the catheter art is re-exported.
// frame 00 deliberately draws about 0.012 short of the plane, which is the tip hovering off the skin before
// contact. anchoring frame 00 to its own tip would delete that.
uiNamespace setVariable ["ACME_IV_FrameAnchors", createHashMapFromArray [
    ["",              [0.49166, 0.44434]],
    ["_15_left",      [0.47928, 0.44580]],
    ["_15_right",     [0.50434, 0.44482]],
    ["_30_left",      [0.46821, 0.44971]],
    ["_30_right",     [0.51542, 0.45020]],
    ["_ej",           [0.48588, 0.55127]],
    ["_ej_15_left",   [0.49876, 0.55127]],
    ["_ej_15_right",  [0.47418, 0.54883]]
]];
// how big the catheter draws, as a fraction of the body rect. the supercath art is three times longer than the
// art it replaced, because it carries the whole barrel and flash chamber, so drawing it at full size made it
// tower over the limb.
// it scales the held catheter, the seated one, the hub and the line together, so the anchors stay true.
// tune it live with ACME_iv_cathScale, for example 0.5 for smaller and 1 for the raw art size.
uiNamespace setVariable ["ACME_IV_CathScale", (missionNamespace getVariable ["ACME_iv_cathScale", 0.62])];
// the direction the needle points, as a unit vector in canvas fractions. the drag only advances the catheter
// along this axis, so pushing sideways does nothing.
// it was measured off the frame 01 art, from the far end of the barrel to the bevel. the real angles are 0, 13
// and 28 degrees, so the 15 and 30 in the folder names are nominal.
// do not hand-edit these. re-run tools/measure_iv.py if the catheter art is re-exported.
uiNamespace setVariable ["ACME_IV_FrameAxis", createHashMapFromArray [
    ["",              [ 0.0015, -1.0000]],
    ["_15_left",      [-0.2280, -0.9737]],
    ["_15_right",     [ 0.2301, -0.9732]],
    ["_30_left",      [-0.4642, -0.8857]],
    ["_30_right",     [ 0.4680, -0.8837]],
    ["_ej",           [-0.0036,  1.0000]],
    ["_ej_15_left",   [ 0.2280,  0.9737]],
    ["_ej_15_right",  [-0.2301,  0.9732]]
]];
// where the floating line meets the hub, as a canvas fraction. it is the connector end of the tubing, so it is
// the point that must sit under the cursor while the medic carries it to the hub.
uiNamespace setVariable ["ACME_IV_LineAnchors", createHashMapFromArray [
    ["",              [0.49246, 0.50391]],
    ["_15_left",      [0.49867, 0.50244]],
    ["_15_right",     [0.48559, 0.50195]],
    ["_30_left",      [0.50242, 0.49951]],
    ["_30_right",     [0.48117, 0.50049]],
    ["_ej",           [0.48510, 0.49170]],
    ["_ej_15_left",   [0.47936, 0.49463]],
    ["_ej_15_right",  [0.49293, 0.49170]]
]];
// Clear transient input, then restore any saved partial catheter on this face.
[] call ACME_fnc_ivMinigameResetView;
if (_isEJ) then {uiNamespace setVariable ["ACME_IV_Stage", "ready"];};
// the needle settles from wherever it is picked up, not from where the last one was left.
uiNamespace setVariable ["ACME_IV_NeedleTipPos", []];
uiNamespace setVariable ["ACME_IV_NeedleTipUV", []];
[] call ACME_fnc_ivMinigameRenderMarks;

// put back anything that was left half done on this limb: a band, a prepped site, a catheter still in the arm.
[] call ACME_fnc_ivMinigameRestoreState;
[true] call ACME_fnc_ivMinigameSyncBand;
[false] call ACME_fnc_ivMinigameSaveState;  // Observe without publishing this loaded view.

// the held-item cursor: a dynamic sprite that always draws above the static buttons and boxes. the static 86505,
// 86506 and 86507 stay hidden, and everything held routes through this control.
(_display displayCtrl 86505) ctrlShow false;
(_display displayCtrl 86506) ctrlShow false;
(_display displayCtrl 86507) ctrlShow false;
// Scrub bruising belongs above the redness background group, like every other
// bruise/hole. Only the held cursor needs to be raised above these patient marks.
private _oldPB = uiNamespace getVariable ["ACME_IV_PrepBruise", controlNull];
if (!isNull _oldPB) then { ctrlDelete _oldPB; };
private _pbC = _display ctrlCreate ["ACME_IV_Bruise", -1];
_pbC ctrlSetText "\acm_extended\ui\iv\bruise_ca.paa";
_pbC ctrlSetTextColor [1, 1, 1, 0];
_pbC ctrlCommit 0;
_pbC ctrlShow false;
uiNamespace setVariable ["ACME_IV_PrepBruise", _pbC];

private _oldHC = uiNamespace getVariable ["ACME_IV_HeldCursorCtrl", controlNull];
if (!isNull _oldHC) then { ctrlDelete _oldHC; };
private _heldC = _display ctrlCreate ["ACME_IV_HeldCursor", -1];
_heldC ctrlShow false;
uiNamespace setVariable ["ACME_IV_HeldCursorCtrl", _heldC];
[_heldC] call ACME_fnc_ivMinigameHookCtrl;

private _old = uiNamespace getVariable ["ACME_IV_PFH", -1];
if (_old isEqualType 0 && {_old >= 0}) then { [_old] call CBA_fnc_removePerFrameHandler; };
private _pfh = [{ call ACME_fnc_ivMinigameTick; }, 0, []] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_IV_PFH", _pfh];

[] call ACME_fnc_ivMinigameRefreshBandSlot;  // populate the slot counts and the blank state on open.

// the ej uses no constricting band, so hide the band slot and any band overlay.
if (_isEJ) then {
    { (_display displayCtrl _x) ctrlShow false; } forEach [86530, 86531, 86532, 86533];
    (_display displayCtrl 86502) ctrlShow false;
};

// the core minigame is complete before optional input integrations are installed. This ordering is deliberate:
// a fault in the flashlight bridge must never leave the limb and tray at their config-time zero-size positions.

// Install escape and flashlight handling on the next frame. They are conveniences around the minigame, not part
// of its layout. Keeping them in a separate scheduled call isolates any ACE interaction-menu fault from this init.
[{
    params [["_d", displayNull, [displayNull]]];
    if (isNull _d) exitWith {};
    _d displayAddEventHandler ["KeyDown", {
    if (_this call ACME_fnc_minigameInput) exitWith {true};
        params ["", "_key"];
        if (_key == 1) exitWith { [86500] call ACME_fnc_minigameClose; true };
        false
    }];
    [_d] call ACME_fnc_installLightKey;
}, [_display]] call CBA_fnc_execNextFrame;
