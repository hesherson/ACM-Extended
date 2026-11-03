/* Trusted server startup API, never an RPC. One complete import per mission.
 * Restore clinical state, stable object bindings and native cargo FIRST.
 * No inventory grant or resumed therapy is funded here. */
params ["_save"];
if (canSuspend) exitWith {private _result = [false,[]];isNil {_result = [_save] call ACME_fnc_equipmentWorldRestore;};_result};
if (!isServer || {isRemoteExecuted} || {!([_save] call ACME_fnc_equipmentWorldSchema)}
    || {!(call ACME_fnc_persistenceJournalsReady)}
    || {count (missionNamespace getVariable ["ACME_eqPending",createHashMap]) > 0}) exitWith {[false,[]]};
private _previous = missionNamespace getVariable ["ACME_eqWorldImport",[]];
if (_previous isNotEqualTo []) exitWith {
    if ((_previous select 0) isNotEqualTo _save) exitWith {[false,[]]};
    private _objects = _previous select 1;
    private _valid = true;
    {if (isNull _x || {(_x getVariable ["ACME_persistenceId",""]) != (((_save select 1) select _forEachIndex) select 0)}) exitWith {_valid = false;};} forEach _objects;
    if (!_valid) exitWith {[false,[]]};
    [true,+_objects]
};
// Refuse loading over a live world. This also protects unbound existing devices.
if (((missionNamespace getVariable ["ACME_eqDevices",[]]) findIf {!isNull _x}) >= 0) exitWith {[false,[]]};
private _rows = _save select 1; private _resolved = []; private _ok = true;
// The caller can reuse/mutate its own array after return without changing the import journal.
private _copy = {params ["_value"];if (_value isEqualType []) then {_value apply {[_x] call _copy}} else {_value}};
_save = [_save] call _copy; _rows = _save select 1;
private _bindings = missionNamespace getVariable ["ACME_clinicalObjectBindings",createHashMap];
{
    _x params ["_id","_kind","","","","","_patientRef","","_linkRef","_custody"];
    if (!isNull (_bindings getOrDefault [_id,objNull])) exitWith {_ok = false;};
    private _patient = ["decode",_patientRef] call ACME_fnc_clinicalObjectRef;
    if ((_patientRef select 2) != "" && {isNull _patient}) exitWith {_ok = false;};
    if (!isNull _patient && {!(_patient isKindOf "CAManBase")}) exitWith {_ok = false;};
    if (!isNull _patient && {!isNull (_patient getVariable ["ACME_eq_"+_kind,objNull])}) exitWith {_ok = false;};
    private _link = objNull; private _linkIndex = -1;
    if ((_linkRef select 2) != "") then {
        _linkIndex = _rows findIf {(_x select 0) == (_linkRef select 2) && {(_x select 1) == "pro"}};
        if (_linkIndex < 0) then {_link = ["decode",_linkRef] call ACME_fnc_clinicalObjectRef;};
        if (_linkIndex < 0 && {isNull _link}) then {_ok = false;};
        if (_linkIndex < 0 && {!isNull _link} && {!(_link isKindOf "ACME_TempusPro")}) then {_ok = false;};
    };
    private _supplier = objNull; private _origin = objNull; private _recovery = objNull;
    if (_kind == "vent") then {
        _supplier = ["decode",_custody select 0] call ACME_fnc_clinicalObjectRef;
        _origin = ["decode",_custody select 2] call ACME_fnc_clinicalObjectRef;
        _recovery = ["decode",_custody select 3] call ACME_fnc_clinicalObjectRef;
        if (!(_patient getVariable ["ACME_vent_onPatient",false])
            || {_patient getVariable ["ACME_vent_recovering",false]}
            || {(_patient getVariable ["ACME_vent_custodyId",""]) in (missionNamespace getVariable ["ACME_vent_custody",createHashMap])}
            || {("world:"+_id) in (missionNamespace getVariable ["ACME_vent_custody",createHashMap])}
            || {((_custody select 0) select 2) != "" && {isNull _supplier}}
            || {((_custody select 2) select 2) != "" && {isNull _origin}}
            || {((_custody select 3) select 2) != "" && {isNull _recovery}}) then {_ok = false;};
    };
    if (!_ok) exitWith {};
    _resolved pushBack [_patient,_link,_linkIndex,_supplier,_origin,_recovery];
} forEach _rows;
if (!_ok) exitWith {[false,[]]};
private _objects = [];
{
    _x params ["","_kind","_pos","_dir","_up"];
    private _class = switch (_kind) do {
        case "pro": {"ACME_TempusPro"}; case "ls": {"ACME_TempusLS"}; case "accu": {"ACME_AccuvacRescue"};
        default {"ACME_VentwaySparrow_Circuit"};
    };
    private _o = createVehicle [_class,ASLToAGL _pos,[],0,"CAN_COLLIDE"];
    if (isNull _o) exitWith {_ok = false;};
    _objects pushBack _o;
    _o setVectorDirAndUp [_dir,_up]; _o setPosASL _pos;
} forEach _rows;
if (!_ok) exitWith {{deleteVehicle _x;} forEach _objects;[false,[]]};
// All allocation succeeded. Publish bindings and restart only observation feeds.
{
    _x params ["_id","_kind","","","","_manual","","_state"];
    private _o = _objects select _forEachIndex;
    (_resolved select _forEachIndex) params ["_patient","_link","_linkIndex","_supplier","_origin","_recovery"];
    ["bind",_o,_id] call ACME_fnc_clinicalObjectRef;
    _o setVariable ["ACME_eq_kind",_kind,true]; _o setVariable ["ACME_eq_patient",_patient,true];
    _o setVariable ["ACME_eq_manual",_manual,true];
    if (!isNull _patient) then {_patient setVariable ["ACME_eq_"+_kind,_o,true];};
    if (_kind in ["pro","ls"]) then {
        private _prefix = ["acme_tempus","acme_tempusls"] select (_kind == "ls");
        _o setVariable [_prefix+"_pw",[_state select 0,CBA_missionTime,false],true];
        _o setVariable [_prefix+"_pat",_patient,true];
        _o setVariable [_prefix+"_v",[],true]; _o setVariable [_prefix+"_st","",true];
        if (_kind == "pro") then {
            _o setVariable ["acme_tempus_sensors",+(_state select 1),true];
            _o setVariable ["acme_tempus_nibp",-1,true];
        } else {
            [_o] call ACME_fnc_tempusLsChargeClear;
            _o setVariable ["acme_tempusls_pads",_state select 2,true]; _o setVariable ["acme_tempusls_ecg",_state select 3,true];
            _o setVariable ["acme_tempusls_pace",[false,70,0,false],true];
            _o setVariable ["acme_tempusls_metro",[false,""],true];
        };
    };
    if (_kind == "vent") then {
        private _custody = _x select 9;
        private _ventId = "world:"+_id;
        private _settings = [];
        {if (!isNil {_patient getVariable _x}) then {_settings pushBack [_x,_patient getVariable _x];};} forEach (call ACME_fnc_ventDeviceFields);
        private _records = missionNamespace getVariable ["ACME_vent_custody",createHashMap];
        private _record = createHashMapFromArray [["patient",_patient],["supplier",_supplier],["supplierUID",_custody select 1],
            ["phase","attached"],["settings",_settings],["lastSent",-100],["lastPos",getPosASL _patient],
            ["lastVehicle",objectParent _patient],["deleted",false]];
        if (!isNull _origin) then {_record set ["supplyOrigin",[_supplier,_origin]];};
        _record set ["recoveryOperator",_recovery]; _record set ["recoveryOperatorUID",_custody select 4];
        _records set [_ventId,_record]; missionNamespace setVariable ["ACME_vent_custody",_records];
        _patient setVariable ["ACME_vent_custodyId",_ventId,true];
        _patient setVariable ["ACME_vent_supplier",_supplier,true]; _patient setVariable ["ACME_vent_supplierUID",_custody select 1,true];
        _o setVariable ["ACME_eq_oxygen",false,true];
        if (isNil "ACME_vent_serverPatients") then {ACME_vent_serverPatients = [];};
        ACME_vent_serverPatients pushBackUnique _patient;
        if ((missionNamespace getVariable ["ACME_vent_custodyPFH",-1]) < 0) then {
            missionNamespace setVariable ["ACME_vent_custodyPFH",[{call ACME_fnc_ventCustodyTick;},0.25,[]] call CBA_fnc_addPerFrameHandler];
        };
    };
} forEach _rows;
missionNamespace setVariable ["ACME_eqDevices",_objects];
missionNamespace setVariable ["ACME_eqWorldImport",[_save,+_objects]];
{
    private _kind = (_rows select _forEachIndex) select 1;
    (_resolved select _forEachIndex) params ["_patient","_link","_linkIndex"];
    if (_kind == "ls") then {
        if (_linkIndex >= 0) then {_link = _objects select _linkIndex;};
        if (!isNull _link && {_x distance _link <= 10}
            && {isNull _patient || {(_link getVariable ["acme_tempus_pat",objNull]) isEqualTo _patient}}) then {
            _x setVariable ["acme_tempusls_link",_link,true];
        };
    };
    if (_kind in ["pro","ls"] && {!isNull _patient}) then {
        [_x,_patient] remoteExecCall [["ACME_fnc_tempusFeed","ACME_fnc_tempusLsFeed"] select (_kind == "ls"),_patient];
    };
} forEach _objects;
[true,+_objects]
