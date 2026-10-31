from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

def test_unrelated_airway_actions_not_blocked_by_bvm_or_cpr():
    src = read(ADDONS / "airway/ACE_Medical_Treatment_Actions.hpp")
    assert "BVM_Medic" not in src
    assert "EFUNC(core,cprActive)" not in src

def test_unrelated_breathing_actions_not_blocked_by_bvm_or_cpr():
    src = read(ADDONS / "breathing/ACE_Medical_Treatment_Actions.hpp")
    assert "BVM_Medic" not in src
    assert "EFUNC(core,cprActive)" not in src
    assert "EFUNC(core,bvmActive)" not in src
    assert "call FUNC(canUseBVM)" in src

def test_medication_and_stimulus_actions_not_blocked_by_bvm():
    src = read(ADDONS / "core/ACE_Medical_Treatment_Actions.hpp")
    assert "BVM_Medic" not in src

def test_surgical_airway_keeps_only_provider_local_and_same_procedure_locks():
    establish = read(ADDONS / "airway/functions/fnc_canEstablishSurgicalAirway.sqf")
    secure = read(ADDONS / "airway/functions/fnc_canSecureSurgicalAirway.sqf")
    assert "ACM_core_ContinuousAction_Active" in establish
    assert "SurgicalAirway_InProgress" in establish
    assert "BVM_Medic" not in establish
    assert "CPR_provider" not in establish
    assert "BVM_Medic" not in secure

def test_acme_restatements_do_not_reintroduce_global_busy_gates():
    cfg = read(ROOT / "config.cpp")
    assert "PARALLEL PROVIDER RULE:" in cfg
    # Recovery physically turns the casualty and must yield to active CPR/BVM. This exact positioning
    # exception must not introduce blanket busy gates on unrelated assessment or treatment actions.
    recovery = re.findall(r'    class RecoveryPosition: CheckAirway \{.*?\n    \};', cfg, re.S)
    assert len(recovery) == 1
    other_actions = cfg.replace(recovery[0], "", 1)
    for support in ("ACM_breathing_BVM_Medic", "ACM_core_fnc_cprActive"):
        assert support in recovery[0]
        assert support not in other_actions

def test_same_role_exclusivity_remains():
    bvm = read(ADDONS / "breathing/functions/fnc_canUseBVM.sqf")
    cpr = read(ADDONS / "circulation/ACE_Medical_Treatment_Actions.hpp")
    assert "bvmSessionValid" in bvm
    assert "call ACEFUNC(medical_treatment,canCPR)" in cpr
