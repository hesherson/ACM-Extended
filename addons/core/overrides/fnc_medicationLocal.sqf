#include "..\script_component.hpp"
/*
 * Author: Glowbal, mharis001
 * Local callback for administering medication to a patient.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 * 1: Body Part <STRING>
 * 2: Treatment <STRING>
 * 3: Medication Dose <NUMBER>
 * 4: Is IV? <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, "RightArm", "Morphine", 1] call ace_medical_treatment_fnc_medicationLocal
 *
 * Public: No
 */

// todo: move this macro to script_macros_medical.hpp?
#define MORPHINE_PAIN_SUPPRESSION 0.6
// 0.2625 = 0.6/0.8 * 0.35
// 0.6 = basic medication morph. pain suppr., 0.8 = adv. medication morph. pain suppr., 0.35 = adv. medication painkillers. pain suppr.
#define PAINKILLERS_PAIN_SUPPRESSION 0.2625

params ["_patient", "_bodyPart", "_classname", ["_dose", 1], ["_iv", false], ["_alreadyAdmitted", false], ["_delivery", []]];
TRACE_3("medicationLocal",_patient,_bodyPart,_classname);
private _preparedMixture = (_delivery param [4, false]) isEqualTo true;
// Critical RSI medications are ACM Extended gameplay systems, not disposable UI-only items. In ACE basic-medication
// mode the stock callback exits after handling only Morphine/Epinephrine/Painkillers; Ketamine and Rocuronium were
// therefore consumed successfully but never entered ace_medical_medications, which made both the physiology and
// ACME debug readers see exactly zero. Keep the server's global basic-mode behavior for ordinary ACE medication,
// but always run the complete ACM medication record path for the RSI/reversal family.
private _forceAdvanced = _classname in ["Ketamine", "Ketamine_IV", "Rocuronium", "Rocuronium_IV", "Sugammadex_IV"];
private _useAdvanced = ACEGVAR(medical_treatment,advancedMedication) || {_forceAdvanced};

// Medication has no effects on dead units
if (!local _patient) exitWith {["ace_medical_treatment_medicationLocal", _this, _patient] call CBA_fnc_targetEvent;};
if (isNull _patient || {!alive _patient} || {!(_dose isEqualType 0)} || {_dose <= 0} || {!finite _dose}) exitWith {};
if (_useAdvanced && {!([_classname, _iv, false, _preparedMixture] call ACME_fnc_medicationRouteAllowed)}) exitWith {};
if ((toLowerANSI _bodyPart) == "ej") then {_bodyPart = "Head";};
if !((toLowerANSI _bodyPart) in ["head","body","leftarm","rightarm","leftleg","rightleg"]) exitWith {};
// These are local infiltration agents, not systemic medication adjustments. Dose is mg or U.
if (_classname in ["Phentolamine", "Hyaluronidase"] && {!_iv} && {!_preparedMixture}) exitWith {
    [_patient, _bodyPart, toLowerANSI _classname, _dose] call ACME_fnc_vesicantReverse;
};
if (_classname in ["EpinephrineCardiac", "EpinephrineCardiac_IV"] && {!_iv} && {!_preparedMixture}) exitWith {};
if (_classname in ["EpinephrineCardiac", "EpinephrineCardiac_IV"]) then {_classname = "Epinephrine_IV";};

// Exit with basic medication handling if advanced medication not enabled
if (!_useAdvanced) exitWith {
    switch (_classname) do {
        case "Morphine": {
            private _painSuppress = GET_PAIN_SUPPRESS(_patient);
            _patient setVariable [VAR_PAIN_SUPP, (_painSuppress + MORPHINE_PAIN_SUPPRESSION) min 1, true];
        };
        case "Epinephrine": {
            [_patient, false, "epinephrine"] call FUNC(requestWake);
        };
        case "Painkillers": {
            private _painSuppress = GET_PAIN_SUPPRESS(_patient);
            _patient setVariable [VAR_PAIN_SUPP, (_painSuppress + PAINKILLERS_PAIN_SUPPRESSION) min 1, true];
        };
    };
};
TRACE_1("Running treatmentMedicationLocal with Advanced configuration for",_patient);


