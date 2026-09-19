/* B66: one adaptive five-slot prepared-syringe carousel shared with Body Map.
   Compact Body Map stays narrow. A/D/click promotion modestly widens the track, pushes the A/D hints outward and
   restores a larger syringe presentation without moving unrelated UI. The current center syringe remains the
   authoritative medication for immediate Body Map injection. */
disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
// UI event handlers may pass a Control in _this. Rendering is intentionally immediate, so never parse _this as a numeric duration.
private _duration = 0;
// Client-performance rule: render state is immediate. Interpolating dozens of carousel controls caused frame hitches.
private _d = findDisplay 84000;
if (isNull _d) exitWith {};
// Establish the duration row before any carousel hit area is measured.
call ACME_fnc_skBodyActionRender;

private _body = (uiNamespace getVariable ["ACME_SK_View","syringe"]) == "body";
private _editMode = uiNamespace getVariable ["ACME_SK_TagEditMode",false];
if (!_body) exitWith {
    for "_slot" from 0 to 4 do {{(_d displayCtrl (84400 + _slot*10 + _x)) ctrlShow false;} forEach [0,1,2,3,4,5,6,8];};
    {(_d displayCtrl _x) ctrlShow false;} forEach [84460,84461,84462,84470,84471,84472,84480,84481,84700,84701,84702,84703,84810,84819,84820];
};

private _expanded = (uiNamespace getVariable ["ACME_SK_CarouselExpanded",false]) || {_editMode};
private _injectBusy = uiNamespace getVariable ["ACME_SK_InjectionBusy",false];
// Only the legacy/display-bound normal push owns the center plunger directly. Hardcore push drains the
// authoritative syringe row over time and therefore NEEDS carousel renders to follow the changing volume.
private _pushAnimPFH = uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1];
private _normalPushAnimActive = _pushAnimPFH isEqualType 0 && {_pushAnimPFH >= 0};
private _carouselBusy = uiNamespace getVariable ["ACME_SK_CarouselBusy",false];
private _hover = (uiNamespace getVariable ["ACME_SK_CarouselHover",false]) && {!_editMode};
private _hoverOffset = uiNamespace getVariable ["ACME_SK_CarouselHoverOffset", 99];
private _rect = _d getVariable ["ACME_SK_CarouselRect", _d getVariable [if (_expanded) then {"ACME_SK_CarouselRectExpanded"} else {"ACME_SK_CarouselRectCompact"}, [_uiX,safeZoneY,_uiW,safeZoneH*0.2]]];
_rect params ["_rx","_ry","_rw","_rh"];

private _native = _d getVariable ["ACME_SK_CarouselNativeRect",[0,0,_uiW*0.12,safeZoneH*0.46]];
private _ratio = ((_native select 2) / ((_native select 3) max 0.001)) max 0.05;
private _travel10 = _d getVariable ["ACME_SK_CarouselTravel10",safeZoneH*0.17];

private _tagFont = _d getVariable ["ACME_SK_TagFont",""];
if (_tagFont == "") then {
    _tagFont = if (fileExists "\acm_extended\ui\fonts\QEDaveMergens\QEDaveMergens96.fxy") then {"ACME_QEDaveMergens"} else {"Caveat"};
    _d setVariable ["ACME_SK_TagFont",_tagFont];
};

private _fnc_medName = {
    params ["_med"];
    private _name = localize (format ["STR_ACM_Circulation_Medication_%1",_med]);
    if (_name == "" || {_name == format ["STR_ACM_Circulation_Medication_%1",_med]}) then {_name = _med;};
    _name
};
private _fnc_mlText = {
    params ["_ml"];
    private _hund = round ((_ml max 0) * 100);
    if ((_hund mod 100) == 0) exitWith {str (round _ml)};
    if ((_hund mod 10) == 0) exitWith {(_ml toFixed 1)};
    _ml toFixed 2
};
// No tag: show only the last two medication pulls, in intentionally simple terms.
private _fnc_noTagTip = {
    params ["_e"];
    private _components = _e param [5,[],[[]]];
    if (!(_components isEqualType []) || {_components isEqualTo []}) then {
        private _m = _e param [0,"",[""]];
        private _ml = _e param [2,0,[0]];
        _components = if (_m == "") then {[]} else {[[_m,_ml]]};
    };
    private _out = [];
    private _start = ((count _components) - 2) max 0;
    for "_k" from _start to ((count _components) - 1) do {
        private _c = _components select _k;
        if (_c isEqualType [] && {count _c >= 2}) then {
            private _m = _c param [0,"",[""]];
            private _ml = _c param [1,0,[0]];
            if (_m != "") then {
                _out pushBack format ["%1mL of %2",[_ml] call _fnc_mlText,[_m] call _fnc_medName];
            };
        };
    };
    _out joinString (toString [10])
};

