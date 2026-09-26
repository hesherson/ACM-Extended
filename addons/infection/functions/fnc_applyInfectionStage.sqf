#include "..\script_component.hpp"
/*
 * ACME 1.3.0 infection stage transition.
 * The stage owns pathology only. Vitals are published as source-separated drives by the
 * locality-safe global infection worker and consumed by ACME's authoritative writers.
 */
params ["_patient", "_newStage"];

private _currentStage = _patient getVariable [QGVAR(Infection_Stage), 0];
if (_newStage == _currentStage) exitWith {};

_patient setVariable [QGVAR(Infection_Stage), _newStage, true];
private _stageTime = (GVAR(infectionStageTime) * 60) + (random 300);

switch (_newStage) do {
    case 0: {
        _patient setVariable [QGVAR(Infection_EligibleTime), -1, true];
        _patient setVariable [QGVAR(Infection_RiskAccumulator), 0, true];
        _patient setVariable [QGVAR(Infection_NextStageTime), -1, true];
        _patient setVariable [QGVAR(Fever_Offset), 0, true];
        _patient setVariable [QGVAR(Sepsis_Onset), -1, true];
    };
    case 1: {
        _patient setVariable [QGVAR(Infection_NextStageTime), CBA_missionTime + _stageTime, true];
        _patient setVariable [QGVAR(Fever_Offset), 0.6, true];
        _patient setVariable [QGVAR(Sepsis_Onset), -1, true];
    };
    case 2: {
        _patient setVariable [QGVAR(Infection_NextStageTime), CBA_missionTime + _stageTime, true];
        _patient setVariable [QGVAR(Fever_Offset), 1.6, true];
        _patient setVariable [QGVAR(Sepsis_Onset), -1, true];
    };
    case 3: {
        _patient setVariable [QGVAR(Infection_NextStageTime), -1, true];
        _patient setVariable [QGVAR(Fever_Offset), 2.6, true];
        if ((_patient getVariable [QGVAR(Sepsis_Onset), -1]) < 0) then {
            _patient setVariable [QGVAR(Sepsis_Onset), CBA_missionTime, true];
        };
    };
};
