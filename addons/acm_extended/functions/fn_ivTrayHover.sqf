/* IV tray hover animation.
   Needle slots rotate 90 degrees left at rest. Hover enlarges the front catheter and fans the provider's
   available stock (up to five total needles) like a small deck. >5 adds a + marker. Band/pad only enlarge.
   All dynamic fan controls are input-disabled and collapse/fade back to the slot as soon as hover ends. */
disableSerialization;
params [['_kind','', ['']], ['_gauge',0,[0]], ['_enter',false,[true]]];
private _d = uiNamespace getVariable ['ACME_IV_DLG',displayNull];
if (isNull _d) exitWith {};
private _ease = missionNamespace getVariable ['ACME_iv_trayHoverSec',0.11];
if !(_ease isEqualType 0 && {finite _ease} && {_ease >= 0}) then {_ease = 0.11;};

private _scaleRect = {
    params ['_r','_mul'];
    _r params ['_x','_y','_w','_h'];
    private _nw = _w * _mul;
    private _nh = _h * _mul;
    [_x + ((_w-_nw)*0.5), _y + ((_h-_nh)*0.5), _nw, _nh]
};

if (_kind in ['band','pad']) exitWith {
    private _idc = if (_kind == 'band') then {86531} else {86536};
    private _ctrl = _d displayCtrl _idc;
    if (isNull _ctrl) exitWith {};
    private _key = format ['ACME_IV_TrayBase_%1',_idc];
    private _base = _d getVariable [_key,[]];
    if (_base isEqualTo []) then {_base = ctrlPosition _ctrl; _d setVariable [_key,+_base];};
    _ctrl ctrlSetPosition ([_base, if (_enter) then {1.10} else {1}] call _scaleRect);
    _ctrl ctrlCommit _ease;
};
if (_kind != 'needle' || {!(_gauge in [14,16,18,20])}) exitWith {};

private _rec = [];
{
    if ((_x param [0,-1]) == _gauge) exitWith {_rec = _x;};
} forEach (uiNamespace getVariable ['ACME_IV_NeedleRects',[]]);
if (count _rec < 4) exitWith {};
_rec params ['','_slot','_base','_logoIdc'];
private _logo = _d displayCtrl _logoIdc;
if (isNull _logo) exitWith {};

// Use the LIVE tray box for the badge boundary. Use the original live logo canvas for every catheter copy.
// The catheter PAA has a large transparent canvas and its opaque artwork is biased below the texture midpoint;
// after the tray's -90 degree rotation that becomes a visible right-side bias. Shrinking the clones into the
// tray box changes the KeepAspect fit and makes that bias much worse. Keeping every copy on the same canvas as
// the real catheter preserves the exact texture aspect and makes the visible catheter centroid predictable.
private _bgIdc = switch (_gauge) do {case 14:{86540}; case 16:{86544}; case 18:{86548}; default {86556};};
private _bg = _d displayCtrl _bgIdc;
if (!isNull _bg) then {
    private _liveSlot = ctrlPosition _bg;
    if ((count _liveSlot) >= 4) then {_slot = +_liveSlot;};
};

private _medic = uiNamespace getVariable ['ACME_IV_Medic',objNull];
private _count = if (isNull _medic) then {0} else {[_medic,format ['ACM_IV_%1g',_gauge]] call ace_common_fnc_getCountOfItem};
private _shown = (_count min 5) max 0;
private _colors = createHashMapFromArray [
    [14,[1,0.55,0.55,0.56]],
    [16,[1,1,1,0.56]],
    [18,[0.70,0.90,1,0.56]],
    [20,[0.60,0.85,1,0.56]]
];
private _fanKey = format ['ACME_IV_TrayFan_%1',_gauge];
private _fan = _d getVariable [_fanKey,[]];
if (_fan isEqualTo []) then {
    // Four copies + the real front logo = five total needles maximum.
    for '_i' from 0 to 3 do {
        private _c = _d ctrlCreate ['RscPictureKeepAspect',-1];
        _c ctrlSetText (ctrlText _logo);
        _c ctrlSetTextColor (_colors getOrDefault [_gauge,[1,1,1,0.56]]);
        _c ctrlSetPosition _base;
        _c ctrlSetAngle [-90,0.5,0.5,false];
        _c ctrlSetFade 1;
        _c ctrlEnable false;
        _c ctrlCommit 0;
        _fan pushBack _c;
    };
    private _plus = _d ctrlCreate ['RscStructuredText',-1];
    _plus ctrlSetStructuredText parseText "<t align='center' valign='middle'>+</t>";
    _plus ctrlSetTextColor [0.94,0.91,0.82,0.90];
    _plus ctrlSetBackgroundColor [0,0,0,0];
    _plus ctrlSetFade 1;
    _plus ctrlEnable false;
    _plus ctrlCommit 0;
    _fan pushBack _plus;
    _d setVariable [_fanKey,_fan];
};
private _plus = _fan param [4,controlNull];