private _zone = _d displayCtrl 84481;
if (!isNull _zone) then {
    private _zoneUsable = !_editMode && {!_carouselBusy};
    _zone ctrlShow _zoneUsable; _zone ctrlEnable _zoneUsable;
};

// Flushes use the same centered workspace but are not persistent store records and do not carry syringe tags.
private _flush = uiNamespace getVariable ["ACME_SK_SelFlush",""];
if (_flush != "") exitWith {
    for "_slot" from 0 to 4 do {{(_d displayCtrl (84400 + _slot*10 + _x)) ctrlShow false;} forEach [0,1,2,3,4,5,6,8];};
    {(_d displayCtrl _x) ctrlShow false;} forEach [84460,84461,84462,84470,84471,84472,84480,84810,84819,84820];
    private _h = safeZoneH * (if (_expanded) then {0.435} else {0.150});
    private _w = _h * _ratio;
    private _x = _rx + _rw/2 - _w/2;
    private _y = _ry + _rh/2 - _h/2;
    private _bid = 84420;
    private _bar = _d displayCtrl (_bid+0); private _back = _d displayCtrl (_bid+1); private _pl = _d displayCtrl (_bid+2); private _tag = _d displayCtrl (_bid+3);
    private _alpha = 0.85;
    _bar ctrlSetText "\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa";
    _back ctrlSetText "\x\ACM\addons\circulation\ui\syringe\syringe_10_backbit_ca.paa";
    _pl ctrlSetText "\x\ACM\addons\circulation\ui\syringe\syringe_10_plunger_ca.paa";
    private _py = _y + (_travel10 * (_h / ((_native select 3) max 0.001)));
    _bar ctrlSetPosition [_x,_y,_w,_h]; _back ctrlSetPosition [_x,_y,_w,_h]; _pl ctrlSetPosition [_x,_py,_w,_h]; _tag ctrlSetText "";
    {_x ctrlSetTextColor [1,1,1,_alpha]; _x ctrlShow true; _x ctrlCommit _duration;} forEach [_bar,_back,_pl];
    _tag ctrlShow false;
    for "_ln" from 0 to 2 do {(_d displayCtrl (_bid+4+_ln)) ctrlShow false;};
    private _hit = _d displayCtrl (_bid+8);
    _hit setVariable ["ACME_SK_CarouselOffset",0];
    _hit ctrlSetTooltip "10mL Saline Flush";
    private _actionC = _d displayCtrl 84820;
    private _boundRect = if (!isNull _actionC) then {ctrlPosition _actionC} else {ctrlPosition (_d displayCtrl 84150)};
    private _bottom = (_boundRect select 1) - safeZoneH*0.012;
    private _padX = _w*0.22; private _padY = _h*0.12;
    private _hitY = _y-_padY;
    private _hitBottom = (_y+_h+_padY) min _bottom;
    private _hh = (_hitBottom-_hitY) max 0;
    _hit ctrlSetPosition [_x-_padX,_hitY,_w+2*_padX,_hh];
    _hit ctrlShow (_hh > 4*pixelH); _hit ctrlEnable (_hh > 4*pixelH); _hit ctrlCommit _duration;
    (_d displayCtrl 84001) ctrlSetText "";
    private _p = _d getVariable ["ACME_SK_ReturnPatient",objNull]; if (isNull _p) then {_p=uiNamespace getVariable ["ACME_SK_Patient",objNull];};
    (_d displayCtrl 84002) ctrlSetText (if (isNull _p) then {"Patient"} else {name _p});
};

