/* Server-only removal from ACE's exact live litter registry. The client supplies no object list or position. */
if (!isServer) exitWith {false};
params [["_operation","",[""]],["_unit",objNull,[objNull]],["_owner",-1,[0]],["_request","",[""]],["_token","",[""]]];
if (!(_operation in ["request","commit","cancel"]) || {isNull _unit} || {!(_unit isKindOf "CAManBase")}
    || {_owner < 2} || {_owner != owner _unit} || {_request == ""} || {count _request > 128}) exitWith {false};
private _key = netId _unit;
if (_key in ["","0:0"]) exitWith {false};
private _records = missionNamespace getVariable ["ACME_litterClaims",createHashMap];
// Claims/tombstones are bounded by recent participants, not by treatment/litter count.
{if (((_records get _x) param [5,0]) + 30 < diag_tickTime) then {_records deleteAt _x;};} forEach (keys _records);
missionNamespace setVariable ["ACME_litterClaims",_records];
// ACE owns registry bookkeeping. Keep only a private pending-delete set until its handles become null.
private _retired = (missionNamespace getVariable ["ACME_litterRemoved",[]]) select {!isNull _x};
missionNamespace setVariable ["ACME_litterRemoved",_retired];
private _record = _records getOrDefault [_key,[]];
if (_record isNotEqualTo [] && {(_record select 1) != _owner}) then {_records deleteAt _key;_record = [];};
private _reply = {
    params ["_result",["_grant",""],["_count",0]];
    ["ACME_medicalLitterReply",[_unit,_request,_result,_grant,_count],_owner] call CBA_fnc_ownerEvent;
};
private _usable = alive _unit && {!(_unit getVariable ["ACE_isUnconscious",false])} && {isNull objectParent _unit};
if (_operation == "request") exitWith {
    if (!_usable) exitWith {false};
    if (_record isNotEqualTo [] && {(_record select 2) == _request}) exitWith {
        if ((_record select 7) == "granted" && {diag_tickTime <= (_record select 5)}) then {
            ["grant",_record select 3,count (_record select 6)] call _reply;
        } else {["done","",0] call _reply;};
        true
    };
    if (_record isNotEqualTo [] && {(_record select 7) == "granted"} && {diag_tickTime <= (_record select 5)}) exitWith {["busy"] call _reply;false};
    private _registry = missionNamespace getVariable ["ace_medical_treatment_litterObjects",[]];
    if !(_registry isEqualType []) exitWith {false};
    private _objects = [];
    {
        if (_x isEqualType [] && {count _x >= 1}) then {
            private _object = _x select 0;
            if (_object isEqualType objNull && {!isNull _object} && {isSimpleObject _object}
                && {!(_object in _retired)} && {_unit distance _object <= 2}) then {_objects pushBackUnique _object;};
        };
        if (count _objects >= 25) exitWith {};
    } forEach _registry;
    if (_objects isEqualTo []) exitWith {["none"] call _reply;true};
    private _serial = (missionNamespace getVariable ["ACME_litterGrantSerial",0]) + 1;
    missionNamespace setVariable ["ACME_litterGrantSerial",_serial];
    private _grant = format ["collect:%1:%2:%3",_serial,diag_tickTime,random 1e9];
    _records set [_key,[_unit,_owner,_request,_grant,diag_tickTime,diag_tickTime + 15,_objects,"granted",getPosASL _unit,0]];
    ["grant",_grant,count _objects] call _reply;
    true
};
if (count _record != 10 || {(_record select 0) isNotEqualTo _unit} || {(_record select 1) != _owner}
    || {(_record select 2) != _request} || {(_record select 3) != _token}) exitWith {false};
if ((_record select 7) == "done") exitWith {["done",_token,_record select 9] call _reply;true};
if ((_record select 7) != "granted") exitWith {false};
if (_operation == "cancel") exitWith {_record set [7,"cancelled"];_record set [6,[]];true};
if (!_usable || {diag_tickTime > (_record select 5)} || {diag_tickTime - (_record select 4) < 2}
    || {(getPosASL _unit) vectorDistance (_record select 8) > 0.75}) exitWith {
    _record set [7,"cancelled"];_record set [6,[]];["cancelled",_token] call _reply;false
};
private _registry = missionNamespace getVariable ["ace_medical_treatment_litterObjects",[]];
if !(_registry isEqualType []) exitWith {false};
private _remove = [];
{
    if (_x isEqualType [] && {count _x >= 1}) then {
        private _object = _x select 0;
        if (_object in (_record select 6) && {_object isEqualType objNull} && {!isNull _object}
            && {isSimpleObject _object} && {!(_object in _retired)} && {_unit distance _object <= 2}) then {_remove pushBackUnique _object;};
    };
} forEach _registry;
// Retire before deletion, so overlapping users and duplicate commits cannot claim an object twice.
_record set [7,"done"];_record set [6,[]];_record set [9,count _remove];
_retired append _remove;
missionNamespace setVariable ["ACME_litterRemoved",_retired];
{deleteVehicle _x;} forEach _remove;
// Deletion turns native handles null; ACE retires those registry slots through its own lifetime/count loop.
// Do not rewrite its registry, creation timestamps, cleanup flag or scheduler.
["done",_token,count _remove] call _reply;
true
