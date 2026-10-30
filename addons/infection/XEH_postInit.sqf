#include "script_component.hpp"

[QACEGVAR(medical_treatment,fullHealLocalMod), LINKFUNC(fullHealLocal)] call CBA_fnc_addEventHandler;
[QACEGVAR(medical_gui,updateInjuryListPart),   LINKFUNC(gui_updateInjuryListPart)] call CBA_fnc_addEventHandler;

if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
if (isNil QGVAR(lastDiscovery)) then {GVAR(lastDiscovery) = -1;};

// A treated wound is the normal entry point into the infection-risk clock. Register it immediately
// rather than waiting for the periodic discovery fallback.
[QACEGVAR(medical_treatment,bandageLocal), {
    params ["_patient"];
    if (GVAR(infectionEnabled) && {local _patient} && {alive _patient}) then {
        GVAR(activePatients) pushBackUnique _patient;
    };
}] call CBA_fnc_addEventHandler;

// One worker per machine, never one long-lived PFH per casualty. Only active patients tick at the
// normal cadence. A slow discovery pass recovers locality migration/JIP and non-bandage wound paths.
if (isNil QGVAR(runtimePFH)) then {
    GVAR(runtimePFH) = [{
        private _active = GVAR(activePatients) select {!isNull _x && {alive _x}};

        if (!GVAR(infectionEnabled)) exitWith {
            // Clear any previously published infection drives once, then retire the registry.
            {
                if (local _x) then {[_x] call FUNC(handleInfectionPFH);};
            } forEach _active;
            GVAR(activePatients) = [];
        };

        {
            if (local _x) then {[_x] call FUNC(handleInfectionPFH);};
        } forEach _active;

        // An enrolled casualty remains enrolled while any durable infection timeline exists.
        // Full heal/reset explicitly retires it.
        _active = _active select {
            local _x && {alive _x} && {
                (_x getVariable [QGVAR(Infection_Stage),0]) > 0
                || {(_x getVariable [QGVAR(Infection_EligibleTime),-1]) != -1}
                || {_x getVariable [QGVAR(Sepsis_Permanent),false]}
            }
        };

        if (GVAR(lastDiscovery) < 0 || {CBA_missionTime - GVAR(lastDiscovery) >= 20}) then {
            GVAR(lastDiscovery) = CBA_missionTime;
            {
                private _patient = _x;
                if (local _patient && {alive _patient} && {_patient isKindOf "CAManBase"}) then {
                    private _known = (_patient getVariable [QGVAR(Infection_Stage),0]) > 0
                        || {(_patient getVariable [QGVAR(Infection_EligibleTime),-1]) != -1}
                        || {_patient getVariable [QGVAR(Sepsis_Permanent),false]};
                    if (!_known) then {
                        ([_patient] call FUNC(getWoundCount)) params ["_c","_b","_w","_s"];
                        _known = (_c + _b + _w + _s) > 0;
                    };
                    if (_known) then {_active pushBackUnique _patient;};
                };
            } forEach allUnits;
        };

        GVAR(activePatients) = _active;
    }, 2, []] call CBA_fnc_addPerFrameHandler;
};
