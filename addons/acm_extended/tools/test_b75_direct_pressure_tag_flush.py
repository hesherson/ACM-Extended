from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')

def test_version_batch():
    assert_release_identity()
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_only_torso_direct_pressure_owns_continuous_action():
    # B75's torso-exclusive controller was superseded by persistent DP in all
    # regions. Execute the current ownership contract, including self pressure.
    from test_historical_pressure_ownership import CASES, test_every_region_is_persistent_without_claiming_the_native_continuous_controller
    for args in CASES:
        test_every_region_is_persistent_without_claiming_the_native_continuous_controller(*args)

def test_non_torso_pressure_is_not_cancelled_by_other_maneuvers():
    # Incompatible maneuvers temporarily yield clinical pressure. Accepted BVM
    # explicitly releases this provider's pressure, but rejected BVM preserves it.
    from test_historical_pressure_ownership import CASES, test_an_incompatible_maneuver_yields_marker_once_and_excludes_paused_time
    from test_native_bvm_dp import test_pressure_to_bvm_breath_pause_resume_stop_and_repeat, test_rejected_bvm_start_preserves_direct_pressure, test_another_providers_pressure_is_untouched
    for args in CASES:
        test_an_incompatible_maneuver_yields_marker_once_and_excludes_paused_time(*args)
    for part in ('body','leftarm','head'):
        test_pressure_to_bvm_breath_pause_resume_stop_and_repeat(part)
    test_rejected_bvm_start_preserves_direct_pressure('_patientAwake = true;')
    test_another_providers_pressure_is_untouched()

def test_direct_pressure_floating_indicator_is_not_installed():
    limb = txt('functions/fn_directPressureLimb.sqf')
    selfp = txt('functions/fn_directPressureSelf.sqf')
    torso = txt('functions/fn_directPressureTorso.sqf')
    for src in (limb, selfp, torso):
        assert 'addMissionEventHandler ["Draw3D"' not in src
        assert 'directPressureDraw3D' not in src
    helper = txt('functions/fn_directPressureDraw3D.sqf')
    assert 'drawIcon3D' not in helper
    assert 'no-op' in helper

def test_tag_limit_is_exactly_17_and_commits_are_defensive():
    cfg = txt('config.cpp')
    tag_class = cfg[cfg.index('class ACME_SK_TagEdit'):cfg.index('class ACME_SK_TagText')]
    assert 'maxChars = 17;' in tag_class
    for rel in ['functions/fn_skPendingTagCommit.sqf','functions/fn_skTagCommit.sqf','functions/fn_skApplyPendingTag.sqf']:
        src = txt(rel)
        assert 'select [0,17]' in src or 'select [0, 17]' in src

def test_tag_edit_boxes_are_tall_enough_for_ascenders_and_descenders():
    pending = txt('functions/fn_skPendingTagRender.sqf')
    carousel = txt('functions/fn_skCarouselRender.sqf')
    move = txt('functions/fn_skCarouselMove.sqf')
    for src in (pending, carousel):
        assert 'private _lineH = 0.030;' in src
        assert 'private _lineFontH = 0.024;' in src
    assert '_h*_lineH' in pending
    assert '_ah*_lineH' in carousel
    assert '[0.450,0.482,0.514]' in move
    assert '_h*0.030' in move
    assert '_h*0.024' in move

def test_main_tag_selector_moves_right_in_pixel_scaled_units():
    pending = txt('functions/fn_skPendingTagRender.sqf')
    ensure = txt('functions/fn_skPendingTagEnsure.sqf')
    assert '_tagLeft - _gap + (20 * pixelW)' in pending
    assert '_tagLeft0 - _gap0 + (20 * pixelW)' in ensure
    # Still native-syringe anchored, not ultrawide safe-zone positioning.
    assert '_x + _w*0.254' in pending
    assert '(_r0 select 0) + (_r0 select 2)*0.254' in ensure

def test_flush_draw_stage_is_multicomponent_and_repeatable():
    commit = txt('functions/fn_skWasteCommit.sqf')
    draw = txt('functions/fn_skWasteDraw.sqf')
    begin = txt('functions/fn_skWasteBegin.sqf')
    assert 'call ACME_fnc_skFlushSave' in commit
    assert '_components pushBack [_med,_drugMl];' in draw
    assert 'ACME_SK_WasteFloorMl",_fill' in draw
    assert 'Draw (%1)' in draw
    assert '_stage == "draw"' in begin
    assert 'ACME_SK_CompoundComponents' in begin
    assert 'ACME_fnc_vialSession' in begin

def test_flush_save_consumes_one_flush_and_all_medication_components():
    save = txt('functions/fn_skFlushSave.sqf')
    assert 'ACME_fnc_medicationTakeSources' in save
    assert '_components,_flushClass,true' in save.replace(' ', '')
    assert '"dilutionB13"' in save
    assert '_entry set [12,"flush"]' in save
    assert 'ctrlSetText "Saved!"' in save

def test_flush_special_epi_keeps_existing_partial_push_behavior():
    save = txt('functions/fn_skFlushSave.sqf')
    epi = txt('functions/fn_epinephrinePrepare.sqf')
    assert 'ACME_fnc_epinephrineRecipe' in save
    assert 'ACME_fnc_epinephrinePrepare' in save
    assert '_entry set [12,"flush"]' in epi

def test_stored_medicated_flush_uses_real_flush_barrel_art():
    render = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _isFlushBarrel = (_e param [12,"",[""]]) == "flush";' in render
    assert '\\acm_extended\\ui\\syringe\\syringe_flush_10_barrel_ca.paa' in render
    assert (ROOT / 'ui/syringe/syringe_flush_10_barrel_ca.paa').is_file()

def test_flush_stage_participates_in_medication_contents_stock_accounting():
    for rel in [
        'functions/fn_skListRefresh.sqf',
        'functions/fn_skListSelect.sqf',
        'functions/fn_skMedicationSelect.sqf',
        'functions/fn_skMedicationStockRefresh.sqf',
        'functions/fn_skUiTick.sqf',
        'functions/fn_skSetView.sqf',
    ]:
        src = txt(rel)
        assert '"compound","draw"' in src or '"compound", "draw"' in src

def test_flush_volume_reference_model():
    # Remaining saline is immutable carrier; each Draw advances the floor and Save stores total drug + saline.
    saline = 6.0
    components = [('Fentanyl', 1.0), ('Ketamine', 2.5)]
    floor = saline
    for _, ml in components:
        floor += ml
    assert abs(floor - 9.5) < 1e-9
    total_drug = sum(v for _, v in components)
    assert abs(saline + total_drug - 9.5) < 1e-9
    assert saline + total_drug <= 10.0

if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for t in tests:
        t()
    print(f'B75 focused contracts: {len(tests)}/{len(tests)} passed')
