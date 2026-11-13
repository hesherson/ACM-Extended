/* Called after the existing native ventilator custody transaction succeeds. No extra inventory debit. */
params ["_patient",["_replace",false]];
if (!isServer || {isNull _patient}) exitWith {};
private _old=_patient getVariable ["ACME_eq_vent",objNull];
private _durable=if (_replace && {!isNull _old}) then {_old getVariable ["ACME_persistenceId",""]} else {""};
if (!_replace && {!isNull _old}) exitWith {};
private _pose=[_patient,"vent"] call ACME_fnc_equipmentPose;
if (_pose isEqualTo []) exitWith {};
private _oxygen=(_patient getVariable ["ACME_vent_o2Session",""])!="";
private _class=["ACME_VentwaySparrow_Circuit","ACME_VentwaySparrow_O2Circuit"] select _oxygen;
private _o=createVehicle [_class,ASLToAGL (_pose select 0),[],0,"CAN_COLLIDE"];
if (isNull _o) exitWith {};
// Retain the existing representation if allocation/surface lookup fails.
// deleteVehicle becomes objNull on the next frame. Transfer our own binding
// explicitly before deletion so the old object cannot block the replacement.
if (_durable!="") then {
    private _bindings=missionNamespace getVariable ["ACME_clinicalObjectBindings",createHashMap];
    if ((_bindings getOrDefault [_durable,objNull]) isEqualTo _old) then {
        _bindings set [_durable,objNull];
        missionNamespace setVariable ["ACME_clinicalObjectBindings",_bindings];
        _old setVariable ["ACME_persistenceId","",true];
    };
};
if (_durable!="") then {
    ["bind",_o,_durable] call ACME_fnc_clinicalObjectRef;
    private _import=missionNamespace getVariable ["ACME_eqWorldImport",[]];
    if (_import isNotEqualTo []) then {
        private _at=((_import select 0) select 1) findIf {(_x select 0)==_durable};
        if (_at>=0) then {(_import select 1) set [_at,_o];};
        missionNamespace setVariable ["ACME_eqWorldImport",_import];
    };
};
if (isNull _old) then {
    [_o,_pose,_patient getVariable ["ACME_vent_operator",objNull]] call ACME_fnc_equipmentSeat;
} else {
    _o setVectorDirAndUp [vectorDir _old,vectorUp _old];
    _o setPosWorld getPosWorld _old;
    deleteVehicle _old;
};
_o setVariable ["ACME_eq_oxygen",_oxygen,true];
_o setVariable ["ACME_eq_kind","vent",true];_o setVariable ["ACME_eq_patient",_patient,true];
_patient setVariable ["ACME_eq_vent",_o,true];
_o hideObjectGlobal (!isNull objectParent _patient);
private _devices=missionNamespace getVariable ["ACME_eqDevices",[]];_devices pushBackUnique _o;missionNamespace setVariable ["ACME_eqDevices",_devices];
