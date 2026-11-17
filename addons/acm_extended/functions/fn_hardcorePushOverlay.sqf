#include "\x\acm\addons\main\ui_theme.hpp"
/* B125: persistent one-handed syringe HUD.
   Flow state never depends on menu visibility. The visual syringe now lives on a dedicated RscTitles display with
   static picture controls so the barrel/plunger/backbit cannot disappear when dynamically-created picture controls
   are culled or rebuilt by ACE displays. The click hitbox is still recreated on the active gameplay/ACE displays. */
disableSerialization;
// B129: bare `call` from a PFH inherits the caller's _this. Accept only an explicit string mode;
// every other payload means a normal HUD update.
private _mode = "update";
if (_this isEqualType "") then {
    _mode = _this;
} else {
    if (_this isEqualType [] && {count _this > 0} && {(_this select 0) isEqualType ""}) then {
        _mode = _this select 0;
    };
};

private _hitId = 98974;
private _displayIds = [46,91919,38580];
private _layer = "ACME_HCPushHUD" call BIS_fnc_rscLayer;
private _clear = {
    {
        private _disp = findDisplay _x;
        if (!isNull _disp) then {
            private _hit = _disp displayCtrl _hitId;
            if (!isNull _hit) then {ctrlDelete _hit;};
        };
    } forEach _displayIds;
    _layer cutText ["","PLAIN"];
    uiNamespace setVariable ["ACME_HCPush_DLG", displayNull];
};
if (_mode == "clear") exitWith {call _clear; true};

private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0} && {_job getOrDefault ["flowing",false]}) exitWith {
    call _clear;
    false
};

// The full Narc Box owns the large syringe while open. Flow continues, but the corner duplicate disappears.
if (!isNull (findDisplay 84000)) exitWith {call _clear; true};

private _medic = _job getOrDefault ["medic",objNull];
private _stable = _job getOrDefault ["stableId",""];
private _remaining = 0;
if (!isNull _medic && {_stable != ""}) then {
    private _store = _medic getVariable ["ACME_narcStore",[]];
    private _ix = _store findIf {(_x param [11,"",[""]]) == _stable};
    if (_ix >= 0) then {
        private _r = _store select _ix;
        _remaining = ((_r param [2,0,[0]]) + (_r param [4,0,[0]])) max 0;
    };
};

private _size = _job getOrDefault ["size",10];
if !(_size in [1,3,5,10]) then {_size = 10;};
private _marker = _job getOrDefault ["barrelMarker",""];
private _barTex = if (_marker == "flush") then {
    "\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa"
} else {
    format ["\acm_extended\ui\syringe\hud\syringe_%1_barrel_ca.paa",_size]
};
private _backTex = format ["\acm_extended\ui\syringe\hud\syringe_%1_backbit_ca.paa",_size];
private _plTex = format ["\acm_extended\ui\syringe\hud\syringe_%1_plunger_ca.paa",_size];

private _travelNorm = ((_job getOrDefault ["overlayTravelNorm",0.195]) max 0.02) min 0.40;
private _sizeRatio = switch (_size) do {case 1:{10.2/10.5}; case 3:{9.83/10.5}; case 5:{10.3/10.5}; default{1};};
private _frac = ((_remaining / (_size max 0.01)) max 0) min 1;

// B127: stack the horizontal syringe directly above the medication/status bar. The PAA layers stay on a
// physically-square canvas so rotation cannot stretch them on ultrawide displays. Only the plunger translates;
// the barrel/backbit remain fixed. The click target is calculated separately around the visible horizontal body.
private _pxAspect = pixelW / (pixelH max 0.000001);
private _canvasH = safeZoneH * 0.245;
private _canvasW = _canvasH * _pxAspect;
private _travelX = _canvasW * _travelNorm * _sizeRatio;
private _screenPadY = safeZoneH * 0.018;
private _screenPadX = _screenPadY * _pxAspect;
private _gapY = safeZoneH * 0.000;
private _syringeNudgeDown = safeZoneH * 0.090;
private _tw = safeZoneH * 0.365 * _pxAspect;
private _th = safeZoneH * 0.066;
private _right = safeZoneX + safeZoneW - _screenPadX;
private _bottom = safeZoneY + safeZoneH - _screenPadY;
private _tx = _right - _tw;
private _ty = _bottom - _th;
private _cx = _tx + (_tw * 0.5);
private _x = _cx - (_canvasW * 0.5);
private _y = _ty - _gapY - _canvasH + _syringeNudgeDown;
private _rate = (_job getOrDefault ["rateMlSec",0]) max 0;
private _totalSec = ceil ((_job getOrDefault ["duration",0]) max 0);
private _targetLeft = ((_job getOrDefault ["targetMl",0]) - (_job getOrDefault ["pushedMl",0])) max 0;
private _leftSec = if (_rate > 0.000001) then {ceil (_targetLeft / _rate)} else {0};
_leftSec = (_leftSec max 0) min (_totalSec max 0);
private _label = _job getOrDefault ["pushLabel",_job getOrDefault ["med","Medication"]];
if (_label == "") then {_label = "Medication";};

