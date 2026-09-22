from historical_source import read_source
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
    assert 'version = "1.0.100-r12";' in txt('config.cpp')
    p = txt('functions/fn_postInit.sqf')
    assert 'ACME_buildBatch = "B48";' in p
    assert 'ACME_infusion_version = "1.0.100-r12"' in p

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
    s = txt('functions/fn_medicationSourceRows.sqf')
    assert 'ace_common_fnc_uniqueItems' in s
    assert "ACM_circulation_MedicationVialList" in s
    assert "getNumber (_cfg >> 'ACM_isVial')" in s
    assert 'if (_sealed <= 0 && {_openMl <= 0.000001}) then {continue};' in s
    assert "if (_label == '') then {_label = _med;};" in s
    assert '_rows pushBack [_label, _med, _picture, _displayClass];' in s

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
    s = txt('functions/fn_treatmentPoseStart.sqf')
    r = txt('functions/fn_rollProviderStart.sqf')
    f = txt('functions/fn_chestSealFlip.sqf')
    assert 'case "roll": {"AinvPknlMstpSnonWrflDnon_medic4"};' in s
    assert '[_medic, _main, 2] call ACME_fnc_doAnim;' in s
    assert '[_medic, "roll", _duration] call ACME_fnc_treatmentPoseStart' in r
    assert 'ACME_fnc_rollProviderStart' in f
    # Reassertion prevents a framework generic medic animation from owning the roll episode.
    assert s.count('[_medic, _main, 2] call ACME_fnc_doAnim;') >= 4
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
    c = txt('config.cpp')
    a = txt('functions/fn_chestSealActualSide.sqf')
    i = txt('functions/fn_chestSealInit.sqf')
    t = txt('functions/fn_chestSealTick.sqf')
    f = txt('functions/fn_chestSealFlip.sqf')
    r = txt('functions/fn_chestSealRoll.sqf')
    assert 'class chestSealActualSide {};' in c
    for token in ['animationState _patient', 'ace_medical_engine_animations', 'modelToWorldVisual', 'vectorCrossProduct']:
        assert token in a
    assert 'ACME_CS_facing as the primary signal' in a
    assert 'ACME_fnc_chestSealActualSide' in i
    assert 'ACME_fnc_chestSealActualSide' in t
    assert 'ACME_fnc_chestSealActualSide' in f
    assert 'ACME_fnc_chestSealActualSide' in r
    assert 'if (_actualSide != _uiSide)' in t
    # Flip cannot fabricate the opposite diagram when the body cannot be rolled; during a real roll B57 locks
    # the diagram to the requested endpoint so intermediate animation geometry cannot make it double-flip.
    assert 'if (!_willAnimate) exitWith' in f
    guard=f.index('if (!_willAnimate) exitWith')
    target=f.index('uiNamespace setVariable ["ACME_CS_Side", _newSide]')
    assert guard < target
    assert 'ACME_CS_FlipTarget' in f
    assert 'if (_flipLocked) then {' in t

def test_tsp_sling_support_retained():
    p = txt('functions/fn_medicAnimationPrep.sqf')
    req = txt('config.cpp').split('requiredAddons[] = {',1)[1].split('};',1)[0]
    for token in ['tsp_fnc_animate_sling', 'tsp_fnc_animate_sling_get', 'tsp_cba_animate_sling', 'tsp_slings']:
        assert token in p
    assert '[_medic, true] call tsp_fnc_animate_sling' in p
    assert 'tsp_animate' not in req.lower()
