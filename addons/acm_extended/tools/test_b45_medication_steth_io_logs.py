from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
def text(rel):
    return read_source(ROOT / rel, errors="ignore")


def test_b45_version_stamp():
    assert_release_identity()
    p = text('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()


def test_medication_source_uses_real_acm_registry_and_inventory_first():
    # The native class catalog plus the selected inventory counter is current policy,
    # not the retired independent uniqueItems enumeration or a literal macro-name variable.
    from test_historical_medication_rows import test_rows_follow_selected_inventory_and_never_manufacture_stock, test_vehicle_rows_use_cargo_counts_not_the_provider_inventory
    for holder in ['_medic','_patient','objNull']:
        test_rows_follow_selected_inventory_and_never_manufacture_stock(holder)
    test_vehicle_rows_use_cargo_counts_not_the_provider_inventory()


def test_postinit_snapshots_actual_native_registry():
    from test_historical_medication_rows import test_initializer_publishes_real_native_catalog_and_snapshot, test_restore_repairs_the_real_native_registry_without_mutating_snapshot
    test_initializer_publishes_real_native_catalog_and_snapshot('[]')
    test_restore_repairs_the_real_native_registry_without_mutating_snapshot('[]')


def test_medication_column_visible_in_body_and_infusion_views():
    # Body Map is now administration-only; prep infusions explicitly return to preparation.
    from test_bounded_medication_presentation import test_actual_view_and_refresh_keep_preparation_sources_off_body_map, require, source
    for view in ('syringe','body','carousel'):
        for infusion in (False,True):
            test_actual_view_and_refresh_keep_preparation_sources_off_body_map(view,infusion,'medication')
    for name in ('skSetView','skListRefresh'):
        s=source(name)
        require(s, 'ctrlShow (!_infusion && {!_body})')
        require(s, 'ctrlShow (!_body)')


def test_narc_box_vascular_highlight_matches_acm_green():
    s = text('functions/fn_skBuildHotspots.sqf')
    assert 'private _vascularColor = [0.20, 0.65, 0.20, 0.42];' in s
    assert 'private _green = [0.20,0.65,0.20,0.92];' in s
    assert 'private _tint = +_vascularColor;' in s
    assert 'private _tint = +_imColor;' in s


def test_stethoscope_dialog_does_not_depend_on_pose_episode():
    s = text('functions/fn_beginStethoscopeAction.sqf')
    assert 'private _poseEnded' not in s
    cancel = s[s.index('if (_patientCondition'):]
    assert '_poseEnded' not in cancel
    assert 'if (_key == 0x01)' in s
    assert 'ACM_core_ContinuousAction_ShouldReopen = true;' in s
    assert 'if (_key == 0x23) exitWith {true};' in s
    assert 'ACM_core_openMedicalMenu' in s


def test_io_insertion_has_moderate_floor_and_fluid_has_max_pain_syncope():
    from test_historical_io_lifecycle import (
        test_placement_keeps_existing_floor_without_scheduling_syncope,
        test_flow_and_medication_preserve_pain_but_only_awake_fluid_schedules,
        test_syncope_uses_public_transition_once_after_the_existing_delay,
    )
    for pain in (0, 0.35, 1):
        test_placement_keeps_existing_floor_without_scheduling_syncope(pain, False)
    for mode in ("fluid", "medication"):
        test_flow_and_medication_preserve_pain_but_only_awake_fluid_schedules(mode, False)
    test_syncope_uses_public_transition_once_after_the_existing_delay(3)
    # Preserve current policy constants and native placement event registration.
    p = text('functions/fn_postInit.sqf')
    assert 'ACME_ioInsertionMinPain = 0.35;' in p
    assert 'ACME_ioFluidSyncopeDelay = 3;' in p
    assert '"ACM_circulation_setIVLocal"' in p
    assert '[_patient, _bodyPart, "placement"] call ACME_fnc_ioPainResponse;' in p


def test_io_pain_fires_on_actual_bag_volume_and_exact_io_pushes():
    from test_historical_core_boundaries import (
        test_ace_volume_bridge_delegates_inputs_and_return_without_second_integration,
        test_only_positive_admitted_io_bag_volume_reaches_the_actual_response,
    )
    from test_historical_io_lifecycle import test_actual_medication_line_routes_only_io_and_debounces_receipts
    test_ace_volume_bridge_delegates_inputs_and_return_without_second_integration()
    for admitted in (0, 25):
        for access in ("ACM_IO_FAST1_M", "ACM_IO_EZ_M", "1"):
            test_only_positive_admitted_io_bag_volume_reaches_the_actual_response(admitted, access)
    # IO medication pushes retain their medication mode; actual carrier flushes use fluid mode.
    for site, operation, mode in ((-1, "administer", "medication"), (-1, "flush", "fluid"), (0, "flush", "")):
        test_actual_medication_line_routes_only_io_and_debounces_receipts(site, operation, mode)


def test_chest_seal_public_wrapper_duplicate_removed():
    s = text('functions/fn_chestSealEffectLocal.sqf')
    assert 'call ACM_breathing_fnc_applyChestSealLocal;' in s
    assert 'call ACM_breathing_fnc_applyChestSeal;' not in s
    assert 'ACME_fnc_chestSealLogOnce' in s
    assert 'class chestSealLogOnce {};' in text('config.cpp')


def test_chest_seal_log_channels_are_independent_and_cooled_down():
    h = text('functions/fn_chestSealLogOnce.sqf')
    for action in ['case "apply"', 'case "burp"', 'case "remove"']:
        assert action in h
    p = text('functions/fn_postInit.sqf')
    assert 'ACME_chestSealApplyLogCooldown = 30;' in p
    assert 'ACME_chestSealBurpLogCooldown = 10;' in p
    assert 'ACME_chestSealRemoveLogCooldown = 10;' in p
    b = text('functions/fn_chestSealBurp.sqf')
    assert '"burp", "Burped chest seal"' in b
