from historical_source import read_source
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8-sig', errors='ignore')

def test_version_batch():
    assert 'version = "1.0.100-r14";' in txt('config.cpp')
    p = txt('functions/fn_postInit.sqf')
    assert 'ACME_buildBatch = "B50";' in p
    assert 'ACME_infusion_version = "1.0.100-r14"' in p

def test_finite_provider_animations_are_one_shot_not_watchdog_replayed():
    s = txt('functions/fn_treatmentPoseStart.sqf')
    assert 'case "response": {"AinvPknlMstpSnonWrflDr_medic3_old"};' in s
    assert 'case "airway": {"AinvPknlMstpSnonWrflDr_medic4_old"};' in s
    assert 'case "roll": {"AinvPknlMstpSnonWrflDnon_medic4"};' in s
    # Immediate, TSP-delayed, and hot-reload compatibility starts only. No Stage 1/2 0.10s restart loop.
    assert s.count('[_medic, _main, 2] call ACME_fnc_doAnim;') == 3
    assert 'CBA_missionTime - _lastAssert >= 0.10' not in s
    assert 'Do not replay the requested state while it is entering' in s
    assert 'CBA_missionTime - _lastAssert >= 0.25' in s  # held stethoscope frame only

def test_tsp_sling_is_latched_and_never_reinvoked_during_same_handoff():
    s = txt('functions/fn_medicAnimationPrep.sqf')
    assert '[_medic, true] call tsp_fnc_animate_sling;' in s
    assert '_elapsed < 1.25' in s
    assert 'if (_elapsed < 0.34)' in s
    assert 'fail safe without replaying its sling gesture' in s

def test_medication_three_column_overlay_is_restored_and_direct_data_driven():
    r = txt('functions/fn_skListRefresh.sqf')
    assert '[84006,84303,"medication"]' in r
    assert 'ACME_SK_ColumnHeader' in r
    for cap in ['"Medication"', '"Contents"', '"Vials"']:
        assert cap in r
    assert 'ACME_SK_MedicationRows' in r
    assert '_specs pushBack [_label, _data, 0, _picture, _physicalClass]' in r
    assert '_countText' in r
    assert 'private _visible = true;' in r
    # The medication branch is explicitly sourced from the stored authoritative rows before the generic native-list else.
    med_branch = r[r.index('if (_kind == "medication") then {'):r.index('} else {', r.index('if (_kind == "medication") then {'))]
    assert 'ACME_SK_MedicationRows' in med_branch
    assert 'lbText' not in med_branch
    assert 'lbPicture' not in med_branch

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
