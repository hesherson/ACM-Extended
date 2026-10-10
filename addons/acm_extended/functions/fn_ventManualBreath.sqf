// Request one operator-triggered ventilator breath. All durable/physiological mutation is casualty-owner-local.
private _patient = uiNamespace getVariable ["ACME_vent_target", objNull];
if (isNull _patient) exitWith {["No patient connected.", 1.5] call ace_common_fnc_displayTextStructured;};

private _serial = (uiNamespace getVariable ["ACME_vent_manualRequestSerial", 0]) + 1;
uiNamespace setVariable ["ACME_vent_manualRequestSerial", _serial];
private _id = format ["ventManual:%1:%2:%3", clientOwner, diag_tickTime, _serial];
private _custody = _patient getVariable ["ACME_vent_custodyId", ""];
if ((_patient getVariable ["ACME_vent_nivMask", false] || {[_patient] call ACME_fnc_ventMaskSelected})) exitWith {
    ["Mask CPAP requires spontaneous breathing; manual breaths need a secured airway.", 2] call ace_common_fnc_displayTextStructured;
};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;

if (missionNamespace getVariable ["ACME_vent_simpleMode", false]) exitWith {
    private _episode = (_patient getVariable ["ACME_vent_simpleEpisode", [false, 0]]) select 1;
    // The owner validates epoch/custody/episode/id. No remote mission-clock timestamp is required.
    ["ACME_ventSimpleManualBreath", [_patient, ACE_player, _custody, _epoch, 0, _id, _episode], _patient] call CBA_fnc_targetEvent;
};

private _configured = _patient getVariable ["ACME_vent_configured", false];
private _connected = _patient getVariable ["ACME_vent_connected", false];
if (!_configured || {!_connected}) exitWith {["Not connected to a patient.", 1.5] call ace_common_fnc_displayTextStructured;};
if ((_patient getVariable ["ACME_vent_iface", ""]) != "INVASIVE") exitWith {
    ["Manual breath requires an INVASIVE interface.", 2] call ace_common_fnc_displayTextStructured;
};
private _securedAirway = (_patient getVariable ["ACME_ETT_Inserted", false])
    || {((_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) isEqualTo "SGA")}
    || {_patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false]};
if (!_securedAirway) exitWith {["No secured airway on this casualty.", 1.5] call ace_common_fnc_displayTextStructured;};

[_patient, "ventManualBreath", [_patient, ACE_player, _custody, _epoch, _id]] call ACME_fnc_ownerDispatch;
