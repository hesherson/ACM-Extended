from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8-sig', errors='ignore')

def test_version_batch():
    assert_release_identity()
    p = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_finite_provider_animations_are_one_shot_not_watchdog_replayed():
    from test_historical_pose_lifecycle import test_finite_work_enters_once_without_a_fixed_replay_loop, test_owner_hold_reasserts_only_observed_drift_and_never_replays_running_action
    for mode in ('response','airway','torsoBandage'):
        test_finite_work_enters_once_without_a_fixed_replay_loop(mode)
    for disturbance in ('none','speed','state'):
        test_owner_hold_reasserts_only_observed_drift_and_never_replays_running_action(disturbance)

def test_tsp_sling_is_latched_and_never_reinvoked_during_same_handoff():
    # The one-shot guarantee belongs to the current holster reservation, not old TSP timings.
    from test_historical_weapon_preflight import test_real_pose_handoff_shares_pending_holster_instead_of_restarting_it
    for weapon in ('pistol','rifle','launcher'):
        test_real_pose_handoff_shares_pending_holster_instead_of_restarting_it(weapon)

def test_medication_three_column_overlay_is_restored_and_direct_data_driven():
    # The native live labels win; metadata joins by medication key and fills missing rows.
    from test_bounded_medication_presentation import renderer_contract
    from test_historical_medication_rows import test_visible_rows_keep_native_labels_but_recover_blank_labels_from_metadata, test_visible_rows_bind_metadata_by_key_and_recover_missing_backing_entries, test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class
    renderer_contract()
    test_visible_rows_keep_native_labels_but_recover_blank_labels_from_metadata()
    test_visible_rows_bind_metadata_by_key_and_recover_missing_backing_entries('[]')
    test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class()

def test_native_medication_list_is_hidden_backing_selector_everywhere():
    for rel, token in [
        ('functions/fn_skMedicationSync.sqf', '_list ctrlShow false;'),
        ('functions/fn_skSetView.sqf', '(_display displayCtrl 84006) ctrlShow false;'),
        ('functions/fn_skUiTick.sqf', '(_d displayCtrl 84006) ctrlShow false;'),
        ('functions/fn_infusionDrawStock.sqf', '_list ctrlShow false;'),
        ('functions/fn_skInject.sqf', '_medListNative ctrlShow false;'),
    ]:
        assert token in txt(rel), rel

def test_medication_source_mirrors_acm_vial_membership_and_never_requires_extra_registry_filter():
    s = txt('functions/fn_medicationSourceRows.sqf')
    assert 'ACM_circulation_MedicationVialList' in s
    assert 'configClasses (configFile >> "CfgWeapons")' in s
    assert 'getNumber (_cfg >> "ACM_isVial")' in s
    assert '[_holder, _class] call ACME_fnc_vialItemCount' in s
    assert 'if (_label == "") then {_label = _med;};' in s
    # B49's concentration-class display gate was removed; concentration belongs to draw math, not row visibility.
    assert 'if !(isClass _conc) then {continue}' not in s

def test_prepared_iv_sets_button_counts_and_pulses_green():
    s = txt('functions/fn_updateTransfusionControls.sqf')
    assert 'private _preparedSetCountB50 = count (ACE_player getVariable ["ACME_preparedIVSets", []]);' in s
    assert 'Prepared IV sets (%1)' in s
    assert '[0.20, 0.65, 0.20, 0.30 + 0.45 * _setPulse]' in s
    assert 'diag_tickTime % 1' in s

def test_prep_infusion_only_enables_for_selected_prepared_saline():
    s = txt('functions/fn_updateTransfusionControls.sqf')
    gate = s[s.index('private _canPrep = false;'):s.index('private _preparedEntries')]
    assert 'if (_preparedMode) then {' in gate
    assert 'ACME_preparedIVSets' in gate
    assert 'param [8, "yset"]' in gate
    assert 'ACME_fnc_isSalineItem' in gate
    assert '_canPrep = (_pSetsPrep findIf' not in gate
    assert 'In loose-bag view _canPrep deliberately remains false' in gate

def test_prep_callback_has_same_hard_gate():
    s = txt('functions/fn_openPrepFromInventoryMenu.sqf')
    assert 'if (!_preparedMode) exitWith' in s
    assert 'Open Prepared IV sets and select a saline set first.' in s
    assert 'Only a selected normal saline set can be prepared into an infusion.' in s
    assert 'ACME_fnc_isSalineItem' in s

def test_previous_b49_intubation_and_obtunded_contracts_untouched():
    p = txt('functions/fn_postInit.sqf')
    assert 'ACME_laryngo_cuffRunTime = 1.0' in p
    assert 'ACME_ETT_MinSeatFrame = 5' in p
    assert 'ACME_obtunded_getUpTime = 5.5' in p
    assert 'ACME_obtunded_sprintFallChance = 0.35' in p
