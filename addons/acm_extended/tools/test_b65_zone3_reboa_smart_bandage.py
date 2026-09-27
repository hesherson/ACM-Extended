"""Regression contracts for Zone 3 AAJT-S, corpse persistence, and the native-bandaging rollback."""
from historical_source import read_source
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def acme(name):
    return read_source(ROOT / "functions" / f"fn_{name}.sqf", encoding="utf-8-sig")


def text(path):
    return read_source(REPO / path, encoding="utf-8-sig")


def cfg_class(source, name):
    m = re.search(rf"\bclass\s+{re.escape(name)}\b[^{{]*\{{", source)
    assert m, f"config class missing: {name}"
    start = m.start()
    i = source.find("{", m.start())
    depth = 0
    for j in range(i, len(source)):
        if source[j] == "{":
            depth += 1
        elif source[j] == "}":
            depth -= 1
            if depth == 0:
                return source[start:j + 1]
    raise AssertionError(f"unclosed config class: {name}")


def test_zone3_action_and_all_aajt_applications_are_twenty_seconds():
    cfg = text("addons/acm_extended/config.cpp")
    zone = cfg_class(cfg, "ACME_ApplyAAJT_Zone3")
    assert 'displayName = "Apply AAJT-S (Zone 3 REBOA)";' in zone
    assert 'allowedSelections[] = {"Body"};' in zone
    assert 'treatmentTime = 20;' in zone
    assert 'aajt-s_zone3_reboa_ca.paa' in zone
    for name in ("ACME_ApplyAAJT_Inguinal", "ACME_ApplyAAJT_Axilla", "ACME_ApplyAAJT_Zone3"):
        assert 'treatmentTime = 20;' in cfg_class(cfg, name)
    assert (ROOT / "ui/items/aajt-s_zone3_reboa_ca.paa").is_file()


def test_aajt_occlusion_is_anatomically_scoped():
    from test_historical_cardiac_execution import test_aajt_application_routes_only_the_selected_limbs
    # The old first-substring slice read the duplicate-placement switch, not application.
    for part,expected in [('Body',['leftleg','rightleg']),('LeftLeg',['leftleg']),
                          ('RightLeg',['rightleg']),('LeftArm',['leftarm']),('RightArm',['rightarm'])]:
        test_aajt_application_routes_only_the_selected_limbs(part,expected)


def test_whole_limb_physiology_uses_single_occlusion_authority():
    hooks={'addons/core/overrides/fnc_updateWoundBloodLoss.sqf',
           'addons/circulation/functions/fnc_getIVFlowRate.sqf',
           'addons/circulation/functions/fnc_getBloodVolumeChange.sqf',
           'addons/core/overrides/fnc_medicationLocal.sqf',
           'addons/acm_extended/functions/fn_yFlushTick.sqf'}
    for path in hooks:
        assert 'ACME_fnc_aajtOccludes' in text(path),path
    assert '[_unit, _deltaT, _syncValues] call ACM_circulation_fnc_getBloodVolumeChange' in text('addons/core/overrides/fnc_getBloodVolumeChange.sqf')
    assert 'ACME_fnc_pulsePerfusionProfile' in text('addons/core/overrides/fnc_checkPulseLocal.sqf')
    from test_historical_cardiac_execution import test_aajt_pulse_occlusion_is_site_specific
    for placement,side,limbs in [('zone3','',['leftleg','rightleg']),('inguinal','leftleg',['leftleg']),
                                  ('inguinal','rightleg',['rightleg']),('axillaleft','',['leftarm']),('axillaright','',['rightarm'])]:
        test_aajt_pulse_occlusion_is_site_specific(placement,side,limbs)


