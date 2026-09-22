from historical_source import read_source
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')


def test_b70_version_stamp():
    assert 'version = "1.0.100-r34";' in txt('config.cpp')
    post = txt('functions/fn_postInit.sqf')
    assert 'ACME_infusion_version = "1.0.100-r34"' in post
    assert 'ACME_buildBatch = "B70";' in post


def test_semifowler_patient_uses_exact_grab_release_without_helper_positioning():
    apply = txt('functions/fn_headElevApplyTilt.sqf')
    start = txt('functions/fn_headElevateStart.sqf')
    stop = txt('functions/fn_headElevateStop.sqf')
    suspend = txt('functions/fn_headElevSuspend.sqf')
    assert 'AinjPpneMrunSnonWnonDb_grab' in apply
    assert 'AinjPpneMrunSnonWnonDb_release' in stop
    assert 'AinjPpneMrunSnonWnonDb_release' in suspend
    assert '[_patient] call ACME_fnc_headElevApplyTilt;' in start
    # No B70 casualty placement/tilt helper may be introduced for the pose.
    assert '_patient attachTo' not in apply
    assert '_patient setPos' not in apply
    assert '_patient setPos' not in stop
    assert '_patient setPos' not in suspend


def test_semifowler_provider_runs_requested_full_duration_sequence_and_finishes_unarmed():
    seq = txt('functions/fn_headElevMedicSeq.sqf')
    assert 'private _dragger = "DraggerBase";' in seq
    assert 'private _toUnarmed = "AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon";' in seq
    assert 'private _unarmed = "AmovPknlMstpSnonWnonDnon";' in seq
    assert 'addEventHandler ["AnimDone"' in seq
    assert 'private _doneEH' in seq
    assert '[_u, _toUnarmed, 0] call ACME_fnc_doAnim;' in seq
    assert '[_u, _unarmed, 0] call ACME_fnc_doAnim;' in seq
    assert 'ACME_fnc_doAnimHeld' not in seq
    assert 'ACME_fnc_animQueue' not in seq


def test_provider_weapon_preflight_is_one_clear_only_and_never_tsp_or_auto_redraw():
    prep = txt('functions/fn_medicAnimationPrep.sqf')
    start = txt('functions/fn_treatmentPoseStart.sqf')
    stop = txt('functions/fn_treatmentPoseStop.sqf')
    assert 'tsp_fnc_animate_sling' not in prep
    assert prep.count('selectWeapon ""') == 1
    assert 'selectWeapon ""' not in start
    assert 'selectWeapon ""' not in stop
    # Ordinary provider-action controllers must not keep fighting a manual weapon redraw.
    for rel in [
        'functions/fn_menuPoseStart.sqf',
        'functions/fn_directPressureSelf.sqf',
        'functions/fn_directPressureTorso.sqf',
        'functions/fn_directPressureTick.sqf',
        'functions/fn_directPressurePose.sqf',
        'functions/fn_directPressureStop.sqf',
        'overrides/fn_treatment.sqf',
        'overrides/fn_beginCPR.sqf',
    ]:
        assert 'selectWeapon ""' not in txt(rel), rel


def test_all_bvm_variants_are_class_routed_to_breathing():
    menu = txt('functions/fn_menuActionInfo.sqf')
    for cls in ['usebvm', 'usebvm_oxygen', 'usebvm_vehicleoxygen', 'usebvm_portableoxygen']:
        assert cls in menu
    assert 'exitWith {["airway", "ventilation", false]};' in menu
    groups = txt('functions/fn_postInit.sqf')
    assert '"Use BVM"' in groups
    assert '"Use BVM with Oxygen"' in groups


def test_adjust_thoracostomy_requires_actual_existing_procedure_and_is_in_chest():
    can = txt('functions/fn_thoraCanOpen.sqf')
    cfg = txt('config.cpp')
    dead = txt('overrides/fn_canTreatCached.sqf')
    menu = txt('functions/fn_menuActionInfo.sqf')
    groups = txt('functions/fn_postInit.sqf')
    assert 'params ["_medic", "_patient", ["_existingOnly", false' in can
    assert 'if (_existingOnly && {!_completed}) exitWith {false};' in can
    assert 'private _partial =' in can
    assert "[_medic, _patient, true] call ACME_fnc_thoraCanOpen" in cfg
    assert 'case "ACME_AdjustThoracostomy": {[_caller, _target, true] call ACME_fnc_thoraCanOpen};' in dead
    assert '"acme_adjustthoracostomy"' in menu
    assert '["airway", "chest", false]' in menu
    assert '"Adjust Thoracostomy"' in groups


def test_main_select_syringe_tag_is_deferred_self_healing_and_always_rendered_on_draw_page():
    cfg = txt('config.cpp')
    inject = txt('functions/fn_skInject.sqf')
    open_draw = txt('functions/fn_skOpenDraw.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    render = txt('functions/fn_skPendingTagRender.sqf')
    assert 'class skPendingTagEnsure {};' in cfg
    assert 'ACME_SK_PendingTagReady", false' in inject
    assert 'ACME_SK_PendingTagReady", true' in open_draw
    assert 'call ACME_fnc_skPendingTagEnsure;' in open_draw
    assert 'ctrlCreate ["ACME_SK_StyledButton", 84610]' in ensure
    assert 'Select Syringe Tag' in ensure
    assert 'call ACME_fnc_skPendingTagEnsure;' in render
    assert 'private _showSetup = (_view == "syringe");' in render
    assert '_button ctrlShow true;' in render


def test_main_tag_text_fields_stay_hidden_until_real_color_exists():
    render = txt('functions/fn_skPendingTagRender.sqf')
    assert 'private _hasTag = !(_color in ["", "none"]);' in render
    assert '_e ctrlShow _hasTag;' in render
    assert '_e ctrlEnable _hasTag;' in render


def test_syringe_can_return_last_hundredth_to_exact_endpoint():
    compound = txt('functions/fn_skCompoundBegin.sqf')
    tick = txt('functions/fn_skUiTick.sqf')
    assert '(_fill - _floorMl) <= 0.015' in compound
    assert '_fill = _floorMl;' in compound
    assert '_newY = _floorY;' in compound
    assert '_drawnNow <= 0.015' in tick
    assert 'ACM_circulation_SyringeDraw_DrawnAmount = 0;' in tick


def test_edit_tag_stays_visible_during_ad_and_center_click_toggles_carousel():
    move = txt('functions/fn_skCarouselMove.sqf')
    pick = txt('functions/fn_skCarouselPick.sqf')
    # Movement may hide editors/list/done/hitbox, but not the persistent Edit Syringe Tag button 84470.
    assert '[84460,84461,84462,84470,84471,84472,84480]' not in move
    assert '[84460,84461,84462,84471,84472,84480]' in move
    assert 'call ACME_fnc_skCarouselToggle;' in pick


def test_b69_chest_seal_spacing_is_retained():
    gen = txt('functions/fn_chestSealGenHoles.sqf')
    assert 'ACME_CS_minHoleSep", 0.052' in gen
    assert 'for "_try" from 1 to 48 do {' in gen
