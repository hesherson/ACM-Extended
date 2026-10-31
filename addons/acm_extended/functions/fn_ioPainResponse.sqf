/* B190 IO pain/syncope contract. Runs on the patient owner.
 *
 * placement: IO insertion establishes at least moderate pain.
 *
 * medication: a medication bolus may hurt through an IO, but it does NOT count as the fluid-pressure episode,
 * does not drive pain to maximum, and can never schedule IO syncope.
 *
 * fluid: the FIRST admitted fluid through this physical IO generation decides eligibility. If the casualty was
 * already unconscious, that IO generation is permanently ineligible for fluid syncope even if they later wake
 * while the same bag keeps flowing. If initially conscious, the generation may schedule exactly one transient
 * syncope event. Removing/replacing the IO increments the line generation in fnc_setIVLocal and therefore creates
 * a fresh episode.
 */
params ["_patient", ["_bodyPart", "body"], ["_mode", "fluid"]];
if (isNull _patient || {!alive _patient} || {!local _patient}
    || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};
_bodyPart = toLowerANSI _bodyPart;
_mode = toLowerANSI _mode;

private _isUncon = (_patient getVariable ["ACE_isUnconscious", false])
    || {_patient getVariable ["ace_medical_unconscious", false]};

if (_mode == "placement") exitWith {
    private _floor = missionNamespace getVariable ["ACME_ioInsertionMinPain", 0.35];
    private _current = (_patient getVariable ["ace_medical_pain", 0]) max 0;
    private _delta = (_floor - _current) max 0;
    if (_delta > 0.001 && {!isNil "ace_medical_fnc_adjustPainLevel"}) then {
        [_patient, _delta] call ace_medical_fnc_adjustPainLevel;
    };
    if (_delta > 0.05 && {!_isUncon} && {!isNil "ace_medical_feedback_fnc_playInjuredSound"}) then {
        [_patient, "hit"] call ace_medical_feedback_fnc_playInjuredSound;
    };
};

// Medication through an IO can be painful, but medication mass is not the fluid-pressure event.
// Keep a moderate floor only so analgesics delivered through the IO can subsequently reduce pain normally.
if (_mode == "medication") exitWith {
    private _floor = missionNamespace getVariable ["ACME_ioMedicationPainFloor", 0.45];
    private _current = (_patient getVariable ["ace_medical_pain", 0]) max 0;
    private _delta = (_floor - _current) max 0;
    if (_delta > 0.001 && {!isNil "ace_medical_fnc_adjustPainLevel"}) then {
        [_patient, _delta] call ace_medical_fnc_adjustPainLevel;
    };
    if (_delta > 0.10 && {!_isUncon} && {!isNil "ace_medical_feedback_fnc_playInjuredSound"}) then {
        [_patient, "hit"] call ace_medical_feedback_fnc_playInjuredSound;
    };
};

if (_mode != "fluid") exitWith {};

// Actual admitted IO fluid is the severe pressure-pain event.
private _rawPain = (_patient getVariable ["ace_medical_pain", 0]) max 0;
if (_rawPain < 0.999) then {
    if (!isNil "ace_medical_fnc_adjustPainLevel") then {[_patient, 1] call ace_medical_fnc_adjustPainLevel;};
    if ((_patient getVariable ["ace_medical_pain", 0]) < 0.999) then {
        [_patient, [["pain", 1, true]]] call ACM_core_fnc_setAceMedicalState;
    };
};

// Episode identity comes from the physical IO line generation maintained by fnc_setIVLocal.
private _generations = _patient getVariable ["ACME_medicationLineGenerations", createHashMap];
if !(_generations isEqualType createHashMap) then {_generations = createHashMap;};
private _generationKey = format ["%1:-1", _bodyPart];
private _lineGeneration = _generations getOrDefault [_generationKey, 0];

private _episodeVar = format ["ACME_ioFluidSyncopeEpisode_%1", _bodyPart];
private _episode = _patient getVariable [_episodeVar, []];
if !(_episode isEqualType [] && {count _episode >= 3} && {(_episode select 0) == _lineGeneration}) then {
    // Eligibility is decided ONCE, by the first admitted fluid through this physical IO generation.
    _episode = [_lineGeneration, !_isUncon, false];
    _patient setVariable [_episodeVar, _episode, true];
};

private _eligible = _episode param [1, false];
private _consumed = _episode param [2, false];
if (!_eligible || {_consumed}) exitWith {};

// Consume the one-shot before scheduling so repeated flow ticks can never queue duplicates.
_episode set [2, true];
_patient setVariable [_episodeVar, _episode, true];

private _delay = (missionNamespace getVariable ["ACME_ioFluidSyncopeDelay", 3]) max 0.1;
private _transient = (missionNamespace getVariable ["ACME_ioFluidSyncopeSeconds", 3]) max 0.5;
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _owner = owner _patient;
// B237: the shared Local-event epoch changes on both sides of an ownership transfer.
// Matching owner ID alone cannot distinguish a departed and returning ownership period.
private _ownerEpoch = _patient getVariable ["ACME_providerLocalityEpoch", 0];

[{
    params ["_patient", "_bodyPart", "_lineGeneration", "_epoch", "_owner", "_transient", "_ownerEpoch"];
    if (isNull _patient || {!local _patient} || {!alive _patient}
        || {owner _patient != _owner}
        || {(_patient getVariable ["ACME_providerLocalityEpoch", 0]) != _ownerEpoch}
        || {([_patient] call ACME_fnc_clinicalEpoch) != _epoch}
        || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};

    private _generations = _patient getVariable ["ACME_medicationLineGenerations", createHashMap];
    if !(_generations isEqualType createHashMap) exitWith {};
    private _generationKey = format ["%1:-1", _bodyPart];
    if ((_generations getOrDefault [_generationKey, -1]) != _lineGeneration) exitWith {};

    private _alreadyUncon = (_patient getVariable ["ACE_isUnconscious", false])
        || {_patient getVariable ["ace_medical_unconscious", false]};
    if (!_alreadyUncon && {!isNil "ace_medical_fnc_setUnconscious"}) then {
        // One short IO syncope. ACE only forces the wake at the minimum time when vitals are actually stable.
        [_patient, true, _transient, true] call ace_medical_fnc_setUnconscious;
    };
}, [_patient, _bodyPart, _lineGeneration, _epoch, _owner, _transient, _ownerEpoch], _delay] call CBA_fnc_waitAndExecute;
