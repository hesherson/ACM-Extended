#!/usr/bin/env python3
"""Stable B177: accepted ACME buttons respond immediately; presentation never delays clinical start."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_generic_treatment_presentation_never_blocks_native_start():
    treatment = read("addons/core/overrides/fnc_treatment.sqf")
    marker = treatment.index("// B177 button-responsiveness invariant")
    end = treatment.index("// A newly accepted head-position action", marker)
    block = treatment[marker:end]

    assert "provider presentation NEVER gates clinical treatment start" in block
    assert "CBA_fnc_waitUntilAndExecute" not in block
    assert "CBA_fnc_waitAndExecute" not in block
    assert "CBA_fnc_execNextFrame" not in block
    assert 'ACME_treatmentPreflightActive", false' in block
    assert 'ACME_treatmentPreflightToken", ""' in block
    assert 'call ACME_fnc_medicAnimationPrep' in block

    native = treatment.index("private _started = _nativeArgs call ACM_core_fnc_treatmentNative;", end)
    assert native > end


def test_provider_gestures_get_patient_without_delaying_treatment():
    treatment = read("addons/core/overrides/fnc_treatment.sqf")
    assert '[_m, _mode, _window, _patient] call ACME_fnc_treatmentGesture;' in treatment


def test_suture_chest_tube_no_longer_inherits_one_second_delay():
    cfg = read("addons/acm_extended/config.cpp")
    block = cfg.split("class ACME_SutureChestTube:", 1)[1].split("};", 1)[0]
    assert 'treatmentTime = 0.001;' in block
    assert 'callbackSuccess = "_this call ACME_fnc_thoraSutureTube";' in block


def test_conscious_patient_animation_is_never_seized_by_native_treatment():
    native = read("addons/core/functions/fnc_treatmentNative.sqf")
    branch = native.split("if (IS_UNCONSCIOUS(_patient)) then {", 1)[1].split("if (!_isSelf", 1)[0]
    assert 'animationPatientUnconscious' in branch
    assert '_patientAnim = "";' in branch
    assert 'getText (_config >> "animationPatient")' not in branch


def test_spike_bag_repaints_active_state_before_its_timer():
    s = read("addons/acm_extended/functions/fn_transfusionSpikeOrAdd.sqf")
    active = s.index('missionNamespace setVariable ["ACME_spikingActive", [_class, diag_tickTime + 1.6]];')
    repaint = s.index("call ACME_fnc_updateTransfusionControls;", active)
    wait = s.index("1.6] call CBA_fnc_waitAndExecute;", repaint)
    assert active < repaint < wait


def test_y_tubing_repaints_and_announces_before_its_timer():
    s = read("addons/acm_extended/functions/fn_transfusionYTubing.sqf")
    active = s.index('missionNamespace setVariable ["ACME_yBuildingActive", diag_tickTime + 2.5];')
    repaint = s.index("call ACME_fnc_updateTransfusionControls;", active)
    message = s.index('"Building Y set..."', repaint)
    wait = s.index("2.5] call CBA_fnc_waitAndExecute;", message)
    assert active < repaint < message < wait


def test_other_deferred_gui_flows_change_ui_or_start_native_action_first():
    clamp = read("addons/acm_extended/functions/fn_closeClamp.sqf")
    assert clamp.index("closeDisplay 2") < clamp.index("CBA_fnc_waitUntilAndExecute")

    move = read("addons/acm_extended/functions/fn_moveInfusionBag.sqf")
    assert move.index("call ACM_circulation_fnc_TransfusionMenu_MoveBag;") < move.index("CBA_fnc_waitUntilAndExecute")

    active = read("addons/acm_extended/functions/fn_openFromTransfusionMenu.sqf")
    assert active.index("closeDialog 0;") < active.index("CBA_fnc_execNextFrame")

    prepared = read("addons/acm_extended/functions/fn_openPrepFromInventoryMenu.sqf")
    assert prepared.index("closeDialog 0;") < prepared.index("CBA_fnc_execNextFrame")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B177 zero-button-latency regression: PASS")
