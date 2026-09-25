/* Acknowledged item transfer. An acknowledged return enters finalization before another request can act. */
params ["_op", "_id", "_medic", "_ok", ["_settings", []]];
if (!isServer) exitWith {};
_settings = +_settings;
private _records = missionNamespace getVariable ["ACME_vent_custody", createHashMap];
private _r = _records getOrDefault [_id, createHashMap];
if (count _r == 0) exitWith {};
private _patient = _r get "patient";
if (_op == "take") exitWith {
    if ((_r get "phase") != "taking" || {_medic isNotEqualTo (_r get "supplier")}) exitWith {};
    if (!_ok) exitWith {
        if (!isNull _patient && {(_patient getVariable ["ACME_vent_custodyId", ""]) == _id}) then {_patient setVariable ["ACME_vent_custodyId", "", true];};
        _records deleteAt _id;
        ["ACME_ventCustodyNotice", [_medic, _patient, false], _medic] call CBA_fnc_targetEvent;
    };
    _r set ["recoveryOperator", _medic];
    _r set ["recoveryOperatorUID", getPlayerUID _medic];
    private _originIndex = _settings findIf {(_x param [0, ""]) == "ACME_supplyOrigin"};
    if (_originIndex >= 0) then {
        private _origin = (_settings select _originIndex) select 1;
        _r set ["supplyOrigin", _origin];
        _r set ["supplier", _origin select 0];
        _r set ["supplierUID", getPlayerUID (_origin select 0)];
        _settings deleteAt _originIndex;
    };
    _r set ["settings", _settings];
    _r set ["phase", "attached"];
    if (!isNull _patient) then {
        _patient setVariable ["ACME_vent_supplier", _r get "supplier", true];
        _patient setVariable ["ACME_vent_supplierUID", _r get "supplierUID", true];
        _patient setVariable ["ACME_vent_operator", _medic, true];
        _patient setVariable ["ACME_vent_onPatient", true, true];
        _patient setVariable ["ACME_vent_recovering", false, true];
        private _fields = [] call ACME_fnc_ventDeviceFields;
        {_patient setVariable [_x, nil, true];} forEach _fields;
        {if ((_x select 0) in _fields) then {_patient setVariable [_x select 0, _x select 1, true];};} forEach _settings;
        _patient setVariable ["ACME_vent_iface", "INVASIVE", true];
        _patient setVariable ["ACME_vent_circuit", true, true];
        _patient setVariable ["ACME_vent_configured", false, true];
        _patient setVariable ["ACME_vent_connected", false, true];
        _patient setVariable ["ACME_vent_booted", false, true];
        _patient setVariable ["ACME_vent_powerOn", false, true];
        _patient setVariable ["ACME_vent_hasBooted", false, true];
        _medic setVariable ["ACME_vent_devicePatient", objNull, true];
    };
    ["ACME_ventCustodyNotice", [_medic, _patient, true], _medic] call CBA_fnc_targetEvent;
    if (!isNull _patient) then {["ACME_ventPatientEnroll", [_patient], _patient] call CBA_fnc_targetEvent;};
    [] call ACME_fnc_ventCustodyTick;
};
if (_op == "give" && {_ok}) then {
    if ((_r get "phase") != "returning" || {_medic isNotEqualTo (_r getOrDefault ["recipient", objNull])}) exitWith {};
    _r set ["phase", "finalizing"];
    _r set ["lastSent", -100];
    [] call ACME_fnc_ventCustodyTick;
};
