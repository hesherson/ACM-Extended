#include "..\script_component.hpp"
// Compare the captured session before clearing anything. An old stop/disconnect cannot release a replacement.
params ["_medic", "_patient", ["_epoch", -1], ["_capturedGrant", []]];
private _released = false;
private _clearProviderFields = !isMultiplayer;
if (isMultiplayer) then {
    private _state = _capturedGrant;
    if (_state isEqualTo [] && {!isNull _medic} && {local _medic}) then {
        private _localState = _medic getVariable ["ACME_resusToken_bvm",[]];
        if (count _localState == 6 && {(_localState select 0) isEqualTo _patient} && {(_localState select 5) == _epoch}) then {_state = _localState;};
    };
    if (!isNull _patient && {count _state == 6}) then {
        _released = [_patient,"resus",["release","bvm",_medic,_state select 1,_state select 2,_state select 3,_state select 4,_epoch,serverTime,[]]] call ACME_fnc_ownerDispatch;
    };
    _clearProviderFields = !isNull _medic && {local _medic} && {count _state == 6}
        && {(_medic getVariable ["ACME_resusToken_bvm",[]]) isEqualTo _state};
    if (_clearProviderFields) then {
        _medic setVariable ["ACME_resusToken_bvm",[],false];
    };
} else {
if (!isNull _patient) then {
    private _session = _patient getVariable [QGVAR(BVM_session), []];
    private _matches = if (_epoch < 0) then {
        _session isEqualTo [] && {(_patient getVariable [QGVAR(BVM_Medic), objNull]) isEqualTo _medic}
    } else {
        _session isEqualTo [_medic, _epoch]
    };
    if (_matches) then {
        if ((_patient getVariable [QGVAR(BVM_provider),objNull]) isEqualTo _medic) then {
            _patient setVariable [QGVAR(BVM_provider),objNull, true];
        };
        _patient setVariable [QGVAR(BVM_Medic), objNull, true];
        if ((_patient getVariable [QGVAR(BVM_provider),objNull]) isEqualTo objNull) then {
            _patient setVariable [QGVAR(BVM_ConnectedOxygen),false, true];
        };
        _patient setVariable [QGVAR(BVM_session), [], true];
        _released = true;
    };
};
};
if (_clearProviderFields && {!isNull _medic} && {(_medic getVariable [QGVAR(BVM_patient), objNull]) isEqualTo _patient}
    && {(_medic getVariable [QGVAR(BVM_epoch), -1]) == _epoch}) then {
    _medic setVariable [QGVAR(isUsingBVM), false, true];
    _medic setVariable [QGVAR(BVM_patient), objNull, true];
    _medic setVariable [QGVAR(BVM_epoch), -1, true];
};
_released
