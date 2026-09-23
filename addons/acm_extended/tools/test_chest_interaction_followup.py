"""Regression contracts for asynchronous chest interactions.
Run with pytest; Arma must still verify PhysX, animation playback and sound attenuation.
"""
from pathlib import Path
from source_scan import lex, matching

ADDON = Path(__file__).resolve().parents[1]
ADDONS = ADDON.parent


def fn(name):
    return (ADDON / "functions" / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def test_patient_flip_cannot_dispatch_from_the_button_or_prep_state():
    # Successful provider acquisition waits for observed medic4; unavailable
    # presentation has a deliberate, eligibility-checked one-shot fallback.
    from test_historical_roll_cancellation import test_physical_roll_waits_for_observed_work_and_dispatches_only_once, test_presentation_acquisition_failure_retains_one_physical_roll_and_scoped_completion, test_ineligible_flip_changes_only_virtual_view
    for stage in (-2,-1,0,1,2):
        for observed in ('prep','ainvpknlmstpsnonwnondnon_medic4'):
            test_physical_roll_waits_for_observed_work_and_dispatches_only_once(stage,observed)
    for change in ('none','session','token'):
        test_presentation_acquisition_failure_retains_one_physical_roll_and_scoped_completion(change)
    for change in ('_patient setVariable ["ACE_isUnconscious",false];','_patientAlive=false;','_parent=missionNamespace;'):
        test_ineligible_flip_changes_only_virtual_view(change)


def test_closing_a_panel_invalidates_pending_roll_before_restoration():
    close = fn("chestSealClose")
    assert close.index('["ACME_CS_FlipPendingToken",""]') < close.index('"chestSealPatientEnd"')
    assert 'if (!_current) exitWith {};' in fn("chestSealFlipTick")


def test_both_burp_paths_check_patient_ownership_without_a_timer():
    for name in ("chestSealBurp", "thoraAftercareLocal"):
        source = fn(name)
        gate = source.index("call ACME_fnc_chestSealBurpReady")
        assert gate < source.index("call ACME_fnc_ptxTreat")
        assert gate < source.index("call ACME_fnc_chestSealLogOnce")
        assert gate < source.index('"chestSealBurpGesture"')
    gate = fn("chestSealBurpReady")
    assert "local _patient" in gate
    assert not any(t.kind == "ident" and t.value in ("serverTime", "CBA_missionTime", "diag_tickTime") for t in lex(gate))
    assert "ACME_CS_burpCooldown" not in gate
    assert '_medic, 0] call ACME_fnc_chestSealLogOnce' in fn("chestSealBurp")
    assert '_medic,0] call ACME_fnc_chestSealLogOnce' in fn("thoraAftercareLocal")
    assert 'case "chestSealBurpGesture"' in fn("ownerDispatch")


def test_seal_validation_still_allows_laying_the_corner_flat():
    assert 'if (_fr <= 0 && {' in fn("chestSealScroll")
    assert 'if (_frame == 0 && {' in fn("thoraSealScroll")


def test_scope_input_is_hold_based_and_display_owned():
    dialog = (ADDONS / "breathing" / "Stethoscope_Dialog.hpp").read_text()
    assert "class Bell: RscPicture" in dialog
    assert "onMouseButtonUp = QUOTE(call FUNC(Stethoscope_MoveBell))" not in dialog
    assert 'onUnload = "_this call ACME_fnc_stethoscopeClose;"' in dialog
    init = fn("stethoscopeInit")
    for event in ("MouseButtonDown", "MouseButtonUp"):
        assert f'displayAddEventHandler ["{event}"' in init
        assert f'ctrlAddEventHandler ["{event}"' in init
    assert 'getMousePosition' in init
    assert 'isGameFocused' in fn("stethoscopeTick")


def test_scope_mixes_playing_channels_and_preserves_pathology_and_cleanup():
    tick = fn("stethoscopeTick")
    assert "say3D" in tick
    assert not any(t.kind == "ident" and t.value == "fadeSound" for t in lex(tick))
    assert "ACME_stethNextBeat" in tick and "ACME_stethNextBreath" in tick
    assert "ACME_aspiration_edema" in tick and "ACM_circulation_Overload_Volume" in tick
    assert '"Shallow","Dull","Crackles"' in tick
    assert "deleteVehicle _sound" in fn("stethoscopeClose")
    assert "deleteVehicle _emitter" in fn("stethoscopeClose")
    assert "ACME_stethChannels" in fn("stethoscopeClose")
    weights = fn("stethoscopeWeights")
    assert "_diaphragm" in weights and "_centerline" in weights
    assert "_lowerHeart" in weights


def test_new_sqf_functions_are_registered_and_balanced():
    config = (ADDON / "config.cpp").read_text()
    for name in ("chestSealFlipTick", "chestSealBurpReady",
                 "stethoscopeInit", "stethoscopeTick", "stethoscopeWeights", "stethoscopeClose"):
        assert config.count(f"class {name} {{}};") == 1
        matching(lex(fn(name)))
