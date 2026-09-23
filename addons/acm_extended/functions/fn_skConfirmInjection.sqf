/* B115: Body Map syringe administration animation.
   IV/IO pushes use the optional numeric duration above the Push button (blank = original 3 seconds). IM retains
   the original 3-second injection. Medication is committed only after the visual push completes, and the same
   duration is passed into ACME's rate-sensitive medication exposure model. */
disableSerialization;
private _d = findDisplay 84000;
if (isNull _d || {(uiNamespace getVariable ["ACME_SK_View","syringe"]) != "body"}) exitWith {false};
if (uiNamespace getVariable ["ACME_SK_InjectionBusy",false]) exitWith {false};
if (uiNamespace getVariable ["ACME_SK_TagEditMode",false]) exitWith {false};

private _pending = uiNamespace getVariable ["ACME_SK_PendingInjection",[]];
if (!(_pending isEqualType []) || {count _pending < 3}) exitWith {false};
_pending params ["_bodyPart","_siteIdx","_route"];
// B121 Hardcore Medications replaces the display-bound animation with a persistent transaction.
// The worker survives every menu close/reopen; only Stop Push, leash/access loss or completion ends flow.
if ((missionNamespace getVariable ["ACME_hcEff_medications",false]) && {_route != "im"}) exitWith {call ACME_fnc_hardcorePushStart};
uiNamespace setVariable ["ACME_SK_SiteIdx",_siteIdx];
uiNamespace setVariable ["ACME_SK_Route",_route];
private _patient = uiNamespace getVariable ["ACME_SK_Patient",objNull];
if (isNull _patient) then {_patient = _d getVariable ["ACME_SK_ReturnPatient",objNull];};
if (isNull _patient) exitWith {uiNamespace setVariable ["ACME_SK_PendingInjection",[]]; call ACME_fnc_skBodyActionRender; false};
private _iv = _route != "im";
private _present = true;
if (_iv) then {_present = if (_siteIdx >= 0) then {[_patient,_bodyPart,0,_siteIdx] call ACM_circulation_fnc_hasIV} else {[_patient,_bodyPart,0] call ACM_circulation_fnc_hasIO};};
if (!_present) exitWith {uiNamespace setVariable ["ACME_SK_PendingInjection",[]]; call ACME_fnc_skBodyActionRender; false};

