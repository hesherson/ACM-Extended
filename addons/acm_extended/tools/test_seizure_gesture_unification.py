from pathlib import Path
import math
import re

ADDON = Path(__file__).resolve().parents[1]
ROOT = ADDON.parent


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")


def test_seizure_gestures_are_isolated_and_105x():
    s = read(ADDON / "config.cpp")
    # Positive config speed is cycles/second. A shared 1.05 would crush every clip to 0.95 seconds.
    assert 'class ACME_SeizureSpasm0: GestureSpasm0 {};' in s
    assert 'ACME_SeizureSpasm0[] = {"ACME_SeizureSpasm0", "Gesture"};' in s
    assert 'ACME_SeizureSpasm3' not in s
    native_speeds = {4: 0.2325, 5: 0.2069, 6: 0.1287}
    for n, native in native_speeds.items():
        assert f'ACME_SeizureSpasm{n}[] = {{"ACME_SeizureSpasm{n}", "Gesture"}};' in s
        match = re.search(
            rf'class ACME_SeizureSpasm{n}: GestureSpasm{n}\s*\{{\s*speed\s*=\s*([0-9.]+);',
            s,
        )
        assert match, f"missing isolated speed for spasm {n}"
        speed = float(match.group(1))
        assert math.isclose(speed / native, 1.05, rel_tol=1e-6)
        assert 3.9 < 1 / speed < 7.5


def test_motion_uses_gesture_done_not_old_jitter_driver():
    s = read(ADDON / "functions" / "fn_seizureMotion.sqf")
    assert 'addEventHandler ["GestureDone"' in s
    assert "ACME_fnc_seizureGestureAdvance" in s
    assert "ACME_seizure_jerkHz" not in s
    assert "ACME_seizure_yawAmp" not in s
    assert "ACME_seizure_yawChaos" not in s
    assert "addCamShake" not in s
    assert "ACME_fnc_forceRagdoll" not in s
    assert "private _tremor" not in s
    assert "private _jitter" not in s


def test_only_selected_spasm_variants_cycle_without_immediate_repeat():
    s = read(ADDON / "functions" / "fn_seizureGestureAdvance.sqf")
    for n in (0, 4, 5, 6):
        assert f'"ACME_SeizureSpasm{n}"' in s
    assert '"ACME_SeizureSpasm3"' not in s
    assert '"ACME_SeizureSpasm1"' not in s
    assert '"ACME_SeizureSpasm2"' not in s
    assert "private _pool = _gestures - [_last];" in s
    assert "selectRandom _pool" in s


def test_sarin_joins_shared_seizure_state_machine():
    effect = read(ROOT / "cbrn" / "functions" / "fnc_effectSarin.sqf")
    tox = read(ADDON / "functions" / "fn_lidoToxTick.sqf")
    reset = read(ROOT / "cbrn" / "functions" / "fnc_resetVariables.sqf")
    assert 'ACME_sarinSeizureCause' in effect
    assert "addCamShake" not in effect
    assert 'private _sarinCause = _patient getVariable ["ACME_sarinSeizureCause", false];' in tox
    assert '|| _sarinCause' in tox
    assert '|| _sarinCause ||' in tox
    assert '_patient setVariable ["ACME_sarinSeizureCause", false, true];' in reset



def test_seizure_gesture_sequence_is_network_visible_and_vehicle_safe():
    motion = read(ADDON / "functions" / "fn_seizureMotion.sqf")
    advance = read(ADDON / "functions" / "fn_seizureGestureAdvance.sqf")
    sync = read(ADDON / "functions" / "fn_seizureGestureSync.sqf")
    owner = read(ADDON / "functions" / "fn_ownerInit.sqf")
    assert '"ACME_seizureGestureSync"' in owner
    assert "CBA_fnc_globalEvent" in advance
    assert '_patient switchGesture [_next,0,1,false];' not in advance
    assert 'switchGesture [_gesture, 0, 1, false]' in sync
    assert '_on && {!isNull objectParent _patient}' in motion
    assert '!isNull objectParent _patient' in sync

def test_full_heal_clears_new_gesture_state():
    s = read(ADDON / "functions" / "fn_clearAllAilments.sqf")
    for name in [
        "ACME_sarinSeizureCause",
        "ACME_seizure_motionActive",
        "ACME_seizure_motionGestureEH",
        "ACME_seizure_motionCurrentGesture",
        "ACME_seizure_motionRetryPending",
        "ACME_seizure_motionAdvancePending",
    ]:
        assert f'"{name}"' in s


def test_old_visual_tuning_is_explicitly_inert():
    cfg = read(ADDON / "functions" / "fn_initDrugPhysiologyConfig.sqf")
    motion = read(ADDON / "functions" / "fn_seizureMotion.sqf")
    assert "Legacy visual tuning names are retained as inert compatibility values" in cfg
    assert "ACME_sarin_seizureThreshold = 10;" in cfg
    for name in [
        "ACME_seizure_jerkHz",
        "ACME_seizure_yawAmp",
        "ACME_seizure_yawChaos",
        "ACME_seizure_burstMin",
        "ACME_seizure_burstMax",
        "ACME_seizure_pauseMin",
        "ACME_seizure_pauseMax",
        "ACME_seizure_ragdollChance",
        "ACME_seizure_ragdollDur",
        "ACME_seizure_camShake",
    ]:
        assert name not in motion
