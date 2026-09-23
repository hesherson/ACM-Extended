from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def text(rel):
    return read_source(ROOT / rel, errors="ignore")


def test_b46_version_stamp():
    assert_release_identity()
    p = text('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()


def test_b38_runtime_title_bar_is_removed_from_renderer():
    s = text('functions/fn_skListRefresh.sqf')
    assert 'ACME_SK_ColumnHeader' not in s
    assert '_headerBack' not in s
    assert '_headerContents' not in s
    assert '_headerCount' not in s
    assert 'forEach [84007,84008]' not in s
    # Source selector controls must stay at ACM's original dialog geometry.
    assert '_pos set [1, (_pos select 1) - _headerH]' not in s


def test_separate_count_child_control_is_removed():
    s = text('functions/fn_skListRefresh.sqf')
    assert '_countText' not in s
    assert 'ctrlCreate ["ACME_SK_RightText"' not in s
    assert '["%1 mL  x%2", _curMl toFixed 2, _count]' in s
    assert '_stock ctrlSetPosition [_innerW - _stockW, _cursorY, _stockW, _rowH];' in s


def test_tick_updates_one_combined_stock_control():
    s = text('functions/fn_skUiTick.sqf')
    assert '_countText' not in s
    assert '_stock ctrlSetText format ["%1 mL  x%2", _curMl toFixed 2, _cnt];' in s


def test_medication_label_has_nonblank_config_and_key_fallback():
    # Current native-row labels are retained; blank native/config fields use metadata or the key.
    from test_historical_medication_rows import test_blank_label_and_unknown_open_vial_use_medication_key_fallback, test_sync_normalizes_missing_or_wrongly_typed_fields_and_rejects_invalid_identities, test_visible_rows_keep_native_labels_but_recover_blank_labels_from_metadata
    test_blank_label_and_unknown_open_vial_use_medication_key_fallback()
    test_sync_normalizes_missing_or_wrongly_typed_fields_and_rejects_invalid_identities()
    test_visible_rows_keep_native_labels_but_recover_blank_labels_from_metadata()


def test_b45_backend_registry_fix_is_retained():
    from test_historical_medication_rows import test_catalog_fallbacks_and_duplicate_entries_do_not_change_medication_identity, test_rows_follow_selected_inventory_and_never_manufacture_stock
    test_catalog_fallbacks_and_duplicate_entries_do_not_change_medication_identity('[]','[]')
    test_rows_follow_selected_inventory_and_never_manufacture_stock('_medic')


def test_medication_group_stays_visible_in_body_and_infusion_paths():
    # Preserve the current shared prep group, not obsolete always-visible Body Map sources.
    from test_bounded_medication_presentation import renderer_contract, test_actual_view_and_refresh_keep_preparation_sources_off_body_map, require, source
    renderer_contract()
    for view in ('body','syringe'):
        for infusion in (False,True):
            test_actual_view_and_refresh_keep_preparation_sources_off_body_map(view,infusion,'medication')
    require(source('skListRefresh'), '_backdropB54 ctrlShow _visible;')
    require(source('skListRefresh'), '{_x ctrlShow _visible; _x ctrlCommit 0;} forEach _header;')
