from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def text(rel):
    return read_source(ROOT / rel, errors="ignore")


def test_b42_runtime_stamp():
    assert_release_identity()
    p = text('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()


def test_medication_membership_uses_selected_holder_and_native_item_count_contract():
    s = text('functions/fn_medicationSourceRows.sqf')
    assert 'ACM_circulation_MedicationVialList' in s
    assert 'ACME_fnc_vialItemCount' in s
    assert 'private _items = items _holder;' not in s
    assert 'ACME_infusion_openVials' in s


def test_medication_rows_are_independent_records_and_stock_uses_same_physical_class():
    from test_historical_medication_rows import test_ampule_and_foreign_keys_keep_their_full_identity_across_refreshes, test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class
    test_ampule_and_foreign_keys_keep_their_full_identity_across_refreshes()
    test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class()


def test_vial_parser_keeps_full_suffix():
    s = text('functions/fn_vialMedication.sqf')
    assert '["_vial_", "_ampule_"]' in s
    assert '_class select [_at + count _needle]' in s
    assert 'splitString "_"' not in s
    assert 'ACM_Ampule_Dimercaprol' in text('functions/fn_vialClass.sqf')


def test_auscultate_chest_keeps_group_child_indent():
    s = text('overrides/fn_updateActions.sqf')
    assert "_actionClass == 'usestethoscope'" in s
    assert "_baseName = 'Auscultate Chest';" in s
    assert "_paintName = if (_wasChild) then" in s
    assert "missionNamespace getVariable ['ACME_menuChildIndent', '        ']" in s
    assert '"examine_chest"' not in text('functions/fn_menuExamineGroups.sqf')


def test_direct_pressure_activity_log_exact_limb_wording():
    limb = text('functions/fn_directPressureLimb.sqf')
    assert '"%1 started Direct pressure on %2"' in limb
    assert '[_bodyPart, "abbr"] call ACME_fnc_bodyPartName' in limb
    body = text('functions/fn_bodyPartName.sqf')
    for short in ('LUE', 'RUE', 'LLE', 'RLE'):
        assert f'"{short}"' in body


def test_direct_pressure_torso_self_and_stop_use_same_log_grammar():
    assert '"%1 started Direct pressure on %2"' in text('functions/fn_directPressureTorso.sqf')
    assert '"%1 started Direct pressure on own %2"' in text('functions/fn_directPressureSelf.sqf')
    assert '"%1 stopped Direct pressure on %2"' in text('functions/fn_directPressureStop.sqf')


def test_audit_removed_stale_lidocaine_latch_read_and_preserved_live_effect_lookup():
    s = text('functions/fn_rhythmThresholdTick.sqf')
    assert 'getVariable ["ACME_rhythm_lidoLastTherapeutic"' not in s
    assert 'ace_medical_medications' in s
    assert 'ACME_fnc_lidoEffectiveness' in s



def test_generated_nv_texture_map_is_purged():
    assert not (ROOT / 'functions/fn_minigameVisionTextures.sqf').exists()
    assert not (ROOT / 'tools/nv_texture_manifest.json').exists()
    assert not (ROOT / 'ui/nv_close').exists()


def test_extended_fentanyl_source_capacity_matches_500mcg_10ml_inventory_item():
    s = text('config.cpp')
    assert 'displayName = "Fentanyl (500mcg/10ml)";' in s
    concentration = s[s.index('class Concentration {', s.index('class ACM_Medication')):]
    assert 'class Fentanyl {' in concentration
    block = concentration[concentration.index('class Fentanyl {'):concentration.index('};', concentration.index('class Fentanyl {')) + 2]
    assert 'concentration = 0.05;' in block
    assert 'dose = "500mcg/10ml";' in block
    assert 'volume = 10;' in block