private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _n = count _store;
if (_n < 1) exitWith {
    for "_slot" from 0 to 4 do {{(_d displayCtrl (84400 + _slot*10 + _x)) ctrlShow false;} forEach [0,1,2,3,4,5,6,8];};
    {(_d displayCtrl _x) ctrlShow false;} forEach [84460,84461,84462,84470,84471,84472,84480,84700,84701,84702,84703,84810,84819,84820];
    (_d displayCtrl 84001) ctrlSetText "";
    private _p = _d getVariable ["ACME_SK_ReturnPatient",objNull]; if (isNull _p) then {_p=uiNamespace getVariable ["ACME_SK_Patient",objNull];};
    (_d displayCtrl 84002) ctrlSetText (if (isNull _p) then {"Patient"} else {name _p});
};
private _idx = [_store] call ACME_fnc_skSelectedIndex;
if (_idx < 0) exitWith {};

private _centerX = _rx + _rw/2;
private _centerY = _ry + _rh/2;
// B66: maximized browsing is larger than B64/B65, while compact size changes only slightly.
private _fullH = safeZoneH * (if (_expanded) then {0.470} else {0.150});
private _fullW = _fullH * _ratio;
private _sc = if (_expanded) then {[0.34,0.66,1.0,0.66,0.34]} else {[0.28,0.55,1.0,0.55,0.28]};
private _al = if (_expanded) then {[0.08,0.34,1.0,0.34,0.08]} else {[0.06,0.24,0.85,0.24,0.06]};
private _dx = _rw * (if (_expanded) then {0.185} else {0.155});

// Hitboxes are bounded by the actual attached Edit Syringe Tag row and Draw Syringe button, never by sprite size.
private _editBodyRect = +(_d getVariable ["ACME_SK_EditTagBodyRect",[0,0,0,0]]);
private _drawForBounds = ctrlPosition (_d displayCtrl 84150);
private _actionCtrl = _d displayCtrl 84820;
private _durationCtrl = _d displayCtrl 84830;
private _boundCtrl = if (!isNull _durationCtrl && {ctrlShown _durationCtrl}) then {_durationCtrl} else {_actionCtrl};
private _actionForBounds = if (!isNull _boundCtrl) then {ctrlPosition _boundCtrl} else {_drawForBounds};
private _hoverTop = if ((_editBodyRect select 3) > 0) then {
    (_editBodyRect select 1) + (_editBodyRect select 3) + safeZoneH*0.007
} else {
    (_ry max (safeZoneY + safeZoneH*0.50))
};
private _hoverBottom = (_actionForBounds select 1) - safeZoneH*0.012;
if (!isNull _zone) then {
    private _zoneH = (_hoverBottom - _hoverTop) max 0;
    _zone ctrlSetPosition [_rx,_hoverTop,_rw,_zoneH];
    private _zoneUsable = !_editMode && {!_carouselBusy} && {_zoneH > 4*pixelH};
    _zone ctrlShow _zoneUsable; _zone ctrlEnable _zoneUsable;
    _zone ctrlCommit 0;
};

// Dedicated stored-tag editor remains native ACM size and is raised so the bottom cannot be cut off.
// B68: tag editing uses the exact native Draw Syringe rectangle for the STORED syringe's own size.
private _editNative = +_native;
private _editSize = (_store select _idx) param [1,10,[0]];
private _editNativeCtrl = _d displayCtrl (84010 + 3 * (([10,5,3,1] find _editSize) max 0) + 2);
if (!isNull _editNativeCtrl) then {
    private _nr = +(ctrlPosition _editNativeCtrl);
    if (_nr isEqualType [] && {count _nr == 4} && {(_nr select 2) > 0} && {(_nr select 3) > 0}) then {_editNative = _nr;};
};
private _editX = _editNative select 0;
private _editY = _editNative select 1;
if (_editMode) then {
    _fullW = _editNative select 2;
    _fullH = _editNative select 3;
    _centerX = _editX + _fullW/2;
    _centerY = _editY + _fullH/2;
};