def test_zone3_conscious_patient_is_collapsed_back_to_prone_without_network_loop():
    tick = acme("aajtDownedTick")
    force = acme("aajtForceProne")
    getup = text("addons/core/functions/fnc_getUp.sqf")
    assert '}, 0.20,' in tick
    assert 'in ["stand", "crouch"]' in tick
    assert 'ACME_fnc_aajtForceProne' in tick
    assert ', true]' not in tick[tick.index('private _handle'):], "posture PFH must not replicate variables each tick"
    assert 'ace_medical_engine_fnc_setUnconsciousAnim' in force
    assert '_patient setUnitPos "DOWN";' in force
    assert 'AmovPpneMstpSnonWnonDnon' in force
    z = getup[getup.index('if (_patient getVariable ["ACME_AAJT_zone3"'):getup.index('// Head elevation owns')]
    assert 'ACME_fnc_aajtDownedTick' in z
    assert 'exitWith' not in z, "Get Up must visibly start before Zone 3 collapses the patient"


def test_aajt_severe_pain_is_local_low_frequency_and_pharmacologically_suppressible():
    pain = acme("aajtPainTick")
    assert '0.82' in pain
    assert '}, 1.0,' in pain
    assert 'ace_medical_fnc_adjustPainLevel' in pain
    loop = pain[pain.index('private _handle'):]
    assert 'setVariable ["ace_medical_pain"' not in loop
    assert ', true]' not in loop, "pain maintenance must not publish a variable every second"


def test_old_bilateral_inguinal_state_migrates_to_one_side():
    owner = acme("ownerRegister")
    migrate = owner[:owner.index('private _headState')]
    assert 'ACME_AAJT_inguinalSide' in migrate
    assert 'ACME_AAJT_legs' in migrate
    assert '(count _legacy) == 1' in migrate
    assert '"leftleg"' in migrate and '"rightleg"' in migrate
    assert 'ACME_fnc_aajtStateCommit' in migrate


def test_dead_patient_freezes_workers_but_keeps_interventions_and_old_corpse():
    life = acme("registerClinicalLifecycleRuntime")
    resp = acme("registerRhythmLifecycleRuntime")
    death = acme("deathFreeze")
    assert 'EntityKilled' in life and 'ACME_fnc_deathFreeze' in life
    assert '["ace_medical_FullHeal", {_this call ACME_fnc_clearAllAilments}]' in life
    assert '[_oldUnit] call ACME_fnc_deathFreeze' in resp
    assert '[_newUnit] call ACME_fnc_clearAllAilments' in resp
    assert 'forEach [_oldUnit, _newUnit]' not in resp
    assert '[_patient, "begin", true] call ACME_fnc_clinicalReset' in death
    assert 'ACME_fnc_clearAllAilments' not in death
    for evidence in ('ACME_IV_Marks', 'ACME_AAJT_zone3', 'ACME_ETT_Inserted', 'ACM_breathing_Thoracostomy_State'):
        assert f'setVariable ["{evidence}", nil' not in death


def test_dead_patient_treatment_paths_do_not_reject_because_patient_is_dead():
    # These are high-use custom treatment paths whose former alive checks made death inferable from the menu/action.
    for name in ("directPressureStart", "directPressureTick", "medicationRequest",
                 "skBeginInjection", "skConfirmInjection", "skInjectSite", "salineFlush",
                 "epinephrinePushStored", "administerPushDoseEpi"):
        src = acme(name)
        assert '!alive _patient' not in src, f"dead-patient treatment rejection remains in {name}"

    # Owner settlement accepts a corpse transaction so provider inventory/syringe accounting completes,
    # then exits before any medication physiology can be created.
    line = acme("medicationLineLocal")
    dead = line.index("if (!alive _patient) exitWith")
    physiology = line.index("private _pending", dead)
    postmortem = line[dead:physiology]
    assert '[true, "postmortem: no physiology"]' in postmortem
    assert 'ACME_medicationAck' in postmortem
    assert 'ace_medical_treatment_fnc_medicationLocal' not in postmortem
    syringe = text("addons/circulation/functions/fnc_Syringe_Inject.sqf")
    first_guard = syringe[:syringe.find('if (alive _patient') if 'if (alive _patient' in syringe else len(syringe)]
    assert '!alive _patient' not in first_guard
    # Physiology itself stays inert on a corpse; availability and inventory/accounting are what remain usable.
    med_local = text("addons/core/overrides/fnc_medicationLocal.sqf")
    assert '!alive _patient' in med_local or 'alive _patient' in med_local


