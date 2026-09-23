from historical_source import read_source, assert_release_identity
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='ignore')

def test_version_batch():
    assert_release_identity()
    p = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_main_tag_button_copies_carousel_tag_face_anchor():
    render = txt('functions/fn_skPendingTagRender.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    assert 'private _tagCenterX = _x + _w*0.36;' in render
    assert 'private _btnY = _y + _h*0.575;' in render
    assert 'safeZoneH * 0.20' in render
    assert 'private _tagCenter0 = (_r0 select 0) + (_r0 select 2)*0.36;' in ensure
    assert 'private _by0 = (_r0 select 1) + (_r0 select 3)*0.575;' in ensure

def test_pending_tag_dropdown_is_hover_open_clickable_dark_and_topmost():
    from test_bounded_tag_dropdowns import dropdown_contract, geometry_contract
    from test_bounded_tag_contracts import require
    dropdown_contract()
    geometry_contract()
    require(txt("config.cpp"), "class ACME_SK_TagList: ACME_SK_StyledList")
    require(txt("config.cpp"), "colorBackground[] = {0.04,0.04,0.04,0.96};")

def test_pending_tag_gives_immediate_feedback_and_only_exists_in_draw_view():
    render = txt('functions/fn_skPendingTagRender.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    view = txt('functions/fn_skSetView.sqf')
    assert 'private _showSetup = (_view == "syringe");' in render
    assert 'private _btnBg = switch (_color) do' in render
    assert '_tag ctrlShow true;' in render
    assert 'private _drawView = (uiNamespace getVariable ["ACME_SK_View", "syringe"]) == "syringe";' in ensure
    assert '[84600,84601,84602,84603,84610,84611]' in view

def test_pushing_status_is_bodymap_injection_only_and_above_active_syringe():
    inject = txt('functions/fn_skInject.sqf')
    render = txt('functions/fn_skCarouselRender.sqf')
    view = txt('functions/fn_skSetView.sqf')
    assert 'ctrlCreate ["ACME_SK_StyledLabel", 84810]' in inject
    assert '_pushStatus ctrlSetText "Pushing...";' in inject
    assert 'private _showPush = _injectBusy && {!_editMode};' in render
    assert 'private _statusY = (_ay - _statusH - _statusGap) max (_editBottom + _statusGap);' in render
    assert '(_display displayCtrl 84810) ctrlShow false;' in view

def test_intubate_hidden_for_conscious_patient():
    cfg = txt('config.cpp')
    block = cfg[cfg.index('class ACME_IntubateStart'):cfg.index('class ACME_IntubateStart')+3500]
    assert "ACE_isUnconscious" in block
    assert "ace_medical_unconscious" in block
    assert "ace_medical_inCardiacArrest" in block
    assert "ACME_Laryngoscope" in block and "ACME_ETTube" in block

def test_head_elevation_rolls_only_actual_prone_patient_to_supine():
    from test_bounded_head_start_contracts import start_contract
    start_contract()

def test_native_acm_treatment_cannot_invent_head_position_roll():
    cfg = txt('config.cpp')
    elev = cfg[cfg.index('class ACME_ElevateHead'):cfg.index('class ACME_LowerHead')]
    lower = cfg[cfg.index('class ACME_LowerHead'):cfg.index('class ACME_TuneHeadTilt')]
    override = txt('overrides/fn_treatment.sqf')
    assert 'ACM_rollToBack = 0;' in elev
    assert 'ACM_rollToBack = 0;' in lower
    assert 'private _nativeArgs = +_this;' in override
    assert '_classname in ["ACME_ElevateHead", "ACME_LowerHead"]' in override
    assert 'toLowerANSI _bodyPart == "body"' in override
    assert '_nativeArgs set [2, "Head"];' in override
    assert 'private _started = _nativeArgs call ACME_native_fnc_treatment;' in override

def test_exact_semifowler_patient_and_provider_animations_retained():
    from test_bounded_head_provider_sequence import provider_contract
    from test_bounded_head_pose_contracts import assert_connected_patient_states
    provider_contract()
    assert_connected_patient_states()

def test_provider_sequence_releases_on_finish_movement_or_menu_exit_without_lowering_head():
    seq = txt('functions/fn_headElevMedicSeq.sqf')
    cancel = txt('functions/fn_headElevateCancelSeq.sqf')
    assert '_u setUnitPos "AUTO";' in seq
    assert 'inputAction _x' in seq
    assert 'ace_medical_gui_menuDisplay' in seq
    assert '[_u,_pfh,true] call _finish;' in seq
    assert 'headElevateStop' not in cancel
    assert '_medic setUnitPos "AUTO";' in cancel

def test_exact_head_elevation_log_wording():
    start = txt('functions/fn_headElevMedicStart.sqf')
    stop = txt('functions/fn_headElevateStop.sqf')
    assert '"%1 elevated head 30 degrees"' in start
    assert '"%1 placed them in Semi-Fowler\'s position"' in start
    assert '"%1 laid head flat"' in stop
    assert '"%1 laid them supine"' in stop

def test_one_time_weapon_stow_no_restore_retained():
    from test_bounded_head_weapon_contract import weapon_contract
    weapon_contract()

if __name__ == '__main__':
    import inspect
    tests = [v for k,v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
    print(f'B71 focused contracts: {len(tests)}/{len(tests)} passed')
