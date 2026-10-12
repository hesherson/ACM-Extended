/* Acknowledgements route to the supplier's CURRENT owner. B121 also settles an incremental Hardcore push slice
   against its exact stable syringe row; normal requests retain the existing refund behavior. */
params ["_medic","_id","_accepted",["_reason",""]];
if (isNull _medic) exitWith {};
if (!local _medic) exitWith {["ACME_medicationAck",_this,_medic] call CBA_fnc_targetEvent;};
private _escrow = _medic getVariable ["ACME_medicationEscrow",createHashMap];
private _row = _escrow getOrDefault [_id,[]];
if (_row isEqualTo []) exitWith {};
_escrow deleteAt _id;
[_medic,_escrow] call ACME_fnc_medicationEscrowCommit;
[_medic,_row select 2,_accepted] call ACME_fnc_medicationRefund;
private _meta = _row param [5,[]];
if (_meta isEqualType [] && {(_meta param [0,""]) == "syringeB279"}) then {
    [_medic,_meta param [1,""],_meta param [2,""]] call ACME_fnc_skInventorySettle;
};
if (_meta isEqualType [] && {(_meta param [0,""]) == "hcPush"}) then {[_medic,_meta,_accepted,_reason] call ACME_fnc_hardcorePushAck;};
// B18 transaction acknowledgements remain silent.
if (hasInterface && {_medic == ACE_player}) then {
    if (!isNull findDisplay 84000) then {call ACME_fnc_skRefreshDrawn;call ACME_fnc_skBuildHotspots;};
};
