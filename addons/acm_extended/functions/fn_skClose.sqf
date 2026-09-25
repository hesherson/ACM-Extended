/* One teardown owns return routing for infusion prep, Done, Cancel and Escape.
   The return snapshot is stored by fn_skInject on this exact display. */
disableSerialization;
params ["_display"];
// Consume this display's teardown before any global cleanup or delegate call.
// A newer injected display, a repeated Unload or an unregistered display owns none of it.
private _closeEpoch = _display getVariable ["ACME_SK_CloseEpoch", -1];
if (_closeEpoch < 0 || {(uiNamespace getVariable ["ACME_SK_CloseEpoch", -2]) != _closeEpoch}) exitWith {};
uiNamespace setVariable ["ACME_SK_CloseEpoch", _closeEpoch + 1];
// Cancel only this display's normal, display-bound push. Hardcore flow survives Unload.
private _normalPush = uiNamespace getVariable ["ACME_SK_NormalPush",[]];
if (count _normalPush >= 5 && {(_normalPush select 0) isEqualTo _display}) then {
    uiNamespace setVariable ["ACME_SK_NormalPush",[]];
    private _hc = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
    if !(_hc isEqualType createHashMap && {count _hc > 0}) then {
        uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
        uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
        private _pushPfh = uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1];
        if (_pushPfh >= 0) then {[_pushPfh] call CBA_fnc_removePerFrameHandler;};
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",-1];
    };
};
private _restore = uiNamespace getVariable ["ACME_SK_RestoreMouse", []];
private _switch = (_restore isEqualType []) && {count _restore == 2};
private _infusion = !((_display getVariable ["ACME_SK_Return", []]) isEqualTo []);
// Infusion prep borrows the Narc Box compound plunger engine, but its contents are committed only by Inject Into Bag.
// Never let the Narc Box close handler auto-save that transient infusion syringe as a stored compound syringe.
if (!_switch && {!_infusion} && {(uiNamespace getVariable ["ACME_SK_WasteStage", ""]) == "compound"}) then {
    call ACME_fnc_skPendingTagCommit;
    call ACME_fnc_skCompoundCommit;
};
uiNamespace setVariable ["ACME_SK_WasteStage", ""];
uiNamespace setVariable ["ACME_SK_VialHolder",objNull];
uiNamespace setVariable ["ACME_SK_WasteMoving", false];
uiNamespace setVariable ["ACME_SK_TagEditMode", false];
uiNamespace setVariable ["ACME_SK_CarouselZoneHover", false];
uiNamespace setVariable ["ACME_SK_PendingInjection", []];
uiNamespace setVariable ["ACME_SK_DiscardArmedId", ""];
[ACE_player] call ACME_fnc_vialLeaseRelease;
{
    private _h = uiNamespace getVariable [_x, -1];
    if (_h >= 0) then {[_h] call CBA_fnc_removePerFrameHandler;};
    uiNamespace setVariable [_x, -1];
} forEach ["ACME_SK_WastePFH", "ACME_SK_PulsePFH"];
if (_switch) exitWith {};
playSound "ACME_NarcBoxClosed";
ace_medical_gui_pendingReopen = false;
call ACME_fnc_restorePausedFlow;
call ACME_fnc_restoreMedicationList;
private _return = _display getVariable ["ACME_SK_Return", []];
private _patient = _display getVariable ["ACME_SK_ReturnPatient", objNull];
private _suppressReturn = uiNamespace getVariable ["ACME_SK_suppressReturn", false];
// B121: closing the Narc Box during a one-handed push means genuinely closing the UI. Do not force the ACE
// medical menu back open underneath the corner syringe. The persistent push PFH is deliberately untouched.
private _hcPushClose = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if (_hcPushClose isEqualType createHashMap && {count _hcPushClose > 0} && {_hcPushClose getOrDefault ["flowing",false]}) then {_suppressReturn = true;};
ACME_infusion_pendingContext = nil;
missionNamespace setVariable ["ACME_infusion_bagTally", []];
uiNamespace setVariable ["ACME_SK_suppressReturn", false];
if (_suppressReturn) exitWith {};
if !(_return isEqualTo []) exitWith {[_return] call ACME_fnc_reopenTransfusion;};
[_patient, "medication"] call ACME_fnc_reopenMedicalMenu;
