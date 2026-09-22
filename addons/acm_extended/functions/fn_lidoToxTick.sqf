// the lidocaine toxicity arc, phase 2: the seizure. it is driven by the serum level, ACME_lido_serumLevel, built
// in phase 1.
// at or above the seizure threshold an unconscious patient seizes: a generalized tonic-clonic event with shared
// ACME physiology and the 1.35x GestureSpasm3-6 visual sequence. the recognizable physiologic tell is apnea. we
// drive a dedicated seizure rr channel, ACME_seizure_rrDrive, which is higher priority than the TBI
// drive in the updateRespirationRate sole-writer, to 0, and the SpO2 then crashes on its own through ACM's
// native oxygen model, because its updateoxygen drops the sat at maxdecrease whenever rr is 0. a sympathetic
// tachycardia is folded into the circ hr drive, and fn_circhandle reads the state.
// the phases run active, which is tonic-clonic with apnea, then postictal, where depressed breathing returns,
// then resolve. or it recurs immediately if the level is still toxic and untreated, which is status epilepticus,
// the pressure that forces stopping the drip plus a benzo.
// midazolam on board aborts the active seizure to postictal and suppresses re-triggering. the cardiac-toxicity
// band, above 15 mcg/ml, with bradycardia, hypotension, QRS and av block and asystole, is handled in the cardiac
// toxicity section below.
// call it as [_patient, _lidoLevel, _dt] call ACME_fnc_lidoToxTick.
params ["_patient", ["_lidoLevel", 0], ["_dt", 1]];
if (isNull _patient) exitWith {};

private _now = CBA_missionTime;
private _state = _patient getVariable ["ACME_lido_seizureState", ""];

// dose-graded benzo control. seizures get more refractory as the level climbs, so the midazolam needed to
// terminate and suppress scales with how far above the seizure threshold the patient is. an adequate dose aborts
// the active seizure and suppresses recurrence, and as midazolam washes out, because the effective count decays,
// or as the level climbs past what is on board, it breaks through again. that is the pressure to stop the drip
// and give lipid rather than just keep pushing benzo. a benzo controls the seizure and does not fix the cause.
// getMedicationCount returns [cumulativedose, effectivecount]. the second element is about 1 per fresh
// administration and decays as it ages out, so the requirement reads in whole pushes, where 1 push controls at
// threshold. older ACE returned a bare number, so both are handled.
private _inArrest = _patient getVariable ["ace_medical_inCardiacArrest", false];
private _thresh      = missionNamespace getVariable ["ACME_lido_seizureThreshold", 12];
private _clearThresh = missionNamespace getVariable ["ACME_lido_seizureClearThreshold", 10];
private _maxSec      = missionNamespace getVariable ["ACME_lido_seizureMaxSec", 120];  // a hard cap: 2 min seizing straight.
private _cooldownSec = missionNamespace getVariable ["ACME_lido_seizureCooldownSec", 30];  // a forced cooldown after an episode.
private _apneaRR     = missionNamespace getVariable ["ACME_lido_seizureApneaRR", 0];
private _adjunctRR   = missionNamespace getVariable ["ACME_lido_seizureAdjunctRR", 6];  // poor breathing with a surviving airway.
private _postRR      = missionNamespace getVariable ["ACME_lido_seizurePostictalRR", 9];
private _phaseEnd    = _patient getVariable ["ACME_lido_seizurePhaseEnd", 0];

// TBI-induced seizures. the pre-herniation decompensation stage, with cushing engaged at or above the cushing
// ICP and not yet herniating, is a high-likelihood seizure window, because a severely injured, decompensating
// brain tends to seize before it herniates. this reuses the whole seizure machine: the collapse, the pulsed
// convulsion, the 2-min cap, the 30 s cooldown and the airway block. the apnea it drives also retains CO2, which
// feeds the ICP model and can hasten the very herniation it precedes, which is the pressure to control the
// seizure and ventilate. once herniation actually begins, the picture is posturing and pupils rather than
// tonic-clonic, so the cause drops, gated by !herniating.
private _tbiState   = _patient getVariable ["ACME_tbi_State", createHashMap];
private _tbiPreHern = (_tbiState getOrDefault ["cushing", false]) && {!(_tbiState getOrDefault ["herniating", false])};

