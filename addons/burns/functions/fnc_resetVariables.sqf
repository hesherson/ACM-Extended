#include "..\script_component.hpp"
/*
 * Clear only burn-owned state. CBRN airway inflammation belongs to CBRN and must never be erased here.
 */
params ["_patient"];

{
    _x params ["_name","_value","_public"];
    _patient setVariable [_name,_value,_public];
} forEach [
    [QGVAR(AirwayBurned),false,true],
    [QGVAR(AirwayBurnOnset),-1,true],
    [QGVAR(AirwayInflammation),0,true],
    [QGVAR(BurnSurface),[0,0,0,0,0,0],true],
    [QGVAR(BurnBurden),0,true],
    [QGVAR(SystemicBurden),0,true],
    [QGVAR(LastBurnAt),-1,true],
    [QGVAR(PermanentInjury),false,true],
    [QGVAR(EffectiveVolumeDeficitL),0,true],
    [QGVAR(HeatLossDrive),0,true],
    [QGVAR(HR_Adjust),0,true],
    [QGVAR(Resistance_Delta),0,true],
    [QGVAR(ShockSeverity),0,true],
    [QGVAR(InfectionRiskMult),1,true],
    [QGVAR(LastTickLocal),-1,false]
];
