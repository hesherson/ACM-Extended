/* Medical and airway entry points share the same placement transaction. */
params ["_medic","_patient",["_onReady",[]],["_args",[]]];
if (isNull _medic || {isNull _patient} || {!alive _medic}
    || {_medic distance _patient > 4} || {!isNull objectParent _medic}
    || {!isNull objectParent _patient} || {_medic getVariable ["ACE_isUnconscious",false]}
    || {_patient getVariable ["ACME_persistenceFrozen",false]}
    || {_medic getVariable ["ACME_persistenceFrozen",false]}) exitWith {false};
private _deployed = [_medic,_patient] call ACME_fnc_equipmentAvailable;
private _supplier = objNull;
if (!_deployed && {isNull (_patient getVariable ["ACME_eq_accu",objNull])}) then {
    private _sources = [_medic,_patient] call ACME_fnc_treatmentSupplyOrder;
    private _index = _sources findIf {alive _x && {!(_x getVariable ["ACME_persistenceFrozen",false])}
        && {([_x,"ACM_ACCUVAC"] call ACME_fnc_itemCount) > 0}};
    if (_index >= 0) then {_supplier = _sources select _index;};
};
if (!_deployed && {isNull _supplier}) exitWith {false};
if (_onReady isEqualTo [] || {!local _medic}) exitWith {true};
private _request = (uiNamespace getVariable ["ACME_accuUseSerial",0]) + 1;
uiNamespace setVariable ["ACME_accuUseSerial",_request];
if (_deployed) exitWith {_args call _onReady; true};
[_supplier,_patient,"accu","setup",false,[],objNull,"",-1,_medic] remoteExecCall ["ACME_fnc_equipmentRequest",2];
[{
    params ["_medic","_patient","_request"];
    ([_medic,_patient] call ACME_fnc_equipmentAvailable)
        || {_request != (uiNamespace getVariable ["ACME_accuUseSerial",0])}
}, {
    params ["_medic","_patient","_request","_stamp","_epoch","_onReady","_args"];
    if (_request == (uiNamespace getVariable ["ACME_accuUseSerial",0])
        && {local _medic} && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious",false])}
        && {_medic distance _patient <= 4} && {([_medic] call ACME_fnc_equipmentTransferStamp) isEqualTo _stamp}
        && {([_patient] call ACME_fnc_clinicalEpoch) isEqualTo _epoch}) then {_args call _onReady;};
}, [_medic,_patient,_request,[_medic] call ACME_fnc_equipmentTransferStamp,
    [_patient] call ACME_fnc_clinicalEpoch,_onReady,_args],8,{
    params ["_medic","","_request"];
    if (local _medic && {_request == (uiNamespace getVariable ["ACME_accuUseSerial",0])}) then {
        ["ACCUVAC placement was not confirmed. Try again when the patient and equipment are in reach.",2]
            call ace_common_fnc_displayTextStructured;
    };
}] call CBA_fnc_waitUntilAndExecute;
true
