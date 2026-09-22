/*
 * Shared cerebral-seizure drive versus anticonvulsant suppression.
 *
 * Important separation:
 *   - seizure drive describes the active neurologic/toxicologic cause.
 *   - medication suppression describes actual anticonvulsant effect.
 *   - rocuronium is intentionally absent: neuromuscular blockade can hide
 *     convulsions but cannot terminate cerebral seizure activity.
 *
 * Midazolam preserves the pre-existing ACME calibration exactly: an effective
 * count of 1 controls a baseline-drive seizure. Propofol uses the induction-
 * normalized native effect already consumed by sedationComponents. Ketamine
 * receives no seizure-control credit at low analgesic exposure; its contribution
 * ramps from ACME_seizure_ketamineControlFloor to induction level and can increase
 * modestly above induction.
 *
 * _this:
 *   0 patient
 *   1 lidocaine serum level
 *   2 TBI pre-herniation seizure cause
 *   3 Sarin seizure cause
 *   4 debug seizure cause
 *
 * returns:
 *   [drive, suppression, controlled, midazolam, propofol, ketamine]
 */
params [
    ["_patient", objNull, [objNull]],
    ["_lidoLevel", 0, [0]],
    ["_tbiCause", false, [false]],
    ["_sarinCause", false, [false]],
    ["_debugCause", false, [false]]
];

if (isNull _patient || {!alive _patient}) exitWith {[0,0,false,0,0,0]};

private _baseDrive = missionNamespace getVariable ["ACME_seizure_driveBase", 1.0];
private _drive = 0;

// Preserve the established lidocaine refractory curve: the old midazolam
// requirement was base + refractory * serum excess. That requirement now becomes
// seizure drive, so existing midazolam behavior is unchanged.
private _lidoClear = missionNamespace getVariable ["ACME_lido_seizureClearThreshold", 10];
private _lidoThreshold = missionNamespace getVariable ["ACME_lido_seizureThreshold", 12];
if (_lidoLevel >= _lidoClear) then {
    private _refrac = missionNamespace getVariable ["ACME_lido_seizureBenzoRefractory", 0.1];
    _drive = _drive max (_baseDrive + (_refrac * ((_lidoLevel - _lidoThreshold) max 0)));
};

if (_tbiCause) then {
    _drive = _drive max (missionNamespace getVariable ["ACME_seizure_driveTBI", _baseDrive]);
};
if (_sarinCause) then {
    _drive = _drive max (missionNamespace getVariable ["ACME_seizure_driveSarin", _baseDrive]);
};
if (_debugCause) then {
    _drive = _drive max (missionNamespace getVariable ["ACME_seizure_driveDebug", _baseDrive]);
};

// Medication-specific anticonvulsant contributions.
// Midazolam uses the old effective-administration count directly.
private _mid = ([_patient] call ACME_fnc_benzoOnBoard) max 0;
private _midSupp = _mid * (missionNamespace getVariable ["ACME_seizure_midazolamControlWeight", 1.0]);

// sedationComponents is already normalized to the medication kinetics used by
// ACME consciousness: ketamine and propofol at about 1.0 are induction-scale.
([_patient] call ACME_fnc_sedationComponents) params [
    ["_ket",0], ["_prop",0], ["_midSed",0], ["_fent",0], ["_adjunct",1], ["_sed",0]
];

private _propWeight = missionNamespace getVariable ["ACME_seizure_propofolControlWeight", 1.0];
private _propSupp = ((_prop max 0) min 3) * _propWeight;

// Low-dose ketamine used for analgesia/procedures must not silently count as
// status treatment. It begins contributing only above the configured floor,
// reaches the configured baseline strength at induction, and gets a smaller
// incremental contribution above induction.
private _ketFloor = (missionNamespace getVariable ["ACME_seizure_ketamineControlFloor", 0.30]) max 0 min 0.95;
private _ketWeight = missionNamespace getVariable ["ACME_seizure_ketamineControlWeight", 1.0];
private _ketExtra = missionNamespace getVariable ["ACME_seizure_ketamineExtraWeight", 0.35];
private _ketSupp = 0;
if (_ket > _ketFloor) then {
    private _toInduction = linearConversion [_ketFloor, 1, _ket, 0, _ketWeight, true];
    private _aboveInduction = (((_ket - 1) max 0) min 2) * _ketExtra;
    _ketSupp = _toInduction + _aboveInduction;
};

// Opioids are deliberately absent. Analgesia is not anticonvulsant therapy.
// Rocuronium is deliberately absent. Paralysis is not anticonvulsant therapy.
private _suppression = (_midSupp + _propSupp + _ketSupp)
    min (missionNamespace getVariable ["ACME_seizure_controlCap", 4.0]);

// Hysteresis prevents a drip sitting on the exact control threshold from
// flickering between seizure and postictal every physiology tick.
private _wasControlled = _patient getVariable ["ACME_seizure_suppressed", false];
private _hys = (missionNamespace getVariable ["ACME_seizure_controlHysteresis", 0.10]) max 0;
private _controlled = false;
if (_drive > 0) then {
    _controlled = if (_wasControlled) then {
        _suppression >= ((_drive - _hys) max 0)
    } else {
        _suppression >= _drive
    };
};

// Publish diagnostic scalars only in 0.05 increments. This keeps a remote debug
// panel useful without turning medication washout into per-tick network traffic.
private _qDrive = (round (_drive * 20)) / 20;
private _qSupp = (round (_suppression * 20)) / 20;
[_patient, "ACME_seizure_drive", _qDrive] call ACME_fnc_setVarNet;
[_patient, "ACME_seizure_suppression", _qSupp] call ACME_fnc_setVarNet;
[_patient, "ACME_seizure_suppressed", _controlled] call ACME_fnc_setVarNet;

[_drive, _suppression, _controlled, _midSupp, _propSupp, _ketSupp]
