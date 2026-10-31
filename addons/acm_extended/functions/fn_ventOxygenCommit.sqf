/* Owner authorization is restricted to the oxygen control; no other device choice is mutated. */
params [["_patient",objNull,[objNull]],["_action","",[""]],["_medic",objNull,[objNull]],
    ["_value",21,[0]],["_source",objNull,[objNull]],["_custody","",[""]],["_epoch",-1,[0]],["_expectedSession","",[""]],["_command",0,[0]]];
if (isNull _patient || {!local _patient} || {isNull _medic}) exitWith {false};
if (_epoch!=([_patient] call ACME_fnc_clinicalEpoch)
    || {_custody==""} || {_custody!=(_patient getVariable ["ACME_vent_custodyId",""])}
    || {!(_patient getVariable ["ACME_vent_onPatient",false])}
    || {_patient getVariable ["ACME_vent_recovering",false]}
    || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
    || {!([_medic,"ventilator",true] call ACME_fnc_procedureAllowed)}
    || {!([_medic,_patient] call ACME_fnc_ventRecoveryNear)}) exitWith {false};
if (_command<1 || {!finite _command} || {floor _command!=_command}) exitWith {false};
private _commands=_patient getVariable ["ACME_vent_o2Commands",createHashMap];
private _key=netId _medic;
if (_command<=(_commands getOrDefault [_key,0])) exitWith {false};
_commands set [_key,_command];
_patient setVariable ["ACME_vent_o2Commands",_commands,true];
if (_expectedSession!=(_patient getVariable ["ACME_vent_o2Session",""])) exitWith {false};
if (_action=="fio2") exitWith {
    if (!finite _value || {!(([_patient] call ACME_fnc_ventOxygenState) select 1)}) exitWith {false};
    [_patient,"ACME_vent_fio2",(round _value) max 21 min 95] call ACME_fnc_setVarNet;
    true
};
if (_action=="detach") exitWith {[_patient] call ACME_fnc_ventOxygenClear;true};
if (_action!="attach" || {isNull _source}
    || {!(_source in ([_medic,_patient] call ACME_fnc_treatmentSupplyOrder))}) exitWith {false};
// Repeated attach never discards prepaid gas or opens a second draw worker.
if ((_patient getVariable ["ACME_vent_o2Session",""])!="") exitWith {false};
private _serial=(_patient getVariable ["ACME_vent_o2Serial",0])+1;
_patient setVariable ["ACME_vent_o2Serial",_serial,true];
private _session=format ["%1:%2:%3:%4",netId _patient,_custody,_epoch,_serial];
_patient setVariable ["ACME_vent_o2Session",_session,true];
_patient setVariable ["ACME_vent_o2Source",_source,true];
_patient setVariable ["ACME_vent_o2Medic",_medic,true];
_patient setVariable ["ACME_vent_o2Custody",_custody,true];
_patient setVariable ["ACME_vent_o2Epoch",_epoch,true];
_patient setVariable ["ACME_vent_o2Sequence",0,true];
_patient setVariable ["ACME_vent_o2Credit",0,true];
_patient setVariable ["ACME_vent_o2Status","VERIFYING",true];
_patient setVariable ["ACME_vent_o2VerifiedUntil",-1,true];
_patient setVariable ["ACME_vent_o2ReserveUnits",0,true];
_patient setVariable ["ACME_vent_o2Pending",[],true];
[_patient] call ACME_fnc_ventOxygenTick;
true
