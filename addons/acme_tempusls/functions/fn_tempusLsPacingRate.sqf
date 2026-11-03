/* Invoked only by the native patient-owner HR writer. No competing HR PFH. */
params ["_patient", "_intrinsic"];
private _settings = _patient getVariable ["acme_tempusls_paceSet", []];
if (count _settings < 7) exitWith {
    if (_patient getVariable ["acme_tempusls_capture", false]) then {
        [_patient, "acme_tempusls_capture", false] call ACME_fnc_setVarNet;
    };
    _intrinsic
};
_settings params ["_device", "_on", "_rate", "_ma", "_demand", "_epoch", "_actor"];
private _valid = _on && {!isNull _device} && {alive _patient}
    && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {(_device getVariable ["acme_tempusls_pat", objNull]) isEqualTo _patient}
    && {(_device getVariable ["acme_tempusls_pw", [false]]) select 0}
    && {_device distance _patient <= 6}
    && {_device getVariable ["acme_tempusls_pads",true]}
    && {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
    && {[_patient] call ACM_circulation_fnc_hasPulse};
private _capture = _valid && {_ma >= (_patient getVariable ["acme_tempusls_thr", 60])}
    && {!_demand || {_intrinsic < _rate}};
[_patient, "acme_tempusls_capture", _capture] call ACME_fnc_setVarNet;
_patient setVariable ["acme_tempusls_intrinsicHR", _intrinsic];
if (_capture) then {_rate} else {_intrinsic}
