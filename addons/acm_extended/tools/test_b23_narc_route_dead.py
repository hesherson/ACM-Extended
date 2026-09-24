from historical_source import read_source
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return read_source(ROOT / rel, encoding='utf-8-sig')

class B23MedicationListContracts(unittest.TestCase):
    def test_live_selected_inventory_is_authoritative(self):
        get_list = read('overrides/fn_syringeGetMedicationList.sqf')
        update = read('overrides/fn_syringeUpdateMedicationList.sqf')
        tick = read('functions/fn_skUiTick.sqf')
        sync = read('functions/fn_skMedicationSync.sqf')
        source = read('functions/fn_medicationSourceRows.sqf')
        post = read('functions/fn_postInit.sqf')
        # B43 uses ACM's finalized vial registry as the class catalog but makes visible membership depend on
        # actual selected-holder counts through ACE's proven getCountOfItem path (via vialItemCount).
        self.assertIn('ACME_fnc_medicationSourceRows', get_list)
        self.assertIn('ACME_fnc_medicationSourceRows', sync)
        self.assertIn('ACM_circulation_MedicationVialList', source)
        self.assertIn('ACME_fnc_vialItemCount', source)
        self.assertIn('ace_common_fnc_getCountOfItem', read('functions/fn_vialItemCount.sqf'))
        self.assertIn('ACME_infusion_openVials', source)
        self.assertIn('ACME_medicationVialRegistryFull', source)
        self.assertNotIn('ace_common_fnc_uniqueItems', source)
        self.assertIn('ACME_fnc_skMedicationSync', tick)
        self.assertIn('ACME_fnc_skMedicationSync', update)
        self.assertIn('ACM_circulation_MedicationVialList', post)
        for text in (get_list, update, tick, sync):
            self.assertNotIn('forEach ACM_MEDICATION_VIALS', text)

    def test_normal_narc_box_rebuilds_empty_backing_list(self):
        # The current UI synchronizes native backing rows before binding the overlay by medication key.
        from test_historical_medication_rows import test_native_sync_rebuilds_empty_selector_once_and_preserves_each_medication, test_preview_builder_is_synced_before_visible_metadata_is_consumed
        test_native_sync_rebuilds_empty_selector_once_and_preserves_each_medication()
        test_preview_builder_is_synced_before_visible_metadata_is_consumed()

    def test_vertical_only_row_group(self):
        cfg = read('config.cpp')
        rows = read('functions/fn_skListRefresh.sqf')
        self.assertIn('class ACME_SK_RowGroup: RscControlsGroupNoHScrollbars', cfg)
        self.assertIn('ctrlCreate ["ACME_SK_RowGroup", _groupID]', rows)
        self.assertNotIn('ctrlCreate ["RscControlsGroup", _groupID]', rows)

    def test_selected_indent_base_does_not_creep(self):
        s = read('functions/fn_skListRefresh.sqf')
        self.assertIn('if !(_back getVariable ["ACME_SK_SelectedVisual", false]) then', s)

class B23VialHardStop(unittest.TestCase):
    def test_infusion_draw_max_is_limited_by_syringe_and_stock(self):
        # Stock refresh is no longer a competing plunger writer. The native mover owns the session ceiling;
        # final bag acceptance independently rechecks real stock and requires reconfirmation after a correction.
        native=(ROOT.parent/'circulation/functions/fnc_Syringe_Draw.sqf').read_text()
        self.assertIn('_effectiveMax = (_effectiveMax max 0) min _size;',native)
        self.assertIn('call ACME_fnc_vialSession',native)
        stock=read('functions/fn_infusionDrawStock.sqf')
        self.assertNotIn('ctrlSetPosition',stock)
        self.assertNotIn('SyringeDraw_DrawnAmount =',stock)
        from test_historical_medication_preparation import test_bag_injection_over_available_stock_or_explicit_quota_requires_reconfirmation
        for limit,stock,drawn in [(2,20,3),(10,2,3),(1,20,1.5)]:
            test_bag_injection_over_available_stock_or_explicit_quota_requires_reconfirmation(limit,stock,drawn)

    def test_live_ui_physically_clamps_plunger_to_stock(self):
        text=read('functions/fn_skUiTick.sqf')
        block=text.split('// The native ACM drag loop now consumes this hard limit',1)[1].split('// Inventory can change',1)[0]
        self.assertIn('_drawnNow > _hardMax',block)
        self.assertIn('[_hardMax, _d, false] call ACME_fnc_syringeDrawSetAmount',block)
        self.assertNotIn('setMousePosition',block)
        from test_historical_medication_preparation import test_syringe_amount_correction_keeps_hitbox_art_and_numeric_fill_together
        for size in [1,3,5,10]:
            test_syringe_amount_correction_keeps_hitbox_art_and_numeric_fill_together(size,0.25)

    def test_compound_path_keeps_stock_hard_stop(self):
        s = read('functions/fn_skCompoundBegin.sqf')
        self.assertIn('_newAvailable = (_unlockedForMed - _lockedSame) max 0', s); self.assertIn('ACME_fnc_vialSession', s)
        self.assertIn('private _maxFill', s)

class B23RouteSelector(unittest.TestCase):
    def test_split_buttons_exist(self):
        s = read('functions/fn_skInject.sqf')
        self.assertIn('ctrlSetText "IV / IO"', s)
        self.assertIn('ctrlSetText "IM"', s)
        self.assertIn('84151', s)
        self.assertIn('84154', s)

    def test_selected_route_has_green_backing(self):
        s = read('functions/fn_skBuildHotspots.sqf')
        self.assertIn('private _green = [0.20,0.65,0.20,0.92]', s)
        self.assertIn('private _gray = [0.20,0.20,0.20,0.72]', s)
        self.assertIn('_route == "vascular"', s)
        self.assertIn('_route == "im"', s)

    def test_both_halves_follow_body_view(self):
        s = read('functions/fn_skSetView.sqf')
        self.assertIn('[84151,84154,84155,84156]', s)

class B23DeadBagAccess(unittest.TestCase):
    def test_dead_target_can_open_transfusion_menu_if_access_exists(self):
        s = read('overrides/fn_canTreatCached.sqf')
        self.assertIn('_className == "OpenTransfusionMenu"', s)
        self.assertIn('ACM_circulation_fnc_hasIV', s)
        self.assertIn('ACM_circulation_fnc_hasIO', s)

    def test_hang_bag_does_not_drop_only_because_patient_is_dead(self):
        start = read('functions/fn_hangBagStart.sqf')
        tick = read('functions/fn_hangBagTick.sqf')
        self.assertNotIn('isNull _patient || {!alive _patient}', start)
        self.assertNotIn('isNull _patient || {!alive _patient}', tick)
        self.assertIn('if (isNull _patient)', tick)

if __name__ == '__main__':
    unittest.main()
