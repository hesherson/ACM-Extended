from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FN = ROOT / "functions"
CONFIG = ROOT / "config.cpp"

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

def test_lmb_press_blocks_underlying_ui_capture_without_manual_pickup():
    s = read(FN / "fn_stethoscopeInit.sqf")
    assert 'setVariable ["ACME_stethPressed",true]' in s
    tail = s.split('setVariable ["ACME_stethPressed",true]', 1)[1]
    assert "true" in tail[:500]
    assert 'setVariable ["ACME_stethPressed",false]' in s
    assert 'displayAddEventHandler ["MouseMoving"' not in s
    assert "ACME_stethMouse" not in s

def test_tick_uses_original_absolute_mouse_position():
    s = read(FN / "fn_stethoscopeTick.sqf")
    assert "private _mouse = getMousePosition;" in s
    assert "ACME_stethMouse" not in s

def test_scope_display_owns_cursor_audio_tick():
    init = read(FN / "fn_stethoscopeInit.sqf")
    use = read(ROOT.parent / "breathing" / "functions" / "fnc_useStethoscope.sqf")
    close = read(FN / "fn_stethoscopeClose.sqf")
    assert 'ACME_stethTickPFH' in init
    assert '[_patient] call ACME_fnc_stethoscopeTick;' in init
    assert '[_display, _patient, _medic] call ACME_fnc_stethoscopeInit;' in use
    assert '\n    [_patient] call ACME_fnc_stethoscopeTick;\n' not in use
    assert 'ACME_fnc_chestAccessVestEvent' in close

def test_scope_display_owns_exact_pose_and_action_generations():
    s = read(FN / "fn_beginStethoscopeAction.sqf")
    assert 'setVariable ["ACME_continuousEpoch", _epoch]' in s
    assert 'setVariable ["ACME_stethMedic", _medic]' in s
    assert 'setVariable ["ACME_stethPoseEpoch", _poseEpoch]' in s

def test_unload_clears_matching_continuous_action_and_pose():
    s = read(FN / "fn_stethoscopeClose.sqf")
    assert 'ACM_core_ContinuousAction_Active = false;' in s
    assert '[_medic,"stethoscope",_poseEpoch,true] call ACME_fnc_treatmentPoseStop;' in s
    assert 'getAnimSpeedCoef _medic == 0' in s
    assert 'ACME_stethPatientAnimLease' in s

def test_stethoscope_work_state_has_crouch_exit():
    s = read(CONFIG)
    block = s.split("class ACME_StethoscopeWork:", 1)[1].split("// shared restriction set", 1)[0]
    assert 'connectTo[] = {"AmovPknlMstpSnonWnonDnon", 0.2};' in block
    assert "connectTo[] = {};" not in block

def test_bell_drag_is_nonlinear_heavy_with_precision_near_target():
    tick = read(FN / "fn_stethoscopeTick.sqf")
    assert "private _dragDistance" in tick
    assert "linearConversion [0.006, 0.18, _dragDistance, 0.15, 0.85, true]" in tick

def test_heartbeat_uses_four_voice_ring_to_avoid_tail_clipping():
    init = read(FN / "fn_stethoscopeInit.sqf")
    tick = read(FN / "fn_stethoscopeTick.sqf")
    assert 'for "_i" from 0 to 7 do {' in init
    assert "private _heartVoices = [2,5,6,7];" in tick
    assert 'ACME_stethHeartVoice' in init and 'ACME_stethHeartVoice' in tick

def test_flip_side_reuses_chest_seal_roll_theatre_and_returns_to_scope():
    cfg = read(CONFIG)
    flip = read(FN / "fn_stethoscopeFlip.sqf")
    tick = read(FN / "fn_stethoscopeFlipTick.sqf")
    dialog = read(ROOT.parent / "breathing" / "Stethoscope_Dialog.hpp")
    assert "class stethoscopeFlip {};" in cfg
    assert "class stethoscopeFlipTick {};" in cfg
    assert '[_provider,"stethoscopeFlip",_patient] call ACME_fnc_rollProviderStart' in flip
    assert 'call ACME_fnc_chestSealRoll' in tick
    assert '[_provider,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart' in tick
    assert 'text = "Flip Side";' in dialog
    assert 'onButtonClick = "[] call ACME_fnc_stethoscopeFlip;"' in dialog
