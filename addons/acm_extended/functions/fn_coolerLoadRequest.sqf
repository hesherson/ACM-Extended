/* Obtain the server's measured loose exposure before reserving a cooler. */
params ["_owner","_sid","_bag"];
if (isNull _owner || {!local _owner} || {_sid==""} || {([_bag] call ACME_fnc_coolerBagVolume)<=0}) exitWith {false};
private _pending=missionNamespace getVariable ["ACME_bloodExposurePending",createHashMap];
if ((values _pending findIf {(_x select 0) isEqualTo _owner && {(_x select 1)==_sid} && {(_x select 2)==_bag}})>=0) exitWith {false};
if (count _pending>=64) exitWith {false};
private _serial=(missionNamespace getVariable ["ACME_bloodExposureSerial",0])+1;
missionNamespace setVariable ["ACME_bloodExposureSerial",_serial];
private _request=[clientOwner,_serial];
_pending set [str _request,[_owner,_sid,_bag,serverTime,_owner getVariable ["ACME_equipmentKitEpoch",0],_owner getVariable ["ACME_providerLocalityEpoch",0],_request,serverTime]];
missionNamespace setVariable ["ACME_bloodExposurePending",_pending];
["ACME_bloodExposureRequest",["read",_owner,_bag,_request]] call CBA_fnc_serverEvent;
true
