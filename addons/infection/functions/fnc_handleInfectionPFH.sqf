#include "..\script_component.hpp"
/*
 * ACME 1.3.0 infection patient tick.
 * Called by one global PFH on the machine that currently owns the patient.
 */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};

private _enabled = GVAR(infectionEnabled);
if (!_enabled) exitWith {
    {
        _x params ["_name","_value"];
        _patient setVariable [_name,_value,true];
    } forEach [
        [QGVAR(Fever_Offset),0],
        [QGVAR(HR_Adjust),0],
        [QGVAR(RR_Adjust),0],
        [QGVAR(Resistance_Delta),0],
        [QGVAR(Metabolic_Demand),1],
        [QGVAR(EffectiveVolumeDeficitL),0],
        [QGVAR(Coag_Mult),1],
        [QGVAR(Sepsis_Severity),0]
    ];
};

private _now = CBA_missionTime;
private _stage = _patient getVariable [QGVAR(Infection_Stage), 0];

// Progression, risk and antibiotic response are throttled to 30 s. Derived physiology below is
// recalculated on every global runtime pass so HR/RR/SVR/preload respond smoothly.
if ((_patient getVariable [QGVAR(Infection_NextCheck), 0]) <= _now) then {
    // Replicate cadence with pathology so a new owner cannot grant an extra treatment/risk tick.
    _patient setVariable [QGVAR(Infection_NextCheck), _now + 30, true];

    ([_patient] call FUNC(getWoundCount)) params ["_c","_b","_w","_s"];
    private _treatedCount = _c + _b + _w + _s;
    private _hasOpenWounds = (ALL_BODY_PARTS findIf {
        ((GET_OPEN_WOUNDS(_patient) getOrDefault [_x, []]) findIf {(_x param [1, 0]) > 0}) >= 0
    }) >= 0;
    if (_stage == 0 && {_treatedCount <= 0} && {!_hasOpenWounds}
        && {!(_patient getVariable [QGVAR(Sepsis_Permanent), false])}) then {
        // Natural wound healing must retire a healthy casualty as well as explicit full heal.
        [_patient] call FUNC(resetVariables);
    };

    if ((_patient getVariable [QGVAR(Infection_EligibleTime), -1]) == -1) then {
        if (_treatedCount > 0) then {
            _patient setVariable [QGVAR(Infection_EligibleTime), _now + 3600, true];
        };
    };

    private _abLevel = [_patient] call FUNC(getAntibioticLevel);

    private _nextStageTime = _patient getVariable [QGVAR(Infection_NextStageTime), -1];
    if (_stage > 0 && {_nextStageTime != -1} && {_now >= _nextStageTime} && {_abLevel < 1.0}) then {
        [_patient, (_stage + 1) min 3] call FUNC(applyInfectionStage);
    };

    _stage = _patient getVariable [QGVAR(Infection_Stage), 0];

    if (_stage > 0) then {
        private _treatAccum = _patient getVariable [QGVAR(Infection_TreatmentAccumulator), 0];
        if (_abLevel >= 1.0) then {
            _treatAccum = _treatAccum + 1;
            if (_treatAccum >= 20) then {
                _treatAccum = 0;
                [_patient, (_stage - 1) max 0] call FUNC(applyInfectionStage);
            };
        } else {
            _treatAccum = (_treatAccum - 2) max 0;
        };
        _patient setVariable [QGVAR(Infection_TreatmentAccumulator), _treatAccum, true];
    };

    _stage = _patient getVariable [QGVAR(Infection_Stage), 0];
    if (_stage == 0) then {
        private _riskDelta = [_patient] call FUNC(getInfectionRisk);
        if (_riskDelta > 0) then {
            private _accumulator = ((_patient getVariable [QGVAR(Infection_RiskAccumulator), 0]) + _riskDelta) min 2.0;
            if (_accumulator >= 1.0) then {
                _accumulator = 0;
                [_patient, 1] call FUNC(applyInfectionStage);
            } else {
                _patient setVariable [QGVAR(Infection_RiskAccumulator), _accumulator, true];
            };
        };
    };

    _stage = _patient getVariable [QGVAR(Infection_Stage), 0];
    if (_stage > 0) then {
        private _painTarget = [0.30, 0.50, 0.70] select (_stage - 1);
        if (GET_PAIN(_patient) < _painTarget) then {
            [_patient, 0.035 * _stage] call ACEFUNC(medical_status,adjustPainLevel);
        };
    };
};

_stage = _patient getVariable [QGVAR(Infection_Stage), 0];
if (_stage == 3) then {[_patient] call FUNC(handleSepsisPFH);};

