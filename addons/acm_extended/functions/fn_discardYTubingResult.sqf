params [["_patient",objNull,[objNull]],["_requestId","",[""]],["_accepted",false,[false]],["_salvage",[],[[]]],["_part","",[""]],["_iv",true,[true]],["_site",-1,[0]],["_reason","",[""]]];
if (!hasInterface || {isNull ACE_player}) exitWith {};
// Replies can settle only a real pending click, and never into a replacement controlled unit.
private _pending=uiNamespace getVariable ["ACME_yDiscardPending",createHashMap];
private _context=_pending getOrDefault [_requestId,[]];
if (!(count _context in [2,3]) || {!((_context select 1) isEqualTo _patient)}) exitWith {};
private _provider=_context select 0;
if (isNull _provider || {!local _provider}) exitWith {};
_pending deleteAt _requestId;uiNamespace setVariable ["ACME_yDiscardPending",_pending];
private _seen=uiNamespace getVariable ["ACME_yDiscardSeen",createHashMap]; if (_requestId in _seen) exitWith {};
_seen set [_requestId,true]; private _ks=keys _seen; while {count _ks>32} do {_seen deleteAt (_ks deleteAt 0);}; uiNamespace setVariable ["ACME_yDiscardSeen",_seen];
if (_provider isNotEqualTo ACE_player || {(_context param [2,_provider getVariable ["ACME_providerLocalityEpoch",0]]) != (_provider getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {};
if (!_accepted) exitWith {if (_reason!="") then {[_reason,2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};};
// Salvage delivery is independent of this UI acknowledgement and follows the
// source-funded server journal across provider locality changes.
["Y tubing discarded. Salvaged fluid is being returned to Used Bags.",3.5,_provider] call ace_common_fnc_displayTextStructured;
missionNamespace setVariable ["ACME_pull_selTrueIndex",-1]; missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex",-1]; missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex",-1];
if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then {[false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;}; uiNamespace setVariable ["ACME_usedRowSig","__force__"]; uiNamespace setVariable ["ACME_coolerRowSig","__force__"]; call ACME_fnc_updateTransfusionControls;
