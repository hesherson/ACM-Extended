/* Server allocation lock. Concurrent providers cannot remove or return the same device twice. */
params [["_op", "", [""]], ["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_interface", "INVASIVE", [""]]];
if (!isServer || {isNull _patient} || {isNull _medic} || {!alive _medic}) exitWith {};
if !([_medic, _patient] call ACME_fnc_ventRecoveryNear) exitWith {};
private _records = missionNamespace getVariable ["ACME_vent_custody", createHashMap];
private _id = _patient getVariable ["ACME_vent_custodyId", ""];

// Airway removal is a forced recovery path. It must not be blocked by the ventilator procedure toggle because
// the patient can no longer support the mounted circuit. The medic removing the airway receives the device.
if (_op == "airwayLoss") exitWith {
    private _r = _records getOrDefault [_id, createHashMap];

    // Adopt a legacy/on-patient device exactly as manual recovery does, but preserve its current device settings.
    if (count _r == 0 && {_patient getVariable ["ACME_vent_onPatient", false]}) then {
        private _serial = (missionNamespace getVariable ["ACME_vent_custodySerial", 0]) + 1;
        missionNamespace setVariable ["ACME_vent_custodySerial", _serial];
        _id = format ["vent:%1:%2", netId _patient, _serial];

        private _settings = [];
        {
            if (!isNil {_patient getVariable _x}) then {
                _settings pushBack [_x, _patient getVariable _x];
            };
        } forEach ([] call ACME_fnc_ventDeviceFields);

        _r = createHashMapFromArray [
            ["patient", _patient],
            ["supplier", _patient getVariable ["ACME_vent_supplier", objNull]],
            ["supplierUID", _patient getVariable ["ACME_vent_supplierUID", ""]],
            ["phase", "attached"],
            ["settings", _settings],
            ["lastSent", -100],
            ["lastPos", getPosASL _patient],
            ["lastVehicle", objectParent _patient],
            ["deleted", false]
        ];
        _records set [_id, _r];
        _patient setVariable ["ACME_vent_custodyId", _id, true];
    };

    if (count _r == 0) exitWith {
        // No device ledger exists; ensure stale patient-side state cannot survive the airway removal.
        ["ACME_ventPatientClear", [_patient, _id, true], _patient] call CBA_fnc_targetEvent;
    };

    if ((_r getOrDefault ["phase", ""]) != "attached") exitWith {};

    _r set ["recipient", _medic];
    _r set ["recipientUID", getPlayerUID _medic];
    _r set ["phase", "returning"];
    _r set ["lastSent", -100];
    _patient setVariable ["ACME_vent_recovering", true, true];

    ["ACME_ventPatientClear", [_patient, _id, false], _patient] call CBA_fnc_targetEvent;

    if ((missionNamespace getVariable ["ACME_vent_custodyPFH", -1]) < 0) then {
        missionNamespace setVariable ["ACME_vent_custodyPFH", [{[] call ACME_fnc_ventCustodyTick;}, 0.25, []] call CBA_fnc_addPerFrameHandler];
    };
    [] call ACME_fnc_ventCustodyTick;
};

if (_op == "attach") exitWith {
    if !([_medic, "ventilator"] call ACME_fnc_procedureAllowed) exitWith {};
    if (!(_patient isKindOf "CAManBase")
        || {_patient getVariable ["ACME_vent_onPatient", false]}
        || {_id in _records}) exitWith {};
    private _airway = (_patient getVariable ["ACME_ETT_Inserted", false])
        || {(_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "SGA"}
        || {_patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false]};
    if !(_interface in ["INVASIVE", "MASK"]) exitWith {};
    if (_patient getVariable ["ACM_airway_RecoveryPosition_State", false]
        || {_patient getVariable ["ACME_vent_recovering", false]}) exitWith {};
    private _eligible = if (_interface == "MASK") then {[_patient] call ACME_fnc_ventNivEligible} else {_airway};
    if (!_eligible || {! (missionNamespace getVariable ["ACME_sys_vent", true])}) exitWith {};
    private _serial = (missionNamespace getVariable ["ACME_vent_custodySerial", 0]) + 1;
    missionNamespace setVariable ["ACME_vent_custodySerial", _serial];
    _id = format ["vent:%1:%2", netId _patient, _serial];
    private _r = createHashMapFromArray [
        ["patient", _patient], ["supplier", _medic], ["supplierUID", getPlayerUID _medic],
        ["phase", "taking"], ["lastSent", -100], ["settings", []], ["interface", _interface],
        ["lastPos", getPosASL _patient], ["lastVehicle", objectParent _patient], ["deleted", false]
    ];
    _records set [_id, _r];
    _patient setVariable ["ACME_vent_custodyId", _id, true];
    if ((missionNamespace getVariable ["ACME_vent_custodyPFH", -1]) < 0) then {
        missionNamespace setVariable ["ACME_vent_custodyPFH", [{[] call ACME_fnc_ventCustodyTick;}, 0.25, []] call CBA_fnc_addPerFrameHandler];
    };
    [] call ACME_fnc_ventCustodyTick;
};
if (_op == "return") then {
    if !([_medic, "ventilator", true] call ACME_fnc_procedureAllowed) exitWith {};
    private _r = _records getOrDefault [_id, createHashMap];
    // Legacy restored custody has no server record. Adopt only a physically marked device.
    if (count _r == 0 && {_patient getVariable ["ACME_vent_onPatient", false]}) then {
        private _serial = (missionNamespace getVariable ["ACME_vent_custodySerial", 0]) + 1;
        missionNamespace setVariable ["ACME_vent_custodySerial", _serial];
        _id = format ["vent:%1:%2", netId _patient, _serial];
        _r = createHashMapFromArray [["patient", _patient], ["supplier", _patient getVariable ["ACME_vent_supplier", objNull]], ["supplierUID", _patient getVariable ["ACME_vent_supplierUID", ""]], ["phase", "attached"], ["settings", []], ["lastSent", -100], ["lastPos", getPosASL _patient], ["lastVehicle", objectParent _patient], ["deleted", false]];
        _records set [_id, _r];
        _patient setVariable ["ACME_vent_custodyId", _id, true];
    };
    if (count _r == 0 || {(_r get "phase") != "attached"}) exitWith {};
    _r set ["recipient", _medic];
    _r set ["recipientUID", getPlayerUID _medic];
    _r set ["phase", "returning"];
    _r set ["lastSent", -100];
    _patient setVariable ["ACME_vent_recovering", true, true];
    ["ACME_ventPatientClear", [_patient, _id, false], _patient] call CBA_fnc_targetEvent;
    if ((missionNamespace getVariable ["ACME_vent_custodyPFH", -1]) < 0) then {
        missionNamespace setVariable ["ACME_vent_custodyPFH", [{[] call ACME_fnc_ventCustodyTick;}, 0.25, []] call CBA_fnc_addPerFrameHandler];
    };
    [] call ACME_fnc_ventCustodyTick;
};
