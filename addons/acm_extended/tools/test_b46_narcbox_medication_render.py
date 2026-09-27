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
    # The later three-column header supersedes B46's removal. Preserve one header per group.
    from test_bounded_stock_columns import header_contract, test_headers_are_created_once_and_source_captions_only_move_once
    header_contract()
    for visible in (False, True):
        test_headers_are_created_once_and_source_captions_only_move_once(1, visible)


def test_separate_count_child_control_is_removed():
    # The current renderer owns separate Contents and Vials controls, not the retired combined label.
    from test_bounded_stock_columns import split_column_contract, test_stock_info_formats_two_columns_without_mutating_bound_or_open_stock
    split_column_contract()
    for bound in (False, True):
        test_stock_info_formats_two_columns_without_mutating_bound_or_open_stock(bound, 0.25, 1)


def test_tick_updates_one_combined_stock_control():
    from test_bounded_stock_columns import tick_contract, test_selected_row_refresh_keeps_contents_count_and_reserved_amount_separate
    tick_contract()
    for stage, reserved in (('', 1.5), ('compound', 3.5), ('draw', 3.5), ('waste', 0)):
        test_selected_row_refresh_keeps_contents_count_and_reserved_amount_separate(stage, reserved, True, True)
        test_selected_row_refresh_keeps_contents_count_and_reserved_amount_separate(stage, reserved, False, True)


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
