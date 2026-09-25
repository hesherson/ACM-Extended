// Release a casualty animation lease if and only if the caller still owns the same token.
params [["_patient", objNull, [objNull]], ["_token", "", [""]], ["_retire", true, [false]]];
if (isNull _patient || {_token == ""}) exitWith {};
if (!local _patient) exitWith {[_patient, "patientAnimRelease", [_patient, _token, _retire]] call ACME_fnc_ownerDispatch;};
if (_retire) then {
    private _retired = _patient getVariable ["ACME_patientAnimRetired", []];
    _retired pushBackUnique _token;
    if (count _retired > 32) then {_retired deleteAt 0;};
    _patient setVariable ["ACME_patientAnimRetired", _retired, true];
};
private _lock = _patient getVariable ["ACME_patientAnimLock", []];
if ((_lock param [0, ""]) == _token) then {_patient setVariable ["ACME_patientAnimLock", [], true];};
if ((_patient getVariable ["ACME_patientAnimSpeedToken", ""]) == _token
    && {(_lock param [0, ""]) in ["", _token]}) then {
    _patient setVariable ["ACME_patientAnimSpeedToken", "", true];
    _patient setAnimSpeedCoef 1;
    ["ace_common_setAnimSpeedCoef", [_patient, 1]] call CBA_fnc_globalEvent;
};
