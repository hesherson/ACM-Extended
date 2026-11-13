/* Client-local thin ropes follow each model's rear ports and the patient's animated anchor. */
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
            private _span = (_device modelToWorldVisualWorld _from) distance (_target modelToWorldVisualWorld _to);
            if (_span > 0.05 && {_span < 8}) then {
                _desired pushBack [format ["%1:%2:%3",netId _device,_kind,netId _target],_device,_from,_target,_to,_span];
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
    _x params ["_key","_device","_from","_target","_to","_span"];
    private _length = _span + 0.45 + _span*0.16;
    private _record = _cache getOrDefault [_key,[objNull,objNull,objNull,0]];
    _record params ["_fromHelper","_toHelper","_rope","_oldLength",["_oldTo",[]]];
    if (!isNull _fromHelper && {!isNull _toHelper} && {!isNull _rope}) then {
        if (_oldTo distance _to > 0.015) then {
            _toHelper attachTo [_target,_to];
            _record set [4,_to];
        };
        if (_oldLength < _span + 0.2 || {abs (_oldLength-_length) > 0.25}) then {
            ropeUnwind [_rope,3,_length];
            _record set [3,_length];
        };
        continue;
    };
    if (diag_tickTime < (missionNamespace getVariable ["ACME_eqCableRetryAt",0])) then {continue;};
    _record call _destroy;
    _fromHelper = "ace_fastroping_helper" createVehicleLocal (_device modelToWorld _from);
    _toHelper = "ace_fastroping_helper" createVehicleLocal (_target modelToWorld _to);
    if (!isNull _fromHelper && {!isNull _toHelper}) then {
        {
            _x allowDamage false;
            _x hideObject true;
            _x enableRopeAttach true;
            _x disableCollisionWith _device;
            _x disableCollisionWith _target;
        } forEach [_fromHelper,_toHelper];
        _fromHelper disableCollisionWith _toHelper;
        _fromHelper attachTo [_device,_from];
        _toHelper attachTo [_target,_to];
        _rope = ropeCreate [_fromHelper,[0,0,0],_toHelper,[0,0,0],_length,[],[],"ACME_TempusCable",40];
    };
    _record = [_fromHelper,_toHelper,_rope,_length,_to];
    if (isNull _rope) then {
        _record call _destroy;
        _cache deleteAt _key;
        missionNamespace setVariable ["ACME_eqCableRetryAt",diag_tickTime+2];
    } else {
        _cache set [_key,_record];
    };
} forEach _desired;
missionNamespace setVariable ["ACME_eqCableCache",_cache];