// Handle tourniquet on body part blocking blood flow at injection site
private _partIndex = ALL_BODY_PARTS find toLowerANSI _bodyPart;

if (!_alreadyAdmitted && {(HAS_TOURNIQUET_APPLIED_ON(_patient,_partIndex) || {[_patient, _partIndex] call ACME_fnc_aajtOccludes}) && (!_iv || (_iv && (!([_patient, _bodyPart] call EFUNC(circulation,hasIO)) || _partIndex > 3)))}) exitWith {
    TRACE_1("unit has tourniquets blocking blood flow on injection site",_tourniquets);
    private _occludedMedications = _patient getVariable [QACEGVAR(medical,occludedMedications), []];
    _occludedMedications pushBack [_partIndex, _classname, _dose, _iv, _delivery];
    _patient setVariable [QACEGVAR(medical,occludedMedications), _occludedMedications, true];
};

// Get adjustment attributes for used medication
private _defaultConfig = configFile >> "ACM_Medication" >> "Medications";
private _medicationConfig = _defaultConfig >> _classname;

private _timeInSystem           = GET_NUMBER(_medicationConfig >> "timeInSystem",getNumber (_defaultConfig >> "timeInSystem"));
private _timeTillMaxEffect      = GET_NUMBER(_medicationConfig >> "timeTillMaxEffect",getNumber (_defaultConfig >> "timeTillMaxEffect"));
private _maxDose                = GET_NUMBER(_medicationConfig >> "maxDose",getNumber (_defaultConfig >> "maxDose"));
private _maxDoseDeviation       = GET_NUMBER(_medicationConfig >> "maxDoseDeviation",getNumber (_defaultConfig >> "maxDoseDeviation"));
private _viscosityChange        = GET_NUMBER(_medicationConfig >> "viscosityChange",getNumber (_defaultConfig >> "viscosityChange"));
private _hrIncrease             = GET_ARRAY(_medicationConfig >> "hrIncrease",getArray (_defaultConfig >> "hrIncrease"));
private _incompatibleMedication = GET_ARRAY(_medicationConfig >> "incompatibleMedication",getArray (_defaultConfig >> "incompatibleMedication"));

private _administrationType = GET_NUMBER(_medicationConfig >> "administrationType",getNumber (_defaultConfig >> "administrationType"));
if (_preparedMixture) then {_administrationType = if (_iv) then {ACM_ROUTE_IV} else {ACM_ROUTE_IM};};
private _maxEffectTime = GET_NUMBER(_medicationConfig >> "maxEffectTime",getNumber (_defaultConfig >> "maxEffectTime"));

private _minEffectDose = GET_NUMBER(_medicationConfig >> "minEffectDose",getNumber (_defaultConfig >> "minEffectDose"));
private _maxEffectDose = GET_NUMBER(_medicationConfig >> "maxEffectDose",getNumber (_defaultConfig >> "maxEffectDose"));

private _painReduce = GET_NUMBER(_medicationConfig >> "painReduce",getNumber (_defaultConfig >> "painReduce"));
private _minPainReduce = GET_NUMBER(_medicationConfig >> "minPainReduce",getNumber (_defaultConfig >> "minPainReduce"));
private _maxPainReduce = GET_NUMBER(_medicationConfig >> "maxPainReduce",getNumber (_defaultConfig >> "maxPainReduce"));

private _weightEffect = GET_NUMBER(_medicationConfig >> "weightEffect",getNumber (_defaultConfig >> "weightEffect"));
private _absorptionEffect = GET_NUMBER(_medicationConfig >> "bloodlossEffect",getNumber (_defaultConfig >> "bloodlossEffect"));

_maxEffectDose = _maxEffectDose max 0.000001;
private _concentrationRatio = 1;
private _absorptionModifier = 1;

if (_absorptionEffect > 0) then {
    _absorptionModifier = linearConversion [4.5, BLOOD_VOLUME_CLASS_4_HEMORRHAGE, GET_BLOOD_VOLUME(_patient), 1, 0.1, true];
};

private _patientWeight = GET_BODYWEIGHT(_patient);

