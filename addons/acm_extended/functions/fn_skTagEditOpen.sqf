/* B69: enter the dedicated stored-syringe tag editor from Body Map.
   Existing tags expose/focus their first text line. Untagged syringes show only Select Syringe Tag until a color is chosen. */
disableSerialization;
private _d = findDisplay 84000;
if (isNull _d || {(uiNamespace getVariable ["ACME_SK_View","syringe"]) != "body"}) exitWith {false};
private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _idx = [_store] call ACME_fnc_skSelectedIndex;
if (_idx < 0) exitWith {false};

// Each editor opening owns its deferred focus request, even on the same display/record.
private _editEpoch = (_d getVariable ["ACME_SK_TagEditEpoch", 0]) + 1;
_d setVariable ["ACME_SK_TagEditEpoch", _editEpoch];

private _list = _d displayCtrl 84471;
if (!isNull _list) then {_list lbSetCurSel -1; _list ctrlShow false;};
uiNamespace setVariable ["ACME_SK_TagEditMode", true];
uiNamespace setVariable ["ACME_SK_CarouselExpanded", true];
uiNamespace setVariable ["ACME_SK_CarouselHover", false];
uiNamespace setVariable ["ACME_SK_CarouselZoneHover", true];
uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", 0];
[0.12] call ACME_fnc_skDynamicLayout;
[0.12] call ACME_fnc_skCarouselRender;
call ACME_fnc_skBuildHotspots;

[{
    disableSerialization;
    params ["_d", "_medic", "_syringeId", "_editEpoch"];
    if (isNull _d || {!((findDisplay 84000) isEqualTo _d)}
        || {!(ACE_player isEqualTo _medic)}
        || {(uiNamespace getVariable ["ACME_SK_View","syringe"]) != "body"}
        || {!(uiNamespace getVariable ["ACME_SK_TagEditMode",false])}
        || {(_d getVariable ["ACME_SK_TagEditEpoch", -1]) != _editEpoch}) exitWith {};
    private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
    private _idx = [_store,false] call ACME_fnc_skSelectedIndex;
    if (_idx < 0 || {((_store select _idx) param [11, ""]) != _syringeId}) exitWith {};
    private _color = (_store select _idx) param [7,"none",[""]];
    private _focusCtrl = _d displayCtrl (if (_color in ["","none"]) then {84470} else {84460});
    if (!isNull _focusCtrl) then {ctrlSetFocus _focusCtrl;};
}, [_d, ACE_player, (_store select _idx) param [11, ""], _editEpoch], 0.14] call CBA_fnc_waitAndExecute;
true
