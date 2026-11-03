/* Called after the existing native ventilator custody transaction succeeds. No extra inventory debit. */
params ["_patient",["_replace",false]];
if (!isServer || {isNull _patient}) exitWith {};
private _old=_patient getVariable ["ACME_eq_vent",objNull];
if (_replace && {!isNull _old}) then {deleteVehicle _old;};
if (!isServer || {isNull _patient} || {!isNull (_patient getVariable ["ACME_eq_vent",objNull])}) exitWith {};
private _pose=[_patient,"vent"] call ACME_fnc_equipmentPose;
if (_pose isEqualTo []) exitWith {};
private _oxygen=(_patient getVariable ["ACME_vent_o2Session",""])!="";
private _class=["ACME_VentwaySparrow_Circuit","ACME_VentwaySparrow_O2Circuit"] select _oxygen;
private _o=createVehicle [_class,ASLToAGL (_pose select 0),[],0,"CAN_COLLIDE"];
if (isNull _o) exitWith {};
[_o,_pose] call ACME_fnc_equipmentSeat;
_o setVariable ["ACME_eq_oxygen",_oxygen,true];
_o setVariable ["ACME_eq_kind","vent",true];_o setVariable ["ACME_eq_patient",_patient,true];
_patient setVariable ["ACME_eq_vent",_o,true];
private _devices=missionNamespace getVariable ["ACME_eqDevices",[]];_devices pushBackUnique _o;missionNamespace setVariable ["ACME_eqDevices",_devices];
