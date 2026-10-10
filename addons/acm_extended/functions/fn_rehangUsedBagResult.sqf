params [["_patient",objNull,[objNull]],["_requestId","",[""]],["_accepted",false,[false]],["_usedId","",[""]],["_record",[],[[]]],["_part","",[""]],["_reason","",[""]],["_bagUid","",[""]]];
if (!hasInterface || {isNull ACE_player}) exitWith {};
private _pending=uiNamespace getVariable ["ACME_usedRehangPending",createHashMap];
// An unsolicited/old rejection cannot mint a used bag from its payload. Only return
// the exact locally reserved record, to the provider who actually reserved it.
if !(_requestId in _pending) exitWith {};
private _contexts=uiNamespace getVariable ["ACME_usedRehangContext",createHashMap];
private _context=_contexts getOrDefault [_requestId,[]];
if (count _context != 3 || {!((_context select 1) isEqualTo _patient)} || {(_context select 2) != _usedId}) exitWith {};
private _provider=_context select 0;
if (isNull _provider || {!local _provider}) exitWith {};
private _saved=_pending get _requestId;
if (count _saved < 7 || {(_saved select 0) != _usedId}) exitWith {};
_contexts deleteAt _requestId; uiNamespace setVariable ["ACME_usedRehangContext",_contexts];
if (_requestId in _pending) then {_pending deleteAt _requestId; uiNamespace setVariable ["ACME_usedRehangPending",_pending];};
private _seen=uiNamespace getVariable ["ACME_usedRehangSeen",createHashMap]; if (_requestId in _seen) exitWith {};
_seen set [_requestId,true]; private _ks=keys _seen; while {count _ks>48} do {_seen deleteAt (_ks deleteAt 0);}; uiNamespace setVariable ["ACME_usedRehangSeen",_seen];
if (!_accepted) exitWith {
    if !(_saved isEqualTo []) then {private _used=_provider getVariable ["ACME_usedBags",[]]; if ((_used findIf {(_x param [0,""])==_usedId})<0) then {_used pushBack _saved; _provider setVariable ["ACME_usedBags",_used,true];};};
    if (_reason!="") then {[_reason,2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;}; uiNamespace setVariable ["ACME_usedRowSig","__force__"];
};
if (count _saved>=7) then {_saved params ["",["_type",""],["_rem",0],"","","",["_name",""]]; [format ["Re-hung %1 (%2 mL).",_name,round _rem],2.5,ACE_player] call ace_common_fnc_displayTextStructured;};
uiNamespace setVariable ["ACME_usedRowSig","__force__"]; uiNamespace setVariable ["ACME_coolerRowSig","__force__"]; if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then {[false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;}; call ACME_fnc_updateTransfusionControls;
