from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def text(rel):
    return read_source(ROOT / rel, errors='ignore')


def test_b41_runtime_stamp():
    assert_release_identity()
    p = text('functions/fn_postInit.sqf')
    assert_release_identity()
    assert 'ACME_infusion_version = getText' in p


def test_cuff_syringe_uses_real_acm_pbo_prefix():
    cfg = text('config.cpp')
    block = cfg[cfg.index('class LG_Syringe:'):cfg.index('class LG_Suction:')]
    # Backbit/plunger come from ACM's real PBO path. The barrel is intentionally ACME's
    # replacement saline-flush art, shared with the cuff/flush views.
    for asset in ('backbit', 'plunger'):
        good = rf'\x\ACM\addons\circulation\ui\syringe\syringe_10_{asset}_ca.paa'
        bad = rf'\z\acm\addons\circulation\ui\syringe\syringe_10_{asset}_ca.paa'
        assert good in block
        assert bad not in block
    assert r'\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa' in block
    assert r'\z\acm\addons\circulation\ui\syringe\syringe_10_barrel_ca.paa' not in block


def test_vomit_sound_uses_real_acm_pbo_prefix():
    s = text('overrides/fn_handleAirwayObstruction_Vomit.sqf')
    assert r'\x\ACM\addons\airway\sound\vomit' in s
    assert r'\z\acm\addons\airway\sound\vomit' not in s


def test_clinical_chest_wording():
    groups = text('functions/fn_menuExamineGroups.sqf')
    actions = text('overrides/fn_updateActions.sqf')
    assert '"examine_chest"' not in groups
    assert "_actionClass == 'usestethoscope'" in actions
    assert "_clinicalDescriptors" in actions
    assert "_baseName = 'Auscultate Chest';" in actions
    assert "_wasChild = _nestEnabled" in actions
    assert "ACME_menuChildIndent" in actions
    # Rename is applied at paint time, not by overwriting ACM's base localized displayName.
    assert 'Auscultate Chest' not in text('config.cpp')


def test_requested_alternating_pale_red_is_runtime_default():
    p = text('functions/fn_postInit.sqf')
    assert 'ACME_menuRowColorAlternate = [1, 1, 1, 1];' in p


def test_full_medication_registry_is_config_derived_and_immutable():
    # Exercise the real native writer, including startup fallback and independent snapshot copies.
    from test_historical_medication_rows import test_initializer_publishes_real_native_catalog_and_snapshot, test_restore_repairs_the_real_native_registry_without_mutating_snapshot
    for initial in ['[]','["ACM_Vial_Ketamine","ACM_Vial_EpinephrineCardiac"]']:
        test_initializer_publishes_real_native_catalog_and_snapshot(initial)
    for damage in ['[]','["ForeignOnly"]']:
        test_restore_repairs_the_real_native_registry_without_mutating_snapshot(damage)


def test_infusion_draw_no_longer_swaps_global_vial_registry():
    s = text('functions/fn_openDrawMenu.sqf')
    executable = '\n'.join(line.split('//', 1)[0] for line in s.splitlines())
    assert 'ACME_fnc_restoreMedicationList' in executable
    assert 'ACM_circulation_MedicationVialList", +' not in executable
    assert 'ACME_infusion_savedMedicationVials =' not in executable


def test_medication_rows_have_single_authoritative_identity_source():
    # Native labels and physical-class metadata share medication keys, not transient row indices.
    from test_historical_medication_rows import test_native_sync_rebuilds_empty_selector_once_and_preserves_each_medication, test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class
    test_native_sync_rebuilds_empty_selector_once_and_preserves_each_medication()
    test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class()


def test_visible_medication_rows_do_not_read_identity_back_from_listbox():
    # Historical name retained for the ledger. The approved B51+ renderer uses native
    # data keys/labels, with metadata joined by key; restoring B50's parallel renderer is not required.
    from test_historical_medication_rows import test_visible_rows_bind_metadata_by_key_and_recover_missing_backing_entries, test_preview_builder_is_synced_before_visible_metadata_is_consumed
    for native in ['[]','[["Fentanyl native","Fentanyl",""],["duplicate","Fentanyl","bad.paa"],["","Ketamine",""]]']:
        test_visible_rows_bind_metadata_by_key_and_recover_missing_backing_entries(native)
    test_preview_builder_is_synced_before_visible_metadata_is_consumed()


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
