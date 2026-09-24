// Commit a medicated 10 mL saline flush after one or more Draw operations. Remaining saline is retained as carrier,
// every medication component keeps its measured source mL, and the physical flush is consumed exactly once.
disableSerialization;
private _dlg=findDisplay 84000;
if (isNull _dlg || {(uiNamespace getVariable ["ACME_SK_WasteStage",""]) != "draw"}) exitWith {};
private _components=+(uiNamespace getVariable ["ACME_SK_CompoundComponents",[]]);
if (_components isEqualTo []) exitWith {["Draw at least one medication into the flush before saving.",2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};
call ACME_fnc_skPendingTagCommit;

private _cap=uiNamespace getVariable ["ACME_SK_WasteCap",10];
private _nsMl=uiNamespace getVariable ["ACME_SK_WasteNS",0];
private _flushClass=uiNamespace getVariable ["ACME_SK_WasteFlushClass","ACM_SalineFlush_10"];
private _totalDrug=0;
private _valid=(_cap isEqualType 0) && {finite _cap} && {_cap==10} && {(_nsMl isEqualType 0)} && {finite _nsMl} && {_nsMl>=0};
{
    if (!(_x isEqualType []) || {count _x != 2} || {!((_x select 0) isEqualType "")} || {(_x select 0)==""} || {!((_x select 1) isEqualType 0)} || {!finite (_x select 1)} || {(_x select 1)<=0}) then {_valid=false;} else {_totalDrug=_totalDrug+(_x select 1);};
} forEach _components;
if (!_valid || {_nsMl+_totalDrug > _cap+0.001}) exitWith {};
if (([ACE_player,_flushClass] call ACME_fnc_itemCount)<1) exitWith {["The saline flush is no longer in inventory.",2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};

// Revalidate the exact explicitly selected vial sessions before any source or flush is consumed.
private _needByMed=createHashMap;
{_x params ["_m","_ml"]; _needByMed set [_m,(_needByMed getOrDefault [_m,0])+_ml];} forEach _components;
private _sessionOK=true;
{if (_y > (["limit",_x,_y,_dlg] call ACME_fnc_vialSession)+0.0005) then {_sessionOK=false;};} forEach _needByMed;
if (!_sessionOK) exitWith {["A selected vial no longer contains the staged amount. Nothing was consumed.",3,ACE_player,13] call ace_common_fnc_displayTextStructured;};

// Preserve the dedicated push-dose epinephrine behavior for its exact 1 mL + 9 mL saline recipe.
private _specialEpi=(count _components)==1 && {((_components select 0) param [0,""])=="EpinephrineCardiac"}
    && {["EpinephrineCardiac",_cap,((_components select 0) param [1,0]),_nsMl] call ACME_fnc_epinephrineRecipe};
private _saved=false;
if (_specialEpi) then {
    _saved=[ACE_player,false,""] call ACME_fnc_epinephrinePrepare;
} else {
    if ([ACE_player,_components,_flushClass,true] call ACME_fnc_medicationTakeSources) then {
        private _label=[_cap,_components,_nsMl] call ACME_fnc_skCompoundLabel;
        private _primary=(_components select 0) select 0;
        private _entry=[[_primary,_cap,_totalDrug,_label,_nsMl,_components,"dilutionB13"]] call ACME_fnc_skApplyPendingTag;
        while {count _entry < 13} do {_entry pushBack "";};
        _entry set [12,"flush"];
        private _store=ACE_player getVariable ["ACME_narcStore",[]];
        _store pushBack _entry;
        [ACE_player, _store] call ACME_fnc_narcStoreCommit;
        _saved=true;
    };
};
if (!_saved) exitWith {["Insufficient source medication or saline flush. Nothing was consumed or saved.",3,ACE_player] call ace_common_fnc_displayTextStructured;};

call ACME_fnc_skRefreshDrawn;
private _size=10;
private _patient=uiNamespace getVariable ["ACME_SK_Patient",objNull];
private _bodyPart=uiNamespace getVariable ["ACME_SK_BodyPart",""];
private _restoreMouse=getMousePosition;
private _token=format ["%1:%2",clientOwner,diag_tickTime];
_dlg setVariable ["ACME_SK_SaveFeedbackToken",_token];
private _saveBtn=_dlg displayCtrl 84004;
private _drawBtn=_dlg displayCtrl 84003;
if (!isNull _saveBtn) then {_saveBtn ctrlSetText "Saved!"; _saveBtn ctrlSetBackgroundColor (["success",0.88] call ACME_fnc_a11yColor); _saveBtn ctrlEnable false; _saveBtn ctrlCommit 0;};
if (!isNull _drawBtn) then {_drawBtn ctrlEnable false;};
[{
    params ["_oldDisplay","_tok","_size","_patient","_bodyPart","_mouse"];
    private _live=findDisplay 84000;
    if (isNull _live || {!(_live isEqualTo _oldDisplay)} || {(_live getVariable ["ACME_SK_SaveFeedbackToken",""]) != _tok}) exitWith {};
    [true] call ACME_fnc_skAfterSaveOpenBody;
    [] call ACME_fnc_skWasteEnd;
    uiNamespace setVariable ["ACME_SK_RestoreMouse",_mouse];
    closeDialog 0;
    [{_this call ACME_fnc_skOpenDraw;},[_size,_patient,_bodyPart],0.05] call CBA_fnc_waitAndExecute;
},[_dlg,_token,_size,_patient,_bodyPart,_restoreMouse],1.10] call CBA_fnc_waitAndExecute;