// Approximate the opaque catheter's center inside the SOURCE canvas. This is intentionally independent from
// ACME_iv_trayIconBias, which only moves the resting tray control. Coupling those two values made a placement tune
// change the hover geometry and could make the fan appear stretched or drift away from the real catheter.
private _artU = 0.5;
private _artV = missionNamespace getVariable ['ACME_iv_trayArtV',0.66];
if !(_artV isEqualType 0 && {finite _artV}) then {_artV = 0.66;};
_artV = (_artV max 0) min 1;

private _artOffset = {
    params ['_w','_h','_ang','_u','_v'];
    private _dx = (_u - 0.5) * _w;
    private _dy = (_v - 0.5) * _h;
    private _ca = cos _ang;
    private _sa = sin _ang;
    [(_dx * _ca) - (_dy * _sa), (_dx * _sa) + (_dy * _ca)]
};
private _rectAtVisualCenter = {
    params ['_anchorX','_anchorY','_w','_h','_ang','_u','_v'];
    private _off = [_w,_h,_ang,_u,_v] call _artOffset;
    [_anchorX - (_off select 0) - (_w * 0.5), _anchorY - (_off select 1) - (_h * 0.5), _w, _h]
};

_base params ['_bx','_by','_bw','_bh'];
private _baseOff = [_bw,_bh,-90,_artU,_artV] call _artOffset;
private _spriteX = _bx + (_bw * 0.5) + (_baseOff select 0);
private _spriteY = _by + (_bh * 0.5) + (_baseOff select 1);

// Grow the real front catheter without moving the visible catheter itself. Scaling the transparent control around
// its geometric center is what previously made the front image shift as the source-art bias became more obvious.
private _frontMul = if (_enter && {_shown > 0}) then {1.11} else {1};
private _frontW = _bw * _frontMul;
private _frontH = _bh * _frontMul;
_logo ctrlSetPosition ([_spriteX,_spriteY,_frontW,_frontH,-90,_artU,_artV] call _rectAtVisualCenter);
_logo ctrlSetAngle [-90,0.5,0.5,false];
_logo ctrlCommit _ease;

_slot params ['_sx','_sy','_sw','_sh'];
// One-sided upward fan. UI Y increases downward, so EVERY clone receives a substantial negative-Y rise.
// The former tiny -0.034/-0.060 offsets moved only the control center a few pixels; once the long catheter was
// rotated, one end still visibly dropped below the resting needle. These offsets clear the full tilted silhouette,
// including 32:9 where one tray slot is physically short relative to the catheter length.
//
// X still opens the deck slightly left/right, but Y is monotonic upward. Nothing is ever spawned below the
// resting/front catheter.
private _poses = [
    [-0.018, -0.50, -94],
    [-0.006, -0.70, -98],
    [ 0.006, -0.90, -102],
    [ 0.018, -1.10, -106]
];
private _cloneCount = ((_shown - 1) max 0) min 4;
private _fanMul = 1.03;
private _fanW = _bw * _fanMul;
private _fanH = _bh * _fanMul;
for '_i' from 0 to 3 do {
    private _c = _fan select _i;
    if (_enter && {_i < _cloneCount}) then {
        (_poses select _i) params ['_ox','_oy','_ang'];
        private _anchorX = _spriteX + (_sw * _ox);
        private _anchorY = _spriteY + (_sh * _oy);
        _c ctrlSetPosition ([_anchorX,_anchorY,_fanW,_fanH,_ang,_artU,_artV] call _rectAtVisualCenter);
        _c ctrlSetAngle [_ang,0.5,0.5,false];
        _c ctrlSetFade 0;
        _c ctrlCommit _ease;
    } else {
        _c ctrlSetPosition _base;
        _c ctrlSetAngle [-90,0.5,0.5,false];
        _c ctrlSetFade 1;
        _c ctrlCommit _ease;
    };
};

if (!isNull _plus) then {
    // >5 badge belongs INSIDE the live gauge tile, at its TOP-LEFT corner. It is deliberately anchored to the
    // background slot rather than the oversized catheter canvas, so aspect changes and hover scaling cannot push it
    // outside the tray icon.
    private _pw = _sw * 0.18;
    private _ph = _sh * 0.22;
    private _insetX = _sw * 0.08;
    private _insetY = _sh * 0.055;
    private _px = _sx + _insetX;
    private _py = _sy + _insetY;
    _plus ctrlSetPosition [_px,_py,_pw,_ph];
    _plus ctrlSetStructuredText parseText format ["<t align='center' size='%1' color='#F0E7D2'>+</t>", 0.95];
    _plus ctrlSetFade (if (_enter && {_count > 5}) then {0} else {1});
    _plus ctrlCommit _ease;
};
