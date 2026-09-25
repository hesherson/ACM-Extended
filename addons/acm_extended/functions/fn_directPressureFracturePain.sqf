// a severe pain response when direct pressure is applied over a fractured limb.
// it runs on the patient owner, so the pain and consciousness changes are local-authoritative.
// call it as [_patient, _bodyPart, _medic] call ACME_fnc_directPressureFracturePain.
params ["_patient", ["_bodyPart", ""], ["_medic", objNull]];
_bodyPart = toLower _bodyPart;
if (isNull _patient || {!alive _patient}) exitWith {};
if !(missionNamespace getVariable ["ACME_DP_fracturePainEnabled", true]) exitWith {};
if !([_patient, _bodyPart] call ACME_fnc_directPressureHasFracture) exitWith {};

private _now = CBA_missionTime;
private _cooldown = missionNamespace getVariable ["ACME_DP_fracturePainCooldown", 8];
private _nextKey = format ["ACME_DP_FracturePainNext_%1", _bodyPart];
if (_now < (_patient getVariable [_nextKey, 0])) exitWith {};
_patient setVariable [_nextKey, _now + _cooldown, false];

// fracture manipulation is severe pain, and it should not cause artificial limb damage or bleeding.
private _painAmt = missionNamespace getVariable ["ACME_DP_fracturePainAmount", 1.0];
if (!isNil "ace_medical_fnc_adjustPainLevel") then {
    [_patient, _painAmt] call ace_medical_fnc_adjustPainLevel;
};

_patient setVariable ["ACME_DP_FracturePainLast", _now, true];
_patient setVariable ["ACME_DP_FracturePainPart", _bodyPart, true];

if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    private _name = if (isNull _medic) then {"A medic"} else {[_medic, false, true] call ace_common_fnc_getName};
    [_patient, "activity",
 "%1 applied direct pressure over a fractured %2, causing severe pain",
 "Direct pressure over fracture, %2, severe pain, %1",
 [_name, [_bodyPart, "short"] call ACME_fnc_bodyPartName]] call ACME_fnc_medLog;
};

// waking is decided exactly as ammonia salts and a slap decide it, and by the same two tests ACM uses. if the
// casualty cannot be roused by salts, pressing on a broken bone will not rouse them either.
// see ACM_circulation_fnc_handleMed_AmmoniaInhalantLocal and ACM_disability_fnc_slapAwakeLocal. both gate on
// stable vitals and on the casualty not being forced unconscious, then roll against oxygen saturation.
// the previous gate here was its own invention, at spo2 85 and MAP 60, which let a casualty who was far too sick
// for salts sit up because somebody leaned on a fracture.
if (!isNil "ACM_core_fnc_isForcedUnconscious" && {[_patient] call ACM_core_fnc_isForcedUnconscious}) exitWith {};
if (isNil "ace_medical_status_fnc_hasStableVitals") exitWith {};
if (!([_patient] call ace_medical_status_fnc_hasStableVitals)) exitWith {};

private _obtunded = _patient getVariable ["ACME_obtunded", false];
private _obtPosture = toLower (_patient getVariable ["ACME_obtunded_posture", ""]);
private _aceUncon = (_patient getVariable ["ACE_isUnconscious", false]) || {_patient getVariable ["ace_medical_unconscious", false]};
if !(_obtunded || _aceUncon) exitWith {};

// the same roll the salts make, on the same curve.
private _spo2 = _patient getVariable ["ace_medical_spo2", 99];
private _chance = linearConversion [80, 99, _spo2, 0.5, 1, true];
if (random 1 >= _chance) exitWith {};

// give the stimulus a short grace window, so the auto-obtunded evaluator does not immediately re-enter the same
// state before the player can react.
_patient setVariable ["ACME_obtunded_wakeStimGraceUntil", _now + (missionNamespace getVariable ["ACME_DP_fractureWakeGrace", 8]), true];

if (_obtunded) then {
    [_patient, false, false, _obtPosture, "recover"] call ACME_fnc_obtundedSet;
};

if (_aceUncon) then {
    // Pain stimulus is a real wake attempt, so use the same canonical request path as ammonia/slap.
    // Mark the casualty treated/lying BEFORE the wake so ACM's normal onUnconscious(false) path leaves them down
    // and offers Get Up rather than standing them automatically.
    [_patient, true, true] call ACM_core_fnc_setWasTreated;
    [_patient, true, true] call ACM_core_fnc_setLyingState;

    if ([_patient, true, "fracture-pressure"] call ACM_core_fnc_requestWake) then {
        ["ACM_core_playWakeUpSound", _patient] call CBA_fnc_localEvent;
    };

    // An AI has no get-up prompt and its own logic can immediately stand it, so retain the down posture.
    if (!isPlayer _patient) then {_patient setUnitPos "DOWN";};
};

// they come round on the floor, and they stay there. ACM's lying state and its own getup gate keep them down
// until something actually improves.
// there used to be a deferred call to ACM_core_fnc_getUp here, a third of a second later, which stood the
// casualty up. that is the rolling over and waking on their own.
[_patient, true, true] call ACM_core_fnc_setLyingState;
