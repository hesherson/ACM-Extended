from historical_source import read_source
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def txt(rel):
    return read_source(ROOT / rel, encoding="utf-8", errors="replace")


def test_version_batch():
    assert 'version = "1.0.100-r37";' in txt('config.cpp')
    post = txt('functions/fn_postInit.sqf')
    assert 'ACME_infusion_version = "1.0.100-r37"' in post
    assert 'ACME_buildBatch = "B73";' in post


def test_main_tag_selector_is_native_syringe_anchored_and_aspect_independent():
    render = txt('functions/fn_skPendingTagRender.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    for src in (render, ensure):
        assert 'ctrlTextWidth' in src
        assert 'pixelW' in src
        assert '*0.254' in src
    assert 'private _btnRight = _tagLeft - _gap;' in render
    assert 'private _btnRight0 = _tagLeft0 - _gap0;' in ensure
    assert 'safeZoneW * 0.070' not in render
    assert 'safeZoneW * 0.070' not in ensure
    assert '_x + _w*0.20' not in render
    assert '(_r0 select 0) + (_r0 select 2)*0.20' not in ensure


def test_selector_right_edge_tracks_tag_face_across_common_aspects():
    # Reference-model the B73 formula in pixels. The native syringe rect is height/UI-grid driven;
    # therefore aspect ratio may change screen width but not the desired small gap from the tag face.
    for width, height in [(1920,1080),(2560,1440),(3440,1440),(3840,2160),(5120,1440)]:
        syringe_w = height * 0.18
        x = width/2 - syringe_w/2
        tag_left = x + syringe_w * 0.254
        gap = max(4.0, syringe_w * 0.010)
        button_right = tag_left - gap
        assert 3.9 <= tag_left - button_right <= max(4.1, syringe_w * 0.011)
        assert button_right < tag_left


def test_pending_tag_typing_is_not_repainted_over_keyboard_focus():
    render = txt('functions/fn_skPendingTagRender.sqf')
    assert 'private _focus = focusedCtrl _d;' in render
    assert '_focusIDC in [84601,84602,84603]' in render
    assert 'ctrlText (_d displayCtrl (84601 + _n))' in render
    assert 'uiNamespace setVariable ["ACME_SK_PendingTagText", _lines];' in render
    assert 'if (_focusIDC != (84601 + _ln)) then {_e ctrlSetText' in render
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    assert 'ctrlAddEventHandler ["KeyUp", {call ACME_fnc_skPendingTagCommit;}]' in ensure
    assert 'ctrlAddEventHandler ["KillFocus", {call ACME_fnc_skPendingTagCommit;}]' in ensure


def test_draw_button_has_success_flash_and_successful_draw_counter():
    begin = txt('functions/fn_skCompoundBegin.sqf')
    draw = txt('functions/fn_skCompoundDraw.sqf')
    assert 'ACME_SK_CompoundDrawCount", 0' in begin
    assert 'private _drawCount = count _components;' in draw
    assert 'ctrlSetText "Drawn!"' in draw
    assert '["success",0.88] call ACME_fnc_a11yColor' in draw
    assert 'ctrlSetText format ["Draw (%1)",_count]' in draw
    assert '0.45] call CBA_fnc_waitAndExecute;' in draw


def test_save_button_has_success_flash_then_fresh_reset():
    save = txt('functions/fn_skCompoundSave.sqf')
    end = txt('functions/fn_skWasteEnd.sqf')
    assert 'ctrlSetText "Saved!"' in save
    assert '["success",0.88] call ACME_fnc_a11yColor' in save
    assert '0.55] call CBA_fnc_waitAndExecute;' in save
    assert '_save ctrlSetText "Save"' in save
    assert '_draw ctrlSetText "Draw"' in save
    assert 'call ACME_fnc_skWasteEnd' in save
    assert 'ACME_SK_CompoundDrawCount", 0' in end


def test_compound_plunger_snaps_final_hundredth_to_current_vial_limit():
    begin = txt('functions/fn_skCompoundBegin.sqf')
    assert '(_maxY - _rawY) <= (2 * pixelH)' in begin
    assert '(_maxFill - _fill) <= 0.015' in begin
    assert '_fill = _maxFill;' in begin
    assert '_newY = _maxY;' in begin


def test_plain_draw_snaps_final_hundredth_to_hard_max():
    tick = txt('functions/fn_skUiTick.sqf')
    assert '(_hardMax - _drawnNow) <= 0.015' in tick
    assert '_my >= _maxMouse - (2 * pixelH)' in tick
    assert 'ACM_circulation_SyringeDraw_DrawnAmount = _hardMax;' in tick


def test_micro_vial_residue_is_safely_discardable_and_not_regranted():
    post = txt('functions/fn_postInit.sqf')
    session = txt('functions/fn_vialSession.sqf')
    take = txt('functions/fn_vialTake.sqf')
    preview = txt('functions/fn_vialPreview.sqf')
    volume = txt('functions/fn_infusionVialVolume.sqf')
    assert 'ACME_vialDiscardResidualMl = 0.0105;' in post
    assert '_openNow <= _discardResidual' in session
    assert '_boundRemainder <= (_discardResidual + 0.000001)' in session
    assert '_unlocked = (_reservedMl + _entryCap)' in session
    assert 'private _discardedSession = (_selectedCapacity - _unlocked) max 0;' in session
    assert '_reservedMl + _discardedSession' in session
    assert '_left <= _discardResidual' in take
    assert 'missionNamespace getVariable ["ACME_vialDiscardResidualMl",0.0105]' in preview
    assert 'missionNamespace getVariable ["ACME_vialDiscardResidualMl",0.0105]' in volume


def test_micro_residue_accounting_reference_model():
    # A 1.00 mL vial stranded at 0.01 mL is intentionally discarded before the next vial.
    reserved = 0.99
    old_unlocked = 1.00
    cap = 1.00
    residual = old_unlocked - reserved
    assert residual <= 0.0105
    new_unlocked = reserved + cap
    assert abs(new_unlocked - 1.99) < 1e-9  # never grants the discarded 0.01 mL back
    # Commit of 1.99 mL from two 1 mL vials leaves 0.01, which fn_vialTake discards.
    post_debit = 2.00 - 1.99
    assert post_debit <= 0.0105


def test_carousel_hover_no_longer_changes_geometry_alpha_or_rerenders():
    hover = txt('functions/fn_skCarouselHover.sqf')
    render = txt('functions/fn_skCarouselRender.sqf')
    assert 'skCarouselRender' not in hover
    assert 'Never repaint, resize or fade' in hover
    assert 'if (_hover) then {_w = _w * 1.10' not in render
    assert '_slot == 2 && {_hover}' not in render
    assert 'private _activeScale = 1;' in render
    assert 'private _alpha = 0.85;' in render


def test_selected_carousel_syringe_has_only_one_live_hitbox():
    render = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _hitUsable = (_slot != 2)' in render
    assert 'private _activeHit = _d displayCtrl 84480;' in render
    assert '_activeHit ctrlSetTooltip _activeTip;' in render
    assert '_activeHit ctrlShow _activeUsable' in render


def test_provider_roll_uses_crouch_connected_wrapper_and_no_switchmove_fallback():
    cfg = txt('config.cpp')
    pose = txt('functions/fn_treatmentPoseStart.sqf')
    flip = txt('functions/fn_chestSealFlip.sqf')
    assert 'class ACME_RollProviderWork: AinvPknlMstpSnonWnonDnon_medic4' in cfg
    assert 'connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};' in cfg
    assert 'case "roll": {"ACME_RollProviderWork"};' in pose
    assert '[_medic, _main, 1] call ACME_fnc_doAnim;' in pose
    assert '[_medic, _main, 2] call ACME_fnc_doAnim;' not in pose
    assert 'ACME_fnc_rollProviderStart' in flip


def test_chest_seal_patient_roll_interpolates_without_priority_two():
    roll = txt('functions/fn_chestSealRoll.sqf')
    assert '[_patient, _trans, 1] call ACME_fnc_doAnim;' in roll
    assert '[_patient, _trans, 2] call ACME_fnc_doAnim;' not in roll


def test_generic_treatment_preflight_uses_transition_priority_one_and_never_restores_weapon():
    tr = txt('overrides/fn_treatment.sqf')
    prep = txt('functions/fn_medicAnimationPrep.sqf')
    stop = txt('functions/fn_treatmentPoseStop.sqf')
    assert '[_medic, _transition, 1] call ACME_fnc_doAnim;' in tr
    assert '[_medic, _transition, 2] call ACME_fnc_doAnim;' not in tr
    assert 'ace_weaponselect_fnc_putWeaponAway' in prep
    for src in (tr, prep, stop):
        assert 'selectWeapon (primaryWeapon' not in src
        assert 'selectWeapon (handgunWeapon' not in src


def test_custom_pose_exit_remains_crouched_and_releases_stance_lock():
    stop = txt('functions/fn_treatmentPoseStop.sqf')
    start = txt('functions/fn_treatmentPoseStart.sqf')
    assert 'private _upright = false;' in start
    assert '_currentMode in ["roll","inspect","pulse"]' in stop
    assert '"AmovPknlMstpSnonWnonDnon"' in stop
    assert '"AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 1' in stop
    assert '_u setUnitPos "AUTO";' in stop


def test_other_current_medical_transition_entries_use_priority_one():
    for rel, needle in [
        ('functions/fn_headElevApplyTilt.sqf', 'AinjPpneMrunSnonWnonDb_grab'),
        ('functions/fn_headElevateStop.sqf', 'AinjPpneMrunSnonWnonDb_release'),
        ('functions/fn_hangBagStart.sqf', '[_medic, _pose, 1]'),
        ('functions/fn_hangBagTick.sqf', '[_medic, _pose, 1]'),
    ]:
        src = txt(rel)
        assert needle in src
        if rel.endswith('fn_headElevApplyTilt.sqf'):
            assert '[_patient, "AinjPpneMrunSnonWnonDb_grab", 1]' in src
        if rel.endswith('fn_headElevateStop.sqf'):
            assert '[_patient, "AinjPpneMrunSnonWnonDb_release", 1]' in src



def test_animation_helpers_default_to_interpolated_priority_one():
    held = txt('functions/fn_doAnimHeld.sqf')
    queue = txt('functions/fn_animQueue.sqf')
    assert 'params ["_unit", "_anim", ["_hold", 1.2], ["_prio", 1]];' in held
    assert '(_x param [2, 1])' in queue
    assert '[["_a", ""], ["_d", 1.4], ["_p", 1]]' in queue
    assert '["_prio", 2]' not in held
    assert '(_x param [2, 2])' not in queue


def test_no_acme_medical_animation_entry_uses_priority_two_switchmove_fallback():
    offenders = []
    for base in (ROOT / 'functions', ROOT / 'overrides'):
        for path in base.glob('fn_*.sqf'):
            src = read_source(path, encoding='utf-8', errors='replace')
            if '] call ACME_fnc_doAnim;' in src:
                for line_no, line in enumerate(src.splitlines(), 1):
                    if 'call ACME_fnc_doAnim;' in line and ', 2]' in line:
                        offenders.append(f'{path.relative_to(ROOT)}:{line_no}')
    assert offenders == []


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
    print(f'B73 focused contracts: {len(tests)}/{len(tests)} passed')
