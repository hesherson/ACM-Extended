/* B62: commit the active stored syringe tag and return immediately to the normal large Body Map + compact carousel. */
disableSerialization;
private _d = findDisplay 84000;
if (isNull _d) exitWith {false};
// Retire pending autofocus before another editor can open on this same display.
_d setVariable ["ACME_SK_TagEditEpoch", (_d getVariable ["ACME_SK_TagEditEpoch", 0]) + 1];
call ACME_fnc_skTagCommit;
private _list = _d displayCtrl 84471;
if (!isNull _list) then {_list lbSetCurSel -1; _list ctrlShow false;};
uiNamespace setVariable ["ACME_SK_TagEditMode", false];
uiNamespace setVariable ["ACME_SK_CarouselExpanded", false];
uiNamespace setVariable ["ACME_SK_CarouselHover", false];
uiNamespace setVariable ["ACME_SK_CarouselZoneHover", false];
uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", 0];
[0.12] call ACME_fnc_skDynamicLayout;
[0.12] call ACME_fnc_skCarouselRender;
call ACME_fnc_skBuildHotspots;
true
