/* Provider UI intent only. Cancelling never removes a patient bag or discards a staged set. */
params [["_operation", "start"],["_requestedId", ""]];
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
if (_operation == "cancel") exitWith {
    missionNamespace setVariable ["ACME_piggybackWorkflowGeneration",(missionNamespace getVariable ["ACME_piggybackWorkflowGeneration",0]) + 1];
    missionNamespace setVariable ["ACME_piggybackPending", []];
    uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
    uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
    true
};
if (_operation == "start") exitWith {
    if !([_patient, _part, _iv, _site] call ACME_fnc_piggybackEligible) exitWith {
        [ACE_player, "Select one attached fluid bag on a connected IV line. Any plain fluid can be its secondary; prepared medication infusions still need a saline primary."] call ACME_fnc_clinicalNotice;
        false
    };
    private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI _part, []];
    private _primary = _bags select (_bags findIf {(_x param [3, -1]) == _site && {(_x param [4, true]) == _iv}
        && {!((_x param [0, ""]) in ["ACME_Empty", "ACME_EmptySaline"])}});
    missionNamespace setVariable ["ACME_piggybackWorkflowGeneration",(missionNamespace getVariable ["ACME_piggybackWorkflowGeneration",0]) + 1];
    missionNamespace setVariable ["ACME_piggybackPending", [_patient, _part, _iv, _site, _primary param [8, ""], [_patient] call ACME_fnc_clinicalEpoch]];
    missionNamespace setVariable ["ACME_yPending", ""];
    missionNamespace setVariable ["ACME_yPendingData", ""];
    private _display = findDisplay 86000;
    if (!isNull _display) then {_display setVariable ["ACME_txActionMenu", ""]; _display setVariable ["ACME_txActivePane", "inventory"];};
    [false] call ACME_fnc_togglePreparedSets;
    uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
    call ACME_fnc_transfusionFilterInventory;
    call ACME_fnc_updateTransfusionControls;
    true
};
private _pending = missionNamespace getVariable ["ACME_piggybackPending", []];
if (count _pending < 6 || {!((_pending select [0,4]) isEqualTo [_patient,_part,_iv,_site])}
    || {(_pending select 5) != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {["cancel"] call ACME_fnc_piggybackWorkflow; false};
if (_operation == "inject") exitWith {call ACME_fnc_openPrepFromInventoryMenu; true};
if (_operation == "add") exitWith {
    private _display = findDisplay 86000;
    if (isNull _display) exitWith {false};
    private _list = _display displayCtrl 86145;
    private _row = lbCurSel _list;
    private _setId = _requestedId;
    // Card rows deliberately hide their backing native lists. Visibility is
    // presentation state, not a test of whether the selected plain set exists.
    if (_setId == "" && {uiNamespace getVariable ["ACME_preparedListMode", false]} && {_row >= 0}) then {_setId = _list lbData _row;};
    if (_setId == "" && {!(uiNamespace getVariable ["ACME_preparedListMode", false])}) then {
        private _selected = call ACME_fnc_getSelectedPreparedInfusion;
        if !(_selected isEqualTo []) then {_setId = (_selected select 1) param [0, ""];};
    };
    if (_setId == "") exitWith {[ACE_player,"Select a fluid bag or prepared infusion for the piggyback."] call ACME_fnc_clinicalNotice; false};
    [_setId] call ACME_fnc_piggybackAttachRequest
};
false
