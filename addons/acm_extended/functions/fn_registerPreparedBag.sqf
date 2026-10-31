/* Commit one injection into the same spiked set. There is no push or single-drug cap. */
params ["_context", "_medication", "_dose", ["_solutionMl", 0]];
if (_medication == "Propofol") exitWith {false};
private _sid = _context param [20, "", [""]];
if (_sid == "" || {_dose <= 0} || {!finite _dose} || {_solutionMl <= 0} || {!finite _solutionMl}) exitWith {false};
if !([ACE_player,"prepared",_sid] call ACME_fnc_inventoryLedgerPossessed) exitWith {false};
private _sets = ACE_player getVariable ["ACME_preparedIVSets", []];
private _si = _sets findIf {(_x param [0, ""]) == _sid};
if (_si < 0 || {((_sets select _si) param [8, ""]) != "saline"}) exitWith {false};
private _set = +(_sets select _si);
private _entries = ACE_player getVariable ["ACME_infusion_PreparedBags", []];
private _index = _entries findIf {(_x param [0, ""]) == _sid};
private _entry = if (_index >= 0) then {+(_entries select _index)} else {
    private _vol = _set param [9, 0];
    if (_vol <= 0) then {_vol = [_set select 1, _set select 2] call ACME_fnc_getSalineVolumeFromItem;};
    [_sid, _set select 1, _set select 2, "", 0, 600, ACME_infusion_defaultDropSet, 0, 0, CBA_missionTime, _vol, 0, ACE_player, objNull, [], _sid, _vol]
};
private _components = [_entry] call ACME_fnc_preparedComponents;
private _ci = _components findIf {(_x select 0) == _medication};
if (_ci < 0) then {_components pushBack [_medication, _dose, 1];} else {
    private _component = +(_components select _ci);
    _component set [1, (_component select 1) + _dose];
    _component set [2, (_component param [2, 1]) + 1];
    _components set [_ci, _component];
};
_entry set [3, (_components select 0) select 0];
_entry set [4, (_components select 0) select 1];
_entry set [10, (_entry select 10) + _solutionMl];
_entry set [14, _components];
_entry set [15, _sid];
if (_index < 0) then {_index = _entries pushBack _entry;} else {_entries set [_index, _entry];};
_set set [6, [_entry] call ACME_fnc_formatPreparedLabel];
_sets set [_si, _set];
ACE_player setVariable ["ACME_infusion_PreparedBags", _entries, true];
ACE_player setVariable ["ACME_preparedIVSets", _sets, true];
    [ACE_player] call ACME_fnc_preparedInventoryCommit;
missionNamespace setVariable ["ACME_infusion_SelectedPreparedIndex", _index];
uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
true
