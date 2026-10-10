/* Patient owner releases clinical support. The identity guard rejects delayed old returns. */
params [["_patient", objNull, [objNull]], ["_id", "", [""]], ["_final", false, [true]]];
if (isNull _patient || {!local _patient}) exitWith {};
if ((_patient getVariable ["ACME_vent_custodyId", ""]) != _id) exitWith {};
// Setup flags precede driving, so fn_ventDriveTick.sqf cannot restart the circuit.
{[_patient, _x, false] call ACME_fnc_setVarNet;} forEach ["ACME_vent_circuit", "ACME_vent_configured", "ACME_vent_connected", "ACME_vent_cpapTherapy"];
{[_patient, _x, 0] call ACME_fnc_setVarNet;} forEach ["ACME_vent_measRR", "ACME_vent_breathAcc", "ACME_vent_mvAdequacy", "ACME_vent_effectiveRR", "ACME_vent_alarmPrio", "ACME_vent_alarmSilencedUntil"];
[_patient, "ACME_vent_breathTimes", []] call ACME_fnc_setVarNet;
_patient setVariable ["ACME_vent_simpleManualVolumes", [], false];
_patient setVariable ["ACME_vent_manualBreathTimes", [], false];
_patient setVariable ["ACME_vent_manualReceipts", [], false];
_patient setVariable ["ACME_vent_simpleManualReceipts", [], false];
[_patient, "ACME_vent_alarms", []] call ACME_fnc_setVarNet;
[_patient, "ACME_vent_driveT0", -1] call ACME_fnc_setVarNet;
[_patient, "ACME_vent_rrDrive", -1] call ACME_fnc_setVarNet;
if ((_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient) then {
    [_patient, [["bvmProvider", objNull], ["bvmConnectedOxygen", false]], true] call ACM_breathing_fnc_setRuntimeState;
};
[_patient, "ACME_vent_driving", false] call ACME_fnc_setVarNet;
// Let the server audio registry retain this patient only as long as shutdown/source cleanup still needs it.
["ACME_ventServerTrack", [_patient, false]] call CBA_fnc_serverEvent;
if (_final) then {
    {_patient setVariable [_x, nil, true];} forEach ([] call ACME_fnc_ventDeviceFields);
    [_patient, "ACME_vent_powerOn", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_hasBooted", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_onPatient", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_nivMask", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_operator", objNull] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_mountVeh", objNull] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_recovering", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_custodyId", ""] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_supplier", objNull] call ACME_fnc_setVarNet;
    [_patient, "ACME_vent_supplierUID", ""] call ACME_fnc_setVarNet;
};