// Infection requests a fever setpoint. ACME's thermal writer decides the actual temperature after
// hemorrhage, environment, burns and rewarming have all contributed.
private _feverOffset = [0,0.6,1.6,2.6] select (_stage max 0 min 3);
[_patient,QGVAR(Fever_Offset),_feverOffset,0.01,5] call ACME_fnc_setVarNetApprox;

private _temp = _patient getVariable ["ACME_hypo_temp", 37];
private _feverC = if (_stage > 0) then {(_temp - 37) max 0} else {0};
private _sepsisSeverity = 0;
if (_stage == 3) then {
    private _onset = _patient getVariable [QGVAR(Sepsis_Onset), _now];
    if (_onset == -1) then {
        _onset = _now;
        _patient setVariable [QGVAR(Sepsis_Onset), _onset, true];
    };
    // Adult combat casualty: distributive physiology begins meaningful but progresses over the first
    // fifteen minutes rather than becoming maximal on the stage-transition frame.
    _sepsisSeverity = 0.45 + (linearConversion [0, 900, (_now - _onset) max 0, 0, 0.40, true]);
};

private _permanent = _patient getVariable [QGVAR(Sepsis_Permanent), false];
if (!_permanent && {_stage == 3} && {missionNamespace getVariable ["ACME_hcEff_infection",false]}) then {
    private _onset = _patient getVariable [QGVAR(Sepsis_Onset), _now];
    private _limit = (GVAR(hardcoreSepsisEvacMinutes) max 1) * 60;
    if (_onset != -1 && {_now - _onset >= _limit}) then {
        _permanent = true;
        _patient setVariable [QGVAR(Sepsis_Permanent), true, true];
        if (!isNil "ACME_fnc_evacuationRequirementCommit") then {
            [_patient, true, true, true, false] call ACME_fnc_evacuationRequirementCommit;
        } else {
            _patient setVariable ["ACME_requiresEvac", true, true];
        };
    };
};

if (_permanent && {!(_patient getVariable ["ACME_requiresEvac",false])}) then {
    if (!isNil "ACME_fnc_evacuationRequirementCommit") then {
        [_patient,true,true,true,false] call ACME_fnc_evacuationRequirementCommit;
    } else {
        _patient setVariable ["ACME_requiresEvac",true,true];
    };
};

// Source-separated drives. ACME's existing endpoints compose them exactly once.
private _hrAdj = switch (_stage) do {
    case 1: {3};
    case 2: {8};
    case 3: {12 + (12 * _sepsisSeverity)};
    default {0};
};
_hrAdj = (_hrAdj + (3 * _feverC)) min 30;

private _rrAdj = switch (_stage) do {
    case 1: {1};
    case 2: {3};
    case 3: {5 + (5 * _sepsisSeverity)};
    default {0};
};
_rrAdj = (_rrAdj + (1.2 * _feverC)) min 14;

private _resistDelta = switch (_stage) do {
    case 2: {-4};
    case 3: {-36 * _sepsisSeverity};
    default {0};
};

private _metabolicDemand = switch (_stage) do {
    case 1: {1.04};
    case 2: {1.12};
    case 3: {1.18 + (0.22 * _sepsisSeverity)};
    default {1};
};
// Septic capillary leak/relative hypovolemia is an effective-volume deficit, not lost RBC mass.
private _effectiveVolumeDeficitL = if (_stage == 3) then {1.4 * _sepsisSeverity} else {0};
private _coagMult = if (_stage == 3) then {1 + (0.25 * _sepsisSeverity)} else {1};

if (_permanent) then {
    // Hardcore sequelae are deliberately modest but field-unresolved. The patient can be stabilized
    // and transported; they are not forced into an unwinnable continuous collapse.
    _metabolicDemand = _metabolicDemand max 1.08;
    _effectiveVolumeDeficitL = _effectiveVolumeDeficitL max 0.35;
    _coagMult = _coagMult max 1.10;
};

[_patient,QGVAR(HR_Adjust),_hrAdj,0.05,5] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(RR_Adjust),_rrAdj,0.05,5] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(Resistance_Delta),_resistDelta,0.05,5] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(Metabolic_Demand),_metabolicDemand,0.002,5] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(EffectiveVolumeDeficitL),_effectiveVolumeDeficitL,0.005,5] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(Coag_Mult),_coagMult,0.002,5] call ACME_fnc_setVarNetApprox;
[_patient,QGVAR(Sepsis_Severity),_sepsisSeverity,0.005,5] call ACME_fnc_setVarNetApprox;

if ((_stage >= 2 || {_permanent}) && {!isNil "ACME_circ_activePatients"}) then {
    ACME_circ_activePatients pushBackUnique _patient;
};
