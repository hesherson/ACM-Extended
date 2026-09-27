#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle airway obstruction due to bleeding.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_airway_fnc_handleAirwayObstruction_Blood;
 *
 * Public: No
 */

params ["_patient", ["_epoch", -1]];
if (isNull _patient) exitWith {};
if (_epoch < 0) then {_epoch = [_patient] call ACME_fnc_clinicalEpoch;};
if (!local _patient) exitWith {
    [QGVAR(handleAirwayObstruction_Blood), [_patient, _epoch], _patient] call CBA_fnc_targetEvent;
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)
    || {!alive _patient} || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};


if (_patient getVariable [QGVAR(AirwayObstructionBlood_PFH), -1] != -1) exitWith {};

if (!(IS_UNCONSCIOUS(_patient))) exitWith {_patient setVariable ["ACME_nativeBloodObstructionActive", false, true];};
_patient setVariable ["ACME_nativeBloodObstructionActive", true, true];
private _PFH = [{
    params ["_args", "_idPFH"];
    _args params ["_patient", "_epoch"];
    // A departed/reset worker may remove itself, never the new owner's or new episode's handle/evidence.
    if (isNull _patient || {!local _patient}
        || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {_patient getVariable ["ACME_clinicalRestoring", false]}
        || {(_patient getVariable [QGVAR(AirwayObstructionBlood_PFH), -1]) != _idPFH}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (!isNull _patient && {(_patient getVariable [QGVAR(AirwayObstructionBlood_PFH), -1]) == _idPFH}) then {
            _patient setVariable [QGVAR(AirwayObstructionBlood_PFH), -1];
        };
    };
    if (!alive _patient) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        _patient setVariable [QGVAR(AirwayObstructionBlood_PFH), -1];
        _patient setVariable ["ACME_nativeBloodObstructionActive", false, true];
    };

    private _isBleeding = [_patient, "head"] call EFUNC(damage,isBodyPartBleeding);
    private _inRecovery = _patient getVariable [QGVAR(RecoveryPosition_State), false];
    private _hasSGA = (_patient getVariable [QGVAR(AirwayItem_Oral), ""]) == "SGA";

    if (!(IS_UNCONSCIOUS(_patient)) || !_isBleeding) exitWith {
        _patient setVariable [QGVAR(AirwayObstructionBlood_PFH), -1];
        _patient setVariable ["ACME_nativeBloodObstructionActive", false, true];
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    if (_inRecovery || _hasSGA) exitWith {}; // TODO check for pose

    private _cardiacArrest = GET_HEART_RATE(_patient) < 20;
    private _obstructChance = (linearConversion [0.05, 0.5, ([_patient, "head"] call EFUNC(damage,getBodyPartBleeding)), 0, 0.5, true]) * GVAR(airwayObstructionBloodChance);
    private _obstructionState = _patient getVariable [QGVAR(AirwayObstructionBlood_State), 0];

    if ((!_cardiacArrest && (random 1 < _obstructChance)) || {_cardiacArrest && (random 1 < (_obstructChance / 2))}) then {
        _patient setVariable [QGVAR(AirwayObstructionBlood_State), (_obstructionState + 1), true];
    };

}, 5 max (random 10), [_patient, _epoch]] call CBA_fnc_addPerFrameHandler;

_patient setVariable [QGVAR(AirwayObstructionBlood_PFH), _PFH];
