/* Registered on every machine. The server owns device allocation; unit owners own inventory. */
if (missionNamespace getVariable ["ACME_vent_custodyInitialized", false]) exitWith {};
missionNamespace setVariable ["ACME_vent_custodyInitialized", true];
["ACME_ventManualAccepted", {
    params ["_patient", "_medic", "_custody"];
    if (hasInterface && {_medic isEqualTo ACE_player}
        && {(uiNamespace getVariable ["ACME_vent_target", objNull]) isEqualTo _patient}
        && {_custody == (_patient getVariable ["ACME_vent_custodyId", ""])}) then {
        uiNamespace setVariable ["ACME_vent_manualGaugeT", diag_tickTime];
    };
}] call CBA_fnc_addEventHandler;
["ACME_ventSimpleManualAccepted", {
    params ["_patient", "_medic", "_custody"];
    if (hasInterface && {_medic isEqualTo ACE_player}
        && {(uiNamespace getVariable ["ACME_vent_target", objNull]) isEqualTo _patient}
        && {_custody == (_patient getVariable ["ACME_vent_custodyId", ""])}) then {
        uiNamespace setVariable ["ACME_vent_manualGaugeT", diag_tickTime];
    };
}] call CBA_fnc_addEventHandler;
["ACME_ventSimpleManualBreath", {_this call ACME_fnc_ventSimpleManualBreath;}] call CBA_fnc_addEventHandler;
["ACME_ventInventory", {_this call ACME_fnc_ventInventoryLocal;}] call CBA_fnc_addEventHandler;
["ACME_ventPatientClear", {_this call ACME_fnc_ventPatientClear;}] call CBA_fnc_addEventHandler;
["ACME_ventPatientEnroll", {
    params ["_patient"];
    if (isNull _patient || {!local _patient}) exitWith {};
    // Device protocol metadata is needed even when corpse physiology is frozen.
    // Duplicate enrollments preserve the current episode; custody also fences old-device commands.
    private _simple = missionNamespace getVariable ["ACME_vent_simpleMode", false];
    private _episode = _patient getVariable ["ACME_vent_simpleEpisode", [!_simple, 0]];
    if !((_episode select 0) isEqualTo _simple) then {
        [_patient, "ACME_vent_simpleEpisode", [_simple, (_episode select 1) + 1]] call ACME_fnc_setVarNet;
    };
    if (alive _patient && {!isNil "ACME_circ_activePatients"}) then {ACME_circ_activePatients pushBackUnique _patient;};
}] call CBA_fnc_addEventHandler;
["ACME_ventCustodyNotice", {
    params ["_medic", "_patient", "_ok"];
    if (!hasInterface || {_medic isNotEqualTo ACE_player}) exitWith {};
    if (_ok) then {
        playSound "ACME_VentClick";
        ["Circuit connected. Open the ventilator and start it up.", 3] call ace_common_fnc_displayTextStructured;
        ["USER", "Patient circuit connected; awaiting setup"] call ACME_fnc_ventLogbookAdd;
        if (!isNull _patient) then {[_patient, "airway", "Airway connected to ventilator circuit", []] call ace_medical_treatment_fnc_addToLog;};
    } else {
        ["Ventilator connection could not complete. Check inventory, airway and range.", 3] call ace_common_fnc_displayTextStructured;
    };
}] call CBA_fnc_addEventHandler;
if (!isServer) exitWith {};
missionNamespace setVariable ["ACME_vent_custody", createHashMap];
missionNamespace setVariable ["ACME_vent_custodySerial", 0];
["ACME_ventCustodyRequest", {_this call ACME_fnc_ventCustodyRequest;}] call CBA_fnc_addEventHandler;
["ACME_ventCustodyAck", {_this call ACME_fnc_ventCustodyAck;}] call CBA_fnc_addEventHandler;
addMissionEventHandler ["EntityKilled", {
    params ["_unit"];
    if ((_unit getVariable ["ACME_vent_custodyId", ""]) != "") then {[] call ACME_fnc_ventCustodyTick;};
}];
addMissionEventHandler ["EntityDeleted", {
    params ["_unit"];
    private _records = missionNamespace getVariable ["ACME_vent_custody", createHashMap];
    {
        private _record = _records get _x;
        if ((_record getOrDefault ["recipient", objNull]) isEqualTo _unit) then {
            private _receipt = (_unit getVariable ["ACME_vent_inventoryReceipts", createHashMap]) getOrDefault [_x + ":give", []];
            if (!(_receipt isEqualTo []) && {_receipt select 0}) then {_record set ["phase", "finalizing"]; _record set ["lastSent", -100];};
        };
    } forEach (keys _records);
    private _r = _records getOrDefault [_unit getVariable ["ACME_vent_custodyId", ""], createHashMap];
    if (count _r > 0) then {
        _r set ["lastPos", getPosASL _unit];
        _r set ["lastVehicle", objectParent _unit];
        private _state = [];
        {if (!isNil {_unit getVariable _x}) then {_state pushBack [_x, _unit getVariable _x];};} forEach ([] call ACME_fnc_ventDeviceFields);
        if ((_r get "phase") != "taking") then {_r set ["settings", _state];};
        _r set ["deleted", true];
    };
}];
