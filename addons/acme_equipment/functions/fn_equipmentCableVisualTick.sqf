/* One bounded client worker. Local simple objects have no physical rope or authoritative state. */
if (!hasInterface) exitWith {};
private _cache=missionNamespace getVariable ["ACME_eqCableCache",createHashMap];
private _desired=[];
if (missionNamespace getVariable ["ACME_equipmentCableVisuals",true]) then {
    if (diag_tickTime >= (missionNamespace getVariable ["ACME_eqCableScanAt",0])) then {
        missionNamespace setVariable ["ACME_eqCableScanAt",diag_tickTime+0.5];
        private _near=nearestObjects [positionCameraToWorld [0,0,0],["ACME_TempusPro","ACME_TempusLS"],20];
        _near=_near select {(_x getVariable ["ACME_eq_kind",""]) in ["pro","ls"]};
        missionNamespace setVariable ["ACME_eqCableDevices",_near select [0,8]];
    };
    {
        private _device=_x;
        if (isNull _device || {isObjectHidden _device}) then {continue;};
        {
            if (count _desired >= 16) exitWith {};
            _x params ["_kind","_target","_patient"];
            private _from=[_device,_kind] call ACME_fnc_equipmentCableAnchor;
            private _to=[_target,_kind,_patient] call ACME_fnc_equipmentCableAnchor;
            private _poses=[_from,_to] call ACME_fnc_equipmentCablePose;
            if (_poses isNotEqualTo []) then {_desired pushBack [netId _device+":"+_kind,_from,_to,_poses];};
        } forEach ([_device] call ACME_fnc_equipmentCableSpecs);
    } forEach (missionNamespace getVariable ["ACME_eqCableDevices",[]]);
};
private _want=_desired apply {_x select 0};
private _allocate=diag_tickTime >= (missionNamespace getVariable ["ACME_eqCableRetryAt",0]);
{
    if !(_x in _want) then {
        {if (!isNull _x) then {deleteVehicle _x;};} forEach ((_cache get _x) select 2);
        _cache deleteAt _x;
    };
} forEach keys _cache;
{
    _x params ["_key","_from","_to","_poses"];
    private _record=_cache getOrDefault [_key,[[],[],[]]];
    private _objects=_record select 2;
    if (count _objects != 8 || {(_objects findIf {isNull _x}) >= 0}) then {
        {if (!isNull _x) then {deleteVehicle _x;};} forEach _objects;
        _objects=[];
        if (_allocate) then {for "_i" from 1 to 8 do {_objects pushBack (createSimpleObject ["\acme_equipment\models\monitor_cable.p3d",_from,true]);};};
        _record=[[],[],_objects];
    };
    if (count _objects!=8 || {(_objects findIf {isNull _x}) >= 0}) then {
        {if (!isNull _x) then {deleteVehicle _x;};} forEach _objects;
        _cache deleteAt _key;
        if (_allocate) then {missionNamespace setVariable ["ACME_eqCableRetryAt",diag_tickTime+2];};
        _allocate=false;
        continue;
    };
    if ((_record select 0) isEqualTo [] || {(_record select 1) isEqualTo []}
        || {(_record select 0) distance _from > 0.002} || {(_record select 1) distance _to > 0.002}) then {
        {
            _x params ["_pos","_dir","_up","_length"];
            private _segment=_objects select _forEachIndex;
            if (!isNull _segment) then {
                _segment setPosWorld _pos;
                _segment setVectorDirAndUp [_dir,_up];
                // Direction resets scale in Arma; apply scale last.
                _segment setObjectScale _length;
            };
        } forEach _poses;
        _record set [0,_from];_record set [1,_to];
    };
    _cache set [_key,_record];
} forEach _desired;
missionNamespace setVariable ["ACME_eqCableCache",_cache];
