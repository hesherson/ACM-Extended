private _acmeBinding = "NA3:updateHeartRate";
#include "\x\ACM\addons\core\script_component.hpp"
/*
 * Author: Glowbal
 * Update the heart rate
 *
 * Arguments:
 * 0: The Unit <OBJECT>
 * 1: Heart Rate Adjustments <NUMBER>
 * 2: Time since last update <NUMBER>
 * 3: Sync value? <BOOL>
 *
 * ReturnValue:
 * Current Heart Rate <NUMBER>
 *
 * Example:
 * [player, 0, 1, false] call ace_medical_vitals_fnc_updateHeartRate
 *
 * Public: No
 */

params ["_unit", "_hrTargetAdjustment", "_deltaT", "_syncValue"];
if (!local _unit) exitWith {_unit getVariable ["ace_medical_heartRate", 0]};

private _desiredHR = ACM_TARGETVITALS_HR(_unit);
private _heartRate = GET_HEART_RATE(_unit);
// NA3 integration. Native medications and native compensation are evaluated below exactly once.
// Extended target values are offsets from the unchanged native resting baseline, not replacement returns.
private _base = _unit getVariable ["ACME_hrRestBaseline", _desiredHR];
private _custom = [_unit] call ACME_fnc_rhythmGet;
if (_custom in [100,101,102,103,104]) then {_desiredHR = _unit getVariable ["ACME_rhythm_targetHR", _desiredHR];};
// Apply circulation first. TBI is applied separately so nonterminal ICP cannot be the sole reason an otherwise
// viable ACM target crosses the fatal <40 bpm line. Terminal stage 3 is intentionally exempt.
private _circTarget = _unit getVariable ["ACME_hrTarget_circ", -1];
if (_circTarget >= 0 && {missionNamespace getVariable ["ACME_sys_circ", true]}) then {
    _desiredHR = _desiredHR + (_circTarget - _base);
};
// Shock phenotype contributes as its own additive chronotropic source. Keeping it here, in the single
// authoritative HR endpoint, prevents a phenotype PFH from fighting circulation/rhythm target writers.
_desiredHR = _desiredHR + (_unit getVariable ["ACME_shock_hrAdj", 0]);
// Adult infection physiology publishes a source-separated fever/sepsis drive. This endpoint remains the only HR writer.
_desiredHR = _desiredHR + (_unit getVariable ["ACM_infection_HR_Adjust", 0]);
private _preTbiDesired = _desiredHR;
private _tbiTarget = _unit getVariable ["ACME_hrTarget_tbi", -1];
if (_tbiTarget >= 0 && {missionNamespace getVariable ["ACME_sys_tbi", true]}) then {
    _desiredHR = _desiredHR + (_tbiTarget - _base);
    private _tbiState = _unit getVariable ["ACME_tbi_State", createHashMap];
    private _tbiStage = _tbiState getOrDefault ["herniationStage", 0];
    if (_tbiStage < 3) then {
        private _floor = missionNamespace getVariable ["ACME_tbi_nonterminalMinHR", 42];
        // If some non-TBI pathology is already below the floor, don't rescue it; just don't make it worse.
        _desiredHR = _desiredHR max (_preTbiDesired min _floor);
    };
};
_desiredHR = _desiredHR + ([_unit] call ACME_fnc_laryngoStimulusEffect) * (missionNamespace getVariable ["ACME_laryngo_hrSurge", 10]);
_desiredHR = (_desiredHR max 0) min (missionNamespace getVariable ["ACME_hrHardMax", 260]);
_unit setVariable ["ACME_hrWrapLast", CBA_missionTime, false];

