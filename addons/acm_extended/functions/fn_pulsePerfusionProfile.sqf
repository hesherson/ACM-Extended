/*
 * ACME pulse-perfusion profile.
 *
 * Separates the electrical ventricular rate from the mechanically palpable rate.  This is deliberately
 * used only by manual pulse assessment/presentation; the monitor keeps the electrical rhythm and rate.
 *
 * Arguments: [patient, bodyPart]
 * Returns: [palpable, electricalHR, mechanicalHR, strength0to1, character, irregularity0to1, deficit0to1,
 *           systolic, diastolic, pulsePressure]
 */
params [["_patient", objNull, [objNull]], ["_bodyPart", "Body", [""]]];
if (isNull _patient) exitWith {[false,0,0,0,"absent",0,1,0,0,0]};

private _part = toLowerANSI _bodyPart;
private _cutoff = switch (_part) do {
    case "head": {60};
    case "leftarm";
    case "rightarm": {80};
    case "leftleg";
    case "rightleg": {70};
    default {60};
};

private _electricalHR = (_patient getVariable ["ace_medical_heartRate", 0]) max 0;
private _bp = if (!isNil "ace_medical_status_fnc_getBloodPressure") then {
    [_patient] call ace_medical_status_fnc_getBloodPressure
} else {
    _patient getVariable ["ace_medical_bloodPressure", [0,0]]
};
_bp params [["_dia",0],["_sys",0]];
private _pp = (_sys - _dia) max 0;

private _rhythm = if (!isNil "ACME_fnc_rhythmGet") then {[_patient] call ACME_fnc_rhythmGet} else {0};
private _torsadesPerfusion = if (_rhythm == 102) then {
    (_patient getVariable ["ACME_rhythm_torsadesPerfusion",1]) max 0 min 1
} else {1};
private _torsadesMature = _rhythm == 102 && {
    (_patient getVariable ["ACME_rhythm_torsadesNonPerfusing",false]) || {_torsadesPerfusion <= 0.001}
};

private _tourniqueted = if (!isNil "ace_medical_treatment_fnc_hasTourniquetAppliedTo") then {
    [_patient, _bodyPart] call ace_medical_treatment_fnc_hasTourniquetAppliedTo
} else {false};
// Pulse assessment accepts names; the shared occlusion API accepts ACE body-part indices.
private _partIndex = ["head","body","leftarm","rightarm","leftleg","rightleg"] find _part;
private _aajt = if (!isNil "ACME_fnc_aajtOccludes") then {[_patient,_partIndex] call ACME_fnc_aajtOccludes} else {false};
private _mechanicalPulse = alive _patient
    && {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
    && {!_torsadesMature}
    && {!_tourniqueted}
    && {!_aajt}
    && {!isNil "ACM_circulation_fnc_hasPulse"}
    && {[_patient, true, _bodyPart] call ACM_circulation_fnc_hasPulse};

if (!_mechanicalPulse || {_electricalHR <= 0}) exitWith {
    [false,_electricalHR,0,0,"absent",0,1,_sys,_dia,_pp]
};

private _marginScore = linearConversion [0,60,(_sys - _cutoff),0,1,true];
private _ppScore = linearConversion [8,60,_pp,0,1,true];
private _strength = ((0.58 * _marginScore) + (0.42 * _ppScore)) max 0 min 1;

private _irregularity = 0;
private _deficit = 0;

// AFib: the monitor counts QRS complexes; the fingers count only ventricular contractions that actually generate
// enough stroke volume to reach the selected artery.  RVR loses more beats, especially as perfusion weakens.
if (_rhythm == 100) then {
    _irregularity = 0.34;
    _deficit = 0.08
        + (linearConversion [120,220,_electricalHR,0,0.24,true])
        + ((1 - _strength) * 0.24);
};
if (_rhythm == 103) then {
    _irregularity = 0.30;
    _deficit = 0.03 + ((1 - _strength) * 0.12);
};

// During the torsades entry strip, electrical activity remains rapid while effective ventricular output collapses.
// The same 1 -> 0 perfusion fraction used by the rhythm morph progressively weakens the palpable impulse and drops
// the mechanical beat count. At the end of the conversion there is no palpable pulse at any site.
if (_rhythm == 102) then {
    private _p = _torsadesPerfusion max 0 min 1;
    _strength = _strength * ((_p ^ 1.35) max 0);
    _deficit = _deficit max (linearConversion [1,0,_p,0.04,0.98,true]);
    _irregularity = linearConversion [1,0,_p,0.10,0.34,true];
};

// Any very rapid organized rhythm can have a mechanical pulse deficit when filling time and stroke volume fall.
// This is intentionally smaller than AFib unless perfusion is already poor.
if (_rhythm in [0,101,104] && {_electricalHR > 135}) then {
    _deficit = _deficit max (
        (linearConversion [135,230,_electricalHR,0,0.18,true])
        * (linearConversion [0.75,0.15,_strength,0.25,1,true])
    );
};

// Phenotype-specific pulse character.  Early distributive shock can be warm/bounding despite hypotension;
// hemorrhagic/cardiogenic/obstructive shock tends toward a narrow, thready pressure wave.
private _shockType = toLowerANSI (_patient getVariable ["ACME_shock_phenotype", ""]);
private _shockSev = (_patient getVariable ["ACME_shock_severity",0]) max 0 min 1;
if (_shockType == "distributive" && {_shockSev > 0.2}) then {
    _strength = (_strength + (0.18 * _shockSev)) min 1;
};
if (_shockType in ["hemorrhagic","cardiogenic","obstructive","burn"] && {_shockSev > 0.2}) then {
    _strength = (_strength - (0.20 * _shockSev)) max 0;
    _deficit = (_deficit + (0.10 * _shockSev)) min (if (_rhythm == 102) then {0.98} else {0.65});
};

_deficit = (_deficit max 0) min (if (_rhythm == 102) then {0.98} else {0.65});
private _mechanicalHR = _electricalHR * (1 - _deficit);

private _character = "normal";
if (_rhythm == 102 && {_torsadesPerfusion < 0.78}) then {_character = "thready";};
if (_pp <= 25 || {_sys <= (_cutoff + 15)} || {_strength < 0.32}) then {_character = "thready";};
if (_character == "normal" && {(_pp >= 55 && {_sys >= (_cutoff + 25)}) || {_shockType == "distributive" && {_shockSev > 0.35}}}) then {
    _character = "bounding";
};

[true,_electricalHR,_mechanicalHR,_strength,_character,_irregularity,_deficit,_sys,_dia,_pp]
