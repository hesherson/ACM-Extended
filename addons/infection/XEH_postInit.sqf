#include "script_component.hpp"

[QACEGVAR(medical_treatment,fullHealLocalMod), LINKFUNC(fullHealLocal)] call CBA_fnc_addEventHandler;
[QACEGVAR(medical_gui,updateInjuryListPart),   LINKFUNC(gui_updateInjuryListPart)] call CBA_fnc_addEventHandler;

// 1.3.0: one worker per machine, never one long-lived PFH per casualty.
// The current owner advances a casualty on the next pass, so locality migration cannot leave
// an old owner continuing to write infection state.
if (isNil QGVAR(runtimePFH)) then {
    GVAR(runtimePFH) = [{
        {
            if (local _x && {alive _x} && {_x isKindOf "CAManBase"}) then {
                [_x] call FUNC(handleInfectionPFH);
            };
        } forEach allUnits;
    }, 2, []] call CBA_fnc_addPerFrameHandler;
};
