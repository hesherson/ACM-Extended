/* Settle the exact reservation once; never give patient supplies to a replacement
   player after death/respawn. Commit with [_receipt, false], refund with [_receipt]. */
params [["_receipt", []], ["_refund", true]];
if (count _receipt != 4) exitWith {false};
_receipt params ["_donor", "_item", "_vehicle", "_id"];
private _pending = missionNamespace getVariable ["ACME_supplyReceipts", createHashMap];
if !((_pending getOrDefault [_id, []]) isEqualTo _receipt) exitWith {false};
_pending deleteAt _id;
if (!_refund) exitWith {true};
if (!isNull _vehicle) exitWith {_vehicle addItemCargoGlobal [_item, 1]; true};
if (isNull _donor) exitWith {false};
[_donor, _item] call ace_common_fnc_addToInventory;
true
