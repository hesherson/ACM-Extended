#include "..\script_component.hpp"
/*
 * Adult burn physiology integrated with the authoritative ACME writers.
 * Burn wounds own anatomy; this worker derives temporary systemic consequences and publishes source-separated
 * inputs for ACME's existing temperature, HR, SVR, preload, shock and infection systems.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};

private _burden = (_patient getVariable [QGVAR(BurnBurden),0]) max 0 min 1;
private _systemic = (_patient getVariable [QGVAR(SystemicBurden),_burden]) max 0 min 1;
private _airway = (_patient getVariable [QGVAR(AirwayInflammation),0]) max 0 min 100;
private _permanent = _patient getVariable [QGVAR(PermanentInjury),false];
if (!GVAR(burnsEnabled) || {_burden <= 0 && {_systemic <= 0} && {_airway <= 0}
    && {!(_patient getVariable [QGVAR(AirwayBurned),false])} && {!_permanent}}) exitWith {
    // An imported clean state or a disabled module must not leave an old source's
    // drives in the shared writers. Keep durable anatomy and evacuation latches.
    {
        _x params ["_name","_neutral"];
        if ((_patient getVariable [_name,_neutral]) != _neutral) then {
            [_patient,_name,_neutral,0,0] call ACME_fnc_setVarNetApprox;
        };
    } forEach [
        [QGVAR(AirwayInflammation),0],
        [QGVAR(EffectiveVolumeDeficitL),0],
        [QGVAR(HeatLossDrive),0],
        [QGVAR(HR_Adjust),0],
        [QGVAR(Resistance_Delta),0],
        [QGVAR(ShockSeverity),0],
        [QGVAR(InfectionRiskMult),1]
    ];
};

private _now = CBA_missionTime;
private _lastTick = _patient getVariable [QGVAR(LastTickLocal), _now - 2];
if (_lastTick < 0) then {_lastTick = _now - 2;};
private _dt = ((_now - _lastTick) max 0) min 10;
_patient setVariable [QGVAR(LastTickLocal), _now, false];

private _lastBurn = _patient getVariable [QGVAR(LastBurnAt),_now];
private _hardcore = missionNamespace getVariable ["ACME_hcEff_burns",false];

if (!_permanent && {_hardcore} && {_burden >= GVAR(hardcoreEvacBurden)}) then {
    _permanent = true;
    _patient setVariable [QGVAR(PermanentInjury),true,true];
    if (!isNil "ACME_fnc_evacuationRequirementCommit") then {
        [_patient,true,true,true,false] call ACME_fnc_evacuationRequirementCommit;
    } else {
        _patient setVariable ["ACME_requiresEvac",true,true];
    };
};

if (_permanent && {!(_patient getVariable ["ACME_requiresEvac",false])}) then {
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
[_patient,QGVAR(SystemicBurden),_systemic,([0.002,0] select (_systemic == 0)),0] call ACME_fnc_setVarNetApprox;

// Capillary leak is an effective intravascular-volume deficit. It is NOT blood loss: fluids can offset it,
// hemoglobin is not deleted, and the shock phenotype is not falsely labeled hemorrhagic.
private _deficitL = linearConversion [0.08,0.85,_systemic,0,2.2,true];
private _heatLoss = linearConversion [0.05,0.75,_systemic,0,1,true];
private _hrAdj = 18 * _systemic;
private _resist = 10 * _systemic;

[_patient,QGVAR(EffectiveVolumeDeficitL),_deficitL,([0.005,0] select (_deficitL == 0)),0] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(HeatLossDrive),_heatLoss,([0.005,0] select (_heatLoss == 0)),0] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(HR_Adjust),_hrAdj,([0.05,0] select (_hrAdj == 0)),0] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(Resistance_Delta),_resist,([0.05,0] select (_resist == 0)),0] call ACME_fnc_setVarNetApprox;
private _shockSeverity = linearConversion [0.12,0.70,_systemic,0,1,true];
[_patient,QGVAR(ShockSeverity),_shockSeverity,([0.005,0] select (_shockSeverity == 0)),0] call ACME_fnc_setVarNetApprox;

// Proper burn coverage reduces, but does not abolish, skin-barrier infection risk.
// A newly inflicted burn clears protection on that region in XEH_postInit.
private _surface = _patient getVariable [QGVAR(BurnSurface),[0,0,0,0,0,0]];
private _protected = _patient getVariable [QGVAR(BurnProtected),[false,false,false,false,false,false]];
private _weights = [0.09,0.36,0.09,0.09,0.18,0.18];
private _unprotectedBurden = 0;
if (_surface isEqualType [] && {count _surface == 6} && {_protected isEqualType []} && {count _protected == 6}) then {
    {
        private _careMult = [1,0.45] select (_protected select _forEachIndex);
        _unprotectedBurden = _unprotectedBurden + ((_surface select _forEachIndex) * _x * _careMult);
    } forEach _weights;
} else {
    _unprotectedBurden = _burden;
};
[_patient,QGVAR(InfectionRiskMult),1 + (1.5 * (_unprotectedBurden min 1)),0.005,0] call ACME_fnc_setVarNetApprox;

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
[_patient,QGVAR(AirwayInflammation),_airway,([0.05,0] select (_airway == 0)),0] call ACME_fnc_setVarNetApprox;

if ((_systemic > 0.001 || {_airway > 0.001}) && {!isNil "ACME_circ_activePatients"}) then {
    ACME_circ_activePatients pushBackUnique _patient;
};