// Severe ACM nerve-agent toxicity joins this same state machine instead of running its old client-only camera
// shake. The CBRN effect owns this cause flag from its buildup threshold; a benzodiazepine suppresses the seizure
// without pretending to remove the toxin, so the episode can recur if the drug wears off while exposure persists.
private _sarinCause = _patient getVariable ["ACME_sarinSeizureCause", false];

// Debug-induced seizures are a temporary real cause, not an animation override. The debug action sets an expiry
// on the patient owner; while it is live the ordinary seizure state machine owns apnea, LOC, motion and postictal.
private _debugUntil = _patient getVariable ["ACME_debugSeizureUntil", 0];
private _debugCause = _debugUntil > _now;
if (!_debugCause && {_debugUntil > 0}) then {
    _patient setVariable ["ACME_debugSeizureUntil", nil, true];
};

// A seizure cause keeps an episode running and allows recurrence after a cooldown. Lidocaine has hysteresis,
// TBI remains the variable pre-herniation trigger, severe Sarin is deterministic, and debug is time-bounded.
private _causePresent = (_lidoLevel >= _clearThresh) || _tbiPreHern || _sarinCause || _debugCause;

private _tbiChance   = missionNamespace getVariable ["ACME_tbi_seizureChancePerTick", 0.3];
private _triggerNow  = (_lidoLevel >= _thresh) || _sarinCause || _debugCause || (_tbiPreHern && {random 1 < _tbiChance});

private _seizureControl = [_patient, _lidoLevel, _tbiPreHern, _sarinCause, _debugCause] call ACME_fnc_seizureControl;
_seizureControl params ["_seizureDrive", "_seizureSuppression", "_seizureControlled"];

switch (_state) do {
    case "active": {
        // a generalized tonic-clonic seizure is apnea. the whole-body muscle contraction of the tonic phase includes the
        // respiratory muscles, so the patient cannot ventilate at all: rr is driven to 0 and the SpO2 crashes through
        // ACM's apnea branch on its own. this holds even with an airway in and even with a TBI on top, because a tensed
        // patient does not breathe. a ventilator overrides it, because the machine breathes for them, and the rate-writer
        // priority in fn_postInit puts the vent first. the convulsion body motion runs through fn_seizuremotion. the
        // episode is hard-capped at ACME_lido_seizureMaxSec, ending on the cap, on an adequate benzo, or on the cause
        // clearing, and then a forced postictal cooldown runs before any recurrence.
        [_patient, "ACME_seizure_rrDrive", 0] call ACME_fnc_setVarNet;
        [_patient, true] call ACME_fnc_seizureMotion;  // idempotent. it guards its own duplicate handler.
        if (_seizureControlled || {!_causePresent} || {_now >= _phaseEnd}) then {
            [_patient, "ACME_lido_seizureState", "postictal"] call ACME_fnc_setVarNet;
            [_patient, "ACME_lido_seizurePhaseEnd", _now + _cooldownSec] call ACME_fnc_setVarNet;
            [_patient, "ACME_seizure_rrDrive", _postRR] call ACME_fnc_setVarNet;
            [_patient, false] call ACME_fnc_seizureMotion;  // stop the convulsion on entering the cooldown.
        };
    };
    case "postictal": {
        [_patient, "ACME_seizure_rrDrive", _postRR] call ACME_fnc_setVarNet;
        if (_now >= _phaseEnd) then {
            [_patient, "ACME_seizure_rrDrive", -1] call ACME_fnc_setVarNet;  // release rr back to the baseline or the TBI drive.
            if (_causePresent && {!_seizureControlled} && {!_inArrest}) then {
                // the cooldown is done and they are still toxic, so another episode runs. drop them unconscious and collapse into
                // ragdoll first.
                [_patient] call ACME_fnc_seizureCollapse;
                [_patient, "ACME_lido_seizureState", "active"] call ACME_fnc_setVarNet;
                [_patient, "ACME_lido_seizurePhaseEnd", _now + _maxSec] call ACME_fnc_setVarNet;
                [_patient, "ACME_seizure_rrDrive", _apneaRR] call ACME_fnc_setVarNet;
            } else {
                [_patient, "ACME_lido_seizureState", ""] call ACME_fnc_setVarNet;
            };
        };
    };
    default {
        // no seizure. trigger one if the level is in the seizure band, is not benzo-suppressed, and they are not already
        // arrested.
        if (_triggerNow && {!_seizureControlled} && {!_inArrest}) then {
            // a generalized seizure causes a loss of consciousness, so drop them unconscious and collapse into ragdoll
            // first.
            [_patient] call ACME_fnc_seizureCollapse;
            [_patient, "ACME_lido_seizureState", "active"] call ACME_fnc_setVarNet;
            [_patient, "ACME_lido_seizurePhaseEnd", _now + _maxSec] call ACME_fnc_setVarNet;
            [_patient, "ACME_seizure_rrDrive", _apneaRR] call ACME_fnc_setVarNet;
        } else {
            // make sure the seizure rr channel is released when not seizing, so it can never stick the patient apneic.
            if ((_patient getVariable ["ACME_seizure_rrDrive", -1]) >= 0) then {
                [_patient, "ACME_seizure_rrDrive", -1] call ACME_fnc_setVarNet;
            };
        };
    };
};

