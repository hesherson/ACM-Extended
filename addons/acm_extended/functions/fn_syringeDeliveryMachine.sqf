/* Engine owner IDs are routing addresses, not persistent machine identities.
 * A new connection using an old address cannot deny the old machine's dose. */
params ["_owner","_nonce"];
// (B391: in single player the one machine is 0, and owner of every unit is 0 too. Rejecting it left no machine to
// deliver a Narc Box syringe to: the dose was taken from the syringe and never given.)
if (!isServer || {!(_owner isEqualType 0)} || {_owner < 2 && {isMultiplayer || {_owner != 0}}}
    || {!(_nonce isEqualType "")} || {_nonce == ""}) exitWith {};
private _machines = missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
if ((_machines getOrDefault [str _owner,""]) == _nonce) exitWith {};
_machines set [str _owner,_nonce];
missionNamespace setVariable ["ACME_syringeDeliveryMachines",_machines,true];
