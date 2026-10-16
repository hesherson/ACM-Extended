// the "Assess Pupils" examine action callback. it reports the pupillary exam in plain language, graded from briskly
// reactive, through sluggish, anisocoria and a unilateral blown pupil, to bilateral fixed.
// the responsiveness is driven by the pupil state, set by the herniation cascade in fn_tbihandle, and by the ICP, so
// a patient with a normal pupil size but a rising ICP already reads as sluggish. that is the early observable tell
// before a pupil actually blows.
// the pupil state scale is 0 for PERRL, 1 for anisocoria or sluggish, 2 for a unilateral blown pupil and 3 for
// bilateral fixed. the first blown pupil is ipsilateral to the lesion, the side.
// _this is the ACE callback [_medic, _patient, _bodyPart].
params ["_medic", "_patient"];
if (isNull _patient) exitWith {};

private _state = _patient getVariable ["ACME_tbi_State", createHashMap];
private _hasState = count _state > 0;
private _pupils  = if (_hasState) then {_state getOrDefault ["pupils", 0]} else {0};
private _icp     = if (_hasState) then {_state getOrDefault ["icp", 10]} else {10};
private _cushing = _hasState && {_state getOrDefault ["cushing", false]};
private _side    = if (_hasState) then {_state getOrDefault ["side", "right"]} else {"right"};
private _other   = ["left", "right"] select (_side == "left");

// the ICP bands that color the description, which are tunable. below early is brisk, and above it is sluggish.
private _icpEarly = missionNamespace getVariable ["ACME_tbi_icpEarlyTell", 18];  // mmhg-like

private _hcP = ((missionNamespace getVariable ["ACME_hc_descriptors", false]) isEqualTo true);
private _exam = switch (_pupils) do {
    // it is clinical under hardcore descriptors and plain otherwise. the exam was already written in the clinical
    // register with no plain branch at all, so a player who had asked not to be given terminology got PERRL and
    // anisocoria anyway. both registers now come from one place.
    case 1: { if (_hcP) then { format ["Pupils: %1 sluggish/dilating, %2 brisk. Anisocoria.", _side, _other] }
              else { format ["The %1 pupil is bigger and slower than the %2.", _side, _other] } };
    case 2: { if (_hcP) then { format ["Pupils: %1 blown (fixed, dilated), %2 reactive.", _side, _other] }
              else { format ["The %1 pupil is wide open and does not react. The %2 still does.", _side, _other] } };
    case 3: { if (_hcP) then { "Pupils: bilateral fixed + dilated." }
              else { "Both pupils are wide open and neither reacts to light." } };
    default {
        if (_icp >= _icpEarly || _cushing) then {
            (if (_hcP) then { "Pupils: equal/round, sluggish bilaterally." }
             else { "Both pupils are equal but react slowly." })
        } else {
            (if (_hcP) then { "Pupils: PERRL." }
             else { "Both pupils are equal and react normally to light." })
        }
    };
};
// Cardiac arrest is not a normal, perfused pupil examination even when no TBI
// has been seeded. Apply a transient NO-FLOW finding only to the description;
// never mutate permanent TBI/herniation stage, so ROSC can restore the
// patient's actual neurologic response.
if (_patient getVariable ["ace_medical_inCardiacArrest", false] && {_pupils < 2}) then {
    _exam = if (_hcP) then {
        "Pupils: bilaterally sluggish/nonreactive during cardiac arrest."
    } else {
        "Both pupils react poorly or not at all while the heart is stopped."
    };
};

// B33: add an observed eye movement to the existing pupil findings. Read current
// effect-site drug loads, so old administration records or a fading sedation flag
// cannot leave this finding behind. Induction-normalized ketamine >= 1 is the
// game threshold; it must exceed the other hypnotics combined. Opioid adjuncts
// cannot promote an analgesic-only ketamine exposure into this finding.
// The original cause of unconsciousness does not matter: an already injured,
// unconscious patient can develop the same finding after deep ketamine sedation.
if (alive _patient
    && {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
    && {!(_patient getVariable ["ACME_roc_paralyzed", false])}
    && {_patient getVariable ["ACE_isUnconscious", false]}) then {
    private _parts = [_patient] call ACME_fnc_sedationComponents;
    _parts params ["_ket", "_prop", "_mid"];
    if (_ket >= 1 && {_ket > ((_prop max 0) + (_mid max 0))}) then {
        _exam = _exam + (if (_hcP) then {" Nystagmus."}
            else {" Their eyes are rapidly and involuntarily moving."});
    };
};

[_exam, 3, _medic] call ace_common_fnc_displayTextStructured;

if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    private _args = [[_medic, false, true] call ace_common_fnc_getName, _exam];
    [_patient, "activity", "%1 assessed pupils: %2", _args] call ace_medical_treatment_fnc_addToLog;
    [_patient, "quick_view", "%1 assessed pupils: %2", _args] call ace_medical_treatment_fnc_addToLog;
};
