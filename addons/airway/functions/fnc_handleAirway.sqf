#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle airway deterioration while unconscious.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_airway_fnc_handleAirway;
 *
 * Public: No
 */

params ["_patient", ["_epoch", -1], ["_reflexOnly", false]];
private _acmeReconcile = "B106:airwayWakeGuard";
if (isNull _patient) exitWith {};
if (_epoch < 0) then {_epoch = [_patient] call ACME_fnc_clinicalEpoch;};
if (!local _patient) exitWith {
    [QGVAR(handleAirway), [_patient, _epoch, _reflexOnly], _patient] call CBA_fnc_targetEvent;
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)
    || {!alive _patient} || {_patient getVariable ["ACME_clinicalRestoring", false]}
    || {!(GVAR(enable))} || {!(IS_UNCONSCIOUS(_patient))}) exitWith {};

// A delayed reflex loss is committed by the current owner and only in the episode that scheduled it.
if (_reflexOnly) exitWith {
    if (_patient getVariable [QGVAR(AirwayReflex_State), false]) then {
        _patient setVariable [QGVAR(AirwayReflex_State), false, true];
    };

    if ([_patient, "head"] call EFUNC(damage,isBodyPartBleeding) && (GVAR(airwayObstructionBloodChance) > 0)) then {
        [QGVAR(handleAirwayObstruction_Blood), [_patient, _epoch], _patient] call CBA_fnc_targetEvent;
    };
};

private _airwayReflexDelay = 20 + (random 25);
[{
    params ["_patient", "_epoch"];
    if (isNull _patient || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};
    [QGVAR(handleAirway), [_patient, _epoch, true], _patient] call CBA_fnc_targetEvent;
}, [_patient, _epoch], _airwayReflexDelay] call CBA_fnc_waitAndExecute;

[{
    params ["_patient", "_epoch"];
    if (isNull _patient || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};

    [QGVAR(handleAirwayCollapse), [_patient, _epoch], _patient] call CBA_fnc_targetEvent;
}, [_patient, _epoch], (_airwayReflexDelay + (240 + (random 60)))] call CBA_fnc_waitAndExecute;

if (GVAR(airwayObstructionVomitChance) > 0) then {
    private _medicationEffect = [_patient] call EFUNC(circulation,getNauseaMedicationEffects);

    if ((((GET_BODYPART_DAMAGE(_patient) select 0) > 1) && (random 1 < (0.8 + _medicationEffect))) || random 1 < (0.3 + _medicationEffect)) then {
        [{
            params ["_patient", "_epoch"];
            if (isNull _patient || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};

            [QGVAR(handleAirwayObstruction_Vomit), [_patient, _epoch], _patient] call CBA_fnc_targetEvent;
        }, [_patient, _epoch], (_airwayReflexDelay + (60 + (random 60)))] call CBA_fnc_waitAndExecute;
    };
};