def test_ventilator_custody_is_not_destroyed_only_because_patient_died():
    tick = acme("ventCustodyTick")
    request = acme("ventCustodyRequest")
    # Recovery is permitted when the entity is gone, not merely dead.
    assert 'isNull _patient' in tick
    assert re.search(r'isNull _patient\s*\|\|\s*\{!alive _patient\}', tick) is None
    assert '!alive _patient' not in request


def test_experimental_smart_bandage_bundle_is_removed_and_native_acm_bandaging_is_restored():
    action = text("addons/core/ACE_Medical_Treatment_Actions.hpp")
    pressure = cfg_class(action, "PressureBandage")
    assert 'items[] = {"ACM_PressureBandage"};' in pressure
    assert 'consumeItem = 1;' in pressure
    assert 'callbackSuccess = QACEFUNC(medical_treatment,bandage);' in pressure
    assert 'smartBandage' not in pressure
    assert 'Bandage Wounds' not in pressure
    for name in (
        'canSmartBandage', 'getSmartBandagePlan', 'getSmartBandageTime', 'smartBandageApplyLocal',
        'smartBandageCancel', 'smartBandageProgress', 'smartBandageRestore', 'smartBandageStart', 'smartBandageSuccess'
    ):
        assert not (REPO / "addons/damage/functions" / f"fnc_{name}.sqf").exists()



def test_generated_nv_art_is_purged_and_only_active_iv_angle_families_remain():
    assert not (ROOT / "ui/nv_close").exists()
    assert not (ROOT / "functions/fn_minigameVisionTextures.sqf").exists()
    assert not (ROOT / "tools/nv_texture_manifest.json").exists()
    assert 'minigameVisionTextures' not in text("addons/acm_extended/config.cpp")

    iv = ROOT / "ui/iv"
    allowed_angles = {"base", "15_left", "15_right", "ej_15_left", "ej_15_right"}
    for gauge in ("14g", "16g", "18g", "20g"):
        assert {p.name for p in (iv / gauge).iterdir() if p.is_dir()} <= allowed_angles
    assert {p.name for p in (iv / "iv_line/standalone").iterdir() if p.is_dir()} <= allowed_angles
    for gauge in ("14g", "16g", "18g", "20g"):
        assert {p.name for p in (iv / "iv_line/connected" / gauge).iterdir() if p.is_dir()} <= allowed_angles


def test_all_acme_function_references_have_a_file_and_cfgfunctions_registration():
    # Prevent stray buttons/callbacks from pointing at a function that can never be compiled.
    source_paths = [REPO / "addons/acm_extended/config.cpp", REPO / "addons/core/ACE_Medical_Treatment_Actions.hpp"]
    refs = set()
    for p in source_paths:
        refs.update(re.findall(r'\bACME_fnc_([A-Za-z0-9_]+)\b', read_source(p, encoding="utf-8-sig")))
    files = {p.stem[3:] for p in (ROOT / "functions").glob("fn_*.sqf")}
    cfg = text("addons/acm_extended/config.cpp")
    registrations = set(re.findall(r'\bclass\s+([A-Za-z0-9_]+)\s*\{\s*\};', cfg))
    missing_files = sorted(refs - files)
    missing_reg = sorted(refs - registrations)
    assert not missing_files, f"ACME callback(s) have no function file: {missing_files}"
    assert not missing_reg, f"ACME callback(s) are not in CfgFunctions: {missing_reg}"
