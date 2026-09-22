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
        rows = read('functions/fn_skListRefresh.sqf')
        sync = read('functions/fn_skMedicationSync.sqf')
        # B41 repairs an empty OR stale native list by comparing the complete identity tuple, then
        # rebuilding it from immutable records. The overlay consumes the exact same records.
        self.assertIn('private _medRows = [_d] call ACME_fnc_skMedicationSync', rows)
        self.assertIn('if !(_present isEqualTo _expected) then', sync)
        self.assertIn('lbClear _list', sync)
        self.assertIn('_display setVariable ["ACME_SK_MedicationRows", +_rows]', sync)

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
        s = read('functions/fn_infusionDrawStock.sqf')
        self.assertIn('ACM_circulation_SyringeDraw_Size min', s)
        self.assertIn('ACME_fnc_infusionVialVolume', s)

    def test_live_ui_physically_clamps_plunger_to_stock(self):
        s = read('functions/fn_skUiTick.sqf')
        for token in ['_hardMax', 'ACM_circulation_SyringeDraw_DrawnAmount = _hardMax', '_maxMouse', 'setMousePosition']:
            self.assertIn(token, s)

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
        self.assertIn('private _green = [0.12,0.62,0.24,0.92]', s)
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
