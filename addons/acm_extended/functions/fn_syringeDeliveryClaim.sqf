/* Server admission precedes the claim callback. The funded carrier, not a
 * provider's privately advanced plunger, is the recovery source of truth. */
if (!isServer) exitWith {};
params ["_medic","_request","_token","_record","_held"];
if (isNull _medic || {_request == ""} || {count _record < 7} || {count _held < 7}
    || {((_held select 6) param [0,""]) != "syringeDeliveryB285"}) exitWith {};
private _all = missionNamespace getVariable ["ACME_syringeDeliveries",createHashMap];
if (_request in _all) exitWith {};
private _payload = +(_record select 2);
if (count _payload != 2 || {!((_payload select 1) isEqualType [])}) exitWith {};
private _j = createHashMapFromArray [
    ["medic",_medic],["request",_request],["token",_token],["sid",_record select 1],
    ["kit",_held select 4],["owner",owner _medic],["state","awaitBegin"],
    ["session",""],["binding",[]],["row",[(_payload select 1)] call ACME_fnc_syringeDeliveryCopy],
    ["initial",[(_payload select 1)] call ACME_fnc_syringeDeliveryCopy],["batches",createHashMap],
    ["lease",CBA_missionTime+20],["revision",_record select 6],["nextReply",0]
];
_all set [_request,_j];
missionNamespace setVariable ["ACME_syringeDeliveries",_all];
private _active = missionNamespace getVariable ["ACME_syringeDeliveryActive",[]];
_active pushBackUnique _request;
missionNamespace setVariable ["ACME_syringeDeliveryActive",_active];
private _public = _medic getVariable ["ACME_syringeDeliverySessions",createHashMap];
_public set [_request,[_j get "kit","","awaitBegin",_token,_j get "revision"]];
_medic setVariable ["ACME_syringeDeliverySessions",_public,true];
