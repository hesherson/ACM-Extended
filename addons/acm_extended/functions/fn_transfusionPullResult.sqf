// Provider-local result for owner-authoritative Pull Bag.
params [
    ["_patient", objNull, [objNull]], ["_requestId", "", [""]], ["_accepted", false, [false]],
    ["_bag", [], [[]]], ["_part", "", [""]], ["_mode", "", [""]], ["_onY", false, [false]], ["_reason", "", [""]]
];
if (!hasInterface || {isNull ACE_player}) exitWith {};
// Replies can settle only a real pending click, and never into a replacement controlled unit.
private _pending=uiNamespace getVariable ["ACME_txPullPending",createHashMap];
private _context=_pending getOrDefault [_requestId,[]];
if (!(count _context in [2,3]) || {!((_context select 1) isEqualTo _patient)}) exitWith {};
private _provider=_context select 0;
if (isNull _provider || {!local _provider}) exitWith {};
_pending deleteAt _requestId;uiNamespace setVariable ["ACME_txPullPending",_pending];
private _seen = uiNamespace getVariable ["ACME_txPullSeen", createHashMap];
if (_requestId in _seen) exitWith {};
_seen set [_requestId, true];
private _ks = keys _seen; while {count _ks > 48} do {_seen deleteAt (_ks deleteAt 0);};
uiNamespace setVariable ["ACME_txPullSeen", _seen];
if (_provider isNotEqualTo ACE_player || {(_context param [2,_provider getVariable ["ACME_providerLocalityEpoch",0]]) != (_provider getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {};
if (!_accepted) exitWith {if (_reason != "") then {[_reason,2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};};

missionNamespace setVariable ["ACME_pull_selTrueIndex", -1];
missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex", -1];
missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex", -1];

// The source owner's canonical resource-return journal delivers Used Bags.
// This acknowledgement owns presentation only, never a second inventory copy.
if (_mode == "discard") then {["Discarded spent infusion.",2.5,_provider] call ace_common_fnc_displayTextStructured;};
if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then {[false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;};
uiNamespace setVariable ["ACME_usedRowSig", "__force__"];
uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
call ACME_fnc_updateTransfusionControls;
