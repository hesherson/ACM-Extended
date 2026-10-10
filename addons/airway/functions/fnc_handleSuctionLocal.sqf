#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle suction of airway (LOCAL)
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [cursorTarget] call ACM_airway_fnc_handleSuctionLocal;
 *
 * Public: No
 */

params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};
if ((_patient getVariable [QGVAR(AirwayObstructionBlood_State), 0]) > 0) then {
    _patient setVariable ["ACME_airwayBloodRefillAt", CBA_missionTime + 30, true];
};
_patient setVariable ["ACME_laryngo_bloodRemaining", [], true];
_patient setVariable ["ACME_laryngo_pool", [], true];

_patient setVariable [QGVAR(AirwayObstructionVomit_State), 0, true];
_patient setVariable [QGVAR(AirwayObstructionBlood_State), 0, true];
_patient setVariable [QGVAR(AirwayObstructionVomit_GracePeriod), CBA_missionTime, true];
[_patient, true] call FUNC(clearAirwayCheckedTime);
