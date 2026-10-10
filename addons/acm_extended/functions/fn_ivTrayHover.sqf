/* B233: single centered catheter per tile; band/pad retain their bounded hover. */
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

// B233: one centered catheter per tile. Never create/reveal fan copies or a + badge.
private _fanIdcBase = switch (_gauge) do {case 14:{86580}; case 16:{86584}; case 18:{86588}; default {86592};};
for "_i" from 0 to 3 do {private _idc=_fanIdcBase+_i;private _layer=_d displayCtrl _idc;_layer ctrlShow false;};
{if (!isNull _x) then {_x ctrlShow false;};} forEach (_d getVariable [format ["ACME_IV_TrayFan_%1",_gauge],[]]);
_logo ctrlSetPosition _base;
_logo ctrlCommit 0;
