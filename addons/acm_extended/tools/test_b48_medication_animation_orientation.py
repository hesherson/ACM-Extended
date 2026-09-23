from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8-sig', errors='ignore')

def block(src, name):
    m = re.search(r'class\s+' + re.escape(name) + r'\b[^\{]*\{', src)
    assert m, name
    i = m.end(); depth = 1
    while i < len(src) and depth:
        if src[i] == '{': depth += 1
        elif src[i] == '}': depth -= 1
        i += 1
    return src[m.start():i]

def test_version_batch():
    assert_release_identity()
    p = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_real_acm_registry_not_fake_literal_key():
    p = txt('functions/fn_postInit.sqf')
    rows = txt('functions/fn_medicationSourceRows.sqf')
    restore = txt('functions/fn_restoreMedicationList.sqf')
    for s in (p, rows, restore):
        assert 'ACM_circulation_MedicationVialList' in s
    behavior = '\n'.join(line for line in (p + '\n' + rows + '\n' + restore).splitlines()
                         if not line.lstrip().startswith('//') and '/*' not in line and '*/' not in line)
    assert 'getVariable ["ACM_MEDICATION_VIALS"' not in behavior
    assert 'setVariable ["ACM_MEDICATION_VIALS"' not in behavior

def test_native_medication_list_is_the_only_renderer():
    r = txt('functions/fn_skListRefresh.sqf')
    s = txt('functions/fn_skMedicationSync.sqf')
    stock = txt('functions/fn_skMedicationStockRefresh.sqf')
    assert 'displayCtrl 84006' in s
    assert 'lbAdd _label' in s
    assert 'if (_label == "") then {_label = _med;};' in s
    assert 'lbSetPicture' in s and 'lbSetData' in s
    assert 'lbSetTextRight' in stock
    # B38/B46 custom medication child renderer is completely absent from the active row loop.
    assert 'forEach [[84130,84300,"size"],[84132,84301,"flush"],[84133,84302,"drawn"]]' in r
    assert '[84006,84303,"medication"]' not in r
    assert 'ACME_SK_ColumnHeader' not in r
    assert '_countText' not in r
    assert 'ctrlCreate ["ACME_SK_RowGroup", 84303' not in r
    assert '_nativeMedList ctrlShow true' in r

def test_medication_membership_is_inventory_backed_and_nonblank():
    from test_historical_medication_rows import test_rows_follow_selected_inventory_and_never_manufacture_stock, test_blank_label_and_unknown_open_vial_use_medication_key_fallback, test_open_partial_survives_consumed_physical_item_without_zero_volume_ghosts
    test_rows_follow_selected_inventory_and_never_manufacture_stock('_patient')
    test_blank_label_and_unknown_open_vial_use_medication_key_fallback()
    for amount,visible in [(0,False),(0.01,True),(2,True)]:
        test_open_partial_survives_consumed_physical_item_without_zero_volume_ghosts(amount,visible)

def test_prep_infusion_uses_same_medication_list():
    s = txt('functions/fn_infusionDrawStock.sqf')
    assert 'displayCtrl 84006' in s
    assert 'call ACME_fnc_skMedicationSync' in s
    assert '_list ctrlShow true' in s
    assert 'call ACME_fnc_skMedicationStockRefresh' in s

def test_native_selection_binds_exact_physical_vial():
    c = txt('config.cpp')
    inj = txt('functions/fn_skInject.sqf')
    sel = txt('functions/fn_skMedicationSelect.sqf')
    ses = txt('functions/fn_vialSession.sqf')
    assert 'class skMedicationSelect {};' in c
    assert 'class skMedicationStockRefresh {};' in c
    assert 'LBSelChanged' in inj and 'ACME_fnc_skMedicationSelect' in inj
    assert 'ACME_SK_MedicationRows' in sel and '_physicalClass' in sel
    assert 'ACME_SK_MedicationRows' in ses and '_physicalClass' in ses

def test_exact_chest_roll_provider_animation_is_forced():
    # Current empty-hand medic4 enters through the shared priority-one controller.
    # Do not restore the older rifle-state/priority-two reassertion loop.
    from test_historical_roll_cancellation import test_roll_enters_shared_empty_hand_medic4_with_current_timeline
    for stance in ('CROUCH','STAND','PRONE'):
        test_roll_enters_shared_empty_hand_medic4_with_current_timeline(stance)
    launch = block(txt('config.cpp'), 'ACME_ApplyChestSeal')
    for key in ['animationMedic = "";', 'animationMedicProne = "";', 'animationMedicSelf = "";', 'animationMedicSelfProne = "";']:
        assert key in launch

def test_requested_assessment_animations_and_durations_retained():
    c = txt('config.cpp')
    s = txt('functions/fn_treatmentPoseStart.sqf')
    response = block(c, 'CheckResponse')
    inspect = block(c, 'ACME_InspectChest')
    assert 'treatmentTime = 5;' in response
    assert "'response', 5" in response
    assert 'case "response": {"AinvPknlMstpSnonWrflDr_medic3_old"};' in s
    assert 'case "airway": {"AinvPknlMstpSnonWrflDr_medic4_old"};' in s
    assert 'treatmentTime = 6;' in inspect
    assert '[_medic, "inspect", 6, _patient]' in txt('functions/fn_inspectChestPoseStart.sqf')

def test_chest_view_follows_actual_patient_orientation():
    # Actual surface classifies physical roll endpoints. The later procedural
    # canvas is explicit-state, not continuously reclassified from moving geometry.
    from test_historical_chest_workspace import (
        test_actual_surface_reader_prefers_known_pose_then_geometry_then_cached_side,
        test_ineligible_patient_flip_remains_a_virtual_view_without_physical_control,
    )
    assert 'class chestSealActualSide {};' in txt('config.cpp')
    for name in ('chestSealRoll','chestSealPatientBegin','chestSealPatientEnd'):
        assert 'ACME_fnc_chestSealActualSide' in txt('functions/fn_'+name+'.sqf')
    front=[[0,0,0],[0,1,0],[0,0,0],[1,0,0]]
    back=[[0,0,0],[0,1,0],[1,0,0],[0,0,0]]
    for animation,points,cached,expected in (
        ('ACM_LyingState',back,'back','front'),
        ('ace_medical_engine_uncon_anim_1',front,'front','back'),
        ('unknown',front,'back','front'),('unknown',back,'front','back')):
        test_actual_surface_reader_prefers_known_pose_then_geometry_then_cached_side(animation,points,cached,expected)
    for side in ('front','back'):
        for dead in (False,True):
            test_ineligible_patient_flip_remains_a_virtual_view_without_physical_control(side,dead)

def test_tsp_sling_support_retained():
    # Keep the historical identity, but do not reinstate the retired optional sling call.
    req = txt('config.cpp').split('requiredAddons[] = {',1)[1].split('};',1)[0]
    assert 'tsp_animate' not in req.lower()
    from test_historical_weapon_preflight import test_one_engine_holster_request_is_retained_across_repeated_controllers, test_logical_clear_during_visible_holster_waits_without_reissuing
    for ace in (True,False):
        test_one_engine_holster_request_is_retained_across_repeated_controllers('rifle',0.70,ace)
    test_logical_clear_during_visible_holster_waits_without_reissuing(True)