private _lineY = [0.443,0.480,0.517];
private _lineH = 0.038;
private _lineFontH = 0.031; // B78: original tag font size, with the taller B75 editor rectangles retained.
for "_slot" from 0 to 4 do {
    private _off = _slot - 2;
    private _bid = 84400 + _slot*10;
    if ((_editMode && {_slot != 2}) || {_n == 1 && {_slot != 2}}) then {
        {(_d displayCtrl (_bid+_x)) ctrlShow false;} forEach [0,1,2,3,4,5,6,8];
    } else {
        private _j = ((((_idx + _off) mod _n) + _n) mod _n);
        private _e = _store select _j;
        _e params ["_med",["_size",10],["_amt",0],["_label",""],["_nsMl",0]];
        private _scale = if (_editMode) then {1} else {_sc select _slot};
        private _alpha = if (_editMode) then {1} else {_al select _slot};
        // B78: hover is presentation-only. It never changes carousel geometry; the syringe under the pointer simply
        // fades up to full opacity. Expansion remains exclusive to click/A/D (or another explicit click workflow).
        if (!_editMode && {_off == _hoverOffset}) then {_alpha = 1;};

        private _w = _fullW * _scale; private _h = _fullH * _scale;
        private _x = if (_editMode) then {_editX} else {_centerX + (_off * _dx) - _w/2};
        private _y = if (_editMode) then {_editY} else {_centerY - _h/2};

        private _bar = _d displayCtrl (_bid+0); private _back = _d displayCtrl (_bid+1); private _pl = _d displayCtrl (_bid+2); private _tag = _d displayCtrl (_bid+3);
        private _sz = str _size;
        private _isFlushBarrel = (_e param [12,"",[""]]) == "flush";
        _bar ctrlSetText (if (_isFlushBarrel && {_size == 10}) then {"\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa"} else {format ["\x\ACM\addons\circulation\ui\syringe\syringe_%1_barrel_ca.paa",_sz]});
        _back ctrlSetText format ["\x\ACM\addons\circulation\ui\syringe\syringe_%1_backbit_ca.paa",_sz];
        _pl ctrlSetText format ["\x\ACM\addons\circulation\ui\syringe\syringe_%1_plunger_ca.paa",_sz];
        _bar ctrlSetPosition [_x,_y,_w,_h]; _back ctrlSetPosition [_x,_y,_w,_h];
        _bar ctrlSetTextColor [1,1,1,_alpha]; _back ctrlSetTextColor [1,1,1,_alpha];

        private _frac = (((_amt + _nsMl) / (_size max 0.01)) max 0) min 1;
        private _sizeRatio = switch (_size) do {case 1:{10.2/10.5};case 3:{9.83/10.5};case 5:{10.3/10.5};default{1};};
        private _py = _y + (_travel10 * _sizeRatio * _frac * (_h / ((_native select 3) max 0.001)));
        // During an ordinary display-bound push, fn_skConfirmInjection owns the center plunger frame by frame.
        // Hardcore pushes do not use that animator: they mutate the stored syringe volume continuously, so the
        // carousel must follow that live fraction instead of freezing the plunger in its starting position.
        if !(_normalPushAnimActive && {_slot == 2}) then {_pl ctrlSetPosition [_x,_py,_w,_h];};
        _pl ctrlSetTextColor [1,1,1,_alpha];

        private _color = _e param [7,"none",[""]];
        private _hasTag = !(_color in ["","none"]);
        if (_hasTag) then {
            _tag ctrlSetText format ["\acm_extended\ui\syringe_tags\%1mL\tag_overlay_%1mL_%2.paa",_sz,_color];
            _tag ctrlSetTextColor [1,1,1,_alpha];
        } else {
            _tag ctrlSetText "";
        };
        _tag ctrlSetPosition [_x,_y,_w,_h];

        for "_ln" from 0 to 2 do {
            private _tc = _d displayCtrl (_bid+4+_ln);
            _tc ctrlSetFont _tagFont;
            _tc ctrlSetText (if (_hasTag) then {(_e param [8+_ln,"",[""]]) select [0,25]} else {""});
            _tc ctrlSetTextColor [0.08,0.08,0.08,_alpha];
            _tc ctrlSetPosition [_x+_w*0.247,_y+_h*(_lineY select _ln),_w*0.245,_h*_lineH];
            _tc ctrlSetFontHeight(_h*_lineFontH);
            _tc ctrlShow (_hasTag && {!(_editMode && {_slot == 2})});
            _tc ctrlCommit _duration;
        };

        {_x ctrlShow true; _x ctrlCommit _duration;} forEach [_bar,_back,_pl,_tag];
        if (!_hasTag) then {_tag ctrlShow false;};

        private _hit = _d displayCtrl (_bid+8);
        _hit setVariable ["ACME_SK_CarouselOffset",_off];
        // Only the selected center syringe owns hover text. Neighbor hitboxes remain clickable but silent.
        _hit ctrlSetTooltip "";

        private _padX = _w * 0.20; private _padY = _h * 0.11;
        private _hitY = (_y-_padY) max _hoverTop;
        private _hitBottom = (_y+_h+_padY) min _hoverBottom;
        private _hitH = (_hitBottom-_hitY) max 0;
        _hit ctrlSetPosition [_x-_padX,_hitY,_w+2*_padX,_hitH];
        // B73: slot 2 has a dedicated top-layer active hitbox. Keeping the generic center hitbox enabled underneath
        // it produced competing MouseEnter/Exit/tooltips as controls were repainted.
        private _hitUsable = (_slot != 2) && {!_editMode} && {!_injectBusy} && {!_carouselBusy} && {_hitH > 4*pixelH};
        _hit ctrlShow _hitUsable; _hit ctrlEnable _hitUsable; _hit ctrlCommit _duration;
    };
};

