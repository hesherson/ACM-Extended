/* Close-range presentation uses Kelly's ACE refuel hose with two client-local PhysX helpers. */
if (!hasInterface) exitWith {};
private _cache = missionNamespace getVariable ["ACME_eqCableCache",createHashMap];
private _desired = [];
if (missionNamespace getVariable ["ACME_equipmentCableVisuals",true]) then {
    if (diag_tickTime >= (missionNamespace getVariable ["ACME_eqCableScanAt",0])) then {
        missionNamespace setVariable ["ACME_eqCableScanAt",diag_tickTime+0.5];
        private _near = nearestObjects [positionCameraToWorld [0,0,0],["ACME_TempusPro","ACME_TempusLS"],20];
        missionNamespace setVariable ["ACME_eqCableDevices",_near select [0,8]];
    };
    {
        private _device = _x;
        if (isNull _device || {isObjectHidden _device}) then {continue;};
        {
            if (count _desired >= 16) exitWith {};
            _x params ["_kind","_target","_patient"];
            private _from = [_device,_kind] call ACME_fnc_equipmentCableAnchor;
            private _to = [_target,_kind,_patient] call ACME_fnc_equipmentCableAnchor;
            private _span = _from distance _to;
            if (_span > 0.05 && {_span < 8}) then {
                _desired pushBack [format ["%1:%2:%3",netId _device,_kind,netId _target],_from,_to,_span];
            };
        } forEach ([_device] call ACME_fnc_equipmentCableSpecs);
    } forEach (missionNamespace getVariable ["ACME_eqCableDevices",[]]);
};
private _destroy = {
    params ["_fromHelper","_toHelper","_rope"];
    if (!isNull _rope) then {ropeDestroy _rope;};
    if (!isNull _fromHelper) then {deleteVehicle _fromHelper;};
    if (!isNull _toHelper) then {deleteVehicle _toHelper;};
};
private _want = _desired apply {_x select 0};
{
    if !(_x in _want) then {
        (_cache get _x) call _destroy;
        _cache deleteAt _x;
    };
} forEach keys _cache;
{
    _x params ["_key","_from","_to","_span"];
    private _record = _cache getOrDefault [_key,[objNull,objNull,objNull,0]];
    _record params ["_fromHelper","_toHelper","_rope","_length",["_oldFrom",[]],["_oldTo",[]]];
    if (!isNull _fromHelper && {!isNull _toHelper} && {!isNull _rope}) then {
        if (_oldFrom distance _from > 0.002) then {_fromHelper setPosWorld _from;_record set [4,_from];};
        if (_oldTo distance _to > 0.002) then {_toHelper setPosWorld _to;_record set [5,_to];};
        if (_length < _span || {_length > _span+0.8}) then {
            _length = _span + 0.2;
            ropeUnwind [_rope,3,_length];
            _record set [3,_length];
        };
        continue;
    };
    if (diag_tickTime < (missionNamespace getVariable ["ACME_eqCableRetryAt",0])) then {continue;};
    _record call _destroy;
    _fromHelper = "ace_fastroping_helper" createVehicleLocal (ASLToAGL _from);
    _toHelper = "ace_fastroping_helper" createVehicleLocal (ASLToAGL _to);
    if (!isNull _fromHelper && {!isNull _toHelper}) then {
        {
            _x allowDamage false;
            _x hideObject true;
            _x enableRopeAttach true;
        } forEach [_fromHelper,_toHelper];
        _fromHelper disableCollisionWith _toHelper;
        _fromHelper setPosWorld _from;
        _toHelper setPosWorld _to;
        _length = _span + 0.2;
        _rope = ropeCreate [_fromHelper,[0,0,0],_toHelper,[0,0,0],_length,[],[],"ace_refuel_fuelHose"];
    };
    _record = [_fromHelper,_toHelper,_rope,_length,_from,_to];
    if (isNull _rope) then {
        _record call _destroy;
        _cache deleteAt _key;
        missionNamespace setVariable ["ACME_eqCableRetryAt",diag_tickTime+2];
    } else {
        _cache set [_key,_record];
    };
} forEach _desired;
missionNamespace setVariable ["ACME_eqCableCache",_cache];