private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _idx = [_store] call ACME_fnc_skSelectedIndex;
if (_idx < 0 || {_idx >= count _store}) exitWith {
    uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
    call ACME_fnc_skBodyActionRender;
    false
};
private _entry = +(_store select _idx);
private _stableId = _entry param [11,"",[""]];
if (_stableId == "") exitWith {
    uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
    call ACME_fnc_skBodyActionRender;
    false
};
_entry params ["_med",["_size",10],["_amt",0],["_label",""],["_nsMl",0]];
private _total = (_amt + _nsMl) max 0;
// Vascular pushes use an explicitly entered duration when present. The grey recommendation remains display-only;
// blank or grey-placeholder always means the original 3-second push.
private _pushSec = 3;
private _pushDurationValid = true;
if (_route != "im") then {
    private _durCtrl = _d displayCtrl 84831;
    private _ghost = isNull _durCtrl || {_durCtrl getVariable ["ACME_SK_GhostActive",false]};
    private _raw = if (_ghost) then {""} else {ctrlText _durCtrl};
    if (_raw != "") then {
        private _typed = parseNumber _raw;
        _pushDurationValid = _typed >= 1 && {_typed <= 300};
        if (_pushDurationValid) then {_pushSec = _typed;};
    };
};
if (!_pushDurationValid) exitWith {
    ["Push duration must be 1-300 seconds. Leave it blank to use 3 seconds.",2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;
    false
};
if (_total <= 0) exitWith {
    uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
    call ACME_fnc_skBodyActionRender;
    false
};

// Push-dose epinephrine can intentionally leave solution behind. Every other prepared syringe empties to zero.
private _remainingFrac = 0;
private _confirmedEpiMl = -1;
if ((_entry param [6,""]) == "epiMixB12") then {
    private _choice = uiNamespace getVariable ["ACME_SK_EpiDoseChoice",0];
    private _pushMl = ([1,2,_total] select (((_choice max 0) min 2))) min _total;
    _confirmedEpiMl = _pushMl;
    _remainingFrac = ((((_total - _pushMl) max 0) / (_size max 0.01)) max 0) min 1;
};

// A normal push must retain the injected workspace as well as the display handle.
// A replacement workspace can exist before it has a replacement normal-push job.
private _closeEpoch = _d getVariable ["ACME_SK_CloseEpoch",-1];
if (_closeEpoch < 0 || {(uiNamespace getVariable ["ACME_SK_CloseEpoch",-2]) != _closeEpoch}) exitWith {false};

// A normal push belongs to this display/provider/patient, not to whichever dialog opens later.
private _epoch = (_d getVariable ["ACME_SK_InjectionEpoch",0]) + 1;
_d setVariable ["ACME_SK_InjectionEpoch",_epoch];
private _job = [_d,ACE_player,_patient,_stableId,_epoch,_closeEpoch];
uiNamespace setVariable ["ACME_SK_NormalPush",_job];
private _validContext = {
    params ["_job"];
    _job params ["_display","_medic","_patient"];
    if (isNull _display || {!(_display isEqualTo findDisplay 84000)} || {!(ACE_player isEqualTo _medic)}) exitWith {false};
    private _closeEpoch = _job select 5;
    if ((uiNamespace getVariable ["ACME_SK_CloseEpoch",-2]) != _closeEpoch
        || {(_display getVariable ["ACME_SK_CloseEpoch",-1]) != _closeEpoch}) exitWith {false};
    if (!(uiNamespace getVariable ["ACME_SK_InjectionBusy",false])
        || {(uiNamespace getVariable ["ACME_SK_View",""]) != "body"}
        || {uiNamespace getVariable ["ACME_SK_TagEditMode",false]}) exitWith {false};
    private _currentPatient = uiNamespace getVariable ["ACME_SK_Patient",objNull];
    if (isNull _currentPatient) then {_currentPatient = _display getVariable ["ACME_SK_ReturnPatient",objNull];};
    private _hc = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
    !isNull _patient && {_currentPatient isEqualTo _patient} && {!(_hc isEqualType createHashMap && {count _hc > 0})}
};
private _retire = {
    params ["_job"];
    if !((uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo _job) exitWith {};
    uiNamespace setVariable ["ACME_SK_NormalPush",[]];
    // Retire this job record, but never unlock or clear the target of a successor workspace/provider.
    if ((uiNamespace getVariable ["ACME_SK_CloseEpoch",-2]) != (_job select 5)
        || {!(ACE_player isEqualTo (_job select 1))}) exitWith {};
    // A persistent push has its own lifecycle and must retain its shared UI locks.
    private _hc = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
    if (_hc isEqualType createHashMap && {count _hc > 0}) exitWith {};
    uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
    uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
    uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
    private _display = _job select 0;
    if (!isNull _display && {_display isEqualTo findDisplay 84000} && {ACE_player isEqualTo (_job select 1)}) then {
        {private _c=_display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true;};} forEach [84150,84152,84151,84154,84470,84820,84831];
        [0.10] call ACME_fnc_skCarouselRender;
        call ACME_fnc_skBuildHotspots;
        call ACME_fnc_skBodyActionRender;
    };
};

uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
uiNamespace setVariable ["ACME_SK_CarouselExpanded",true];
uiNamespace setVariable ["ACME_SK_CarouselHover",false];
uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",0];
_d setVariable ["ACME_SK_InjectionStableId",_stableId];
_d setVariable ["ACME_SK_InjectionBodyPart",_bodyPart];
_d setVariable ["ACME_SK_InjectionSiteIdx",_siteIdx];
_d setVariable ["ACME_SK_InjectionRoute",_route];

[0.12] call ACME_fnc_skDynamicLayout;
[0.12] call ACME_fnc_skCarouselRender;
call ACME_fnc_skBuildHotspots;
{private _c=_d displayCtrl _x; if (!isNull _c) then {_c ctrlEnable false;};} forEach [84150,84152,84151,84154,84470,84820,84831];

[{
    params ["_stableId","_size","_remainingFrac","_bodyPart","_siteIdx","_route","_pushSec","_job","_validContext","_retire","_confirmedEpiMl"];
    disableSerialization;
    if !((uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo _job) exitWith {};
    if !([_job] call _validContext) exitWith {[_job] call _retire;};
    private _d = _job select 0;
    private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
    if (([_stableId,_store] call ACME_fnc_skSelectStored) < 0) exitWith {
        [_job] call _retire;
    };

    playSound "ACME_SyringePush";
    private _bar = _d displayCtrl 84420;
    private _pl = _d displayCtrl 84422;
    if (!isNull _bar && {!isNull _pl}) then {
        private _br = +(ctrlPosition _bar);
        private _native = _d getVariable ["ACME_SK_CarouselNativeRect",[0,0,1,1]];
        private _travel10 = _d getVariable ["ACME_SK_CarouselTravel10",safeZoneH*0.17];
        private _sizeRatio = switch (_size) do {case 1:{10.2/10.5};case 3:{9.83/10.5};case 5:{10.3/10.5};default{1};};
        private _targetY = (_br select 1) + (_travel10 * _sizeRatio * _remainingFrac * ((_br select 3) / (((_native select 3) max 0.001))));
        private _startY = (ctrlPosition _pl) select 1;
        private _oldAnim = uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1];
        if (_oldAnim isEqualType 0 && {_oldAnim >= 0}) then {[_oldAnim] call CBA_fnc_removePerFrameHandler;};
        private _anim = [{
            params ["_args","_hid"];
            _args params ["_display","_ctrl","_x","_startY","_targetY","_w","_h","_started","_duration","_job","_validContext"];
            if (!((uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo _job)
                || {isNull _ctrl} || {!([_job] call _validContext)}) exitWith {
                [_hid] call CBA_fnc_removePerFrameHandler;
                if ((uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1]) == _hid) then {uiNamespace setVariable ["ACME_SK_PushAnimPFH",-1];};
            };
            private _t = (((diag_tickTime - _started) / (_duration max 0.05)) max 0) min 1;
            // Smoothstep gives a continuous physical plunger stroke without the slideshow-like large-control commit.
            private _e = _t * _t * (3 - (2 * _t));
            private _y = _startY + ((_targetY - _startY) * _e);
            _ctrl ctrlSetPosition [_x,_y,_w,_h];
            _ctrl ctrlCommit 0;
            if (_t >= 1) then {
                [_hid] call CBA_fnc_removePerFrameHandler;
                if ((uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1]) == _hid) then {uiNamespace setVariable ["ACME_SK_PushAnimPFH",-1];};
            };
        },0,[_d,_pl,_br select 0,_startY,_targetY,_br select 2,_br select 3,diag_tickTime,_pushSec,_job,_validContext]] call CBA_fnc_addPerFrameHandler;
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",_anim];
    };

    [{
        params ["_stableId","_bodyPart","_siteIdx","_route","_pushSec","_job","_validContext","_retire","_confirmedEpiMl"];
        disableSerialization;
        if !((uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo _job) exitWith {};
        if !([_job] call _validContext) exitWith {[_job] call _retire;};
        private _d = _job select 0;
        // Retire before the medication handoff so duplicate delivery cannot administer twice.
        uiNamespace setVariable ["ACME_SK_NormalPush",[]];
        private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
        if (([_stableId,_store] call ACME_fnc_skSelectStored) >= 0) then {
            uiNamespace setVariable ["ACME_SK_SiteIdx",_siteIdx];
            uiNamespace setVariable ["ACME_SK_Route",_route];
            // Unlock immediately before the authoritative commit so its normal refresh/removal path can repaint.
            uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
            uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
            uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
            uiNamespace setVariable ["ACME_SK_Patient",_job select 2];
            // Use the same measured aliquot as the stroke, not a later dose-selector value.
            if (_confirmedEpiMl >= 0) then {
                [_bodyPart,_pushSec,_confirmedEpiMl] call ACME_fnc_skInjectSite;
            } else {
                [_bodyPart,_pushSec] call ACME_fnc_skInjectSite;
            };
        } else {
            uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
            uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
            uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
        };
        uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",diag_tickTime + 1.00];
        {private _c=_d displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true;};} forEach [84150,84152,84151,84154,84470,84820,84831];
        [0.10] call ACME_fnc_skCarouselRender;
        call ACME_fnc_skBuildHotspots;
        call ACME_fnc_skBodyActionRender;
    },[_stableId,_bodyPart,_siteIdx,_route,_pushSec,_job,_validContext,_retire,_confirmedEpiMl],_pushSec] call CBA_fnc_waitAndExecute;
},[_stableId,_size,_remainingFrac,_bodyPart,_siteIdx,_route,_pushSec,_job,_validContext,_retire,_confirmedEpiMl],0.14] call CBA_fnc_waitAndExecute;
true