private _cur = +(_store select _idx);
while {count _cur < 12} do {_cur pushBack "";};
private _curColor = _cur param [7,"none",[""]];
private _curHasTag = !(_curColor in ["","none"]);
private _activeScale = 1;
private _aw = if (_editMode) then {_fullW} else {_fullW * _activeScale};
private _ah = if (_editMode) then {_fullH} else {_fullH * _activeScale};
private _ax = if (_editMode) then {_editX} else {_centerX - _aw/2};
private _ay = if (_editMode) then {_editY} else {_centerY - _ah/2};

// B71 injection feedback: center "Pushing..." directly above the active syringe but never on top of the
// Edit Syringe Tag row. It appears only for the three-second Body Map push.
private _pushStatus = _d displayCtrl 84810;
if (!isNull _pushStatus) then {
    private _showPush = _injectBusy && {!_editMode};
    if (_showPush) then {
        private _statusW = safeZoneH * 0.18;
        private _statusH = safeZoneH / 34;
        private _statusGap = safeZoneH * 0.005;
        private _editBottom = if ((_editBodyRect select 3) > 0) then {
            (_editBodyRect select 1) + (_editBodyRect select 3)
        } else {
            _ay - _statusH - (2*_statusGap)
        };
        private _statusY = (_ay - _statusH - _statusGap) max (_editBottom + _statusGap);
        _pushStatus ctrlSetPosition [_centerX - _statusW/2,_statusY,_statusW,_statusH];
        _pushStatus ctrlSetFontHeight (_statusH * 0.72);
        _pushStatus ctrlSetText "Pushing...";
        _pushStatus ctrlSetBackgroundColor [0,0,0,0];
        _pushStatus ctrlShow true;
        _pushStatus ctrlCommit _duration;
    } else {
        _pushStatus ctrlShow false;
    };
};

private _activeHit = _d displayCtrl 84480;
private _remembered = [_store,_idx] call ACME_fnc_skSyringeRemembered;
private _activeTip = if (_curHasTag) then {
    [_cur param [8,"",[""]],_cur param [9,"",[""]],_cur param [10,"",[""]]] joinString (toString [10])
} else {
    if (_remembered) then {[_cur] call _fnc_noTagTip} else {"???"}
};
_activeHit ctrlSetTooltip _activeTip;
private _hitW = _fullW * 1.55; private _hitH = _fullH * 1.26;
private _activeHitY = (_centerY-_hitH/2) max _hoverTop;
private _activeHitBottom = (_centerY+_hitH/2) min _hoverBottom;
private _activeH = (_activeHitBottom-_activeHitY) max 0;
_activeHit ctrlSetPosition [_centerX-_hitW/2,_activeHitY,_hitW,_activeH];
private _activeUsable = !_editMode && {!_injectBusy} && {!_carouselBusy} && {_activeH > 4*pixelH};
_activeHit ctrlShow _activeUsable; _activeHit ctrlEnable _activeUsable; _activeHit ctrlCommit _duration;

// Stored tag line editors: clickable/typeable without visible frames. Use the runtime font fallback so typed letters
// cannot disappear merely because the optional local QEDaveMergens bitmap assets are absent.
for "_ln" from 0 to 2 do {
    private _edit = _d displayCtrl (84460+_ln);
    _edit ctrlSetFont _tagFont;
    _edit ctrlSetText ((_cur param [8+_ln,"",[""]]) select [0,25]);
    _edit ctrlSetPosition [_ax+_aw*0.247,_ay+_ah*(_lineY select _ln),_aw*0.245,_ah*_lineH];
    _edit ctrlSetFontHeight (_ah*_lineFontH);
    _edit ctrlSetBackgroundColor [0,0,0,0];
    _edit ctrlSetTextColor [0.08,0.08,0.08,1];
    private _showEditor = _editMode && {_curHasTag};
    _edit ctrlShow _showEditor;
    _edit ctrlEnable _showEditor;
    _edit ctrlCommit _duration;
};

