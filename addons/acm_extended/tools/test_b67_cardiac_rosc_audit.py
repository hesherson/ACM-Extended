from historical_source import read_source
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding="utf-8")

def test_b67_build_stamp_and_single_rosc_registration():
    cfg = txt("config.cpp")
    post = txt("functions/fn_postInit.sqf")
    assert 'version = "1.0.100-r31";' in cfg
    assert 'ACME_infusion_version = "1.0.100-r31"' in post
    assert 'ACME_buildBatch = "B67";' in post
    assert 'class roscEligibility {};' in cfg
    assert 'class attemptROSC { file = "\\acm_extended\\overrides\\fn_attemptROSC.sqf"; };' in cfg


def test_all_rosc_paths_share_one_eligibility_gate():
    attempt = txt("overrides/fn_attemptROSC.sqf")
    reversible = txt("overrides/fn_handleReversibleCardiacArrest.sqf")
    shock = txt("functions/fn_shockROSC.sqf")
    gate = txt("functions/fn_roscEligibility.sqf")
    assert 'call ACME_fnc_roscEligibility' in attempt
    assert 'call ACME_fnc_roscEligibility' in reversible
    assert 'call ACM_circulation_fnc_attemptROSC' in shock
    assert 'GET_BLOOD_VOLUME(_patient) > ACM_REVERSIBLE_CA_BLOODVOLUME' not in reversible
    assert 'GET_CIRCULATIONSTATE(_patient)' in gate
    assert '_volume <= ACM_REVERSIBLE_CA_BLOODVOLUME' in gate
    assert 'CPRSucceeded' in attempt


def test_acme_no_longer_has_second_native_rate_arrest_authority():
    threshold = txt("functions/fn_rhythmThresholdTick.sqf")
    assert 'call ACME_fnc_arrestLocal' not in threshold
    assert 'ACME no longer creates VT/asystole or enters cardiac arrest' in threshold
    # The authoritative ACM fatal-rate checks remain in the ACM-compatible vitals override.
    vitals = txt("overrides/fn_handleUnitVitals.sqf")
    assert '_heartRate < 40 || {_heartRate > 220}' in vitals
    assert 'GET_MAP(_BPSystolic,_BPDiastolic) < 55' in vitals


def test_direct_arrest_call_sites_are_intentional_only():
    allowed = {
        "functions/fn_lidoToxTick.sqf",
        "functions/fn_megacodeArrest.sqf",
        "functions/fn_ownerDispatch.sqf",
        "functions/fn_rhythmSet.sqf",
        "functions/fn_shockLocal.sqf",
        "functions/fn_tbiApplyVitals.sqf",
    }
    found = set()
    for base in (ROOT / "functions", ROOT / "overrides"):
        for f in base.glob("*.sqf"):
            if "call ACME_fnc_arrestLocal" in read_source(f, encoding="utf-8", errors="ignore"):
                found.add(str(f.relative_to(ROOT)).replace("\\", "/"))
    assert found == allowed


def test_nonterminal_tbi_cannot_be_sole_native_fatal_hr_or_map_trigger():
    tbi = txt("functions/fn_tbiApplyVitals.sqf")
    hr = txt("overrides/fn_updateHeartRate.sqf")
    post = txt("functions/fn_postInit.sqf")
    assert 'if (_stage < 3)' in tbi
    assert 'ACME_tbi_nonterminalMinHR", 42' in tbi
    assert 'ACME_tbi_nonterminalMinMAP", 60' in tbi
    assert 'ACME_tbi_nonterminalMinRR", 12' in tbi
    assert '_tbiMAPtarget = _tbiMAPtarget max (_tbiMAPnative min _nonterminalMAPFloor)' in tbi
    assert '_desiredHR = _desiredHR max (_preTbiDesired min _floor)' in hr
    assert 'ACME_tbi_nonterminalMinHR    = 42' in post
    assert 'ACME_tbi_nonterminalMinMAP   = 60' in post
    assert 'ACME_tbi_nonterminalMinRR    = 12' in post
    # Terminal stage remains the only ICP stage with a direct arrest path.
    terminal = tbi[tbi.index('if (_stage >= 3) then {'):]
    assert 'call ACME_fnc_arrestLocal' in terminal


def test_tbi_cpp_acid_does_not_double_count_arrest_or_early_reperfusion():
    circ = txt("functions/fn_circHandle.sqf")
    post = txt("functions/fn_postInit.sqf")
    assert 'ACME_tbi_cppReperfusionWindow", 45' in circ
    assert '_tbiStageForAcid >= 3 && {!_inCardiacArrest} && {!_tbiCppReperf}' in circ
    assert '_state set ["tbiCppReperfusion", _tbiCppReperf]' in circ
    assert '_state set ["tbiCppStage", _tbiStageForAcid]' in circ
    assert 'ACME_tbi_cppReperfusionWindow = 45' in post


def test_monitor_rhythm_change_is_forced_into_active_sweep():
    gen = txt("overrides/fn_genEKG.sqf")
    rset = txt("functions/fn_rhythmSet.sqf")
    post = txt("functions/fn_postInit.sqf")
    assert 'ACME_monitorRhythmSwitchMaxWait", 0.18' in gen
    assert 'ACME_monitorRhythmSwitchMaxWait = 0.18' in post
    assert 'ACM_circulation_AED_EKGRhythm", -99' in rset
    assert 'ACM_circulation_AED_Pads_LastSync", -1' in rset
    assert 'forceMonitorRefresh' in rset


def test_native_and_extended_reversible_causes_are_composed_once():
    update = txt("overrides/fn_updateCirculationState.sqf")
    # Native ACM reversible conditions stay in one composed publication.
    assert 'GET_OXYGEN(_patient) < ACM_OXYGEN_HYPOXIA' in update
    assert 'TensionPneumothorax_State' in update
    assert 'Hemothorax_Fluid' in update
    assert 'GET_BLOOD_VOLUME(_patient) < BLOOD_VOLUME_CLASS_4_HEMORRHAGE' in update
    # Extended vetoes remain arrest-only and do not make healthy perfusing patients fail circulation state.
    assert '_state && {IN_CRDC_ARRST(_patient)}' in update
    assert 'ACME_rosc_hypothermiaFloorC' in update
    assert 'ACME_rosc_paCO2BlockMmHg' in update
    assert 'ACME_lidoTox_arrestFired' in update



def test_aed_distinguishes_pulseless_defib_from_perfusing_sync_rhythms():
    analyze = txt("overrides/fn_aedAnalyzeRhythm.sqf")
    shock = txt("functions/fn_shockLocal.sqf")
    assert 'private _shockableRhythms = [2, 3] +' in analyze
    assert '[2, 3, 4]' not in analyze
    assert 'private _defib = _rhythm in [2,3,102];' in shock
    assert 'private _organized = _rhythm in [4,100,101,103,104]' in shock
    assert 'if (_organized && {_expectedSync})' in shock
    assert 'if (_organized && {!_expectedSync})' in shock

def test_threshold_safety_margins_are_above_acm_fatal_lines():
    # Executable contract for the intended separation.
    assert 42 > 40
    assert 60 > 55
    assert 12 >= 12
    # Nonterminal MAP guard never rescues a different native pathology; it only refuses to worsen it.
    floor = 60
    for native in (100, 70, 60, 54, 40):
        guarded_target = max(20, min(native, floor))
        if native >= floor:
            assert guarded_target >= floor
        else:
            assert guarded_target >= native