// cardiac toxicity, at a level at or above the cardiac threshold: bradycardia, hypotension, then bradyasystolic
// arrest.
// these are higher levels than the seizure band. as conduction fails the sympathetic seizure tachycardia gives
// way to progressive bradycardia, driven down in the circ hr block through min, so it overrides the seizure
// tachycardia, and the falling rate plus a layered vasodilation, a negative resistance folded into the
// updatePeripheralResistance override, drive hypotension.
// caught before the ceiling, all of this reverses as the level decays, by stopping the drip or giving lipid. at
// or above the arrest threshold it tips into asystole, which is a real arrest that needs CPR and ROSC plus
// removing the cause, rather than clearance alone. the bradycardia also stands in for a high-grade av block
// here, because the slow rate is the hemodynamic tell, and a QRS-morphology widening on the ecg is a later
// refinement.
private _cardThresh   = missionNamespace getVariable ["ACME_lido_cardiacThreshold", 15];
private _arrestThresh = missionNamespace getVariable ["ACME_lido_arrestThreshold", 25];
if (_lidoLevel < _cardThresh) then {
    // below the cardiac band: clear any cardiac-tox drive and re-arm the arrest one-shot.
    if ((_patient getVariable ["ACME_lidoTox_hrTarget", -1]) >= 0) then { _patient setVariable ["ACME_lidoTox_hrTarget", -1, true]; };
    if ((_patient getVariable ["ACME_lidoTox_resistDelta", 0]) != 0) then { _patient setVariable ["ACME_lidoTox_resistDelta", 0, true]; };
    if (_patient getVariable ["ACME_lidoTox_arrestFired", false]) then { _patient setVariable ["ACME_lidoTox_arrestFired", false, true]; };
} else {
    if (!_inArrest) then {
        private _sev   = linearConversion [_cardThresh, _arrestThresh, _lidoLevel, 0, 1, true];
        private _base  = _patient getVariable ["ACME_hrRestBaseline", 77];
        private _floor = missionNamespace getVariable ["ACME_lido_cardiacBradyFloor", 30];
        private _drop  = missionNamespace getVariable ["ACME_lido_cardiacResistDrop", 45];
        [_patient, "ACME_lidoTox_hrTarget", (linearConversion [0, 1, _sev, _base, _floor, true])] call ACME_fnc_setVarNet;
        [_patient, "ACME_lidoTox_resistDelta", (linearConversion [0, 1, _sev, 0, (-_drop), true])] call ACME_fnc_setVarNet;
        if (_lidoLevel >= _arrestThresh && {!(_patient getVariable ["ACME_lidoTox_arrestFired", false])}) then {
            // lethal toxicity gives a bradyasystolic arrest, through the canonical trigger of the rhythm, the target and
            // fatalvitals. it is a one-shot.
            [_patient, "ACME_lidoTox_arrestFired", true] call ACME_fnc_setVarNet;
            [_patient, 1, false] call ACM_circulation_fnc_setCardiacArrestTargetRhythm;  // asystole, preserve the original local-only write.
            [_patient, 1] call ACME_fnc_rhythmSet;
            [_patient, 1] call ACME_fnc_arrestLocal;
        };
    } else {
        // already arrested. ACM owns the vitals, so drop our hr and resistance drive.
        if ((_patient getVariable ["ACME_lidoTox_hrTarget", -1]) >= 0) then { _patient setVariable ["ACME_lidoTox_hrTarget", -1, true]; };
        if ((_patient getVariable ["ACME_lidoTox_resistDelta", 0]) != 0) then { _patient setVariable ["ACME_lidoTox_resistDelta", 0, true]; };
    };
};