private _colorBtn = _d displayCtrl 84470;
private _btnH = safeZoneH/32;
private _gap = (4 * pixelW) max (_aw * 0.010);
private _btnX = 0;
private _btnY = 0;
private _btnW = safeZoneH*0.22;
_colorBtn ctrlSetText (if (_editMode) then {"Select Syringe Tag"} else {"Edit Syringe Tag"});
private _curTagShort = switch (_curColor) do {
    case "yellow_induction": {"Yellow"};
    case "orange_benzodiazepine": {"Orange"};
    case "blue_opioid": {"Light Blue"};
    case "blue_stripe_reversal": {"Blue / White"};
    case "red_paralytic": {"Red"};
    case "red_stripe_reversal": {"Red / White"};
    case "violet_vasopressor": {"Violet"};
    case "violet_stripe_hypotensive": {"Violet / White"};
    case "green_anticholinergic": {"Green"};
    case "gray_local_anesthetic": {"Gray"};
    case "salmon_antiemetic": {"Salmon / Pink"};
    case "white_saline_flush": {"White"};
    default {"None"};
};
_colorBtn ctrlSetTooltip (if (_editMode) then {format ["Select or change this syringe tag. Current: %1. None removes the tag.",_curTagShort]} else {"Edit this syringe's tag text and color"});
if (_editMode) then {
    private _btnBg = switch (_curColor) do {
        case "yellow_induction": {[0.38,0.31,0.04,0.92]};
        case "orange_benzodiazepine": {[0.42,0.20,0.04,0.92]};
        case "blue_opioid": {[0.08,0.28,0.46,0.92]};
        case "blue_stripe_reversal": {[0.08,0.28,0.46,0.92]};
        case "red_paralytic": {[0.42,0.07,0.07,0.92]};
        case "red_stripe_reversal": {[0.42,0.07,0.07,0.92]};
        case "violet_vasopressor": {[0.30,0.14,0.40,0.92]};
        case "violet_stripe_hypotensive": {[0.30,0.14,0.40,0.92]};
        case "green_anticholinergic": {[0.08,0.30,0.15,0.92]};
        case "gray_local_anesthetic": {[0.24,0.24,0.24,0.92]};
        case "salmon_antiemetic": {[0.43,0.20,0.22,0.92]};
        case "white_saline_flush": {[0.36,0.36,0.36,0.92]};
        default {[0.05,0.05,0.05,0.82]};
    };
    _colorBtn ctrlSetBackgroundColor _btnBg;
    _colorBtn ctrlSetTextColor [1,1,1,1];
} else {
    _colorBtn ctrlSetBackgroundColor [0.05,0.05,0.05,0.65];
    _colorBtn ctrlSetTextColor [1,1,1,1];
};
if (_editMode) then {
    // B78: both Select Syringe Tag buttons use the compact Draw width and the Body Map tag-face placement.
    // The button is centered under the physical tag area and uses native syringe geometry at every resolution.
    private _textW = ctrlTextWidth _colorBtn;
    _btnW = ((_textW + 12*pixelW) max (safeZoneH*0.090)) min (safeZoneH*0.145);
    private _tagCenterX = _ax + _aw*0.36;
    _btnX = _tagCenterX - _btnW/2;
    _btnY = _ay + _ah*0.575;
} else {
    // Ordinary Body Map: geometry is owned by skDynamicLayout so it moves in lock-step with IV/IO + IM.
    private _bodyEdit = +(_d getVariable ["ACME_SK_EditTagBodyRect",[_uiX + _uiW/2 - (_uiW/22),safeZoneY + safeZoneH*0.78,_uiW/11,_btnH]]);
    _btnX = _bodyEdit select 0;
    _btnY = _bodyEdit select 1;
    _btnW = _bodyEdit select 2;
    _btnH = _bodyEdit select 3;
};
_btnX = (_btnX max (_uiX + _gap)) min (_uiX + _uiW - _btnW - _gap);
if (_editMode) then {
    _colorBtn ctrlSetPosition [_btnX,_btnY,_btnW,_btnH];
    _colorBtn ctrlCommit _duration;
};
_colorBtn ctrlShow true;
_colorBtn ctrlEnable (!_injectBusy);

