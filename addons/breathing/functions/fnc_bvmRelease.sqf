#include "..\script_component.hpp"
// Compare the captured session before clearing anything. An old stop/disconnect cannot release a replacement.
params ["_medic", "_patient", ["_epoch", -1]];
private _released = false;
if (!isNull _patient) then {
    private _session = _patient getVariable [QGVAR(BVM_session), []];
    private _matches = if (_epoch < 0) then {
        _session isEqualTo [] && {(_patient getVariable [QGVAR(BVM_Medic), objNull]) isEqualTo _medic}
    } else {
        _session isEqualTo [_medic, _epoch]
    };
    if (_matches) then {
        _patient setVariable [QGVAR(BVM_provider), objNull, true];
        _patient setVariable [QGVAR(BVM_Medic), objNull, true];
        _patient setVariable [QGVAR(BVM_ConnectedOxygen), false, true];
        _patient setVariable [QGVAR(BVM_session), [], true];
        _released = true;
    };
};
if (!isNull _medic && {(_medic getVariable [QGVAR(BVM_patient), objNull]) isEqualTo _patient}
    && {(_medic getVariable [QGVAR(BVM_epoch), -1]) == _epoch}) then {
    _medic setVariable [QGVAR(isUsingBVM), false, true];
    _medic setVariable [QGVAR(BVM_patient), objNull, true];
    _medic setVariable [QGVAR(BVM_epoch), -1, true];
};
_released
