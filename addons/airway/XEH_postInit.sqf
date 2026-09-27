#include "script_component.hpp"

[QGVAR(handleAirway), LINKFUNC(handleAirway)] call CBA_fnc_addEventHandler;
[QGVAR(handleAirwayCollapse), LINKFUNC(handleAirwayCollapse)] call CBA_fnc_addEventHandler;
[QGVAR(handleAirwayObstruction_Vomit), LINKFUNC(handleAirwayObstruction_Vomit)] call CBA_fnc_addEventHandler;
[QGVAR(handleAirwayObstruction_Blood), LINKFUNC(handleAirwayObstruction_Blood)] call CBA_fnc_addEventHandler;

[QGVAR(handleRecoveryPosition), LINKFUNC(handleRecoveryPosition)] call CBA_fnc_addEventHandler;

[QGVAR(handleSuctionLocal), LINKFUNC(handleSuctionLocal)] call CBA_fnc_addEventHandler;
[QGVAR(setAirwayCheckedTime), {
    params [["_patient", objNull, [objNull]]];
    if (isNull _patient || {!local _patient}) exitWith {};
    _patient setVariable [QGVAR(AirwayChecked_Time), CBA_missionTime, true];
    _patient setVariable ["ACME_airwayCheckedServer", serverTime, true];
}] call CBA_fnc_addEventHandler;

["ace_unconscious", LINKFUNC(onUnconscious)] call CBA_fnc_addEventHandler;

["ACM_GuedelTube", "ACM_OPA"] call ACEFUNC(common,registerItemReplacement); // TODO remove after 1.5
