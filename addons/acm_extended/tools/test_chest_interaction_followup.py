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
    request = fn("chestSealFlip")
    wait = fn("chestSealFlipTick")
    assert "call ACME_fnc_chestSealRoll" not in request
    assert wait.count("call ACME_fnc_chestSealRoll") == 1
    dispatch = wait.index("call ACME_fnc_chestSealRoll")
    assert wait.index("(toLowerANSI animationState _provider) == _work") < dispatch
    assert wait.index('(_pose param [3,-2]) >= 1') < dispatch
    assert wait.index("_args set [9,diag_tickTime]") < dispatch
    for guard in ("ACME_CS_SessionToken", "ACME_CS_FlipPendingToken",
                  "ACME_rollProviderToken", '(_pose param [0,-2]) != _epoch',
                  "diag_tickTime >= _deadline"):
        assert guard in wait[:dispatch]


def test_closing_a_panel_invalidates_pending_roll_before_restoration():
    close = fn("chestSealClose")
    assert close.index('["ACME_CS_FlipPendingToken",""]') < close.index('"chestSealPatientEnd"')
    assert 'if (!_current) exitWith {};' in fn("chestSealFlipTick")


def test_both_burp_paths_commit_shared_cooldown_before_effects():
    for name in ("chestSealBurp", "thoraAftercareLocal"):
        source = fn(name)
        gate = source.index("call ACME_fnc_chestSealBurpReady")
        assert gate < source.index("call ACME_fnc_ptxTreat")
        assert gate < source.index("call ACME_fnc_chestSealLogOnce")
        assert gate < source.index('"chestSealBurpGesture"')
    gate = fn("chestSealBurpReady")
    assert "ACME_fnc_clinicalEpoch" in gate
    assert "local _patient" in gate
    assert 'serverTime + 6' in gate
    assert 'case "chestSealBurpGesture"' in fn("ownerDispatch")


def test_burp_cooldown_still_allows_laying_the_corner_flat():
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
    for name in ("chestSealFlipTick", "chestSealBurpReady", "dragHandleRope",
                 "stethoscopeInit", "stethoscopeTick", "stethoscopeWeights", "stethoscopeClose"):
        assert config.count(f"class {name} {{}};") == 1
        matching(lex(fn(name)))