switch (_weightEffect) do {
    case 1: {
        _maxEffectDose = (_maxEffectDose / IDEAL_BODYWEIGHT) * _patientWeight;
        _minEffectDose = (_minEffectDose / IDEAL_BODYWEIGHT) * _patientWeight;

        _concentrationRatio = _dose / _maxEffectDose;

        if (_painReduce != 0) then {
            _painReduce = [(linearConversion [_minEffectDose, 0, (_dose * _absorptionModifier), _minPainReduce, 0]), (linearConversion [_minEffectDose, _maxEffectDose, (_dose * _absorptionModifier), _minPainReduce, _painReduce])] select (_dose > _minEffectDose);
        };
    };
    case 2: {
        _maxEffectDose = (_maxEffectDose / IDEAL_BODYWEIGHT) * _patientWeight;
        _minEffectDose = (_minEffectDose / IDEAL_BODYWEIGHT) * _patientWeight;

        _concentrationRatio = _dose / _maxEffectDose;

        if (_painReduce != 0) then {
            _painReduce = [(linearConversion [_minEffectDose, 0, (_dose * _absorptionModifier), _minPainReduce, 0]), (linearConversion [_minEffectDose, _maxEffectDose, (_dose * _absorptionModifier), _minPainReduce, _painReduce])] select (_dose > _minEffectDose);
        };
    };
    default {
        _concentrationRatio = _dose / _maxEffectDose;

        if (_painReduce != 0) then {
            if (_minEffectDose == _maxEffectDose) then {
                _painReduce = (_painReduce min _maxPainReduce) * (((_dose * _absorptionModifier) / (_minEffectDose max 0.000001)) min 1);
            } else {
                _painReduce = (linearConversion [_minEffectDose, _maxEffectDose, (_dose * _absorptionModifier), _minPainReduce, _painReduce]) min _maxPainReduce;
            };
        };
    };
};

_concentrationRatio = _concentrationRatio * _absorptionModifier;

private _heartRateChange = 0;

_hrIncrease params ["_hrIncreaseLow", "_hrIncreaseHigh"];

if ((_hrIncreaseLow + _hrIncreaseHigh) != 0) then {
    _heartRateChange = if (_concentrationRatio < 0.5) then {
        (linearConversion [0, 0.5, _concentrationRatio, 0, _hrIncreaseLow, true]) * 1.2
    } else {(linearConversion [0.5, 1, _concentrationRatio, _hrIncreaseLow, _hrIncreaseHigh]) * 1.2};
};

private _rrAdjust = GET_ARRAY(_medicationConfig >> "rrAdjust",getArray (_defaultConfig >> "rrAdjust"));
private _rrAdjustment = 0;

if ((_rrAdjust select 0) + (_rrAdjust select 1) != 0) then {
    _rrAdjustment = if ((_maxEffectDose * _concentrationRatio) < _minEffectDose && {_minEffectDose > 0}) then {
        linearConversion [0, _minEffectDose, (_maxEffectDose * _concentrationRatio), 0, (_rrAdjust select 0), true]
    } else {
        if (_minEffectDose >= _maxEffectDose) then {(_rrAdjust select 1) * _concentrationRatio}
        else {linearConversion [_minEffectDose, _maxEffectDose, (_maxEffectDose * _concentrationRatio), (_rrAdjust select 0), (_rrAdjust select 1)]}
    };
};

private _coSensitivityAdjust = GET_ARRAY(_medicationConfig >> "coSensitivityAdjust",getArray (_defaultConfig >> "coSensitivityAdjust"));
private _coSensitivityAdjustment = 0;

if ((_coSensitivityAdjust select 0) + (_coSensitivityAdjust select 1) != 0) then {
    _coSensitivityAdjustment = if ((_maxEffectDose * _concentrationRatio) < _minEffectDose && {_minEffectDose > 0}) then {
        linearConversion [0, _minEffectDose, (_maxEffectDose * _concentrationRatio), 0, (_coSensitivityAdjust select 0), true]
    } else {
        if (_minEffectDose >= _maxEffectDose) then {(_coSensitivityAdjust select 1) * _concentrationRatio}
        else {linearConversion [_minEffectDose, _maxEffectDose, (_maxEffectDose * _concentrationRatio), (_coSensitivityAdjust select 0), (_coSensitivityAdjust select 1)]}
    };
};

