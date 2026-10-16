/* Provider asks the casualty owner to attach/detach a real supply or change FiO2 only. */
params [["_patient",objNull,[objNull]],["_action","attach",[""]],["_medic",objNull,[objNull]],["_value",21,[0]]];
if (isNull _patient || {isNull _medic} || {!local _medic}) exitWith {false};
private _source=if (_action=="attach") then {[_medic,_patient] call ACME_fnc_ventOxygenSource} else {objNull};
private _command=(_medic getVariable ["ACME_vent_o2CommandSerial",0])+1;
_medic setVariable ["ACME_vent_o2CommandSerial",_command,true];
[_patient,"ventOxygen",[_patient,_action,_medic,_value,_source,
    _patient getVariable ["ACME_vent_custodyId",""],[_patient] call ACME_fnc_clinicalEpoch,
    _patient getVariable ["ACME_vent_o2Session",""],_command]] call ACME_fnc_ownerDispatch;
true
