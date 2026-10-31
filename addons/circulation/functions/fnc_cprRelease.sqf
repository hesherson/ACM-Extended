#include "..\script_component.hpp"
// Release only the captured session. A late stop cannot clear a replacement provider.
params ["_medic", "_patient", ["_epoch", -1], ["_capturedGrant", []]];
private _released = false;
private _clearProviderFields = !isMultiplayer;
if (isMultiplayer) then {
    private _state = _capturedGrant;
    if (_state isEqualTo [] && {!isNull _medic} && {local _medic}) then {
        private _localState = _medic getVariable ["ACME_resusToken_cpr",[]];
        if (count _localState == 6 && {(_localState select 0) isEqualTo _patient} && {(_localState select 5) == _epoch}) then {_state = _localState;};
    };
    if (!isNull _patient && {count _state == 6}) then {
        _released = [_patient,"resus",["release","cpr",_medic,_state select 1,_state select 2,_state select 3,_state select 4,_epoch,serverTime,[]]] call ACME_fnc_ownerDispatch;
    };
    _clearProviderFields = !isNull _medic && {local _medic} && {count _state == 6}
        && {(_medic getVariable ["ACME_resusToken_cpr",[]]) isEqualTo _state};
    if (_clearProviderFields) then {
        _medic setVariable ["ACME_resusToken_cpr",[],false];
    };
} else {
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
};
if (_clearProviderFields && {!isNull _medic} && {(_medic getVariable [QGVAR(CPR_Patient), objNull]) isEqualTo _patient}
    && {(_medic getVariable [QGVAR(CPR_Epoch), -1]) == _epoch}) then {
    _medic setVariable [QGVAR(isPerformingCPR), false, true];
    _medic setVariable [QGVAR(CPR_Patient), objNull, true];
    _medic setVariable [QGVAR(CPR_Epoch), -1, true];
};
_released
