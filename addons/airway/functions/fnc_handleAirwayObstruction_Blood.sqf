#include "..\script_component.hpp"
/*
 * Author: Blue, ACM Extended Fork
 * Handle airway obstruction due to bleeding.
 *
 * ACME note:
 * The native obstruction field is current airway occupancy, not an event counter. Only the patient owner may
 * generate new contamination. Each accepted contamination increments ACME_airwayBloodEventSerial, while the
 * native obstruction state is held at 1 until suction clears it. This prevents multiple machines from stacking
 * duplicate PFHs and prevents a long-running head bleed from turning one state variable into an unbounded volume.
 */
params ["_patient", ["_epoch", -1]];
if (isNull _patient) exitWith {};
if (_epoch < 0 && {!isNil "ACME_fnc_clinicalEpoch"}) then {_epoch = [_patient] call ACME_fnc_clinicalEpoch;};

if (!local _patient) exitWith {
    [QGVAR(handleAirwayObstruction_Blood), [_patient, _epoch], _patient] call CBA_fnc_targetEvent;
};

if (_epoch >= 0 && {!isNil "ACME_fnc_clinicalEpoch"} && {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};

private _old = _patient getVariable [QGVAR(AirwayObstructionBlood_PFH), -1];
if (_old isEqualType 0 && {_old >= 0}) exitWith {};

private _PFH = [{
    params ["_args", "_idPFH"];
    _args params ["_patient", "_epoch"];

    if (isNull _patient || {!local _patient}
        || {(_patient getVariable [QGVAR(AirwayObstructionBlood_PFH), -1]) != _idPFH}
        || {_epoch >= 0 && {!isNil "ACME_fnc_clinicalEpoch"} && {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (!isNull _patient && {(_patient getVariable [QGVAR(AirwayObstructionBlood_PFH), -1]) == _idPFH}) then {
            _patient setVariable [QGVAR(AirwayObstructionBlood_PFH), -1, false];
        };
    };

    private _isBleeding = [_patient, "head"] call EFUNC(damage,isBodyPartBleeding);
    private _inRecovery = _patient getVariable [QGVAR(RecoveryPosition_State), false];
    private _hasSGA = (_patient getVariable [QGVAR(AirwayItem_Oral), ""]) == "SGA";

    if (!(IS_UNCONSCIOUS(_patient)) || {!_isBleeding}) exitWith {
        _patient setVariable [QGVAR(AirwayObstructionBlood_PFH), -1, false];
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    if (_inRecovery || {_hasSGA}) exitWith {};

    private _cardiacArrest = GET_HEART_RATE(_patient) < 20;
    private _obstructChance = (linearConversion [0.05, 0.5, ([_patient, "head"] call EFUNC(damage,getBodyPartBleeding)), 0, 0.5, true]) * GVAR(airwayObstructionBloodChance);

    if ((!_cardiacArrest && {random 1 < _obstructChance}) || {_cardiacArrest && {random 1 < (_obstructChance / 2)}}) then {
        // Event identity is monotonic; current obstruction is presence/absence. Suction can clear the occupancy to
        // zero without rewinding history, and a genuinely new bleed event can then refill it once.
        private _serial = (_patient getVariable ["ACME_airwayBloodEventSerial", 0]) + 1;
        _patient setVariable ["ACME_airwayBloodEventSerial", _serial, true];
        _patient setVariable [QGVAR(AirwayObstructionBlood_State), 1, true];
    };

}, 5 max (random 10), [_patient, _epoch]] call CBA_fnc_addPerFrameHandler;

_patient setVariable [QGVAR(AirwayObstructionBlood_PFH), _PFH, false];
