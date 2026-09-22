from historical_source import read_source
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')


def test_version_batch():
    cfg = txt('config.cpp')
    post = txt('functions/fn_postInit.sqf')
    assert 'version = "1.0.100-r36";' in cfg
    assert '"1.0.100-r36"' in post
    assert 'ACME_buildBatch = "B72";' in post


def test_rpt_confirmed_pending_tag_renderer_compile_bug_is_removed():
    src = txt('functions/fn_skPendingTagRender.sqf')
    assert 'if (!_showSetup) exitWith {' in src
    assert 'if (!_showSetup) then {' not in src
    assert 'exitWith {};\n};\n\nprivate _color' not in src


def test_main_tag_button_is_compact_and_anchored_left_of_barrel():
    render = txt('functions/fn_skPendingTagRender.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    assert 'safeZoneH * 0.165' in render
    assert 'private _btnRight = _x + _w*0.20;' in render
    assert 'private _btnX = _btnRight - _btnW;' in render
    assert 'safeZoneH * 0.165' in ensure
    assert 'private _btnRight0 = (_r0 select 0) + (_r0 select 2)*0.20;' in ensure


def test_main_tag_dropdown_is_directly_below_and_full_description_width():
    render = txt('functions/fn_skPendingTagRender.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    cfg = txt('config.cpp')
    assert 'private _menuX = _btnX max' in render
    assert 'private _menuY = _btnY + _btnH + 2*pixelH;' in render
    assert 'safeZoneW * 0.24' in render
    assert 'safeZoneH * 0.58' in render
    assert 'ctrlAddEventHandler ["MouseEnter"' in ensure
    assert 'ctrlAddEventHandler ["LBSelChanged"' in ensure
    assert 'ctrlAddEventHandler ["MouseButtonUp"' in ensure
    assert 'class ACME_SK_TagList: ACME_SK_StyledList' in cfg
    assert 'colorBackground[] = {0.04,0.04,0.04,0.96};' in cfg


def test_selected_main_tag_immediately_renders_real_overlay_and_edit_lines():
    render = txt('functions/fn_skPendingTagRender.sqf')
    color = txt('functions/fn_skPendingTagColor.sqf')
    assert r'\acm_extended\ui\syringe_tags\%1mL\tag_overlay_%1mL_%2.paa' in render
    assert '_tag ctrlShow true;' in render
    assert '_e ctrlShow _hasTag;' in render
    assert 'call ACME_fnc_skPendingTagRender;' in color


def test_draw_save_commits_tag_color_and_three_lines_to_syringe():
    draw = txt('overrides/fn_syringeDrawButton.sqf')
    apply = txt('functions/fn_skApplyPendingTag.sqf')
    assert 'call ACME_fnc_skPendingTagCommit;' in draw
    assert 'call ACME_fnc_skApplyPendingTag' in draw
    assert '_out set [7, _color];' in apply
    assert '_out set [8 + _i' in apply


def test_new_qedavemergens_font_replaces_old_runtime_wiring():
    cfg = txt('config.cpp')
    pending = txt('functions/fn_skPendingTagRender.sqf')
    carousel = txt('functions/fn_skCarouselRender.sqf')
    assert 'class ACME_QEDaveMergens' in cfg
    assert r'\acm_extended\ui\fonts\QEDaveMergens\QEDaveMergens96' in cfg
    assert 'font = "ACME_QEDaveMergens";' in cfg
    assert 'QEDaveMergens96.fxy' in pending and 'ACME_QEDaveMergens' in pending
    assert 'QEDaveMergens96.fxy' in carousel and 'ACME_QEDaveMergens' in carousel
    for src in (cfg, pending, carousel):
        assert 'ACME_QEPhillips' not in src
        assert r'ui\fonts\QEPhillips' not in src
    assert (ROOT / 'B72_QEDAVEMERGENS_LOCAL_SETUP.txt').exists()
    assert not (ROOT / 'B64_QEPHILLIPS_LOCAL_SETUP.txt').exists()


def test_chest_reveal_is_not_expired_by_cross_machine_mission_clock():
    edit = txt('functions/fn_chestSealEdit.sqf')
    effect = txt('functions/fn_chestSealEffectLocal.sqf')
    assert 'CBA_missionTime - _issued' not in edit
    assert '_issued > CBA_missionTime' not in edit
    assert 'Treatment request expired' not in edit
    assert '!finite _issued' in edit
    assert 'CBA_missionTime - _issued' not in effect
    assert 'ACME_CS_blockedEffectEpoch' in effect
    assert 'ACME_CS_lastSealEffectRev' in effect


def test_chest_reveal_keeps_epoch_revision_idempotence_guards():
    request = txt('functions/fn_chestSealRequest.sqf')
    edit = txt('functions/fn_chestSealEdit.sqf')
    assert 'ACME_CS_pending set' in request
    assert 'ACME_CS_editResults getOrDefault' in edit
    assert '_epoch != (_snapshot select 0)' in edit
    assert '_expected > (_snapshot select 1)' in edit
    assert 'ACME_CS_sealRevisions' in edit


def test_head_patient_grab_uses_priority_two_and_startup_grace():
    apply = txt('functions/fn_headElevApplyTilt.sqf')
    guard = txt('functions/fn_headElevAnimGuard.sqf')
    assert 'ACME_headElev_animGraceUntil' in apply
    assert 'CBA_missionTime + 2.5' in apply
    assert '[_patient, "AinjPpneMrunSnonWnonDb_grab", 2]' in apply
    assert 'ACME_headElev_animGraceUntil' in guard
    assert '_anim == _restAnim' in guard
    assert 'CBA_missionTime <= _graceUntil' in guard


def test_head_patient_release_is_priority_two_and_never_setpos():
    stop = txt('functions/fn_headElevateStop.sqf')
    apply = txt('functions/fn_headElevApplyTilt.sqf')
    assert '[_patient, "AinjPpneMrunSnonWnonDb_release", 2]' in stop
    assert '_patient setPos' not in stop
    assert '_patient setPos' not in apply
    assert '_patient attachTo' not in apply


def test_head_provider_stands_only_for_draggerbase_then_returns_crouched():
    seq = txt('functions/fn_headElevMedicSeq.sqf')
    assert 'private _dragger = "DraggerBase";' in seq
    assert '_medic setUnitPos "AUTO";' in seq
    stage0 = seq[seq.index('if (_stage == 0) exitWith {'):]
    assert '_u setUnitPos "MIDDLE";' in stage0
    assert 'AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon' in seq
    assert 'private _unarmed = "AmovPknlMstpSnonWnonDnon";' in seq


def test_head_elevation_only_rolls_patient_when_actually_prone():
    start = txt('functions/fn_headElevateStart.sqf')
    assert 'call ACME_fnc_chestSealActualSide) == "back"' in start
    assert 'if (_mustRollSupine) exitWith {' in start
    assert '[_patient, "front"] call ACME_fnc_chestSealRoll;' in start


def test_generic_provider_work_preflights_to_empty_hands_and_crouch_once():
    prep = txt('functions/fn_medicAnimationPrep.sqf')
    tr = txt('overrides/fn_treatment.sqf')
    assert 'ace_weaponselect_fnc_putWeaponAway' in prep
    assert 'SwitchWeapon' in prep and '299' in prep
    assert 'selectWeapon ""' not in prep
    assert 'ACME_treatmentPreflightActive' in tr
    assert 'currentWeapon _m == ""' in tr
    assert 'stance _m == "CROUCH"' in tr
    assert '_medic setUnitPos "MIDDLE";' in tr
    assert '_headOwned = _classname in ["ACME_ElevateHead", "ACME_LowerHead"]' in tr
    assert 'ACME_treatmentPreflightBypass' in tr


def test_generic_acme_treatment_poses_never_choose_standing_medicup_variants():
    pose = txt('functions/fn_treatmentPoseStart.sqf')
    assert 'private _upright = false;' in pose
    assert 'call ACME_fnc_poseUprightState' not in pose


def test_no_automatic_weapon_restore_in_core_provider_paths():
    for rel in [
        'functions/fn_medicAnimationPrep.sqf',
        'functions/fn_treatmentPoseStart.sqf',
        'functions/fn_treatmentPoseStop.sqf',
        'functions/fn_headElevMedicSeq.sqf',
        'overrides/fn_treatment.sqf',
    ]:
        src = txt(rel)
        assert 'selectWeapon (primaryWeapon' not in src
        assert 'selectWeapon (handgunWeapon' not in src
        assert 'selectedWeaponOnTreatment' not in src


def test_generic_preflight_never_falls_through_with_weapon_or_standing_state():
    tr = txt('overrides/fn_treatment.sqf')
    assert '[_medic,_argsB72,_tokenB72], 3.0' in tr
    timeout = tr[tr.index('[_medic,_argsB72,_tokenB72], 3.0'):tr.index('}] call CBA_fnc_waitUntilAndExecute;', tr.index('[_medic,_argsB72,_tokenB72], 3.0'))]
    assert '_args call ace_medical_treatment_fnc_treatment;' not in timeout
    assert '_m setUnitPos "AUTO";' in timeout


def test_provider_stance_lock_is_released_after_native_and_custom_treatment_end():
    post = txt('functions/fn_postInit.sqf')
    stop = txt('functions/fn_treatmentPoseStop.sqf')
    assert 'B72 provider stance release' in post
    assert '} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];' in post
    assert '_m setUnitPos "AUTO";' in post
    assert '_u setUnitPos "AUTO";' in stop
    assert '0.85] call CBA_fnc_waitAndExecute;' in stop


def test_cursor_menu_defers_before_provider_preflight():
    tr = txt('overrides/fn_treatment.sqf')
    cursor = tr.index('ace_interact_menu_cursorMenuOpened')
    preflight = tr.index('ACME_treatmentPreflightActive')
    assert cursor < preflight


if __name__ == '__main__':
    tests = [v for k,v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
    print(f'B72 focused contracts: {len(tests)}/{len(tests)} passed')
