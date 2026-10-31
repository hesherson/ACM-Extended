/* Acknowledgements route to the supplier's CURRENT owner. B121 also settles an incremental Hardcore push slice
   against its exact stable syringe row; normal requests retain the existing refund behavior. */
params ["_medic","_id","_accepted",["_reason",""]];
if (isNull _medic) exitWith {};
if (!local _medic) exitWith {["ACME_medicationAck",_this,_medic] call CBA_fnc_targetEvent;};
private _escrow = _medic getVariable ["ACME_medicationEscrow",createHashMap];
private _row = _escrow getOrDefault [_id,[]];
if (_row isEqualTo []) exitWith {};
private _meta = _row param [5,[]];
if (_meta isEqualType [] && {(_meta param [0,""]) == "hcPushKitReset"}) exitWith {
    // This exact patient's decision ends the old request, but a fresh kit has
    // explicitly invalidated its syringe accounting. Never touch replacement
    // contents, token custody or another active controller for this receipt.
    _escrow deleteAt _id;
    [_medic,_escrow] call ACME_fnc_medicationEscrowCommit;
};
private _hcPush = _meta isEqualType [] && {(_meta param [0,""]) == "hcPush"};
private _settled = true;
private _settling = _medic getVariable ["ACME_medicationAckSettling",createHashMap];
if (_hcPush && {_id in _settling}) exitWith {};
if (_hcPush) then {
    // Keep the canonical receipt available to Retire until exact syringe restoration
    // succeeds. The private guard also blocks synchronous duplicate ACK re-entry.
    _settling set [_id,true]; _medic setVariable ["ACME_medicationAckSettling",_settling,false];
    _settled = [_medic,_meta,_accepted,_reason,_id] call ACME_fnc_hardcorePushAck;
};
if (!_settled) exitWith {
    _settling deleteAt _id; _medic setVariable ["ACME_medicationAckSettling",_settling,false];
};
// Settlement may synchronously update other requests; do not republish an older map.
_escrow = _medic getVariable ["ACME_medicationEscrow",createHashMap];
_escrow deleteAt _id;
[_medic,_escrow] call ACME_fnc_medicationEscrowCommit;
if (_hcPush) then {_settling deleteAt _id; _medic setVariable ["ACME_medicationAckSettling",_settling,false];};
[_medic,_row select 2,_accepted] call ACME_fnc_medicationRefund;
if (_meta isEqualType [] && {(_meta param [0,""]) == "syringeB279"}) then {
    [_medic,_meta param [1,""],_meta param [2,""]] call ACME_fnc_skInventorySettle;
};
// B18 transaction acknowledgements remain silent.
if (hasInterface && {_medic == ACE_player}) then {
    if (!isNull findDisplay 84000) then {call ACME_fnc_skRefreshDrawn;call ACME_fnc_skBuildHotspots;};
};
