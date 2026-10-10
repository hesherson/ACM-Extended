#include "script_component.hpp"

[QGVAR(initFullHealFacility), {
    params ["_object"];

    [_object] call FUNC(initFullHealFacility);
}] call CBA_fnc_addEventHandler;

["CBA_settingsInitialized", {
    GVAR(TrainingCasualtyGroup) = createGroup [civilian, false];
    if (isServer) then {GVAR(TrainingBluforGroup) = createGroup [west, false];};
}] call CBA_fnc_addEventHandler;

[QGVAR(requestTrainingPatient), {
    if (!isServer) exitWith {};
    _this call FUNC(requestTrainingPatient);
}] call CBA_fnc_addEventHandler;

// Locality changes, wake-up and JIP all re-enroll marked patients; ordinary mission AI is untouched.
["CAManBase","Local",{
    [{_this call FUNC(trainingPatientHold);},[_this select 0],0.25] call CBA_fnc_waitAndExecute;
}] call CBA_fnc_addClassEventHandler;
["ace_unconscious",{
    params ["_patient","_unconscious"];
    if (!_unconscious) then {[_patient] call FUNC(trainingPatientHold);};
}] call CBA_fnc_addEventHandler;
GVAR(trainingHoldScanAt) = -1;
[{
    if (CBA_missionTime >= GVAR(trainingHoldScanAt)) then {
        GVAR(trainingHoldScanAt) = CBA_missionTime + 10;
        {if (_x getVariable ["ACME_trainingCrouchOnly",false]) then {[_x] call FUNC(trainingPatientHold);};} forEach allUnits;
    };
    private _keep = [];
    {if ([_x] call FUNC(trainingPatientHoldTick)) then {_keep pushBack _x;};} forEach (+(missionNamespace getVariable ["ACME_trainingHeldPatients",[]]));
    missionNamespace setVariable ["ACME_trainingHeldPatients",_keep];
},0.5,[]] call CBA_fnc_addPerFrameHandler;
