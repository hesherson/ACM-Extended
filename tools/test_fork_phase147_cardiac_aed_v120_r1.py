#!/usr/bin/env python3
"""B238: execute the reviewed historical contract under pytest and direct CLI."""

def test_current_contract():
    """Phase 147: ACM-native cardiac thresholds, one vital writer/tick, AED beat/QRS lock and v1.2.0-r0 r1."""
    from pathlib import Path
    import re

    ROOT = Path(__file__).resolve().parents[1]

    def txt(path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8", errors="replace")

    def need(cond: bool, msg: str) -> None:
        if not cond:
            raise AssertionError(msg)

    cfg = txt("addons/acm_extended/config.cpp")
    startup = txt("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    debug = txt("addons/acm_extended/functions/fn_debugMenu.sqf")
    unit = txt("addons/core/overrides/fnc_handleUnitVitals.sqf")
    critical = txt("addons/core/functions/fnc_handleCriticalVitals.sqf")
    threshold = txt("addons/acm_extended/functions/fn_rhythmThresholdTick.sqf")
    rhythm_tick = txt("addons/acm_extended/functions/fn_rhythmTick.sqf")
    handle = txt("addons/circulation/functions/fnc_handleAED.sqf")
    getter = txt("addons/circulation/functions/fnc_getEKGHeartRate.sqf")
    updater = txt("addons/circulation/functions/fnc_updateEKGHeartRate.sqf")
    monitor = txt("addons/circulation/functions/fnc_displayAEDMonitor.sqf")
    gen = txt("addons/circulation/functions/fnc_displayAEDMonitor_generateEKG.sqf")
    custom_gen = txt("addons/acm_extended/functions/fn_genRhythmEKG.sqf")
    register = txt("addons/acm_extended/functions/fn_registerCirculationRuntime.sqf")
    circ = txt("addons/acm_extended/functions/fn_circHandle.sqf")
    volume = txt("addons/circulation/functions/fnc_getBloodVolumeChange.sqf")

    # B238: public identity is an independent current-build contract, not a retired RC stamp.
    from build_contract import assert_current_build
    assert_current_build(ROOT)

    # ACE/ACM vital cadence remains authoritative: only handleUnitVitals invokes updateHeartRate and it is gated >=1 s.
    all_sqf = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in (ROOT/'addons').rglob('*.sqf'))
    call_count = all_sqf.count('] call ACEFUNC(medical_vitals,updateHeartRate);')
    need(call_count == 1, f"vitals: expected exactly one updateHeartRate call site, found {call_count}")
    need('if (_deltaT < 1) exitWith { false };' in unit, "vitals: one-second ACE cadence guard missing")
    need(unit.count('call ACEFUNC(medical_vitals,updateHeartRate)') == 1, "vitals: heart rate advances more than once per tick")

    # Restore ACM's native fatal-rate transition contract exactly at <40/>220, including its low-rate VF path.
    need('case (!_activeGracePeriod && {_heartRate < 40 || {_heartRate > 220}})' in unit,
         "thresholds: ACM fatal HR boundary missing")
    need('_unit setVariable [QEGVAR(circulation,Cardiac_RhythmState), ACM_Rhythm_VT, true];' in unit
         and '_unit setVariable [QEGVAR(circulation,CardiacArrest_TargetRhythm), ACM_Rhythm_PVT];' in unit,
         "thresholds: ACM >220 VT/PVT path missing")
    need('getMedicationCount) > 0.5' in unit and 'ACM_Rhythm_VF' in unit and 'ACM_Rhythm_Asystole' in unit,
         "thresholds: ACM <40 adenosine-asystole / otherwise-VF path missing")
    need('_HR > 240 || _HR < 30' in critical and '_MAP > 200 || _MAP < 55' in critical,
         "critical: ACM grace limits changed")
    need('_HR > 245 || _HR < 10 || _MAP > 220 || _MAP < 30' in critical,
         "critical: ACM immediate fatal limits changed")
    need('_HR > 45 && _HR < 200 && _MAP > 60 && _MAP < 180' in critical
         and 'ACM_Rhythm_Sinus' in critical,
         "critical: ACM recovery hysteresis/VT exit path changed")
    need('single authority' in threshold.lower() and 'never latches' in threshold.lower(),
         "thresholds: Extended observer is not explicitly subordinate to ACM")
    need('ACME_rhythmACMFatalLowHR' in rhythm_tick and 'ACME_rhythmACMFatalHighHR' in rhythm_tick,
         "thresholds: custom rhythm does not release at ACM fatal boundaries")

    # The numeric AED rate is sampled, never animated through intermediate numbers.
    need('_lastSync + 5.25 < CBA_missionTime' in handle, "AED: stock ACM 5.25 s HR sample cadence missing")
    need('setVariable [QGVAR(AED_Pads_Display), round (_ekgHR max 0), true]' in handle,
         "AED: numeric HR sample is not a single assignment")
    need('call FUNC(updateEKGHeartRate)' in handle, "AED: controlled electrical-rate writer not called")

    # getEKGHeartRate is a true accessor. One writer owns electrical-rate mutation at >=1 s cadence.
    need('setVariable' not in getter, "AED: getEKGHeartRate has side effects")
    need('(_now - _last) < 1' in updater and '(_now - _last) max 1' in updater,
         "AED: electrical-rate delta-time/cadence guard missing")
    need('round (100 + random 120)' in updater, "VF: electrical display is not random 100-220")
    need('case ACM_Rhythm_PEA' in updater and 'max 60) min 100' in updater,
         "PEA: 60-100 bounded fluctuation missing")
    need('ACME_PEA_ElectricalGoalUntil' in updater and 'ACME_PEA_ElectricalGoal' in updater,
         "PEA: unstable wandering set-point missing")
    need('ACME_AED_ElectricalRateRhythm' in getter,
         "AED: stale previous-rhythm rate cache can leak across a transition")

    # One beat epoch owns both audio and R wave; no frame catch-up burst is allowed.
    for token in ('ACME_AED_NextRR', 'ACME_AED_PreviousRR', 'ACME_AED_BeatSerial'):
        need(token in handle and token in (gen + custom_gen), f"AED: shared beat-clock token missing: {token}")
    need('QGVAR(AED_Pads_LastBeep)' in handle and 'ACM_circulation_AED_Pads_LastBeep' in (gen + custom_gen),
         "AED: shared last-beep epoch missing")
    need('private _dueAt = _lastBeep + _hrDelay;' in handle and 'private _beatAt' in handle,
         "AED: audible beat does not use a stable due epoch")
    need('ACME_AED_MonitorCursorTime' in monitor and 'ACME_AED_MonitorCursorTime' in gen and 'ACME_AED_MonitorCursorTime' in custom_gen,
         "AED: waveform is not anchored to the actual committed screen cursor time")
    need('private _rawStepsDue' in monitor and 'private _stepsDue = _rawStepsDue min 4;' in monitor
         and 'if (_rawStepsDue > 4)' in monitor,
         "AED: render hitch guard/catch-up limiter missing")
    need('private _vitalsEKG = abs' in monitor and '> 10;' in monitor,
         "AED: stock-style HR regeneration hysteresis missing")
    need('private _fnc_spliceEKG' in monitor and '_freshSafeEKG' in monitor,
         "AED: safe rhythm transition bridge missing")
    need('private _chaoticJoin' in monitor, "AED: VF/torsades zero-crossing transition path missing")

    # Acid/base state has one writer and one >=1 s integration clock even though device circulation runs at 0.25 s.
    need('private _acidDt = 0;' in circ and 'if (_acidElapsed >= 1)' in circ and 'acidTickDt' in circ,
         "acidosis: one-second delta-time clock missing")
    need('ACME_plasmaLyteAcidCredit' in volume and 'metabolicAcidosis' not in volume[volume.find('case "PlasmaLyte"'):volume.find('case "PlasmaLyte"')+1200],
         "acidosis: fluid drainer still directly mutates metabolic acid state")
    writers = []
    for p in (ROOT/'addons').rglob('*.sqf'):
        t = p.read_text(encoding='utf-8', errors='replace')
        if 'set ["totalAcidosis"' in t or 'set ["metabolicAcidosis"' in t or 'set ["acidosis"' in t:
            writers.append(str(p.relative_to(ROOT)))
    need(writers == ['addons/acm_extended/functions/fn_circHandle.sqf'], f"acidosis: multiple state writers remain: {writers}")

    # Runtime PFHs are idempotent: replaying postInit cannot duplicate the 0.25 s circulation integration loop.
    need('CBA_fnc_removePerFrameHandler' in register and 'ACME_PFH_circHandle' in register,
         "runtime: circulation PFH is not idempotently replaced")

    print("phase 147 cardiac/AED cadence, thresholds, phase lock and v1.2.0-r0-r1 regression: PASS")

if __name__ == "__main__":
    test_current_contract()
