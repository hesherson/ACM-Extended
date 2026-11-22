private _deadline = diag_tickTime + 30;
waitUntil {
    sleep .1;
    missionNamespace getVariable ["ace_common_settingsInitFinished", false] || {diag_tickTime >= _deadline}
};

private _required = ["ACM_core", "ace_medical", "acme_sked_ace", "acme_talon", "acme_hpmk"];
private _missing = _required select {!isClass (configFile >> "CfgPatches" >> _x)};
if (_missing isNotEqualTo [] || {!(missionNamespace getVariable ["ace_common_settingsInitFinished", false])}) exitWith {
    ACMEQA_startError = format ["Load ACM Extended, ACE and CBA. Missing patches %1", _missing];
    publicVariable "ACMEQA_startError";
    diag_log format ["[ACME QA] STARTUP_FAIL %1", ACMEQA_startError];
};

ACMEQA_run = format ["%1-%2", systemTimeUTC, floor diag_tickTime];
ACMEQA_workload = ["ACMEQA_Workload", 0] call BIS_fnc_getParamValue;
ACMEQA_patients = [];
ACMEQA_chests = [];
ACMEQA_caseNames = call ACMEQA_fnc_cases;
missionNamespace setVariable ["acme_sked_debug", true, true];

private _spawnObject = {
    params ["_class", "_pos", ["_direction", 0]];
    if (!isClass (configFile >> "CfgVehicles" >> _class)) exitWith {
        diag_log format ["[ACME QA] MISSING_CLASS class=%1", _class];
        objNull
    };
    private _object = createVehicle [_class, _pos, [], 0, "CAN_COLLIDE"];
    if (!isNull _object) then {
        _object setDir _direction;
        _object setPosATL _pos;
    } else {
        diag_log format ["[ACME QA] SPAWN_FAIL class=%1", _class];
    };
    _object
};
private _createPatient = {
    params ["_group", "_pos", "_role"];
    private _patient = _group createUnit ["B_Soldier_F", _pos, [], 0, "CAN_COLLIDE"];
    if (isNull _patient) exitWith {objNull};
    _patient setPosATL _pos;
    _patient setDir 90;
    _patient setVehicleVarName format ["ACMEQA_%1", _role];
    removeAllWeapons _patient;
    removeBackpack _patient;
    {_patient disableAI _x;} forEach ["PATH", "TARGET", "AUTOTARGET"];
    _patient
};

ACMEQA_control = ["Land_CampingTable_small_F", [1530, 3598, 0]] call _spawnObject;
if (isNull ACMEQA_control) exitWith {
    ACMEQA_startError = "The QA table could not be created.";
    publicVariable "ACMEQA_startError";
};
private _stations = [["QA table", [1530, 3598, 0]]];
private _loadPatients = [];
if (ACMEQA_workload == 0) then {
    private _group = createGroup [west, true];
    {
        _x params ["_role", "_pos"];
        private _patient = [_group, _pos, _role] call _createPatient;
        if (!isNull _patient) then {ACMEQA_patients pushBack [_role, _patient];};
    } forEach [["treatment", [1530, 3609, 0]], ["transfer", [1540, 3609, 0]], ["pickup", [1542, 3610, 0]]];

    ["ACME_SKED_Open", [1542, 3608, 0], 90] call _spawnObject;
    ["ACME_Talon_Folded", [1546, 3610, 0], 90] call _spawnObject;
    ["ACME_SKED_Item", [1538, 3605, 0]] call _spawnObject;
    ["B_Truck_01_medical_F", [1559, 3617, 0], 90] call _spawnObject;

    {
        private _chest = _x call _spawnObject;
        if (!isNull _chest) then {ACMEQA_chests pushBack _chest;};
    } forEach [["ACME_MedicalChest", [1535, 3604, 0], 180],
        ["ACME_MedicalChest_02", [1524, 3603, 0], 180], ["ACME_MedicalChest_11", [1524, 3607, 0], 180]];
    private _supplies = ["Box_NATO_Ammo_F", [1536, 3605, 0], 180] call _spawnObject;
    if (!isNull _supplies) then {
        clearItemCargoGlobal _supplies;
        clearWeaponCargoGlobal _supplies;
        clearMagazineCargoGlobal _supplies;
        clearBackpackCargoGlobal _supplies;
        {
            _x params ["_item", "_count"];
            if (isClass (configFile >> "CfgWeapons" >> _item)) then {_supplies addItemCargoGlobal [_item, _count];};
            if (isClass (configFile >> "CfgMagazines" >> _item)) then {_supplies addMagazineCargoGlobal [_item, _count];};
        } forEach [["ACME_HPMK", 8], ["ACME_SKED_Item", 4], ["ACME_IV_16g", 12],
            ["ACE_fieldDressing", 40], ["ACE_tourniquet", 12], ["ACE_salineIV_500", 15],
            ["ACME_SalineFlush_10", 20], ["ACME_BloodCooler_CSWB2U", 4]];
    };
    _stations append [["Treatment", [1530, 3609, 0]], ["Transfer", [1540, 3609, 0]],
        ["Supplies", [1536, 3605, 0]], ["Hardigg test", [1524, 3606, 0]], ["Evacuation", [1559, 3617, 0]]];

    if ((["ACMEQA_Hatchet", 0] call BIS_fnc_getParamValue) == 1) then {
        private _types = "getNumber (_x >> 'scope') == 2 && {configName _x isKindOf 'vtx_H60_base'}" configClasses (configFile >> "CfgVehicles");
        private _typeNames = _types apply {configName _x};
        _typeNames sort true;
        if (_typeNames isEqualTo []) then {
            diag_log "[ACME QA] HATCHET_OPTIONAL_UNAVAILABLE";
        } else {
            [_typeNames select 0, [1581, 3628, 0], 90] call _spawnObject;
            _stations pushBack ["Hatchet seat test", [1581, 3628, 0]];
        };
    };
} else {
    // Clear the base Test Zone's demonstration AI before creating the fixed workload.
    {
        if (_x isKindOf "CAManBase" && {!isPlayer _x} && {!(_x in playableUnits)}) then {deleteVehicle _x;};
    } forEach allUnits;
    for "_row" from 0 to 3 do {
        private _group = createGroup [west, true];
        for "_column" from 0 to 5 do {
            private _role = format ["load_%1", _row * 6 + _column + 1];
            private _ai = [_group, [1583 + _column * 4, 3598 + _row * 5, 0], _role] call _createPatient;
            if (!isNull _ai) then {_loadPatients pushBack _ai;};
        };
    };
    private _unconscious = [0, 0, 1, 5, 10] param [ACMEQA_workload, 0];
    {[_x, "load"] call ACMEQA_fnc_preparePatient;} forEach (_loadPatients select [0, _unconscious]);
    _stations pushBack ["Performance AI", [1593, 3606, 0]];
    diag_log format ["[ACME QA] WORKLOAD run=%1 population=%2 requestedUnconscious=%3", ACMEQA_run, count _loadPatients, _unconscious];
};

