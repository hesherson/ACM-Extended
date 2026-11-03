params ["_actor","_box","_open"];
if (!isServer || {isNull _actor} || {isNull _box}) exitWith {};
if (isRemoteExecuted && {remoteExecutedOwner!=owner _actor}) exitWith {};
if !((typeOf _box) in ["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"]) exitWith {};
private _users=(_box getVariable ["ACME_eqCoolerUsers",[]]) select {(_x select 0) isNotEqualTo _actor};
if (_open && {alive _actor} && {_actor distance _box<=4.5} && {!(_box getVariable ["ACME_coolerRetired",false])} && {!(_box getVariable ["ACME_coolerPacking",false])}) then {_users pushBack [_actor,serverTime+6];};
_box setVariable ["ACME_eqCoolerUsers",_users];
private _boxes=missionNamespace getVariable ["ACME_eqOpenCoolers",[]];_boxes pushBackUnique _box;missionNamespace setVariable ["ACME_eqOpenCoolers",_boxes];
