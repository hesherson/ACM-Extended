// Settle one captured, owner-funded native Remove Bag request exactly once.
params [
    ["_patient",objNull,[objNull]],["_requestId","",[""]],["_accepted",false,[false]],
    ["_bag",[],[[]]],["_part","",[""]],["_reason","",[""]]
];
if (!hasInterface) exitWith {};
private _contexts = uiNamespace getVariable ["ACME_txRemoveContexts",createHashMap];
private _context = _contexts getOrDefault [_requestId,[]];
if (!(count _context in [3,4]) || {!((_context select 1) isEqualTo _patient)} || {(_context select 2) != _part}) exitWith {};
private _provider = _context select 0;
if (isNull _provider || {!local _provider}) exitWith {};
_contexts deleteAt _requestId; uiNamespace setVariable ["ACME_txRemoveContexts",_contexts];
private _seen = uiNamespace getVariable ["ACME_txRemoveSeen",createHashMap];
if (_requestId in _seen) exitWith {};
_seen set [_requestId,true]; private _keys = keys _seen;
while {count _keys > 64} do {_seen deleteAt (_keys deleteAt 0);};
uiNamespace setVariable ["ACME_txRemoveSeen",_seen];
private _ownsUiRequest = (uiNamespace getVariable ["ACME_txRemovePending",""]) == _requestId;
if (_ownsUiRequest) then {uiNamespace setVariable ["ACME_txRemovePending",""];};
private _viewingProvider = !isNull ACE_player && {ACE_player isEqualTo _provider}
    && {(_context param [3,_provider getVariable ["ACME_providerLocalityEpoch",0]]) == (_provider getVariable ["ACME_providerLocalityEpoch",0])};
if (!_accepted || {count _bag < 7}) exitWith {
    if (_reason != "" && {_viewingProvider}) then {[_reason,2.5,_provider,13] call ace_common_fnc_displayTextStructured;};
    if (_ownsUiRequest && {_viewingProvider} && {!isNull _patient} && {alive _provider}) then {[_provider,_patient,_part] call ACM_circulation_fnc_openTransfusionMenu;};
};
// Inventory/Used Bags are delivered by the server-certified resource-return
// journal even if this provider has switched locality or closed every menu.
if (_ownsUiRequest && {_viewingProvider} && {!isNull _patient} && {alive _provider}) then {[_provider,_patient,_part] call ACM_circulation_fnc_openTransfusionMenu;};
