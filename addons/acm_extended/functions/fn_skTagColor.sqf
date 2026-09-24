/* B62: change the selected stored syringe tag. Works only on the stable selected syringe and remains inside
   dedicated Edit Tag mode. Reset the row before/after each use so selecting the same color twice is always valid. */
disableSerialization;
params ["_c","_row"];
if (_row < 0) exitWith {};
private _id = _c lbData _row;
if (_id == "") then {_id = "none";};
private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _i = [_store,false] call ACME_fnc_skSelectedIndex;
if (_i < 0) exitWith {};
private _entry = +(_store select _i);
while {count _entry < 12} do {_entry pushBack "";};
_entry set [7,_id];
_store set [_i,_entry];
[ACE_player, _store] call ACME_fnc_narcStoreCommit;
_c lbSetCurSel -1;
_c ctrlShow false;
call ACME_fnc_skCarouselRender;
// Color selection owns only this display/editor/record's deferred focus request.
// A later color choice, including None, retires older requests even if the color repeats.
private _d = findDisplay 84000;
if (isNull _d) exitWith {};
private _colorEpoch = (_d getVariable ["ACME_SK_TagColorEpoch", 0]) + 1;
_d setVariable ["ACME_SK_TagColorEpoch", _colorEpoch];
if (uiNamespace getVariable ["ACME_SK_TagEditMode",false]) then {
    [{
        params ["_d", "_medic", "_syringeId", "_id", "_editEpoch", "_colorEpoch"];
        disableSerialization;
        if (isNull _d || {!((findDisplay 84000) isEqualTo _d)}
            || {!(ACE_player isEqualTo _medic)}
            || {(uiNamespace getVariable ["ACME_SK_View", "syringe"]) != "body"}
            || {!(uiNamespace getVariable ["ACME_SK_TagEditMode",false])}
            || {(_d getVariable ["ACME_SK_TagEditEpoch", 0]) != _editEpoch}
            || {(_d getVariable ["ACME_SK_TagColorEpoch", -1]) != _colorEpoch}) exitWith {};
        private _store = [_medic] call ACME_fnc_skStoreEnsureIds;
        private _index = [_store,false] call ACME_fnc_skSelectedIndex;
        if (_index < 0) exitWith {};
        private _entry = _store select _index;
        if ((_entry param [11, ""]) != _syringeId || {(_entry param [7, "none"]) != _id}) exitWith {};
        private _focusCtrl = _d displayCtrl (if (_id in ["","none"]) then {84470} else {84460});
        if (!isNull _focusCtrl) then {ctrlSetFocus _focusCtrl;};
    },[_d,ACE_player,_entry param [11,""],_id,_d getVariable ["ACME_SK_TagEditEpoch",0],_colorEpoch],0.01] call CBA_fnc_waitAndExecute;
};
