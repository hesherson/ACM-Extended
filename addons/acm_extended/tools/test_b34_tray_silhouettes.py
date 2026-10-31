"""Tray coverage/lifecycle and input-isolation contracts; no Arma renderer available."""
from pathlib import Path
import re
import unittest

from source_scan import lex

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / 'functions' / ('fn_' + name + '.sqf')).read_text()


class TraySilhouetteContracts(unittest.TestCase):
    def test_renderer_reuses_art_without_controls_input_or_patient_writes(self):
        text = source('traySlotState')
        commands = {token.value for token in lex(text) if token.kind != 'string'}
        for forbidden in ('ctrlCreate', 'ctrlDelete', 'ctrlEnable', 'ctrlSetText',
                          'ctrlSetPosition', 'ctrlAddEventHandler', 'remoteExec',
                          'CBA_fnc_addPerFrameHandler', 'allControls'):
            self.assertNotIn(forbidden, commands)
        self.assertIn('_icon ctrlSetTextColor', text)
        self.assertIn('[0, 0, 0, 1]', text)
        self.assertEqual(re.findall(r'(\w+) setVariable', text), ['_icon'])
        self.assertIn('if (isNull _icon) exitWith', text)

    def test_consumed_last_item_keeps_shadow_until_restocked(self):
        text = source('traySlotState')
        # The only retained state is a control-local prior pickup, gated by no stock:
        # a fresh empty slot is dim, a depleted picked slot stays black, and a
        # returned/restocked item clears the marker without patient persistence.
        self.assertRegex(text, r'_removed \|\| \{_stock <= 0 && \{_icon getVariable \["ACME_TrayTaken", false\]\}\}')
        self.assertIn('_icon setVariable ["ACME_TrayTaken", _vacant]', text)
        self.assertIn('_icon ctrlShow _visible', text)

    def test_iv_covers_every_gauge_pad_band_and_optional_line(self):
        text = source('ivMinigameRefreshBandSlot')
        for idc in ('86531', '86536', '86541', '86545', '86549', '86557', '86553'):
            self.assertIn(idc, text)
        for idc in ('86532', '86537', '86543', '86547', '86551', '86559', '86555'):
            self.assertNotRegex(text, rf'displayCtrl {idc}\) ctrlEnable')
        self.assertIn('_bandOn || {_held == "band"}', text)
        self.assertIn('!(uiNamespace getVariable ["ACME_IV_EJMode", false])', text)
        from test_b241_current_ui_expectations import current_finish_tray_contract
        # The old line silhouette stays hidden. B233+ uses the separate physical
        # finishing tray, including tubing, rather than a retired option toggle.
        current_finish_tray_contract(text, source('ivFinishTray'))
        for function in ('ivMinigameGrabPad', 'ivMinigameGrabBand', 'ivMinigameGrabNeedle',
                         'ivMinigameSyncBand', 'ivMinigameStickSuccess'):
            self.assertIn('ACME_fnc_ivMinigameRefreshBandSlot', source(function), function)
        self.assertEqual(source('ivMinigameGrabLine').strip(), '["line"] call ACME_fnc_ivFinishGrab;')
        finish = source('ivFinishGrab')
        self.assertIn('[] call ACME_fnc_ivMinigameRefreshBandSlot;', finish)
        self.assertIn('ACME_IV_FinishGrabPress', finish)
        self.assertIn('ACME_IV_FinishBusy', finish)

    def test_chest_seal_and_spear_refresh_use_separate_slot_logos(self):
        for function, idc in (('chestSealRefreshSlot', 86422), ('chestSealRefreshSpearSlot', 86432)):
            text = source(function)
            self.assertIn(f'displayCtrl {idc}', text)
            self.assertIn('[_logo, _held, _n] call ACME_fnc_traySlotState', text)
            self.assertNotIn('_logo ctrlShow false', text)
        for function in ('chestSealToggleHeld', 'chestSealToggleSpear', 'chestSealAck', 'chestSealInit'):
            self.assertIn('ACME_fnc_chestSealRefresh', source(function), function)

    def test_laryngoscopy_tracks_pinned_and_patient_placed_items(self):
        text = source('laryngoRefreshSlots')
        for state in ('ACME_laryngo_bladeLocked', 'ACME_laryngo_tubeIn', 'ACME_laryngo_tubeDepth',
                      'ACME_ETT_Inserted', 'ACME_ETT_Secured', 'ACME_laryngo_syringeUsed',
                      'ACME_laryngo_collarUsed', 'ACME_suction_standalone'):
            self.assertIn(state, text)
        suction = source('suctionSelectDevice')
        for state in ('ACME_laryngo_sucPinned', 'ACME_laryngo_held', 'ACME_suction_standalone'):
            self.assertIn(state, suction)
        self.assertIn('call ACME_fnc_traySlotState', suction)
        self.assertIn('call ACME_fnc_laryngoRefreshSlots', source('laryngoTubeEject'))
        init = source('laryngoInit')
        # Hydration occurs after the first refresh. The final reconciliation must
        # follow all resume state so reopening cannot briefly restock a used tool.
        self.assertGreater(init.rindex('call ACME_fnc_laryngoRefreshSlots'),
                           init.index('uiNamespace setVariable ["ACME_laryngo_held", _sHeld]'))

    def test_existing_thoracostomy_shadow_survives_hover_and_inventory_refresh(self):
        from test_historical_procedure_trays import test_inventory_refresh_preserves_held_identity_and_black_shadow, test_hover_preserves_only_the_actual_held_tools_shadow
        # Rendering moved to the shared refresh helper; the selected physical tool remains the authority.
        self.assertIn('call ACME_fnc_thoraUpdateTrayIcons',source('thoraSelectTool'))
        self.assertIn('call ACME_fnc_thoraUpdateTrayIcons',source('thoraTick'))
        for held in ('tube','seal'):
            test_inventory_refresh_preserves_held_identity_and_black_shadow(held)
            for hover in ('tube','seal'):
                for enter in (True,False):
                    test_hover_preserves_only_the_actual_held_tools_shadow(held,hover,enter)


if __name__ == '__main__':
    unittest.main()
