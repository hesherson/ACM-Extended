/* Request-machine reconciliation; retries never allocate another supply.
   Seal decisions renew their lease; widening retains its single legacy query. */
params ["_packet", "_receipt"];
private _pending = missionNamespace getVariable ["ACME_supplyReceipts", createHashMap];
if !((_pending getOrDefault [_receipt param [3, ""], []]) isEqualTo _receipt) exitWith {};
_packet call ACME_fnc_ownerDispatch;
// A local owner can acknowledge synchronously. Stop immediately once settled.
_pending = missionNamespace getVariable ["ACME_supplyReceipts", createHashMap];
if (((_packet param [2, []]) param [3, ""]) == "seal"
    && {(_pending getOrDefault [_receipt param [3, ""], []]) isEqualTo _receipt}) then {
    [ACME_fnc_thoraAftercareRetry, [_packet, _receipt], 16] call CBA_fnc_waitAndExecute;
};