{
    _x params ["_text", "_pos"];
    private _marker = createMarker [format ["ACMEQA_%1", _forEachIndex], _pos];
    _marker setMarkerTypeLocal "mil_dot";
    _marker setMarkerText _text;
} forEach _stations;

private _nearTable = {
    params ["_caller"];
    !isNull _caller && {alive _caller} && {isPlayer _caller} && {_caller distance ACMEQA_control <= 4}
};
missionNamespace setVariable ["ACMEQA_nearTable", _nearTable];
["ACMEQA_prepareAI", {
    params ["_caller"];
    if !([_caller] call ACMEQA_nearTable) exitWith {};
    {[_x select 1, _x select 0] call ACMEQA_fnc_preparePatient;} forEach ACMEQA_patients;
}] call CBA_fnc_addEventHandler;
["ACMEQA_mark", {
    params ["_caller", ["_index", -1, [0]], ["_passed", false, [true]]];
    if (!([_caller] call ACMEQA_nearTable) || {_index < 0} || {_index >= count ACMEQA_caseNames}
        || {_index != floor _index}) exitWith {};
    diag_log format ["[ACME QA] RESULT run=%1 case=%2 result=%3 role=%4 time=%5 state=%6", ACMEQA_run,
        ACMEQA_caseNames select _index select 0, ["FAIL", "PASS"] select _passed,
        vehicleVarName _caller, round serverTime, [_caller] call ACMEQA_fnc_snapshot];
}] call CBA_fnc_addEventHandler;
["ACMEQA_capture", {
    params ["_caller"];
    if ([_caller] call ACMEQA_nearTable) then {[120] call ACMEQA_fnc_capture;};
}] call CBA_fnc_addEventHandler;
["ACMEQA_curator", {
    params ["_caller"];
    if (!([_caller] call ACMEQA_nearTable) || {vehicleVarName _caller != "joe"}
        || {!isNull (getAssignedCuratorLogic _caller)}) exitWith {};
    if (isNil "ACMEQA_curator" || {isNull ACMEQA_curator}) then {
        private _group = createGroup [sideLogic, true];
        ACMEQA_curator = _group createUnit ["ModuleCurator_F", getPosATL ACMEQA_control, [], 0, "NONE"];
        ACMEQA_curator addCuratorAddons ["acme_sked", "acme_sked_ace"];
    };
    if (isNull getAssignedCuratorUnit ACMEQA_curator) then {_caller assignCurator ACMEQA_curator;};
}] call CBA_fnc_addEventHandler;

{publicVariable _x;} forEach ["ACMEQA_control", "ACMEQA_patients", "ACMEQA_chests", "ACMEQA_run", "ACMEQA_workload"];
ACMEQA_ready = true;
publicVariable "ACMEQA_ready";
diag_log format ["[ACME QA] READY run=%1 build=%2 world=%3 dedicated=%4 workload=%5 cases=%6 chests=%7 activeAI=%8",
    ACMEQA_run, missionNamespace getVariable ["ACME_buildBatch", "unknown"], worldName, isDedicated,
    ACMEQA_workload, count ACMEQA_patients, count ACMEQA_chests, count _loadPatients];

if ((["ACMEQA_AutoCapture", 0] call BIS_fnc_getParamValue) == 1) then {
    sleep 30;
    [120] call ACMEQA_fnc_capture;
};