if (!(alive _unit) || !(HAS_PULSE(_unit)) || alive (_unit getVariable [QACEGVAR(medical,CPR_provider), objNull])) then {
    if (alive (_unit getVariable [QACEGVAR(medical,CPR_provider), objNull])) then {
        if (_heartRate == 0) then { _syncValue = true }; // always sync on large change
        _heartRate = random [100, 110, 120];
    } else {
        if (_heartRate != 0) then { _syncValue = true }; // always sync on large change
        _heartRate = 0
    };
} else {
    private _hrChange = 0;
    private _targetHR = 0;
    private _bloodVolume = GET_BLOOD_VOLUME(_unit);
    private _oxygenSaturation = GET_OXYGEN(_unit);
    if (_bloodVolume > BLOOD_VOLUME_CLASS_4_HEMORRHAGE) then {
        private _timeSinceROSC = (CBA_missionTime - (_unit getVariable [QEGVAR(circulation,ROSC_Time), -45]));

        GET_BLOOD_PRESSURE(_unit) params ["_BPDiastolic", "_BPSystolic"];
        private _meanBP = GET_MAP(_BPSystolic,_BPDiastolic);
        private _painLevel = GET_PAIN_PERCEIVED(_unit);
        // The atrial rhythm already supplies its ventricular-rate target. Its own discomfort must not
        // add another sympathetic HR boost on top of that target. Native wound/tourniquet pain still
        // contributes normally, as do medication, oxygen, blood-loss and other physiological effects.

        _targetHR = _desiredHR;
        if (_bloodVolume <= BLOOD_VOLUME_CLASS_2_HEMORRHAGE) then {
            private _targetBP = linearConversion [BLOOD_VOLUME_CLASS_2_HEMORRHAGE, BLOOD_VOLUME_CLASS_3_HEMORRHAGE, _bloodVolume, 90, 80, true];

            if (_bloodVolume <= BLOOD_VOLUME_CLASS_3_HEMORRHAGE) then {
                _targetBP = linearConversion [BLOOD_VOLUME_CLASS_3_HEMORRHAGE, BLOOD_VOLUME_CLASS_4_HEMORRHAGE, _bloodVolume, 80, 40, true];
            };

            _targetHR = _desiredHR max (_heartRate * (_targetBP / (45 max _meanBP)));
        };

        if (_painLevel > 0.2) then {
            if !(IS_UNCONSCIOUS(_unit)) then {
                _targetHR = _targetHR max (_desiredHR + 50 * _painLevel);
            } else {
                _targetHR = _targetHR max (_desiredHR + 40 * _painLevel);
            };
        };
        // Increase HR to compensate for low blood oxygen/higher oxygen demand (e.g. running, recovering from sprint)
        private _oxygenDemand = _unit getVariable [VAR_OXYGEN_DEMAND, 0];
        private _missingOxygen = (ACM_TARGETVITALS_OXYGEN(_unit) - _oxygenSaturation);
        private _targetOxygenHR = _targetHR + ((_missingOxygen * (linearConversion [5, 20, _missingOxygen, 0, 2, true])) max (_oxygenDemand * -2000));
        _targetOxygenHR = _targetOxygenHR min ACM_TARGETVITALS_MAXHR(_unit);

        _targetHR = _targetHR max _targetOxygenHR;

        _targetHR = (_targetHR + _hrTargetAdjustment) max 0;
        // Perfusing torsades owns its ventricular rate. Generic compensatory tachycardia must not push the
        // 210-bpm torsades target across ACM's >220 native VT/PVT threshold and replace the morphology.
        if (_custom == 102) then {_targetHR = _targetHR min (_unit getVariable ["ACME_rhythm_targetHR",210]);};

        if (_timeSinceROSC < 45) then {
            _targetHR = _targetHR max (_desiredHR + 40 * ((30 / (_timeSinceROSC max 0.001)) min 1));
            _targetHR = _targetHR min ACM_TARGETVITALS_MAXHR(_unit);
        } else {
            if (_unit getVariable [QEGVAR(circulation,Hardcore_PostCardiacArrest), false]) then {
                _targetHR = _targetHR min (_targetHR / (_desiredHR max 0.001)) * (_desiredHR * 0.7);
            };
        };
        if (_custom == 102) then {_targetHR = _targetHR min (_unit getVariable ["ACME_rhythm_targetHR",210]);};

        _hrChange = round(_targetHR - _heartRate) / 2;
    } else {
        _hrChange = -round(_heartRate / 10);
    };
    if (_hrChange < 0) then {
        _heartRate = (_heartRate + _deltaT * _hrChange) max _targetHR;
    } else {
        _heartRate = (_heartRate + _deltaT * _hrChange) min _targetHR;
    };
};

_unit setVariable [VAR_HEART_RATE, _heartRate, _syncValue];

_heartRate
