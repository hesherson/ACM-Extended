/* Debit the packed item on the carrier, then deliver each component with
 * ACE's usual overflow handling. */
params ["_unit","_kit"];
if (isNull _unit || {!local _unit} || {!alive _unit} || {_unit getVariable ["ACME_persistenceFrozen",false]}) exitWith {false};
private _gauge = ["ACME_IVStartKit_14g","ACME_IVStartKit_16g","ACME_IVStartKit_18g","ACME_IVStartKit_20g"] find _kit;
if (_gauge < 0) exitWith {false};
private _receipt = [_unit,_unit,[_kit],true] call ACME_fnc_treatmentSupplyTake;
if (_receipt isEqualTo []) exitWith {false};
if !([_receipt,false] call ACME_fnc_treatmentSupplyRefund) exitWith {false};
private _catheter = ["ACM_IV_14g","ACM_IV_16g","ACM_IV_18g","ACM_IV_20g"] select _gauge;
{
    [_unit,_x] call ace_common_fnc_addToInventory;
} forEach [_catheter,"ACME_NARBOA","ACME_Tegaderm","ACME_SalineLock","ACME_IVExtension","ACME_IVLine","ACM_SalineFlush_10"];
true
