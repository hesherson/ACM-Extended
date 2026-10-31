#include "..\script_component.hpp"
/*
 * Author: INFERNO
 * Initialises a fresh unit without erasing state already received during JIP or restored by
 * clinical persistence. Respawn has its own explicit definitive reset.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_burns_fnc_initUnit;
 *
 * Public: No
 */

params ["_patient"];

if (isNull _patient || {!local _patient}) exitWith {};

if (([QGVAR(BurnSurface),QGVAR(BurnBurden),QGVAR(AirwayBurned),QGVAR(PermanentInjury)] findIf {
    !isNil {_patient getVariable _x}
}) >= 0) exitWith {
    _patient setVariable [QGVAR(LastTickLocal),-1,false];
    if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
    GVAR(activePatients) pushBackUnique _patient;
};

[_patient] call FUNC(resetVariables);
