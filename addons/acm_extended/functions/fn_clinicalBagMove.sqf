/* Reserving a move changes only intent. The entire connected line remains attached and flowing
   until a new established, empty access is selected and the owner commits its exact live UIDs. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_clinicalBagMove;};};
params ["_p", "_medic", "_id", "_mode", "_part", "_iv", "_site", "_epoch", ["_token", ""]];
if (!local _p || {_epoch != ([_p] call ACME_fnc_clinicalEpoch)}) exitWith {};
private _map = _p getVariable ["ACM_circulation_IV_Bags",createHashMap];
private _moves = _p getVariable ["ACME_bagMoves",createHashMap];
if (_mode == "cancel") exitWith {
    private _move = _moves getOrDefault [_id,[]];
    if !(_move isEqualTo []) then {
        if ((_move select 2) isEqualTo _medic && {(_move param [5,""]) == _token}) then {_moves deleteAt _id; [_p,"ACME_bagMoves",_moves] call ACME_fnc_setVarNet;};
    };
};
if (isNull _medic || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
    || {_medic distance _p > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _p}}}) exitWith {};
if (_mode == "reserve") exitWith {
    if (_id == "" || {_token == ""} || {_id in _moves}) exitWith {[_medic,"That bag is already being moved."] call ACME_fnc_clinicalNotice;};
    private _arr = _map getOrDefault [_part,[]];
    private _idx = _arr findIf {(_x param [8,""]) == _id};
    if (_idx < 0) exitWith {[_medic,"That bag is no longer on this site."] call ACME_fnc_clinicalNotice;};
    private _bag = +(_arr select _idx);
    if ((_bag param [11, ""]) isEqualTo "bagOnly") exitWith {
        [_medic,"Pull this bag and attach it to another installed IV line. Its tubing stays with this access."] call ACME_fnc_clinicalNotice;
    };
    private _originIV = _bag param [4,true]; private _originSite = _bag param [3,-1];
    private _key = toLowerANSI format["%1#%2#%3",_part,_originIV,_originSite];
    if (_key in (_p getVariable ["ACME_yFlushJobs",createHashMap])) exitWith {[_medic,"Finish priming/flushing before moving this line."] call ACME_fnc_clinicalNotice;};
    private _reserved = values _moves findIf {
        private _other = _x param [1,[]];
        (_x param [0,""]) == _part && {(_other param [3,-2]) == _originSite} && {(_other param [4,!_originIV]) == _originIV}
    };
    if (_reserved >= 0) exitWith {[_medic,"This connected line is already being moved."] call ACME_fnc_clinicalNotice;};
    _moves set [_id,[_part,_bag,_medic,CBA_missionTime,_epoch,_token]];
    [_p,"ACME_bagMoves",_moves] call ACME_fnc_setVarNet;
};
if (_mode != "place") exitWith {};
private _move = _moves getOrDefault [_id,[]];
if (_move isEqualTo [] || {!((_move select 2) isEqualTo _medic)} || {(_move param [5,""]) != _token}) exitWith {};
_move params ["_origin","_snapshot"];
private _originIV = _snapshot param [4,true]; private _originSite = _snapshot param [3,-1];
private _source = +(_map getOrDefault [_origin,[]]);
private _sourceIndex = _source findIf {(_x param [8,""]) == _id && {(_x param [3,-1]) == _originSite} && {(_x param [4,true]) == _originIV}};
if (_sourceIndex < 0) exitWith {_moves deleteAt _id; [_p,"ACME_bagMoves",_moves] call ACME_fnc_setVarNet; [_medic,"That bag moved or was removed. Nothing was detached."] call ACME_fnc_clinicalNotice;};
if !([_p,_part,_iv,_site] call ACME_fnc_transfusionAccessValid) exitWith {[_medic,"Select an established IV/IO. The bag remains at its original site."] call ACME_fnc_clinicalNotice;};
private _fromServiceKey = toLowerANSI format["%1#%2#%3",_origin,_originIV,_originSite];
if (_fromServiceKey in (_p getVariable ["ACME_yFlushJobs",createHashMap])) exitWith {[_medic,"Finish priming/flushing before moving this line. It remains attached."] call ACME_fnc_clinicalNotice;};
private _sameAccess = _origin == _part && {_originIV == _iv} && {_originSite == _site};
if (_sameAccess) exitWith {_moves deleteAt _id; [_p,"ACME_bagMoves",_moves] call ACME_fnc_setVarNet;};
private _dest = +(_map getOrDefault [_part,[]]);
if ((_dest findIf {(_x param [3,-1]) == _site && {(_x param [4,true]) == _iv}}) >= 0
    || {[_p,_part,_iv,_site] call ACME_fnc_isYLineAccess}
    || {toLowerANSI format["%1#%2#%3",_part,_iv,_site] in (_p getVariable ["ACME_PiggybackLines",createHashMap])}) exitWith {
    [_medic,"The destination already has a line. The bag remains at its original site."] call ACME_fnc_clinicalNotice;
};
private _onY = [_p,_origin,_originIV,_originSite] call ACME_fnc_isYLineAccess;
private _pib = [_p,_origin,_originIV,_originSite] call ACME_fnc_piggybackLine;
private _group = if (_onY || {!(_pib isEqualTo [])}) then {_source select {(_x param [3,-1]) == _originSite && {(_x param [4,true]) == _originIV}}} else {[_source select _sourceIndex]};
if ((_group findIf {(_x param [11, ""]) isEqualTo "bagOnly"}) >= 0) exitWith {
    _moves deleteAt _id;
    [_p,"ACME_bagMoves",_moves] call ACME_fnc_setVarNet;
    [_medic,"Pull the bag and reconnect it to an installed IV line. The original apparatus remains attached."] call ACME_fnc_clinicalNotice;
};
private _ids = _group apply {_x param [8,""]};
private _pi = ACME_infusion_bodyParts find toLowerANSI _part;
private _access = [_p,_iv,_pi,_site] call ACM_circulation_fnc_getAccessType;
if !([_p,_origin,_originIV,_originSite,_part,_iv,_site] call ACME_fnc_lineWarmerMove) exitWith {[_medic,"The destination has another warmer. The original line remains attached."] call ACME_fnc_clinicalNotice;};
_source = _source select {!((_x param [8,""]) in _ids)};
if (_origin == _part) then {_dest = +_source;};
{
    private _bag = +_x;
    _bag set [2,_access]; _bag set [3,_site]; _bag set [4,_iv];
    _dest pushBack _bag;
} forEach _group;
_map set [_origin,_source]; _map set [_part,_dest];
private _fromKey = toLowerANSI format["%1#%2#%3",_origin,_originIV,_originSite];
private _toKey = toLowerANSI format["%1#%2#%3",_part,_iv,_site];
if (_onY) then {
    private _lines = +(_p getVariable ["ACME_YLines",[]]);
    _lines = _lines select {toLowerANSI _x != _fromKey}; _lines pushBackUnique _toKey;
    // Preserve source values before yLinesCommit initializes a newly moved access as unprimed.
    private _serviceHistory = [];
    {
        private _state = _p getVariable [_x,createHashMap];
        if (_fromKey in _state) then {_serviceHistory pushBack [_x,_state get _fromKey];};
    } forEach ["ACME_YLinePrimed","ACME_YLineDirty","ACME_YLineUnitsSinceFlush","ACME_YLineVolSinceFlush"];
    [_p,_lines] call ACME_fnc_yLinesCommit;
    {
        _x params ["_name","_value"];
        private _state = _p getVariable [_name,createHashMap];
        _state deleteAt _fromKey; _state set [_toKey,_value];
        [_p,_name,_state] call ACME_fnc_setVarNet;
    } forEach _serviceHistory;
};
if !(_pib isEqualTo []) then {
    private _lines = _p getVariable ["ACME_PiggybackLines",createHashMap];
    _lines deleteAt _fromKey; _lines set [_toKey,_pib]; [_p,_lines] call ACME_fnc_piggybackLinesCommit;
};
[_p,_map,true] call ACME_fnc_ivBagsCommit;
_moves deleteAt _id; [_p,"ACME_bagMoves",_moves] call ACME_fnc_setVarNet;
private _entries = _p getVariable ["ACME_infusion_BagMedications",[]];
{
    if ((_x param [23,""]) in _ids) then {
        _x set [1,_part];
        _x set [4,_site]; _x set [5,_iv];
    };
} forEach _entries;
// Relink the drug entries by their physical UID, never by the old row/index.
{private _e = _x; if ((_e param [23,""]) in _ids) then {_e set [2,_dest findIf {(_x param [8,""]) == (_e param [23,""])}];};} forEach _entries;
[_p,_entries] call ACME_fnc_infusionMedicationStateCommit;
[_p,_origin] call ACM_circulation_fnc_updateActiveFluidBags;
[_p,_part] call ACM_circulation_fnc_updateActiveFluidBags;
[_p,_part,_iv,_site] call ACME_fnc_resumeSiteFlow;
[_p,(_p getVariable ["ACME_detachedBags",[]]) - _ids] call ACME_fnc_detachedBagsCommit;
[_p,"ACME_IV_DisconnectedBagUIDs",(_p getVariable ["ACME_IV_DisconnectedBagUIDs",[]]) - _ids] call ACME_fnc_setVarNet;
