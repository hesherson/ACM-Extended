#include "\x\ACM\addons\circulation\script_component.hpp"
#include "\x\ACM\addons\circulation\SyringeDraw_defines.hpp"
/* Change Narc Box syringe size without destroying/recreating the dialog. */
disableSerialization;
params [["_size",10,[0]]];
if !(_size in [1,3,5,10]) exitWith {false};
private _d = findDisplay 84000;
if (isNull _d) exitWith {false};
if (([ACE_player, uiNamespace getVariable ["ACME_SK_Patient",objNull], format ["ACM_Syringe_%1",_size]] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {false};
if (uiNamespace getVariable ["ACME_SK_InjectionBusy",false]) exitWith {false};

private _current = uiNamespace getVariable ["ACME_SK_CurSize",10];
private _stageBefore = uiNamespace getVariable ["ACME_SK_WasteStage",""];
if (_size == _current && {_stageBefore == "compound"}) exitWith {true};

// Preserve an already prepared compound exactly as the old reopen path did.
private _autoSaved = false;
private _hadPendingCompound = _stageBefore == "compound" && {!((uiNamespace getVariable ["ACME_SK_CompoundComponents",[]]) isEqualTo [])};
if (_hadPendingCompound) then {_autoSaved = call ACME_fnc_skCompoundCommit;};
if (_hadPendingCompound && {!_autoSaved}) exitWith {false};
if (_autoSaved) then {
    call ACME_fnc_skPendingTagReset;
    call ACME_fnc_skRefreshDrawn;
};
if (_stageBefore != "") then {[] call ACME_fnc_skWasteEnd;};

// Hide all four native syringe triples, then reveal only the requested one.
for "_id" from 84010 to 84021 do {(_d displayCtrl _id) ctrlShow false;};
private _visualId = 84010;
private _top = SYRINGEDRAW_LIMIT_10_TOP;
private _bottom = SYRINGEDRAW_LIMIT_10_BOTTOM;
private _topMouse = SYRINGEDRAW_LIMIT_10_TOP_MOUSE;
private _adjust = SYRINGEDRAW_10_Y_OFFSET;
private _base = 84010;
switch (_size) do {
    case 1: {_base=84019; _visualId=84019; _top=SYRINGEDRAW_LIMIT_1_TOP; _bottom=SYRINGEDRAW_LIMIT_1_BOTTOM; _topMouse=SYRINGEDRAW_LIMIT_1_TOP_MOUSE; _adjust=SYRINGEDRAW_1_Y_OFFSET;};
    case 3: {_base=84016; _visualId=84016; _top=SYRINGEDRAW_LIMIT_3_TOP; _bottom=SYRINGEDRAW_LIMIT_3_BOTTOM; _topMouse=SYRINGEDRAW_LIMIT_3_TOP_MOUSE; _adjust=SYRINGEDRAW_3_Y_OFFSET;};
    case 5: {_base=84013; _visualId=84013; _top=SYRINGEDRAW_LIMIT_5_TOP; _bottom=SYRINGEDRAW_LIMIT_5_BOTTOM; _topMouse=SYRINGEDRAW_LIMIT_5_TOP_MOUSE; _adjust=SYRINGEDRAW_5_Y_OFFSET;};
    default {_base=84010;};
};
{(_d displayCtrl (_base+_x)) ctrlShow true;} forEach [0,1,2];

uiNamespace setVariable ["ACME_SK_CurSize",_size];
ACM_circulation_SyringeDraw_Size = _size;
ACM_circulation_SyringeDraw_DrawnAmount = 0;
ACM_circulation_SyringeDraw_Moving = false;
ACM_circulation_SyringeDraw_MaxDose = _size;
ACM_circulation_SyringeDraw_Ctrl_PlungerVisual = _visualId;
ACM_circulation_SyringeDraw_Ctrl_LimitTop = _top;
ACM_circulation_SyringeDraw_Ctrl_LimitBottom = _bottom;
ACM_circulation_SyringeDraw_Ctrl_LimitTopMouse = _topMouse;
ACM_circulation_SyringeDraw_Ctrl_PlungerAdjustment = _adjust;

private _hit = _d displayCtrl 84009;
if (!isNull _hit) then {
    (ctrlPosition _hit) params ["_x","","_w","_h"];
    _hit ctrlSetPosition [_x,_top,_w,_h];
    _hit ctrlCommit 0;
};
private _vis = _d displayCtrl _visualId;
if (!isNull _vis) then {
    (ctrlPosition _vis) params ["_vx","","_vw","_vh"];
    _vis ctrlSetPosition [_vx,_top-_adjust,_vw,_vh];
    _vis ctrlCommit 0;
};

// Update the geometry cache used by the Body Map carousel without recreating the dialog.
private _barrel = _d displayCtrl (_base+2);
if (!isNull _barrel) then {_d setVariable ["ACME_SK_CarouselNativeRect",ctrlPosition _barrel];};
private _travelNow = _bottom - _top;
private _ratio = switch (_size) do {case 1:{10.2/10.5};case 3:{9.83/10.5};case 5:{10.3/10.5};default{1};};
if (_travelNow > 0) then {_d setVariable ["ACME_SK_CarouselTravel10",_travelNow / (_ratio max 0.01)];};

// Plain Narc Box returns immediately to a fresh compound preparation in the same display.
if ((missionNamespace getVariable ["ACME_infusion_pendingContext",[]]) isEqualTo []) then {[] call ACME_fnc_skCompoundBegin;};
call ACME_fnc_skPendingTagRender;
call ACME_fnc_skListRefresh;
true