// Dedicated title layer: use statically-configured picture controls. This is the authoritative visual HUD.
private _hud = uiNamespace getVariable ["ACME_HCPush_DLG",displayNull];
if (isNull _hud) then {
    _layer cutRsc ["ACME_HCPush_Display","PLAIN",-1,false];
    _hud = uiNamespace getVariable ["ACME_HCPush_DLG",displayNull];
};
if (!isNull _hud) then {
    private _back = _hud displayCtrl 71521;
    private _pl = _hud displayCtrl 71522;
    private _bar = _hud displayCtrl 71523;
    private _panel = _hud displayCtrl 71524;
    private _txt = _hud displayCtrl 71525;

    _back ctrlSetText _backTex;
    _pl ctrlSetText _plTex;
    _bar ctrlSetText _barTex;
    {_x ctrlSetTextColor [1,1,1,1]; _x ctrlSetFade 0;} forEach [_back,_pl,_bar];
    _back ctrlSetPosition [_x,_y,_canvasW,_canvasH];
    _pl ctrlSetPosition [_x - (_travelX*_frac),_y,_canvasW,_canvasH];
    _bar ctrlSetPosition [_x,_y,_canvasW,_canvasH];
    // Rotate all three layers together around their own centers. 90 degrees makes the syringe horizontal;
    // the plunger's X translation mirrors the former vertical travel after rotation.
    _back ctrlSetAngle [90,0.5,0.5];
    _pl ctrlSetAngle [90,0.5,0.5];
    _bar ctrlSetAngle [90,0.5,0.5];

    _panel ctrlSetPosition [_tx,_ty,_tw,_th];
    _panel ctrlSetBackgroundColor (ACM_UI_PANEL_RGB + [0.90]);
    _txt ctrlSetPosition [_tx,_ty + _th*0.08,_tw,_th*0.84];
    _txt ctrlSetFontHeight (_th*0.46);
    _txt ctrlSetStructuredText parseText format [
        "<t align='center' color='#F0E9D1' size='1.04'>%1</t><br/><t align='center' color='#FFFFFF' size='0.92'>%2s / %3s  |  %4 mL remaining</t>",
        _label,_leftSec,_totalSec,_remaining toFixed 2
    ];
    {_x ctrlShow true; _x ctrlSetFade 0; _x ctrlCommit 0;} forEach [_back,_pl,_bar,_panel,_txt];
};

// Clickability belongs to whichever UI display currently owns the mouse. The title resource is presentation-only.
// The syringe art itself has generous transparent margins inside its square texture, so keep the hit target to a
// slim horizontal strip around the visible syringe rather than using the entire square canvas. This puts the
// transparent button behind the syringe with only modest padding around its visible silhouette.
private _hitW = _canvasW * 0.96;
private _hitH = _canvasH * 0.34;
private _hitXPad = (10*pixelW) max (_canvasW*0.024);
private _hitYPad = (6*pixelH) max (_canvasH*0.022);
private _hitPos = [
    _cx - (_hitW*0.5) - _hitXPad,
    _y + (_canvasH*0.5) - (_hitH*0.5) - _hitYPad,
    _hitW + (2*_hitXPad),
    _hitH + (2*_hitYPad)
];
{
    private _disp = findDisplay _x;
    if (!isNull _disp) then {
        private _hit = _disp displayCtrl _hitId;
        if (isNull _hit) then {
            _hit = _disp ctrlCreate ["ACME_SK_HotspotButton",_hitId];
            _hit ctrlSetText "";
            _hit ctrlSetTextColor [0,0,0,0];
            _hit ctrlSetBackgroundColor [0,0,0,0];
            _hit ctrlSetTooltip "Open Narc Box at the active syringe push";
            _hit ctrlAddEventHandler ["ButtonClick",{call ACME_fnc_hardcorePushReopen;}];
            _hit ctrlAddEventHandler ["MouseEnter",{(_this select 0) ctrlSetBackgroundColor [0,0,0,0];}];
            _hit ctrlAddEventHandler ["MouseButtonDown",{(_this select 0) ctrlSetBackgroundColor [0,0,0,0];}];
            _hit ctrlAddEventHandler ["MouseButtonUp",{(_this select 0) ctrlSetBackgroundColor [0,0,0,0];}];
        };
        _hit ctrlSetPosition _hitPos;
        _hit ctrlShow true;
        _hit ctrlCommit 0;
    };
} forEach _displayIds;

!isNull _hud