private _breathingEffectivenessAdjust = GET_ARRAY(_medicationConfig >> "breathingEffectivenessAdjust",getArray (_defaultConfig >> "breathingEffectivenessAdjust"));
private _breathingEffectivenessAdjustment = 0;

if ((_breathingEffectivenessAdjust select 0) + (_breathingEffectivenessAdjust select 1) != 0) then {
    _breathingEffectivenessAdjustment = if ((_maxEffectDose * _concentrationRatio) < _minEffectDose && {_minEffectDose > 0}) then {
        linearConversion [0, _minEffectDose, (_maxEffectDose * _concentrationRatio), 0, (_breathingEffectivenessAdjust select 0), true]
    } else {
        if (_minEffectDose >= _maxEffectDose) then {(_breathingEffectivenessAdjust select 1) * _concentrationRatio}
        else {linearConversion [_minEffectDose, _maxEffectDose, (_maxEffectDose * _concentrationRatio), (_breathingEffectivenessAdjust select 0), (_breathingEffectivenessAdjust select 1)]}
    };
};

// B14: additive reference-dose amplitudes. Splitting one dose into tiny infusion
// pulses must not change its total HR/RR/CO2/analgesic effect. Native per-type caps
// are applied after summation in handleUnitVitals, never once per pulse.
_heartRateChange = (_hrIncrease select 1) * 1.2 * _concentrationRatio;
_rrAdjustment = (_rrAdjust select 1) * _concentrationRatio;
_coSensitivityAdjustment = (_coSensitivityAdjust select 1) * _concentrationRatio;
_breathingEffectivenessAdjustment = (_breathingEffectivenessAdjust select 1) * _concentrationRatio;
private _referencePain = GET_NUMBER(_medicationConfig >> "painReduce",getNumber (_defaultConfig >> "painReduce"));
_painReduce = (_referencePain min _maxPainReduce) * _concentrationRatio;

private _medicationType = GET_STRING(_medicationConfig >> "medicationType",getText (_defaultConfig >> "medicationType"));

if (_medicationType == "Default") then {
    _medicationType = _classname;
};

// Adjust the medication effects and add the medication to the list
TRACE_3("adjustments",_heartRateChange,_painReduce,_viscosityChange);

// B13: route-configured clocks do not depend on arbitrary syringe/pulse partitioning.
// Keep a positive onset and elimination interval even for malformed external config.
_timeTillMaxEffect = (_timeTillMaxEffect max 0.01) min ((_timeInSystem max 1) - 0.02);
_timeInSystem = _timeInSystem max (_timeTillMaxEffect + 0.02);
_maxEffectTime = (_maxEffectTime max 0) min ((_timeInSystem - _timeTillMaxEffect - 0.01) max 0);
[_patient, _classname, _timeTillMaxEffect, _timeInSystem, _heartRateChange, _painReduce, _viscosityChange * _concentrationRatio, _administrationType, _maxEffectTime, _rrAdjustment, _coSensitivityAdjustment, _breathingEffectivenessAdjustment, _concentrationRatio, _medicationType, _partIndex] call ACEFUNC(medical_status,addMedicationAdjustment);

// Check for medication compatiblity
if (_classname in ["Rocuronium", "Rocuronium_IV", "Sugammadex_IV"]) then {[_patient] call ACME_fnc_medicationRecordIDs;};
[_patient, _classname, _maxDose, _maxDoseDeviation, _concentrationRatio, _maxEffectDose, _patientWeight, _incompatibleMedication] call ACEFUNC(medical_treatment,onMedicationUsage);
[_patient,_classname,_dose,_iv,_maxEffectDose,_delivery] call ACME_fnc_medicationExposure;
[_patient] call ACME_fnc_ownerRegister;

// Preserve the native four fields and append actual IV/IO delivery for Extended's route gate.
// The native subscriber in ACM circulation/XEH_postInit.sqf still consumes the first four fields.
[QEGVAR(circulation,handleMedicationEffects), [_patient, _bodyPart, _classname, _dose, _iv, _delivery]] call CBA_fnc_localEvent;
