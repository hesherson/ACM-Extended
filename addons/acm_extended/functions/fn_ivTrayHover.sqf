/* IV tray hover animation.
   Needle textures are already horizontal. Hover enlarges the front catheter and fans the provider's
   available stock (up to five total needles) like a small deck. >5 adds a + marker. Band/pad only enlarge.
   Fan pictures are declared behind each main logo, farthest first. They are input-disabled and collapse/fade
   back to the slot as soon as hover ends. */
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

// Use the live tile for the badge boundary and the saved square canvas for every stock copy.
// The fixed fan poses are pre-rotated in source-pixel space; no native control rotation is involved.
private _bgIdc = switch (_gauge) do {case 14:{86540}; case 16:{86544}; case 18:{86548}; default {86556};};
private _bg = _d displayCtrl _bgIdc;
if (!isNull _bg) then {
    private _liveSlot = ctrlPosition _bg;
    if ((count _liveSlot) >= 4) then {_slot = +_liveSlot;};
};
_slot params ['_sx','_sy','_sw','_sh'];
private _pw = _sw * 0.18;
private _ph = _sh * 0.22;
private _insetX = _sw * 0.08;
private _insetY = _sh * 0.055;
private _px = _sx + _insetX;
private _py = _sy + _insetY;
private _badgeRect = [_px,_py,_pw,_ph];

private _medic = uiNamespace getVariable ['ACME_IV_Medic',objNull];
private _count = if (isNull _medic) then {0} else {[_medic,uiNamespace getVariable ['ACME_IV_Patient',objNull],format ['ACM_IV_%1g',_gauge]] call ACME_fnc_treatmentSupplyCount};
private _shown = (_count min 5) max 0;
// Preserve the original catheter colors. Only opacity changes with distance from the main logo.
private _alphas = [0.72,0.52,0.34,0.18];
private _fanIdcBase = switch (_gauge) do {case 14:{86580}; case 16:{86584}; case 18:{86588}; default {86592};};
private _fanKey = format ['ACME_IV_TrayFan_%1',_gauge];
private _fan = _d getVariable [_fanKey,[]];
if (_fan isEqualTo []) then {
    // Four existing copies + the real front logo = five total needles maximum. Config declares the copies
    // farthest-to-nearest BEFORE the main logo; ctrlCreate here would incorrectly cover that foreground icon.
    for '_i' from 0 to 3 do {
        private _c = _d displayCtrl (_fanIdcBase + _i);
        _c ctrlSetText format ['\acm_extended\ui\iv\tray\iv_tray_%1g_%2_ca.paa',_gauge,_i + 1];
        _c ctrlSetTextColor [1,1,1,_alphas select _i];
        _c ctrlSetPosition _base;
        _c ctrlSetFade 1;
        _c ctrlEnable false;
        _c ctrlCommit 0;
        _fan pushBack _c;
    };
    private _plus = _d ctrlCreate ['RscStructuredText',-1];
    // New controls start at UI (0,0). Commit their tray location while hidden,
    // before assigning text or easing their fade, so the first hover cannot fly
    // a visible + across the patient's body.
    _plus ctrlShow false;
    _plus ctrlSetPosition _badgeRect;
    _plus ctrlSetTextColor [0.94,0.91,0.82,0.90];
    _plus ctrlSetBackgroundColor [0,0,0,0];
    _plus ctrlSetFade 1;
    _plus ctrlEnable false;
    _plus ctrlCommit 0;
    _plus ctrlShow true;
    _fan pushBack _plus;
    _d setVariable [_fanKey,_fan];
};
private _plus = _fan param [4,controlNull];

// Centered rest art makes uniform hover scaling sufficient. Every fan texture shares the same
// left-tip anchor and source scale. Its handle rises 4/8/12/16 degrees above the baseline.
_logo ctrlSetPosition ([_base, if (_enter && {_shown > 0}) then {1.06} else {1}] call _scaleRect);
_logo ctrlCommit _ease;

_base params ['_bx','_by','_bw','_bh'];
private _cloneCount = ((_shown - 1) max 0) min 4;
for '_i' from 0 to 3 do {
    private _c = _fan select _i;
    if (_enter && {_i < _cloneCount}) then {
        // UI Y increases downward. A small upward step separates the tips too; the baked
        // rotation lifts only the handle, so no end drops below the resting catheter.
        private _rise = _sh * 0.02 * (_i + 1);
        _c ctrlSetPosition [_bx,_by - _rise,_bw,_bh];
        _c ctrlSetFade 0;
        _c ctrlCommit _ease;
    } else {
        _c ctrlSetPosition _base;
        _c ctrlSetFade 1;
        _c ctrlCommit _ease;
    };
};

if (!isNull _plus) then {
    // >5 badge belongs INSIDE the live gauge tile, at its TOP-LEFT corner. It is deliberately anchored to the
    // background slot rather than the oversized catheter canvas, so aspect changes and hover scaling cannot push it
    // outside the tray icon.
    // Position is never animated, even if the tray was relaid out between hovers.
    _plus ctrlSetPosition _badgeRect;
    _plus ctrlCommit 0;
    _plus ctrlSetStructuredText parseText format ["<t align='center' size='%1' color='#F0E7D2'>+</t>", 0.95];
    _plus ctrlSetFade (if (_enter && {_count > 5}) then {0} else {1});
    _plus ctrlCommit _ease;
};
