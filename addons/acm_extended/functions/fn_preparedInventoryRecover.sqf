/* Provider locality may change after the carrier leaves native inventory. Recover from serializable intent. */
params ["_provider"];
if (isNull _provider || {!local _provider}) exitWith {};
// Latch expiry in the existing one-second inventory pass. No new polling worker.
// Prepared metadata edits wait for ordinary custody to settle and use its ledger.
if !(_provider getVariable ["ACME_persistenceFrozen",false]) then {
    private _used=_provider getVariable ["ACME_usedBags",[]];
    private _aged=_used apply {[_x,"used"] call ACME_fnc_bloodUseRow};
    if (_aged isNotEqualTo _used) then {_provider setVariable ["ACME_usedBags",_aged,true];};
    private _idle=(["ACME_inventoryEscrow","ACME_inventoryPending","ACME_inventoryMutations","ACME_inventoryIncoming"] findIf {count (_provider getVariable [_x,createHashMap])>0})<0;
    if (_idle) then {
        private _sets=_provider getVariable ["ACME_preparedIVSets",[]];
        private _agedSets=_sets apply {[_x,"prepared"] call ACME_fnc_bloodUseRow};
        if (_agedSets isNotEqualTo _sets) then {[_provider] call ACME_fnc_preparedInventoryCommit;};
    };
};
private _intents = _provider getVariable ["ACME_inventoryActionIntents",createHashMap];
private _escrow = _provider getVariable ["ACME_inventoryEscrow",createHashMap];
{
    private _request = _x; private _intent = _y;
    private _held = _escrow getOrDefault [_request,[]];
    if (_held isEqualTo []) then {_intents deleteAt _request; continue;};
    if (CBA_missionTime < (_intent param [2,0])) then {continue;};
    private _payload = _held select 1;
    if (([_provider,"prepared",_payload select 0,_request] call ACME_fnc_inventoryLedgerCertificate) isEqualTo []) then {continue;};
    private _mode = _intent select 0; private _args = _intent select 1;
    private _patient = objNull;
    if (_mode == "preparedHang") then {
        _patient = _args select 0;
        private _pending = missionNamespace getVariable ["ACME_preparedHangPending",createHashMap];
        if !(_request in _pending) then {_pending set [_request,[_patient,_args,CBA_missionTime,false]]; missionNamespace setVariable ["ACME_preparedHangPending",_pending];};
    } else {
        _patient = (_args select 0) select 1;
        private _pending = missionNamespace getVariable ["ACME_preparedPending",createHashMap];
        if !(_request in _pending) then {_pending set [_request,[_args select 0,CBA_missionTime,false,_args select 2]]; missionNamespace setVariable ["ACME_preparedPending",_pending];};
    };
    if (!isNull _patient) then {[_patient,_mode,_args] call ACME_fnc_ownerDispatch;};
    _intent set [2,CBA_missionTime+5]; _intents set [_request,_intent];
} forEach _intents;
_provider setVariable ["ACME_inventoryActionIntents",_intents,false];
