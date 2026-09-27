#!/usr/bin/env python3
"""Stable B177: standing/crouched-conscious carrier protection and controlled-NPC provider lifecycle."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_conscious_standing_or_crouched_casualty_is_never_stripped_for_chest_access():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    commit = acquire.split("private _commitRemoval = {", 1)[1].split("// Animation is allowed", 1)[0]
    assert 'private _standingConscious = alive _p' in commit
    assert 'getVariable ["ACE_isUnconscious", false]' in commit
    assert 'getVariable ["ace_medical_unconscious", false]' in commit
    assert '(stance _p) in ["STAND", "CROUCH"]' in commit
    assert commit.index("if (_standingConscious) exitWith {true};") < commit.index("removeVest _p;")


def test_carrier_is_force_restored_if_patient_wakes_and_stands_or_crouches_during_custody():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    watchdog = acquire.split("// Custody watchdog.", 1)[1].split("// Animation is allowed", 1)[0]
    assert 'private _standingConscious = alive _patient' in watchdog
    assert '(stance _patient) in ["STAND", "CROUCH"]' in watchdog
    assert '[_patient, true, objNull, _ctx, true] call ACME_fnc_chestAccessVestRestore;' in watchdog


def test_chest_seal_and_nar_spear_accept_locally_controlled_npc_medic():
    open_fn = read("addons/acm_extended/functions/fn_chestSealOpen.sqf")
    tick = read("addons/acm_extended/functions/fn_chestSealTick.sqf")
    init = read("addons/acm_extended/functions/fn_chestSealInit.sqf")
    close = read("addons/acm_extended/functions/fn_chestSealClose.sqf")
    mouse = read("addons/acm_extended/functions/fn_chestSealMouseDown.sqf")
    presence = read("addons/acm_extended/functions/fn_chestSealPresenceSend.sqf")

    assert '!([_m] call ace_common_fnc_isPlayer)' in open_fn
    assert '!([_medic] call ace_common_fnc_isPlayer)' in tick
    assert 'private _viewer = _medic;' in init
    assert '[_flipMedic] call ace_common_fnc_isPlayer' in close
    assert "ACE_player" not in open_fn
    assert "ACE_player" not in tick
    assert "ACE_player" not in init
    assert "ACE_player" not in close
    assert "ACE_player" not in mouse
    assert "name _viewer" in presence


def test_thoracostomy_accepts_locally_controlled_npc_medic():
    open_fn = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    tick = read("addons/acm_extended/functions/fn_thoraTick.sqf")
    close = read("addons/acm_extended/functions/fn_thoraClose.sqf")

    assert "uiNamespace getVariable ['ACME_Thora_Medic',objNull]" in open_fn
    assert '[_m] call ace_common_fnc_isPlayer' in open_fn
    assert '!([_thMedic] call ace_common_fnc_isPlayer)' in tick
    assert '[_medic] call ace_common_fnc_isPlayer' in close
    assert "ACE_player" not in open_fn
    assert "ACE_player" not in tick
    assert "ACE_player" not in close


def test_shared_treatment_preflight_uses_controlled_provider_identity_not_cached_ace_player():
    treatment = read("addons/core/overrides/fnc_treatment.sqf")
    stance = read("addons/acm_extended/functions/fn_providerStanceOwned.sqf")
    assert "ACE_player" not in treatment
    assert "ACE_player" not in stance
    assert treatment.count("ace_common_fnc_isPlayer") >= 5
    assert 'objectFromNetId' in treatment
    assert '[_unit] call ace_common_fnc_isPlayer' in stance


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B177 controlled-NPC and standing-carrier regression: PASS")
