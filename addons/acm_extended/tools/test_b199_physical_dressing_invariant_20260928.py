from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def test_wraps_never_schedule_spontaneous_failure():
    s = read("addons/damage/functions/fnc_wrapBodyPartLocal.sqf")

    assert "Stable B199 physical-dressing invariant" in s
    assert "VAR_WRAPPED_WOUNDS" in s
    assert "VAR_BANDAGED_WOUNDS" in s
    assert "VAR_CLOTTED_WOUNDS" in s

    for forbidden in (
        "_fnc_handleReopening",
        "CBA_fnc_waitAndExecute",
        "GET_PLATELET_COUNT",
        "wrappedWoundReopenChance",
        "VAR_OPEN_WOUNDS, _openWounds, true",
    ):
        assert forbidden not in s


def test_native_ace_bandage_reopen_roll_is_hard_disabled_after_cba_settings():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg_functions = read("addons/core/CfgFunctions.hpp")

    assert startup.count('missionNamespace setVariable ["ace_medical_treatment_woundReopenChance", -1, false];') == 2
    assert '["CBA_settingsInitialized", {' in startup
    assert "Only ACME's explicit" in startup
    assert "class handleBandageOpening" not in cfg_functions


def test_only_unsecured_clot_code_can_create_a_spontaneous_reopen():
    pop = read("addons/acm_extended/functions/fn_popClots.sqf")
    tick = read("addons/acm_extended/functions/fn_clotPopTick.sqf")
    native = read("addons/damage/functions/fnc_clotWoundsOnBodyPart.sqf")

    assert 'getVariable ["ACM_damage_ClottedWounds", createHashMap]' in pop
    assert 'setVariable ["ACM_damage_ClottedWounds", _clotted, true]' in pop
    assert "ACME_fnc_popClots" in native
    assert '"ACME_popClots"' in tick

    for forbidden in (
        "GET_BANDAGED_WOUNDS",
        "VAR_BANDAGED_WOUNDS",
        "GET_WRAPPED_WOUNDS",
        "VAR_WRAPPED_WOUNDS",
        "GET_STITCHED_WOUNDS",
        "VAR_STITCHED_WOUNDS",
    ):
        assert forbidden not in pop


def test_naloxone_handler_cannot_directly_create_wounds_or_fractures():
    s = read("addons/circulation/functions/fnc_handleMed_NaloxoneLocal.sqf")

    assert "removeMedicationAdjustment" in s
    for forbidden in (
        "VAR_OPEN_WOUNDS",
        "VAR_BANDAGED_WOUNDS",
        "VAR_WRAPPED_WOUNDS",
        "VAR_FRACTURES",
        "woundsHandler",
        "handleFracture",
        "setHitPointDamage",
        "addDamage",
    ):
        assert forbidden not in s



def test_naloxone_never_forces_patient_roll_or_other_posture_change():
    actions = read("addons/core/ACE_Medical_Treatment_Actions.hpp")
    block = actions.split("class Naloxone: Paracetamol {", 1)[1].split("class FentanylLozenge: Paracetamol {", 1)[0]

    assert "ACM_rollToBack = 0;" in block
    assert "ACME_neverRollToBack = 1;" in block
    assert "ACM_rollToBack = 1;" not in block

def test_b203_keeps_public_stable_version_1241():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    config = read("addons/acm_extended/config.cpp")

    assert 'version = "1.2.4.1";' in config
    assert 'ACME_buildBatch = "B208";' in startup
    assert 'ACME_networkAuditRevision = "NA8-B208-1.2.4.1-stable";' in startup
