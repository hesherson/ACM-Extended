/* Shared medical-menu and world-menu eligibility; sensor commits are serialized on the server. */
params ["_medic","_patient","_kind","_action",["_apply",false],["_device",objNull]];
if (isNull _medic || {isNull _patient} || {!alive _medic} || {!alive _patient}
    || {!(_medic isKindOf "CAManBase")} || {!(_patient isKindOf "CAManBase")}
    || {_medic distance _patient > 4} || {!isNull objectParent _patient}
    || {!isNull objectParent _medic} || {_medic getVariable ["ACE_isUnconscious",false]}
    || {_medic getVariable ["ACME_persistenceFrozen",false]} || {_patient getVariable ["ACME_persistenceFrozen",false]}
    || {!(_kind in ["pro","ls"])}) exitWith {false};
if (isRemoteExecuted && {!_apply}) exitWith {false};
if (_apply && {isRemoteExecuted && {!isServer || {remoteExecutedOwner != owner _medic}}}) exitWith {false};
private _ls = _kind == "ls";
private _prefix = ["acme_tempus","acme_tempusls"] select _ls;
private _class = ["ACME_TempusPro","ACME_TempusLS"] select _ls;
if (isNull _device) then {_device = _patient getVariable ["ACME_eq_"+_kind,objNull];};
if (_action isEqualTo "setup") exitWith {
    private _available = isNull _device && {([_medic,_class+"_Item"] call ACME_fnc_itemCount)>0};
    if (_available && {_apply} && {!isRemoteExecuted}) then {
        // The treatment action already ran its progress bar.
        [_medic,_patient,_kind] remoteExecCall ["ACME_fnc_equipmentRequest",2];
    };
    _available
};
if (isNull _device || {!(_device isKindOf _class)} || {_device distance _medic > 3.5}
    || {_device distance _patient > 6} || {_device getVariable ["ACME_eq_busy",false]}
    || {_device getVariable ["ACME_eq_restoreStaged",false]} || {isObjectHidden _device}
    || {(_device getVariable [_prefix+"_pat",objNull]) isNotEqualTo _patient}) exitWith {false};
if (_action isEqualTo "view") exitWith {
    if (_apply && {!isRemoteExecuted}) then {
        private _use = [ACME_fnc_tempusUse,ACME_fnc_tempusLsUse] select _ls;
        [_device] call _use;
    };
    true
};
if (_action isEqualTo "nibp") exitWith {
    private _allowed = !_ls && {(_device getVariable ["acme_tempus_sensors",[true,false,false,false,false]]) select 2}
        && {(_device getVariable ["acme_tempus_pw",[false]]) select 0};
    if (_allowed && {_apply}) then {
        if (isServer) then {_device setVariable ["ACME_eq_nibpRequest",CBA_missionTime,true];} else {
            [_medic,_patient,_kind,_action,true,_device] remoteExecCall ["ACME_fnc_equipmentMonitorAction",2];
        };
    };
    _allowed
};
if !(_action isEqualType [] && {count _action == 2} && {(_action select 0) isEqualType 0}
    && {(_action select 1) isEqualType false}) exitWith {false};
_action params ["_index","_attach"];
if !(_index in ([[0,1,2,3,4],[0,5]] select _ls)) exitWith {false};
private _sensors = +(_device getVariable ["acme_tempus_sensors",[true,false,false,false,false]]);
private _key = if (_index == 5) then {"acme_tempusls_pads"} else {"acme_tempusls_ecg"};
private _attached = if (_ls) then {_device getVariable [_key,_index==5]} else {_sensors select _index};
if (_attached == _attach) exitWith {false};
if (_apply) then {
    if (!isServer) then {
        [_medic,_patient,_kind,_action,true,_device] remoteExecCall ["ACME_fnc_equipmentMonitorAction",2];
    } else {
        if (_ls) then {
            _device setVariable [_key,_attach,true];
            if (_index == 5 && {!_attach}) then {
                [_device] call ACME_fnc_tempusLsChargeClear;
                _device setVariable ["acme_tempusls_pace",[false,70,0,false],true];
            };
        } else {
            _sensors set [_index,_attach];
            _device setVariable ["acme_tempus_sensors",_sensors,true];
        };
    };
};
true
