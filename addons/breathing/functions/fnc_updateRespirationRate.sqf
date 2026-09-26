/* NA3 single respiratory endpoint. Preserve native drug/hypoxic contributors; mandatory breaths do not imply effort. */
params ["_unit", "_oxygenSaturation", ["_oxygenDemand", 0], ["_respirationRateAdjustment", 0], ["_coSensitivityAdjustment", 0], "_deltaT", "_syncValue"];
private _acmeBinding = "NA3:updateRespirationRate";
if (isNull _unit) exitWith {0};
if (!local _unit) exitWith {_unit getVariable ["ACM_breathing_RespirationRate", 0]};
// Native target remains authoritative; no separate rest-baseline writer exists.
private _base = _unit getVariable ["ACM_core_TargetVitals_RespirationRate", 18];
private _desired = _base max 1;
private _blast = if (missionNamespace getVariable ["ACME_sys_blastLung", true]) then {_unit getVariable ["ACME_blastLung_rrDrive", -1]} else {-1};
if (_blast > 0) then {_desired = _desired max _blast;};
// Fever/systemic infection raises neural respiratory drive; exact central apnea/TBI/seizure commands below still outrank it.
_desired = _desired + (_unit getVariable ["ACM_infection_RR_Adjust", 0]);
private _overload = _unit getVariable ["ACM_circulation_Overload_Volume", 0];
private _edemaThreshold = missionNamespace getVariable ["ACME_edema_threshold", 0.5];
if (_overload > _edemaThreshold) then {
    private _severity = linearConversion [_edemaThreshold, _edemaThreshold + (missionNamespace getVariable ["ACME_edema_fullSpan", 1.5]), _overload, 0, 1, true];
    _desired = _desired max (linearConversion [0, 1, _severity, 20, missionNamespace getVariable ["ACME_edema_tachypneaMax", 32], true]);
};
private _central = -1;
private _centralExact = false;
// Central command priority does not outrank delivered ventilation.
private _seizure = _unit getVariable ["ACME_seizure_rrDrive", -1];
private _tbi = _unit getVariable ["ACME_rrDrive_tbi", -1];
private _demo = _unit getVariable ["ACME_cs_rrDrive", -1];
if (missionNamespace getVariable ["ACME_sys_tbi", true] && {_tbi >= 0}) then {_central = _tbi;};
if (_demo >= 0) then {_central = _demo; _centralExact = true;};
if (_seizure >= 0) then {_central = _seizure; _centralExact = (_seizure == 0);};
if (_central >= 0) then {_desired = _central;};
private _missingOxygen = ((_unit getVariable ["ACM_core_TargetVitals_OxygenSaturation", 99]) * (1 + _coSensitivityAdjustment)) - _oxygenSaturation;
private _target = (_desired + (_missingOxygen * linearConversion [0,20,_missingOxygen,1,0.6,true])) max (_oxygenDemand * -500);
if (_unit getVariable ["ACE_isUnconscious", false]) then {_target = (_desired + 16) min _target;};
_target = ((_target + _respirationRateAdjustment) max 0) min 60;
// Complete central apnea and neuromuscular blockade are distinct from low native respiratory targets.
private _arrest = _unit getVariable ["ace_medical_inCardiacArrest", false];
private _paralyzed = _unit getVariable ["ACME_roc_paralyzed", false];
if (_centralExact) then {_target = (_desired + _respirationRateAdjustment) max 0 min 60;};
if (_central == 0 || {_arrest} || {_paralyzed} || {!alive _unit} || {(_unit getVariable ["ace_medical_heartRate", 80]) < 20}) then {_target = 0;};
private _effort = _unit getVariable ["ACME_resp_neuralRR", (_unit getVariable ["ACM_breathing_RespirationRate", 18])];
if (_centralExact || {_paralyzed} || {_arrest} || {!alive _unit}) then {_effort = _target;} else {
    _effort = _effort + ((_target - _effort) * ((_deltaT max 0) / 2 min 1));
};
_unit setVariable ["ACME_resp_neuralRR", _effort, _syncValue];
// ACME_vent_spontRR belongs to the ventilator's supported-breath count, not neural effort.
private _path = ([_unit] call ACM_airway_fnc_getAirwayState) > 0 && {( [_unit] call ACM_breathing_fnc_getBreathingState) > 0};
private _spasm = (missionNamespace getVariable ["ACM_CBRN_enable", false]) && {_unit getVariable ["ACM_CBRN_AirwaySpasm", false]}
    && {(([_unit, "Atropine", false] call ace_medical_status_fnc_getMedicationCount) + ([_unit, "Atropine_IV", false] call ace_medical_status_fnc_getMedicationCount)) < 3}
    && {!(_unit getVariable ["ACM_airway_SurgicalAirway_State", false])};
private _manualTimes = (_unit getVariable ["ACME_vent_manualBreathTimes", []]) select {CBA_missionTime - _x <= 60};
private _manual = count _manualTimes > 0;
private _rr = _effort;
if (missionNamespace getVariable ["ACME_sys_vent", true] && {_unit getVariable ["ACME_vent_driving", false]}) then {
    _rr = _unit getVariable ["ACME_vent_effectiveRR", 0];
} else {
    if (_manual) then {_rr = count _manualTimes;} else {
        if ([_unit] call ACM_core_fnc_bvmActive) then {_rr = 10;} else {
            if ([_unit] call ACM_core_fnc_cprActive) then {_rr = random [20,25,30];};
        };
    };
};
if (!_path || {_spasm} || {!alive _unit}) then {_rr = 0;};
_rr = _rr max 0 min 80;
_unit setVariable ["ACME_resp_deliveredRR", _rr, _syncValue];
_unit setVariable ["ACM_breathing_RespirationRate", _rr, _syncValue];
_rr
