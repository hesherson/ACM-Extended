#!/usr/bin/env python3
"""Phase 146: exact AED beat/sweep clock, safe rhythm bridging, Zone 3 visibility and native bandage rollback."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def txt(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def need(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)

cfg = txt("addons/acm_extended/config.cpp")
monitor = txt("addons/circulation/functions/fnc_displayAEDMonitor.sqf")
step = txt("addons/circulation/functions/fnc_displayAEDMonitor_updateStep.sqf")
gen = txt("addons/circulation/functions/fnc_displayAEDMonitor_generateEKG.sqf")
custom = txt("addons/acm_extended/functions/fn_genRhythmEKG.sqf")
handle = txt("addons/circulation/functions/fnc_handleAED.sqf")
hr = txt("addons/circulation/functions/fnc_getEKGHeartRate.sqf")
treatment = txt("addons/core/overrides/fnc_treatment.sqf")
actions = txt("addons/core/ACE_Medical_Treatment_Actions.hpp")

# Head positioning is head-only; body/chest no longer proxies to Head.
for cls in ("ACME_ElevateHead", "ACME_LowerHead"):
    m = re.search(rf"class\s+{cls}\s*:[^{{]+\{{(.*?)\n\s*\}};", cfg, re.S)
    need(m is not None, f"head: {cls} missing")
    body = m.group(1)
    need('allowedSelections[] = {"Head"};' in body, f"head: {cls} is not head-only")
need('set [2, "Head"]' not in treatment and 'select 2, "Body"' not in treatment,
     "head: treatment wrapper still proxies body/chest to Head")

# Zone 3 action is a normal all-location ACE treatment constrained specifically to Body by allowedSelections.
z = re.search(r'class\s+ACME_ApplyAAJT_Zone3\s*:[^{]+\{(.*?)\n\s*\};', cfg, re.S)
need(z is not None, "AAJT: Zone 3 apply class missing")
z = z.group(1)
need('displayName = "Apply AAJT-S (Zone 3 REBOA)";' in z, "AAJT: Zone 3 display name changed")
need('treatmentLocations = 0;' in z, "AAJT: Zone 3 must use ACE TREATMENT_LOCATIONS_ALL (0)")
need('allowedSelections[] = {"Body"};' in z, "AAJT: Zone 3 not exposed on Body/chest")
need('items[] = {"ACME_AAJT_S"};' in z and 'consumeItem = 1;' in z, "AAJT: Zone 3 item gate missing")
need('getCountOfItem' not in z, "AAJT: manual provider-only item check can hide a valid Zone 3 action")

# Experimental smart multi-bandage transaction is gone; native ACM action semantics are back.
need('class PressureBandage: BasicBandage {' in actions, "bandage: native PressureBandage missing")
need('callbackSuccess = QACEFUNC(medical_treatment,bandage);' in actions, "bandage: native callback missing")
need('items[] = {"ACME_PressureBandage"};' in actions and 'consumeItem = 1;' in actions,
     "bandage: native item consumption not restored")
need('smartBandage' not in actions, "bandage: smart bundle still wired")
for name in (
    "fnc_canSmartBandage.sqf", "fnc_getSmartBandagePlan.sqf", "fnc_getSmartBandageTime.sqf",
    "fnc_smartBandageApplyLocal.sqf", "fnc_smartBandageCancel.sqf", "fnc_smartBandageProgress.sqf",
    "fnc_smartBandageRestore.sqf", "fnc_smartBandageStart.sqf", "fnc_smartBandageSuccess.sqf",
):
    need(not (ROOT / "addons/damage/functions" / name).exists(), f"bandage: retired file remains: {name}")

# Provider presentation never delays the accepted clinical click.
need('provider presentation NEVER gates clinical treatment start' in treatment,
     "treatment: immediate clinical-start invariant missing")
need('ACME_treatmentPreflightActive", false' in treatment,
     "treatment: stale preflight retirement missing")

# ECG is sampled by exact time against the selected audio RR. Integer-width beat tiling is forbidden here.
need('private _sampleTime = _cursorEpoch + ((_i - _anchor) * _dt);' in gen, "AED: native exact-time sampler missing")
need('ACME_AED_PreviousRR' in gen and 'ACME_AED_NextRR' in gen, "AED: waveform does not consume audio RR clock")
need('ACME_AED_BeatSerial' in gen and 'private _beatOrdinal' in gen, "AED: stable beat morphology ordinal missing")
need('(_rr / _dt)' in gen, "AED: morphology rate selection missing")

# Audio owns one selected interval for the full beat; the waveform reads that exact interval.
need('private _hrDelay = _patient getVariable ["ACME_AED_NextRR", _nominalRR];' in handle,
     "AED: audible scheduler still recomputes its due interval independently")
need('ACME_AED_ClockRhythm' in handle and 'ACME_AED_BeatSerial' in handle,
     "AED: rhythm clock reset / beat serial missing")
need('_patient setVariable ["ACME_AED_NextRR", _nextRR, false];' in handle,
     "AED: selected next RR is not published locally")

# Mid-sweep changes bridge the CURRENT scheduled continuation, not stale prior-sweep display samples.
need('private _ekgBasis = if (count _monitorArray_EKGRefresh >= AED_MONITOR_WIDTH)' in monitor,
     "AED: bridge still starts from stale display future")
need('private _fnc_spliceEKG' in monitor and '[_ekgBasis, _freshEKG, _freshSafeEKG, _startIndex, _rhythmChangeEKG] call _fnc_spliceEKG' in monitor,
     "AED: safe EKG splice/bridge missing")
need('private _columns = if (_rhythmChange) then {8} else {4};' in monitor,
     "AED: rhythm transition bridge width missing")

# The sweep is an accumulator, not a frame-quantized 30 ms timer; controls render sample N -> N+1.
need('private _rawStepsDue = floor (((CBA_missionTime - GVAR(EKG_Tick)) max 0) / 0.03);' in monitor,
     "AED: fixed-step sweep accumulator missing")
need('GVAR(EKG_Tick) = GVAR(EKG_Tick) + (_stepsDue * 0.03);' in monitor,
     "AED: sweep still discards fractional timing remainder")
need('private _previousIndex = _updateStep - 1;' in step and '[_dlg, 0, _previousIndex' in step,
     "AED: line-control index is not sample N -> N+1")
need('_monitorArray_EKG set [0, _monitorArray_EKGRefresh select 0];' in step,
     "AED: left-edge wrap sample is not refreshed")

# All perfusing custom rhythms and torsades are screen-time anchored; torsades must not splice array[0] mid-sweep.
need('if (_rhythm in [100,101,102,103,104]) exitWith {' in custom,
     "AED: custom rhythms not routed through direct sampler")
need('if (_rhythm == 102) exitWith {' in custom and 'private _sampleTime = _cursorEpoch + ((_i - _anchor) * _dt);' in custom,
     "AED: torsades is not screen-time anchored")
need('ACME_AED_PreviousRR' in custom and 'ACME_AED_NextRR' in custom,
     "AED: organized custom rhythms do not share the audible RR clock")

# PEA is updated by one dedicated rate writer and the public getter is read-only.
updater = txt("addons/circulation/functions/fnc_updateEKGHeartRate.sqf")
need('case ACM_Rhythm_PEA' in updater and 'ACME_PEA_ElectricalGoal' in updater,
     "PEA: controlled electrical-rate writer missing")
need('max 60) min 100' in updater, "PEA: 60-100 electrical-rate clamp missing")
need('setVariable' not in hr, "PEA/AED: getEKGHeartRate is no longer side-effect free")
for path in (
    "addons/acm_extended/functions/fn_arrestLocal.sqf",
    "addons/acm_extended/functions/fn_rhythmSet.sqf",
    "addons/circulation/functions/fnc_handleCardiacArrest.sqf",
    "addons/circulation/functions/fnc_handleReversibleCardiacArrest.sqf",
):
    t = txt(path)
    need('ACME_peaElectricalStart' in t, f"PEA: entry epoch missing in {path}")
    need('ACME_peaNormalMaxHR", 100' in t or 'ACME_peaElectricalStart' in t,
         f"PEA: new bounded seed defaults missing in {path}")

# Fractional R-R intervals must remain fractional; 111/131 BPM cannot be rounded into a repeated column period.
for bpm in (111, 131):
    rr = 60.0 / bpm
    columns = rr / 0.03
    need(abs(columns - round(columns)) > 0.005, f"test setup unexpectedly integer at {bpm} BPM")
    # Direct time sampling places nearest sample within half a column of each exact beat forever (no accumulation).
    worst = 0.0
    for n in range(1, 400):
        beat = n * rr
        sample = round(beat / 0.03) * 0.03
        worst = max(worst, abs(sample - beat))
    need(worst <= 0.0150001, f"AED: exact sampler math exceeds half-column error at {bpm} BPM")

print("phase 146 AED phase lock / Zone 3 / bandage rollback regression: PASS")
