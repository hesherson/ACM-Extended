/* Recheck the exact visible site before dispatch. A stale icon must not use a different line. */
params ["_ctrl"];
if (isNull _ctrl) exitWith {};
private _d = ctrlParent _ctrl;
// A queued click may outlive its control's workspace or its selectable state.
// Reject before changing the shared site, staging medication, or dispatching a flush.
if (isNull _d || {!(_d isEqualTo findDisplay 84000)}) exitWith {};
private _epoch = _d getVariable ["ACME_SK_CloseEpoch", -1];
if (_epoch < 0 || {_epoch != (uiNamespace getVariable ["ACME_SK_CloseEpoch", -2])}) exitWith {};
if ((uiNamespace getVariable ["ACME_SK_View", "syringe"]) != "body"
    || {uiNamespace getVariable ["ACME_SK_TagEditMode", false]}
    || {uiNamespace getVariable ["ACME_SK_InjectionBusy", false]}
    || {uiNamespace getVariable ["ACME_SK_CarouselBusy", false]}
    || {diag_tickTime < (_d getVariable ["ACME_SK_LayoutBusyUntil", 0])}) exitWith {};
private _p = _d getVariable ["ACME_SK_ReturnPatient", objNull];
if (isNull _p) then {_p = ACE_player;};
(_ctrl getVariable ["ACME_SK_Target", []]) params ["_part", "_site", "", "_vascular"];
private _route = uiNamespace getVariable ["ACME_SK_Route", "vascular"];
if ((_vascular && {_route != "vascular"}) || {!_vascular && {_route != "im"}}) exitWith {};
if (_vascular) then {
    private _have = if (_site < 0) then {[_p, _part, 0] call ACM_circulation_fnc_hasIO} else {[_p, _part, 0, _site] call ACM_circulation_fnc_hasIV};
    if (!_have) then {_ctrl setVariable ["ACME_SK_Stale", true];};
} else {_ctrl setVariable ["ACME_SK_Stale", false];};
if (_ctrl getVariable ["ACME_SK_Stale", false]) exitWith {
    _ctrl setVariable ["ACME_SK_Stale", false];
    call ACME_fnc_skBuildHotspots;
    ["That access is no longer present.", 2, ACE_player] call ace_common_fnc_displayTextStructured;
};
uiNamespace setVariable ["ACME_SK_SiteIdx", _site];
if (_vascular && {(uiNamespace getVariable ["ACME_SK_SelFlush", ""]) != ""}) exitWith {[_part] call ACME_fnc_skFlushSite;};
[_part] call ACME_fnc_skBeginInjection;
