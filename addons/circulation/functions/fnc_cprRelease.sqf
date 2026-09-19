#include "..\script_component.hpp"
// Release only the captured session. A late stop cannot clear a replacement provider.
params ["_medic", "_patient", ["_epoch", -1]];
private _released = false;
if (!isNull _patient) then {
    private _session = _patient getVariable [QGVAR(CPR_session), []];
    private _matches = if (_epoch < 0) then {
        _session isEqualTo [] && {(_patient getVariable [QGVAR(CPR_Medic), objNull]) isEqualTo _medic}
    } else {
        _session isEqualTo [_medic, _epoch]
    };
    if (_matches) then {
        if ((_patient getVariable [QACEGVAR(medical,CPR_provider), objNull]) isEqualTo _medic) then {
            _patient setVariable [QACEGVAR(medical,CPR_provider), objNull, true];
        };
        if ((_patient getVariable [QGVAR(CPR_Medic), objNull]) isEqualTo _medic) then {
            _patient setVariable [QGVAR(CPR_Medic), objNull, true];
        };
        _patient setVariable [QGVAR(CPR_session), [], true];
        _released = true;
    };
};
if (!isNull _medic && {(_medic getVariable [QGVAR(CPR_Patient), objNull]) isEqualTo _patient}
    && {(_medic getVariable [QGVAR(CPR_Epoch), -1]) == _epoch}) then {
    _medic setVariable [QGVAR(isPerformingCPR), false, true];
    _medic setVariable [QGVAR(CPR_Patient), objNull, true];
    _medic setVariable [QGVAR(CPR_Epoch), -1, true];
};
_released
