#!/usr/bin/env python3
"""Stable B189: thoracostomy modal launch must not strand menu/weapon/provider state."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_thoracostomy_launchers_bypass_generic_timed_treatment_preflight():
    treatment = read("addons/core/overrides/fnc_treatment.sqf")
    # Isolate the actual modal exitWith block, not the earlier retired-action guard.
    start = treatment.index('// Opening a shared workspace')
    opening = treatment.index(']) exitWith {', start) + len(']) exitWith ')
    depth = 1
    end = opening + 1
    while depth:
        depth += (treatment[end] == '{') - (treatment[end] == '}')
        end += 1
    launcher = treatment[start:end]
    assert end < treatment.index('// Chest-access preparation is a physical gear transaction')
    for name in ("ACME_PerformThoracostomy", "ACME_AdjustThoracostomy", "ACME_InsertChestTube"):
        assert f'"{name}"' in launcher
    assert '[_medic, _patient, _bodyPart] call ACME_fnc_thoraOpen;' in launcher
    assert 'call ACM_core_fnc_treatmentNative' not in launcher

def test_thoracostomy_click_owns_menu_close_for_entire_preparation():
    renderer = read("addons/gui/overrides/fnc_updateActions.sqf")
    for name in ("acme_performthoracostomy", "acme_adjustthoracostomy", "acme_insertchesttube"):
        assert f"'{name}'" in renderer
    thora = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    assert 'ACME_chestAccessPreflightActive", true' in thora
    assert 'ACME_chestAccessPreflightToken", _lease' in thora
    assert 'ace_medical_gui_pendingReopen = false;' in thora
    assert 'ace_medical_gui_menuDisplay' in thora
    assert '_menuDisplay closeDisplay 1;' in thora
    assert 'closeDialog 0;' in thora
    assert '[true, _medic, _patient, _lease] call ACME_fnc_chestAccessPreparing;' in thora

def test_thoracostomy_entry_scrubs_stale_generic_provider_preflight():
    thora = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    for token in (
        'ACME_treatmentPreflightActive',
        'ACME_treatmentPreflightToken',
        'ACME_treatmentPreflightBypass',
        'ACME_treatmentPreflightStartedAt',
        'ACME_nativeTreatmentRate',
        'treatmentEndInAnim',
    ):
        assert token in thora
    assert '[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;' in thora
    assert '[_medic, true] call ACME_fnc_menuPoseStop;' in thora

def test_walkaway_or_lost_provider_contact_aborts_entry_and_open_panel():
    thora = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    tick = read("addons/acm_extended/functions/fn_thoraTick.sqf")
    assert '(_m distance _p) > ace_medical_gui_maxDistance' in thora
    assert 'objectParent _m isNotEqualTo objectParent _p' in thora
    assert '_m getVariable ["ACE_isUnconscious", false]' in thora
    assert '(_thMedic distance _thPatient) > ace_medical_gui_maxDistance' in tick
    assert 'objectParent _thMedic isNotEqualTo objectParent _thPatient' in tick
    assert '[86600] call ACME_fnc_minigameClose;' in tick

def test_abort_and_close_restore_free_provider_input_state_without_normal_provider_pose():
    thora = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    close = read("addons/acm_extended/functions/fn_thoraClose.sqf")
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    assert 'if (_treatmentClass == "thoracostomy") exitWith {' in acquire
    providerless = acquire.split('if (_treatmentClass == "thoracostomy") exitWith {',1)[1].split('if (_context == "chestseal") then {',1)[0]
    assert 'call ACME_fnc_chestAccessVestProvider' not in providerless
    assert '_patientArgs call _beginPatient;' in providerless
    assert 'private _releaseProvider = {' not in thora
    for src in (thora, close):
        assert 'setUnitPos "AUTO"' in src
        assert 'setAnimSpeedCoef 1' in src
        assert 'ACME_nativeTreatmentRate' in src
        assert 'treatmentEndInAnim' in src

def test_stable_debug_identity_is_b183_without_hotfix_suffix():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup
    _assert_current_build()

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable thoracostomy modal/input regression: PASS")
