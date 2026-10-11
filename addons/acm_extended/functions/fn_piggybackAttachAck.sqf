/* Settle the exact reserved set once, regardless of UI closure or a cancelled follow-on workflow. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_piggybackAttachAck;};};
params ["_patient","_id","_setId","_ok",["_message",""],["_doseId",""],["_provider",objNull],["_attempt",0]];
private _deferProof = {
    // A transferred provider may receive ACK before its escrow or owner receipt.
    // Wait briefly for those public facts; never synthesize a refund on timeout.
    if (!isNull _provider && {local _provider} && {_attempt < 20}) then {
        [{_this call ACME_fnc_piggybackAttachAck;},[_patient,_id,_setId,_ok,_message,_doseId,_provider,_attempt+1],0.25] call CBA_fnc_waitAndExecute;
    };
};
// A provider transfer may deliver this ACK before the next recovery tick.
if (!isNull _provider && {local _provider}) then {[_provider,false] call ACME_fnc_piggybackRecover;};
private _requests = missionNamespace getVariable ["ACME_piggybackRequests",createHashMap];
private _pending = _requests getOrDefault [_id,[]];
if (_pending isEqualTo []) exitWith {call _deferProof;};
if (_pending param [2,false]) exitWith {};
private _args = _pending select 0;
private _medic = _args select 0;
if (isNull _medic || {!local _medic} || {!((_args select 1) isEqualTo _patient)} || {(_args select 3) != _setId}) exitWith {};
if (!isNull _provider && {!(_medic isEqualTo _provider)}) exitWith {};
private _fingerprint = [_medic,_setId,toLowerANSI (_args select 4),_args select 5,_args select 6,_args select 7,_args select 8,+(_args select 9),+(_args select 10),_args select 11];
private _certificate = (_patient getVariable ["ACME_piggybackResults",createHashMap]) getOrDefault [_id,[]];
// The reply may precede its replicated receipt. Leave custody reserved and let
// reconciliation query the owner again; an unproved ACK never refunds a bag.
if (_certificate isEqualTo [] || {(_certificate param [0,!_ok]) isNotEqualTo _ok}
    || {(_certificate param [2,"__missing__"]) != _doseId}
    || {!((_certificate param [4,[]]) isEqualTo _fingerprint)}) exitWith {call _deferProof;};
private _escrow = _medic getVariable ["ACME_piggybackEscrow",createHashMap];
private _held = _escrow getOrDefault [_setId,[]];
if (_held isEqualTo [] || {(_held select 0) != _id}) exitWith {};
_pending set [2,true]; _requests set [_id,_pending];
// Completed local bookkeeping can be pruned; physical escrow and owner receipts
// are the durable reconciliation proof.
{if ((_requests get _x) param [2,false]) then {_requests deleteAt _x;};} forEach keys _requests;
missionNamespace setVariable ["ACME_piggybackRequests",_requests];
if (!_ok) then {
    private _sets = +(_medic getVariable ["ACME_preparedIVSets",[]]);
    if ((_sets findIf {(_x param [0,""]) == _setId}) < 0) then {_sets pushBack +(_held select 3);};
    _medic setVariable ["ACME_preparedIVSets",_sets,true];
    private _meds = +(_medic getVariable ["ACME_infusion_PreparedBags",[]]);
    if (!((_held select 4) isEqualTo []) && {(_meds findIf {(_x param [0,""]) == _setId}) < 0}) then {_meds pushBack +(_held select 4);};
    _medic setVariable ["ACME_infusion_PreparedBags",_meds,true];
};
_escrow deleteAt _setId;
_medic setVariable ["ACME_piggybackEscrow",_escrow,true];
private _intent = missionNamespace getVariable ["ACME_piggybackPending",[]];
private _sameWorkflow = _intent isEqualTo [_patient,_args select 4,_args select 5,_args select 6,_args select 7,_args select 8];
if (_sameWorkflow) then {["cancel"] call ACME_fnc_piggybackWorkflow;};
uiNamespace setVariable ["ACME_preparedRowSig","__force__"];
if (_message != "") then {[_medic,_message] call ACME_fnc_clinicalNotice;};
if (_sameWorkflow) then {
    if (_ok && {_doseId != ""}) then {[_patient,_doseId,_medic,_args select 4,_id] call ACME_fnc_queueInfusionClamp;}
    else {if (!isNil "ACME_fnc_reopenTransfusion") then {[[_medic,_patient,_args select 4,_args select 5,_args select 6]] call ACME_fnc_reopenTransfusion;};};
};
call ACME_fnc_updateTransfusionControls;
