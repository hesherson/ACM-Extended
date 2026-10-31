#include "script_component.hpp"

[QGVAR(handleAirway), LINKFUNC(handleAirway)] call CBA_fnc_addEventHandler;
[QGVAR(handleAirwayCollapse), LINKFUNC(handleAirwayCollapse)] call CBA_fnc_addEventHandler;
[QGVAR(handleAirwayObstruction_Vomit), LINKFUNC(handleAirwayObstruction_Vomit)] call CBA_fnc_addEventHandler;
[QGVAR(handleAirwayObstruction_Blood), LINKFUNC(handleAirwayObstruction_Blood)] call CBA_fnc_addEventHandler;

[QGVAR(handleRecoveryPosition), LINKFUNC(handleRecoveryPosition)] call CBA_fnc_addEventHandler;
// Fixed native owner endpoint; no dynamic function or arbitrary variable transport.
[QGVAR(setRecoveryPosition), LINKFUNC(setRecoveryPosition)] call CBA_fnc_addEventHandler;

// B220: catch native/third-party rolls as well as ACME's arbiter. State changes
// in an animation chain are observed immediately, without an all-unit polling loop.
if (isNil QGVAR(recoveryRollEH)) then {
    GVAR(recoveryRollEH) = ["CAManBase", "AnimStateChanged", {
        params ["_patient", "_animation"];
        if (!local _patient || {!alive _patient}) exitWith {};
        private _anim = toLowerANSI _animation;
        if ((_anim find "rolltofront") < 0 && {(_anim find "rolltoback") < 0}) exitWith {};
        [objNull, _patient, false, true, "interrupt"] call FUNC(setRecoveryPosition);
    }] call CBA_fnc_addClassEventHandler;
};

[QGVAR(handleSuctionLocal), LINKFUNC(handleSuctionLocal)] call CBA_fnc_addEventHandler;
[QGVAR(setAirwayCheckedTime), {
    params [["_patient", objNull, [objNull]]];
    if (isNull _patient || {!local _patient}) exitWith {};
    _patient setVariable [QGVAR(AirwayChecked_Time), CBA_missionTime, true];
    _patient setVariable ["ACME_airwayCheckedServer", serverTime, true];
}] call CBA_fnc_addEventHandler;

["ace_unconscious", LINKFUNC(onUnconscious)] call CBA_fnc_addEventHandler;

["ACM_GuedelTube", "ACM_OPA"] call ACEFUNC(common,registerItemReplacement); // TODO remove after 1.5
