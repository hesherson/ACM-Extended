#!/usr/bin/env python3
"""Stable B216 build: B180 clot-only reopening plus B199 physical-dressing invariants remain enforced."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_applied_bandage_commit_has_no_reopen_scheduler():
    s = read("addons/core/overrides/fnc_handleBandageOpening.sqf")
    assert "Stable B180 wound-control invariant" in s
    assert "VAR_BANDAGED_WOUNDS" in s
    assert "CBA_fnc_waitAndExecute" not in s
    assert "reopeningChance" not in s
    assert "Platelet_Count" not in s
    assert "GET_PLATELET_COUNT" not in s
    assert "GET_CLOTTED_WOUNDS" not in s
    assert "VAR_OPEN_WOUNDS" not in s


def test_custom_clot_pop_never_reads_or_writes_physical_dressings():
    s = read("addons/acm_extended/functions/fn_popClots.sqf")
    assert 'getVariable ["ACM_damage_ClottedWounds", createHashMap]' in s
    assert '[["clottedWounds", _clotted]], true] call ACM_damage_fnc_setWoundState;' in s
    for forbidden in (
        "ace_medical_bandagedWounds",
        "GET_BANDAGED_WOUNDS",
        "VAR_BANDAGED_WOUNDS",
        "GET_WRAPPED_WOUNDS",
        "VAR_WRAPPED_WOUNDS",
        "GET_STITCHED_WOUNDS",
        "VAR_STITCHED_WOUNDS",
    ):
        assert forbidden not in s


def test_one_pop_can_only_create_one_partial_wound():
    s = read("addons/acm_extended/functions/fn_popClots.sqf")
    assert "_fraction = (_fraction max 0.05) min 0.25;" in s
    assert "private _move = _fraction min _camt;" in s
    assert "private _pick = _candidates select 0;" in s
    assert "_candidates pushBack" in s
    assert "forEach _candidates" in s

    # The selected candidate is mutated once; there is no loop that reopens several rows.
    mutation = s.split('_pick params ["_part", "_idx", "_id"];', 1)[1]
    assert mutation.count("private _move =") == 1
    assert "forEach _candidates" not in mutation


def test_dilutional_clot_pop_is_rare_per_minute_and_has_long_cooldown():
    init = read("addons/acm_extended/functions/fn_initBloodStorageRuntime.sqf")
    tick = read("addons/acm_extended/functions/fn_clotPopTick.sqf")

    assert "ACME_clotPop_chance      = 0.001;" in init
    assert "ACME_clotPop_dt          = 60;" in init
    assert "ACME_clotPop_maxChance   = 0.003;" in init
    assert "ACME_clotPop_fraction    = 0.15;" in init
    assert "ACME_clotPop_cooldown    = 600;" in init
    assert "ACME_clotPop_nativeChance = 0.0015;" in init
    assert "ACME_clotPop_nativeMaxChance = 0.003;" in init

    assert 'getVariable ["ACME_clotPop_nextServer", -1]' in tick
    assert 'setVariable ["ACME_clotPop_nextServer", _now + _cooldown, true]' in tick
    assert 'getVariable ["ACM_damage_ClottedWounds", createHashMap]' in tick
    assert "if (!_hasClot) then {continue};" in tick
    assert 'missionNamespace getVariable ["ACME_clotPop_maxChance", 0.003]' in tick


def test_native_clot_instability_uses_same_single_partial_pop_and_shared_cooldown():
    s = read("addons/damage/functions/fnc_clotWoundsOnBodyPart.sqf")
    closure = s.split("private _fnc_handleReopening = {", 1)[1].split("private _fnc_finalUpdate = {", 1)[0]

    assert 'getVariable ["ACME_clotPop_nextServer", -1]' in closure
    assert 'missionNamespace getVariable ["ACME_clotPop_nativeChance", 0.0015]' in closure
    assert 'missionNamespace getVariable ["ACME_clotPop_nativeMaxChance", 0.003]' in closure
    assert 'setVariable ["ACME_clotPop_nextServer", serverTime + _delay + _cooldown, true]' in closure
    assert "ACME_fnc_popClots" in closure
    assert "VAR_OPEN_WOUNDS" not in closure
    assert "VAR_BANDAGED_WOUNDS" not in closure

    # The old per-clot loop could queue several full reopens from one clotting episode.
    assert 'for "_i" from 1 to _amountClotted do' not in s
    assert 'private _reopenChance = [0, (0.5 / _plateletCount)]' not in s


def test_txa_detection_is_real_medication_state_not_always_true_multiplier():
    s = read("addons/damage/functions/fnc_clotWoundsOnBodyPart.sqf")
    assert 'private _hasTXA = ([_patient, "TXA_IV", false] call ACEFUNC(medical_status,getMedicationCount)) > 0.05;' in s
    assert "private _hasTXA = _TXAEffect > 0.15;" not in s
    assert 'if (_unstable && {!_hasTXA}) then {' in s


def test_generic_reopen_helper_is_future_proofed_to_clots_only():
    s = read("addons/damage/functions/fnc_handleWoundReopening.sqf")
    assert "Stable B180: treated-wound reopening is clot-only." in s
    assert "GET_CLOTTED_WOUNDS" in s
    for forbidden in (
        "GET_BANDAGED_WOUNDS",
        "GET_WRAPPED_WOUNDS",
        "GET_STITCHED_WOUNDS",
        "VAR_BANDAGED_WOUNDS",
        "VAR_WRAPPED_WOUNDS",
        "VAR_STITCHED_WOUNDS",
    ):
        assert forbidden not in s


def test_build_identity_is_b203_stable():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B216 bandage/clot invariant regression: PASS")
