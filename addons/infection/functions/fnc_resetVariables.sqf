#include "..\script_component.hpp"
/*
 * Clear infection state. Legacy per-patient PFHs are retired for hot-reload compatibility.
 */
params ["_patient"];

private _infectionPFH = _patient getVariable [QGVAR(Infection_PFH), -1];
if (_infectionPFH != -1) then {[_infectionPFH] call CBA_fnc_removePerFrameHandler;};
private _sepsisPFH = _patient getVariable [QGVAR(Sepsis_PFH), -1];
if (_sepsisPFH != -1) then {[_sepsisPFH] call CBA_fnc_removePerFrameHandler;};

{
    _x params ["_name","_value","_public"];
    _patient setVariable [_name,_value,_public];
} forEach [
    [QGVAR(Infection_PFH),-1,false],
    [QGVAR(Sepsis_PFH),-1,false],
    [QGVAR(Infection_Stage),0,true],
    [QGVAR(Infection_EligibleTime),-1,true],
    [QGVAR(Infection_RiskAccumulator),0,true],
    [QGVAR(Infection_NextCheck),0,false],
    [QGVAR(Infection_NextStageTime),-1,true],
    [QGVAR(Infection_TreatmentAccumulator),0,true],
    [QGVAR(Fever_Offset),0,true],
    [QGVAR(Sepsis_Onset),-1,true],
    [QGVAR(Sepsis_NextPain),0,false],
    [QGVAR(Sepsis_Severity),0,true],
    [QGVAR(Sepsis_Permanent),false,true],
    [QGVAR(HR_Adjust),0,true],
    [QGVAR(RR_Adjust),0,true],
    [QGVAR(Resistance_Delta),0,true],
    [QGVAR(Metabolic_Demand),1,true],
    [QGVAR(Preload_Mult),1,true],
    [QGVAR(Coag_Mult),1,true]
];
