#include "..\script_component.hpp"
/*
 * ACME 1.3.0 adult burn physiology.
 * Burn wounds own anatomy; this worker derives temporary systemic consequences and publishes source-separated
 * inputs for ACME's existing temperature, HR, SVR, preload, shock and infection systems.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};

private _burden = (_patient getVariable [QGVAR(BurnBurden),0]) max 0 min 1;
private _airway = (_patient getVariable [QGVAR(AirwayInflammation),0]) max 0 min 100;
private _permanent = _patient getVariable [QGVAR(PermanentInjury),false];
if (_burden <= 0.001 && {_airway <= 0.001} && {!_permanent}) exitWith {};

private _now = CBA_missionTime;
private _lastTick = _patient getVariable [QGVAR(LastTickLocal), _now - 2];
private _dt = ((_now - _lastTick) max 0) min 10;
_patient setVariable [QGVAR(LastTickLocal), _now, false];

private _systemic = (_patient getVariable [QGVAR(SystemicBurden),_burden]) max 0 min 1;
private _lastBurn = _patient getVariable [QGVAR(LastBurnAt),_now];
private _hardcore = GVAR(hardcorePersistentBurns);

if (!_permanent && {_hardcore} && {_burden >= GVAR(hardcoreEvacBurden)}) then {
    _permanent = true;
    _patient setVariable [QGVAR(PermanentInjury),true,true];
    if (!isNil "ACME_fnc_evacuationRequirementCommit") then {
        [_patient,true,true,true,false] call ACME_fnc_evacuationRequirementCommit;
    } else {
        _patient setVariable ["ACME_requiresEvac",true,true];
    };
};

// The acute leak/thermal load is allowed to settle in ordinary gameplay. Anatomical burn burden remains,
// preserving wound care and infection risk without making every burn a mission-long hidden debuff.
if ((_now - _lastBurn) > 300) then {
    private _recoverySec = (GVAR(fieldRecoveryMinutes) max 1) * 60;
    private _floor = if (_permanent) then {0.18 max (_burden * 0.30)} else {0};
    _systemic = (_systemic - (_dt / _recoverySec)) max _floor;
};
_patient setVariable [QGVAR(SystemicBurden),_systemic,true];

// Capillary leak is an effective intravascular-volume deficit. It is NOT blood loss: fluids can offset it,
// hemoglobin is not deleted, and the shock phenotype is not falsely labeled hemorrhagic.
private _deficitL = linearConversion [0.08,0.85,_systemic,0,2.2,true];
private _heatLoss = linearConversion [0.05,0.75,_systemic,0,1,true];
private _hrAdj = 18 * _systemic;
private _resist = 10 * _systemic;

_patient setVariable [QGVAR(EffectiveVolumeDeficitL),_deficitL,true];
_patient setVariable [QGVAR(HeatLossDrive),_heatLoss,true];
_patient setVariable [QGVAR(HR_Adjust),_hrAdj,true];
_patient setVariable [QGVAR(Resistance_Delta),_resist,true];
_patient setVariable [QGVAR(ShockSeverity),linearConversion [0.12,0.70,_systemic,0,1,true],true];
_patient setVariable [QGVAR(InfectionRiskMult),1 + (1.5 * _burden),true];

// Upper-airway burn edema is its own source. Never overwrite ACM_CBRN_AirwayInflammation.
if (_patient getVariable [QGVAR(AirwayBurned),false]) then {
    private _onset = _patient getVariable [QGVAR(AirwayBurnOnset),_now];
    private _ramp = linearConversion [0,360,(_now - _onset) max 0,0.15,1,true];
    private _target = (35 + (45 * (_burden max 0.20))) min 85;
    private _acuteWindow = (_now - _lastBurn) <= 1200;
    private _desired = if (_acuteWindow) then {_target * _ramp} else {0};
    private _step = (10 / 60) * _dt;
    if (_airway < _desired) then {_airway = (_airway + _step) min _desired;} else {_airway = (_airway - _step) max _desired;};
    if (_airway <= 0.25 && {!_acuteWindow}) then {
        _patient setVariable [QGVAR(AirwayBurned),false,true];
    };
} else {
    _airway = (_airway - ((10 / 60) * _dt)) max 0;
};
_patient setVariable [QGVAR(AirwayInflammation),_airway,true];

if ((_systemic > 0.001 || {_airway > 0.001}) && {!isNil "ACME_circ_activePatients"}) then {
    ACME_circ_activePatients pushBackUnique _patient;
};
