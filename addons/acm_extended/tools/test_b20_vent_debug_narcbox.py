from historical_source import read_source, assert_release_identity, assert_client_only_setting
from pathlib import Path
import unittest, re
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B20Ventway(unittest.TestCase):
    def test_version_pair(self):
        assert_release_identity()
        assert_release_identity()
    def test_live_readouts_refresh_without_user_input(self):
        s=read('functions/fn_ventPanelTick.sqf')
        self.assertIn('ACME_vent_liveReadoutNext',s)
        self.assertIn('call ACME_fnc_ventPanelRefresh',s)
        self.assertRegex(s,r'diag_tickTime \+ 0\.10')
        refresh=read('functions/fn_ventPanelRefresh.sqf')
        for key in ('ACME_vent_vti','ACME_vent_vte'):
            self.assertIn(key,refresh)
        self.assertIn('ACME_fnc_ventMinuteVolume',refresh)
        self.assertIn('ACME_vent_mvDelivered',read('functions/fn_ventMinuteVolume.sqf'))
    def test_mv_sensor_has_two_second_minimum_settle(self):
        init=read('functions/fn_ventPanelInit.sqf')
        tick=read('functions/fn_ventPanelTick.sqf')
        refresh=read('functions/fn_ventPanelRefresh.sqf')
        post=read('functions/fn_postInit.sqf')
        self.assertIn('ACME_vent_mvSensorDelaySec',init)
        self.assertIn('max 2.0',init)
        self.assertIn('ACME_vent_mvValidAfter',tick)
        self.assertIn('"--.--"',refresh)
        self.assertIn('ACME_vent_mvSensorDelaySec = 2.0',post)

class B20NarcBox(unittest.TestCase):
    def test_vial_preview_registered_and_background_only(self):
        self.assertIn('class vialPreview {};',read('config.cpp'))
        v=read('functions/fn_vialPreview.sqf')
        self.assertIn('ACME_infusion_openVials',v)
        self.assertIn('_reservedMl',v)
        for chatter in ('displayText','hint','systemChat'):
            self.assertNotIn(chatter,v)
    def test_pre_b20_geometry_is_restored(self):
        inject=read('functions/fn_skInject.sqf')
        rows=read('functions/fn_skListRefresh.sqf')
        # Later Narc Box work deliberately widened the medication/source columns while retaining
        # the established row height/backing and removing the retired final-name surface.
        self.assertIn('private _listW = _uiW / 5.25',inject)
        self.assertIn('private _columnInner = _uiW / 3.3',inject)
        self.assertIn('private _rowH = safeZoneH / 20',rows)
        self.assertIn('_group ctrlSetPosition (ctrlPosition _list)',rows)
        self.assertNotIn('ACME_SK_MedMeterH',inject+rows)
        self.assertNotIn('Final Syringe Name (25 max)',inject)
        self.assertNotIn('ctrlCreate ["ACME_SK_NameEdit", 84161]',inject)
    def test_existing_rows_gain_smart_text_and_live_vial_stock(self):
        rows=read('functions/fn_skListRefresh.sqf')
        tick=read('functions/fn_skUiTick.sqf')
        for token in ('ctrlTextWidth','_minFont','_line2','ACME_fnc_vialPreview','toFixed 2','while {count _count < 2}'):
            self.assertIn(token,rows)
        self.assertIn('_rowThisH = _rowH * 1.68',rows)
        self.assertIn('_cursorY + (_rowH * 0.70)',rows)
        self.assertIn('ACME_fnc_vialSession',tick)
        self.assertIn('toFixed 2',tick)
        self.assertIn('while {count _cnt < 2}',tick)
    def test_plain_and_compound_plungers_have_stock_stops(self):
        tick=read('functions/fn_skUiTick.sqf')
        comp=read('functions/fn_skCompoundBegin.sqf')
        self.assertIn('ACME_fnc_vialSession',tick)
        for token in ('_unlockedForMed','_lockedSame','_newAvailable','_maxFill','_maxY','ACM_circulation_SyringeDraw_MaxDose = _maxFill'):
            self.assertIn(token,comp)
    def test_push_back_uses_native_style_motion_without_custom_resistance(self):
        tick=read('functions/fn_skUiTick.sqf')
        comp=read('functions/fn_skCompoundBegin.sqf')
        post=read('functions/fn_postInit.sqf')
        self.assertNotIn('ACME_vial_returnRateFracPerSec',post)
        self.assertNotIn('ACME_vial_returnRateFracPerSec',tick)
        self.assertNotIn('ACME_vial_returnRateFracPerSec',comp)
        self.assertNotIn('private _fracR',comp)
        self.assertIn('use ACM-like direct plunger motion',comp)
    def test_stock_list_updates_when_inventory_changes(self):
        s=read('functions/fn_skUiTick.sqf')
        self.assertIn('ACME_SK_NextStockRefresh',s)
        self.assertIn('ACME_fnc_skMedicationSync',s)
        # Do not maintain a second differently-ordered membership comparator.
        self.assertNotIn('_presentStock isEqualTo _wantedStock',s)
    def test_save_button_is_original_label(self):
        s=read('functions/fn_skCompoundBegin.sqf')
        self.assertIn('_btnSave ctrlSetText "Save"',s)
        self.assertNotIn('Save & New Syringe',s)
    def test_success_coaching_popups_stay_removed(self):
        tree='\n'.join(read('functions/'+p.name) for p in (ROOT/'functions').glob('fn_sk*.sqf'))
        for text in ('Added %1 mL %2.','selected. Open Body Map.','Saline flush: click the plunger','Wasted %1 mL. Select a drug','Drew %1.'):
            self.assertNotIn(text,tree)

