/* Engine owner IDs are routing addresses, not persistent machine identities.
 * A new connection using an old address cannot deny the old machine's dose. */
params ["_owner","_nonce"];
if (!isServer || {!(_owner isEqualType 0)} || {_owner < 2}
    || {!(_nonce isEqualType "")} || {_nonce == ""}) exitWith {};
private _machines = missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
if ((_machines getOrDefault [str _owner,""]) == _nonce) exitWith {};
_machines set [str _owner,_nonce];
missionNamespace setVariable ["ACME_syringeDeliveryMachines",_machines,true];
