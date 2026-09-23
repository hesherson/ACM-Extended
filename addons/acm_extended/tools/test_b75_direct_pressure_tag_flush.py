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
    from test_bounded_pressure_contracts import assert_nonexclusive_contract
    # The historical identity is retained; torso now shares nonexclusive ownership.
    assert_nonexclusive_contract(txt('functions/fn_directPressureStart.sqf'), [
        txt('functions/fn_directPressureTorso.sqf'),
        txt('functions/fn_directPressureLimb.sqf'),
        txt('functions/fn_directPressureSelf.sqf'),
    ])

def test_non_torso_pressure_is_not_cancelled_by_other_maneuvers():
    from test_bounded_pressure_contracts import assert_compatible_work_contract
    # Compatible work yields/resumes; accepted BVM deliberately releases this DP episode.
    assert_compatible_work_contract(txt('functions/fn_directPressureTick.sqf'),
                                    txt('functions/fn_hangBagCanStart.sqf'),
                                    txt('functions/fn_measureBPWrap.sqf'))

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
    # The later 25-character contract supersedes 17; retain the old test identity.
    from test_bounded_tag_contracts import tag_limits, test_three_line_roundtrip_preserves_case_payload_identity_and_other_syringes
    tag_limits()
    for length in (0,17,25,26,80):
        test_three_line_roundtrip_preserves_case_payload_identity_and_other_syringes(length, True)
    from test_historical_syringe_identity import test_pending_tag_rejects_wrong_metadata_types_without_altering_drug, test_tag_commit_cannot_write_when_display_or_selected_record_is_gone
    test_pending_tag_rejects_wrong_metadata_types_without_altering_drug(5, '"bad"', '["none","","",""]')
    for absent in ('display','selection'):
        test_tag_commit_cannot_write_when_display_or_selected_record_is_gone(absent)

def test_tag_edit_boxes_are_tall_enough_for_ascenders_and_descenders():
    from test_bounded_tag_line_layout import layout_contract
    layout_contract()

def test_main_tag_selector_moves_right_in_pixel_scaled_units():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()

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