private _colorList = _d displayCtrl 84471;
if (!_editMode) then {_colorList lbSetCurSel -1; _colorList ctrlShow false;};
// B78: identical dropdown styling/behavior/placement to the Draw Syringe selector: dark list, click-toggle,
// left-aligned directly below the selector, with enough width for full purpose descriptions. Never hover-opens.
private _menuW = (_uiW * 0.24) min (safeZoneH * 0.78);
private _menuX = _btnX max (_uiX + _gap);
_menuX = _menuX min (_uiX + _uiW - _menuW - _gap);
private _menuY = _btnY + _btnH + 2*pixelH;
private _maxBelow = (safeZoneY + safeZoneH - _gap - _menuY) max (safeZoneH*0.12);
private _menuH = (safeZoneH * 0.58) min _maxBelow;
_colorList ctrlSetPosition [_menuX,_menuY,_menuW,_menuH];
_colorList ctrlSetBackgroundColor [0.04,0.04,0.04,0.96];
_colorList ctrlCommit _duration;

private _done = _d displayCtrl 84472;
_done ctrlShow _editMode;
_done ctrlCommit _duration;
(_d displayCtrl 84150) ctrlShow (!_editMode);
(_d displayCtrl 84153) ctrlShow (!_editMode);
{(_d displayCtrl _x) ctrlShow (!_editMode);} forEach [84151,84154,84155,84156];

// A/D navigation affordance. Promotion widens the carousel AND moves the keys outward rather than consuming track.
private _hintScale = if (_expanded) then {1.24} else {0.92};
private _keyW = safeZoneH*0.030*_hintScale;
private _keyH = safeZoneH*0.032*_hintScale;
private _arrowW = safeZoneH*0.024*_hintScale;
private _hintPad = safeZoneH * (if (_expanded) then {0.020} else {0.006});
private _hintY = _centerY - _keyH/2;
private _leftKey = _d displayCtrl 84700;
private _leftArrow = _d displayCtrl 84701;
private _rightArrow = _d displayCtrl 84702;
private _rightKey = _d displayCtrl 84703;

private _toolbarW = _uiW / 11;
private _toolbarX = _uiX + _uiW/2 - _toolbarW/2;
private _leftKeyX = if (_expanded) then {(_rx - _keyW - _hintPad) max _uiX} else {_toolbarX};
private _leftArrowX = if (_expanded) then {(_rx - _arrowW*0.55) max (_uiX + _keyW)} else {(_rx - _arrowW - _hintPad) max (_leftKeyX + _keyW)};
private _rightKeyX = if (_expanded) then {(_rx + _rw + _hintPad) min (_uiX + _uiW - _keyW)} else {_toolbarX + _toolbarW - _keyW};
private _rightArrowX = if (_expanded) then {(_rx + _rw - _arrowW*0.45) min (_uiX + _uiW - _keyW - _arrowW)} else {(_rx + _rw + _hintPad) min (_rightKeyX - _arrowW)};
_leftKey ctrlSetPosition [_leftKeyX,_hintY,_keyW,_keyH];
_leftArrow ctrlSetPosition [_leftArrowX,_hintY,_arrowW,_keyH];
_rightArrow ctrlSetPosition [_rightArrowX,_hintY,_arrowW,_keyH];
_rightKey ctrlSetPosition [_rightKeyX,_hintY,_keyW,_keyH];
{_x ctrlSetFontHeight (_keyH*0.62); _x ctrlShow (!_editMode); _x ctrlCommit _duration;} forEach [_leftKey,_leftArrow,_rightArrow,_rightKey];

// Body Map header is deliberately patient-name only; the selected syringe itself is the medication readout.
(_d displayCtrl 84001) ctrlSetText "";
private _p = _d getVariable ["ACME_SK_ReturnPatient",objNull]; if (isNull _p) then {_p=uiNamespace getVariable ["ACME_SK_Patient",objNull];};
(_d displayCtrl 84002) ctrlSetText (if (isNull _p) then {"Patient"} else {name _p});