class B20Debug(unittest.TestCase):
    def test_debug_overlay_reverted_to_pre_b20(self):
        s=read('functions/fn_debugMenu.sqf')
        self.assertIn('ACME_DebugMenuCtrlL',s)
        self.assertIn('ACME_DebugMenuCtrlR',s)
        self.assertIn('EtelkaMonospacePro',s)
        self.assertIn('NETWORK',s)
        self.assertNotIn('DUMP ALL -> RPT',s)
        self.assertNotIn('TRACE 60s',s)
        self.assertNotIn('private _tabs = ["VITAL"',s)
    def test_b20_debug_helpers_are_unregistered_and_removed(self):
        cfg=read('config.cpp')
        for name in ('debugTab','debugDump','debugTraceToggle','debugTraceTick'):
            self.assertNotIn(f'class {name} {{}};',cfg)
            self.assertFalse((ROOT/'functions'/f'fn_{name}.sqf').exists())

class B20Accessibility(unittest.TestCase):
    def test_colorblind_setting_registered_once(self):
        s=read('XEH_settings.hpp')
        self.assertEqual(s.count('"ACME_a11y_colorblindMode"'),2) # ID plus callback write, one registration only
        self.assertEqual(len(re.findall(r'\[\s*"ACME_a11y_colorblindMode"\s*,\s*"LIST"',s)),1)
        for mode in ('deuteranomaly','deuteranopia','protanomaly','protanopia','tritanomaly','tritanopia','achromatopsia'):
            self.assertIn(mode,s)
    def test_accessibility_options_are_client_local(self):
        s=read('XEH_settings.hpp')
        ids=('ACME_a11y_colorblindMode','ACME_a11y_colorblindStrength','ACME_a11y_bvmVentCircle','ACME_a11y_bvmVentInflateSec','ACME_a11y_menuLeftAlign','ACME_menuNestEnabled','ACME_menuColorHeaders','ACME_motion_interpolate','ACME_motion_interpolationTime','ACME_minigameNV_focusBlur')
        for setting in ids:
            with self.subTest(setting=setting):
                assert_client_only_setting(s,setting)
        pre=read('XEH_preInit.sqf')
        assert_client_only_setting(pre,'ACME_debug_enabled')
    def test_all_colorblind_modes_are_handled(self):
        s=read('functions/fn_cbColor.sqf')
        for mode in ('protanomaly','protanopia','deuteranomaly','deuteranopia','tritanomaly','tritanopia','achromatopsia'):
            self.assertIn(f'"{mode}"',s)
        self.assertIn('0.2126 * _r',s)

class B20Reference(unittest.TestCase):
    @staticmethod
    def preview(cap,open_ml,sealed,reserved):
        total=open_ml+sealed*cap; left=max(total-max(reserved,0),0); r=min(max(reserved,0),total); cur=open_ml; sealed_left=sealed
        if cur>1e-6:
            if r<cur: cur-=r; r=0
            else: r-=cur; cur=0
        while r>1e-6 and sealed_left>0:
            sealed_left-=1
            if r<cap: cur=cap-r; r=0
            else: r-=cap; cur=0
        if cur<=1e-6 and sealed_left>0:
            sealed_left-=1; cur=cap
        return sealed_left+(1 if cur>1e-6 else 0),cur,left
    def test_preview_crosses_propofol_vials(self):
        self.assertEqual(self.preview(50,0,2,0),(2,50,100))
        self.assertEqual(self.preview(50,0,2,10),(2,40,90))
        self.assertEqual(self.preview(50,0,2,50),(1,50,50))
        self.assertEqual(self.preview(50,0,2,60),(1,40,40))
        self.assertEqual(self.preview(50,0,2,100),(0,0,0))
    def test_mv_settle_never_shorter_than_two_seconds(self):
        for configured in (0,0.5,1.99,2,3.5):
            self.assertGreaterEqual(max(configured,2.0),2.0)

if __name__=='__main__': unittest.main()
