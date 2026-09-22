from historical_source import read_source
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def text(rel):
    return read_source(ROOT / rel, errors='ignore')


def test_b41_runtime_stamp():
    assert 'version = "1.0.100-r7";' in text('config.cpp')
    p = text('functions/fn_postInit.sqf')
    assert 'ACME_buildBatch = "B43";' in p
    assert 'ACME_infusion_version = getText' in p


def test_cuff_syringe_uses_real_acm_pbo_prefix():
    cfg = text('config.cpp')
    for asset in ('backbit', 'plunger', 'barrel'):
        good = rf'\x\ACM\addons\circulation\ui\syringe\syringe_10_{asset}_ca.paa'
        bad = rf'\z\acm\addons\circulation\ui\syringe\syringe_10_{asset}_ca.paa'
        assert good in cfg
        assert bad not in cfg


def test_vomit_sound_uses_real_acm_pbo_prefix():
    s = text('overrides/fn_handleAirwayObstruction_Vomit.sqf')
    assert r'\x\ACM\addons\airway\sound\vomit' in s
    assert r'\z\acm\addons\airway\sound\vomit' not in s


def test_clinical_chest_wording():
    groups = text('functions/fn_menuExamineGroups.sqf')
    actions = text('overrides/fn_updateActions.sqf')
    assert '["examine_chest", "Chest Inspection"' in groups
    assert "_actionClass == 'usestethoscope'" in actions
    assert "_clinicalDescriptors" in actions
    assert "format ['%1Auscultate Chest'" in actions
    assert "ACME_menuChildIndent" in actions
    # Rename is applied at paint time, not by overwriting ACM's base localized displayName.
    assert 'Auscultate Chest' not in text('config.cpp')


def test_requested_alternating_pale_red_is_runtime_default():
    p = text('functions/fn_postInit.sqf')
    assert 'ACME_menuRowColorAlternate = [1, 0.84, 0.84, 1];' in p


def test_full_medication_registry_is_config_derived_and_immutable():
    p = text('functions/fn_postInit.sqf')
    assert 'configClasses (configFile >> "CfgWeapons")' in p
    assert 'ACM_isVial' in p
    assert 'ACME_medicationVialRegistryFull' in p
    assert 'missionNamespace setVariable ["ACM_circulation_MedicationVialList", +_acmVials]' in p
    restore = text('functions/fn_restoreMedicationList.sqf')
    assert 'ACME_medicationVialRegistryFull' in restore
    assert 'missionNamespace setVariable ["ACM_circulation_MedicationVialList", +_full]' in restore


def test_infusion_draw_no_longer_swaps_global_vial_registry():
    s = text('functions/fn_openDrawMenu.sqf')
    executable = '\n'.join(line.split('//', 1)[0] for line in s.splitlines())
    assert 'ACME_fnc_restoreMedicationList' in executable
    assert 'ACM_circulation_MedicationVialList", +' not in executable
    assert 'ACME_infusion_savedMedicationVials =' not in executable


def test_medication_rows_have_single_authoritative_identity_source():
    sync = text('functions/fn_skMedicationSync.sqf')
    source = text('functions/fn_medicationSourceRows.sqf')
    count = text('functions/fn_vialItemCount.sqf')
    assert 'ACME_fnc_medicationSourceRows' in sync
    assert '_display setVariable ["ACME_SK_MedicationRows", +_rows];' in sync
    # B43 uses ACM's finalized vial registry only as the class catalog, then tests actual holder stock
    # through the same ACE item-count primitive used by native ACM. It must not maintain a second
    # items/uniform/vest/backpack enumeration path.
    assert 'ACM_circulation_MedicationVialList' in source
    assert 'ACME_medicationVialRegistryFull' in source
    assert 'ACME_fnc_vialItemCount' in source
    assert 'ace_common_fnc_getCountOfItem' in count
    assert 'items _holder' not in source
    assert 'uniformContainer _holder' not in source
    assert 'vestContainer _holder' not in source
    assert 'backpackContainer _holder' not in source
    assert "getText (_displayCfg >> 'displayName')" in source
    assert "getText (_displayCfg >> 'picture')" in source
    assert '_rows pushBack [_label, _med, _picture, _displayClass];' in source


def test_visible_medication_rows_do_not_read_identity_back_from_listbox():
    s = text('functions/fn_skListRefresh.sqf')
    start = s.index('if (_kind == "medication") then {')
    block = s[start:s.index('    } else {', start)]
    code = '\n'.join(line.split('//', 1)[0] for line in block.splitlines())
    assert 'forEach _medRows' in code
    assert 'lbText' not in code
    assert 'lbPicture' not in code
    assert 'lbData' not in code
    assert 'ACME_fnc_vialClass' not in code


def test_native_medication_bridge_delegates_to_same_builder():
    s = text('overrides/fn_syringeUpdateMedicationList.sqf')
    assert '[_display] call ACME_fnc_skMedicationSync;' in s
    assert 'lbClear' not in s
    assert 'forEach' not in s


def test_get_medication_list_uses_selected_inventory_rows():
    s = text('overrides/fn_syringeGetMedicationList.sqf')
    assert 'ACME_fnc_medicationSourceRows' in s
    assert 'ACME_medicationVialRegistryFull' not in s
    assert 'ACME_fnc_infusionVialVolume' not in s


def test_no_live_z_acm_resource_reference_outside_compat_texture_map():
    offenders = []
    for base in ('config.cpp', 'functions', 'overrides'):
        p = ROOT / base
        files = [p] if p.is_file() else list(p.glob('*.sqf'))
        for f in files:
            if f.name == 'fn_minigameVisionTextures.sqf':
                continue
            data = read_source(f, errors='ignore')
            # Ignore comments; quoted live paths are what caused the popup.
            code = '\n'.join(line.split('//', 1)[0] for line in data.splitlines())
            if '\\z\\acm\\' in code:
                offenders.append(str(f.relative_to(ROOT)))
    assert not offenders, offenders


def test_b41_stock_refresh_does_not_compare_unsorted_registry_to_sorted_ui():
    s = text('functions/fn_skUiTick.sqf')
    assert '[_d] call ACME_fnc_skMedicationSync' in s
    assert 'private _wantedStock = []' not in s
    assert '_presentStock isEqualTo _wantedStock' not in s
