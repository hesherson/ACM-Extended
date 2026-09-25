#!/usr/bin/env python3
"""Batch 2 source contracts and small reference models. Does not execute Arma/SQF."""
from pathlib import Path
import itertools
import re
import unittest
from source_scan import lex
R = Path(__file__).resolve().parents[1]

def read(name):
    return (R/name).read_text(encoding='utf-8-sig')

def sqf(name):
    return read('functions/fn_'+name+'.sqf')

def tokens(name):
    return [t.value for t in lex(sqf(name))]

def device(accuvac, bags, opened=False, valid=True):
    return -1 if not valid else 1 if accuvac > 0 else 0 if bags > 0 or opened else -1

def squeeze(accuvac, bags, opened=False, removed=True):
    if device(accuvac,bags,opened) != 0:
        return bags, opened, False
    if not opened:
        if not removed: return bags, False, False
        bags -= 1
        opened = True
    return bags, opened, True

def airway(ett, oral):
    return 'ett' if ett else 'igel' if oral == 'SGA' else ''

def emma(ett=False, oral='', required='', attached=False, distance=0, same_vehicle=False,
         carried=True, bvm=False, system=True, valid=True):
    kind=airway(ett,oral)
    return valid and system and bool(kind) and (not required or kind == required) and not attached \
        and (same_vehicle or distance <= 5) and (carried or bvm)

def tally_rectangles(x,y,w,h):
    # Same ratios as skInject and patchDrawDialog; this tests arithmetic, not engine rendering.
    list_w=w/6.5
    left=(x+w/2-w/3.3)-list_w
    top=y+h/2-h/5.3
    list_h=h/5
    button_y=y+h/1.19
    gap=h/40
    header_y=top+list_h+gap
    header_h=h/28
    body_y=header_y+header_h
    body_h=max(button_y-gap-body_y,h/20)
    return (left,top,list_w,list_h),(left,header_y,list_w,header_h),(left,body_y,list_w,body_h),button_y

class SuctionSource(unittest.TestCase):
    def test_selection_uses_treating_provider(self):
        s=sqf('suctionSelectDevice')
        self.assertIn('ACME_laryngo_medic',s)
        self.assertIn('[_medic, _patient, "ACM_ACCUVAC"] call ACME_fnc_treatmentSupplyCount',s)
        self.assertIn('[_medic, _patient, "ACM_SuctionBag"] call ACME_fnc_treatmentSupplyCount',s)
        self.assertNotIn('[_patient, "ACM_ACCUVAC"]',s)
    def test_accuvac_precedes_bag(self):
        s=sqf('suctionSelectDevice')
        self.assertIn('if (_accuN > 0) then {_type = 1;} else',s)
        self.assertIn('if (_opened || {_bagN > 0}) then {_type = 0;}',s)
    def test_inventory_check_is_local_and_bounded(self):
        t=tokens('suctionSelectDevice')
        self.assertIn('diag_tickTime',t)
        self.assertIn('0.25',t)
        for token in ['remoteExec','remoteExecCall','CBA_fnc_globalEvent','CBA_fnc_addPerFrameHandler']:
            self.assertNotIn(token,t)
    def test_tray_and_held_renderer_share_selection(self):
        for f in ['laryngoInit','laryngoRefreshSlots','laryngoGrab','laryngoSuction','suctionBulb']:
            with self.subTest(file=f):self.assertIn('ACME_fnc_suctionSelectDevice',tokens(f))
        s=sqf('laryngoInit')
        self.assertLess(s.index('[true] call ACME_fnc_suctionSelectDevice'),s.index('[] call ACME_fnc_laryngoRefreshSlots'))
    def test_profiles_have_existing_tray_art(self):
        for rel in ['ui/laryngo/suction/yank_master.paa','ui/laryngo/suctionbag/nar_tsd_level_0000_ca.paa']:
            with self.subTest(path=rel):self.assertTrue((R/rel).is_file())
        self.assertIn('_dev getOrDefault ["tray", ""]',sqf('suctionSelectDevice'))
    def test_last_bag_is_not_consumed_by_action(self):
        block=read('config.cpp').split('class UseSuctionBag: CheckAirway {',1)[1].split('class UseAccuvac:',1)[0]
        self.assertIn('consumeItem = 0;',block)
        self.assertIn('[_medic, _pat, ["ACM_SuctionBag"]] call ACME_fnc_treatmentSupplyTake',sqf('suctionBulb'))
    def test_consumption_is_verified_and_session_bound(self):
        s=sqf('suctionBulb')
        self.assertIn('!local _medic',s)
        self.assertIn('_receipt isNotEqualTo []',s)
        self.assertIn('isEqualTo [_medic, _pat]',s)
        self.assertEqual(s.count('call ACME_fnc_treatmentSupplyTake'),1)
    def test_opening_does_not_spend_disposable(self):
        self.assertNotIn('removeItem',tokens('suctionOpen'))
        self.assertNotIn('removeItem',tokens('laryngoOpen'))
    def test_no_device_does_not_render(self):
        self.assertIn('if (_type < 0)',sqf('suctionSelectDevice'))
        self.assertIn('"ACME_laryngo_held", ""',sqf('suctionSelectDevice'))
        self.assertIn('getVariable ["ACME_suction_type", -1]) < 0) exitWith',sqf('laryngoSuction'))
    def test_existing_profile_capacity_and_rates(self):
        s=sqf('suctionDevice')
        for fragment in ['["capacityMl",  1000]','["mlPerSqueeze", 50]',
                         '["v", 0.083]', '["b", 0.111]', '["s", 0.167]', '["frameMs",    110]']:
            self.assertIn(fragment,s)
    def test_flashlight_rebuild_is_bound_to_medic_and_patient(self):
        s=sqf('laryngoInit')
        for v in ['count _suctionResume == 6','_suctionResume select 0','_suctionResume select 1',
                  'ACME_suction_bagOwner','ACME_suction_bagMl','ACME_suction_totalMl']:
            self.assertIn(v,s)
        self.assertIn('ACME_Laryngoscopy_Dialog',sqf('laryngoClose'))
    def test_final_close_clears_open_bag_without_refund(self):
        s=sqf('laryngoClose')
        self.assertIn('if (!_suctionRebuild)',s)
        self.assertNotIn('addItem',tokens('laryngoClose'))
        self.assertIn('[_pfh] call CBA_fnc_removePerFrameHandler',s)
    def test_suction_tick_runs_once_per_frame(self):
        # B13 fixes the B2 duplicate invocation rather than preserving double drainage.
        self.assertEqual(tokens('laryngoTick').count('ACME_fnc_laryngoSuction'),1)

class SuctionModel(unittest.TestCase):
    def test_device_priority_matrix(self):
        for a,b,o in itertools.product([0,1,2],[0,1,3],[False,True]):
            with self.subTest(a=a,b=b,opened=o):
                self.assertEqual(device(a,b,o), 1 if a else 0 if b or o else -1)
    def test_invalid_patient_or_provider_cannot_select(self):
        self.assertEqual(device(2,2,True,False),-1)
    def test_last_bag_can_be_used_repeatedly(self):
        b,o,ok=squeeze(0,1)
        self.assertEqual((b,o,ok),(0,True,True))
        for _ in range(20):
            b,o,ok=squeeze(0,b,o)
            self.assertEqual((b,o,ok),(0,True,True))
    def test_failed_inventory_removal_does_not_create_bag(self):
        self.assertEqual(squeeze(0,1,False,False),(1,False,False))
    def test_accuvac_does_not_spend_bag(self):
        self.assertEqual(squeeze(1,3),(3,False,False))
    def test_accuvac_arrival_takes_priority_over_open_bag(self):
        self.assertEqual(device(1,0,True),1)
        self.assertEqual(device(0,0,True),0)

class FlushSource(unittest.TestCase):
    def test_flush_reopens_native_dialog_with_ten(self):
        s=sqf('skPickFlush')
        self.assertIn('[10, _patient, _bodyPart, _flushClass]',s)
        self.assertLess(s.index('_display closeDisplay 0'),s.index('call ACME_fnc_skOpenDraw'))
        self.assertIn('ACME_SK_RestoreMouse',s)
    def test_flush_forces_size_before_native_closure_capture(self):
        s=sqf('skOpenDraw')
        self.assertLess(s.index('if (_flushClass != "") then {_size = 10;}'),s.index('call ACM_circulation_fnc_Syringe_Draw'))
        self.assertIn('0, [0, _flushClass]',s)
    def test_every_previous_size_opens_ten(self):
        s=sqf('skPickFlush')
        target=int(re.search(r'\}, \[(\d+), _patient, _bodyPart, _flushClass\]',s).group(1))
        for previous in [1,3,5,10]:
            with self.subTest(previous=previous):self.assertEqual(target,10)
    def test_does_not_require_empty_ten_ml_syringe(self):
        for f in ['skPickFlush','skWasteBegin','skOpenDraw']:
            self.assertNotIn('ACM_Syringe_10',tokens(f))
    def test_pending_compound_is_committed_before_close(self):
        s=sqf('skPickFlush')
        self.assertLess(s.index('ACME_fnc_skCompoundCommit'),s.index('_display closeDisplay 0'))
        self.assertIn('if (_saveFailed) exitWith',s)
    def test_flush_full_state_initialized_at_entry(self):
        s=sqf('skWasteBegin')
        for part in ['private _cap = 10;', '["ACME_SK_WasteFill", _cap]',
                     '["ACME_SK_WasteNS", _cap]', '["ACME_SK_CurSize", 10]']:
            self.assertIn(part,s)
        self.assertIn('ACM_circulation_SyringeDraw_Size", 0]) != 10',s)
    def test_old_medication_and_geometry_are_not_carried(self):
        s=sqf('skWasteBegin')
        for part in ['SyringeDraw_Medication = ""','SyringeDraw_MedicationSelected = false',
                     'Saline flush (10 mL)','SyringeDraw_Ctrl_LimitBottom']:
            self.assertIn(part,s)
    def test_flush_picker_does_not_run_in_bag_prep(self):
        self.assertIn('_display getVariable ["ACME_SK_Return", []]',sqf('skPickFlush'))
        self.assertIn('if (dialog) exitWith',sqf('skPickFlush'))

class EmmaSource(unittest.TestCase):
    def test_airway_kind_prioritizes_et_tube(self):
        s=sqf('emmaAirwayKind')
        self.assertLess(s.index('ACME_ETT_Inserted'),s.index('ACM_airway_AirwayItem_Oral'))
    def test_menu_and_hud_use_same_airway_helper(self):
        for f in ['emmaCanAttachIGel','emmaAttachIGel','emmaRemoveIGel','emmaTick']:
            self.assertIn('ACME_fnc_emmaAirwayKind',tokens(f))
    def test_attach_does_not_require_previous_contact(self):
        self.assertNotIn('ACME_emma_lastContact',sqf('emmaCanAttachIGel'))
        self.assertIn('ACME_fnc_emmaMarkContact',tokens('emmaAttachIGel'))
    def test_ett_action_and_success_both_check_type(self):
        s=read('config.cpp').split('class ACME_AttachEMMAETT:',1)[1].split('class ACME_RemoveEMMAETT:',1)[0]
        self.assertIn("[_medic, _patient, 'ett'] call ACME_fnc_emmaCanAttachIGel",s)
        self.assertIn("[_medic, _patient, _bodyPart, 'ett'] call ACME_fnc_emmaAttachIGel",s)
        self.assertIn('Attach EMMA to ETT',s)
    def test_ett_uses_capnography_group(self):
        s=sqf('menuActionInfo')
        self.assertIn('acme_attachemmaett',s)
        self.assertIn('acme_removeemmaett',s)
        self.assertIn('["airway", "capno", false]',s)
    def test_detach_has_existing_sound(self):
        s=read('config.cpp').split('class ACME_RemoveEMMAETT:',1)[1].split('class ACME_AttachEMMAIGel:',1)[0]
        self.assertIn('ACME_EMMA_Detach',s)
    def test_existing_state_keys_are_retained(self):
        from test_bounded_assessment_contracts import assert_emma_identity_contract
        # Attachment keys belong to the current shared writer, not every caller.
        assert_emma_identity_contract()

class EmmaModel(unittest.TestCase):
    def test_ett_and_igel_supported(self):
        self.assertTrue(emma(ett=True,required='ett'))
        self.assertTrue(emma(oral='SGA',required='igel'))
    def test_other_airways_do_not_enable_attachment(self):
        for oral in ['', 'OPA', 'NPA']:
            self.assertFalse(emma(oral=oral))
    def test_label_routing_is_unambiguous(self):
        self.assertFalse(emma(ett=True,required='igel'))
        self.assertFalse(emma(oral='SGA',required='ett'))
        self.assertEqual(airway(True,'SGA'),'ett')
    def test_inventory_or_bvm_emma_required(self):
        self.assertFalse(emma(ett=True,carried=False))
        self.assertTrue(emma(ett=True,carried=False,bvm=True))
    def test_same_vehicle_and_distance(self):
        self.assertTrue(emma(ett=True,distance=5))
        self.assertFalse(emma(ett=True,distance=5.01))
        self.assertTrue(emma(ett=True,distance=8,same_vehicle=True))
    def test_attached_disabled_and_invalid_cases(self):
        for kw in [{'attached':True},{'system':False},{'valid':False}]:
            self.assertFalse(emma(ett=True,**kw))

class TallySourceAndModel(unittest.TestCase):
    def test_layout_reads_actual_size_list_bounds(self):
        s=sqf('patchDrawDialog')
        self.assertIn('ctrlPosition (_display displayCtrl 84130)',s)
        self.assertIn('_sizeY + _sizeH + _gap',s)
        self.assertNotIn('safeZoneH / 1.72',s)
    def test_old_headers_and_lists_hidden(self):
        from test_bounded_stock_columns import test_preparation_hides_only_existing_flush_sources_and_keeps_tally_wiring
        from test_bounded_medication_presentation import test_actual_view_and_refresh_keep_preparation_sources_off_body_map
        test_preparation_hides_only_existing_flush_sources_and_keeps_tally_wiring()
        for kind in ('flush', 'medication'):
            test_actual_view_and_refresh_keep_preparation_sources_off_body_map('syringe', True, kind)
    def test_text_lives_in_scrolling_group(self):
        s=sqf('patchDrawDialog')
        self.assertIn('["RscControlsGroup", 84362]',s)
        self.assertIn('["RscStructuredText", 84361, _tallyGroup]',s)
        self.assertIn('ctrlTextHeight _ctrl',sqf('infusionRefreshTally'))
    def test_tally_lists_all_accepted_components_without_old_cap(self):
        s=sqf('infusionRefreshTally')
        self.assertNotIn('Up to %1 syringes of one drug.',s)
        self.assertNotIn('_maxPush',s)
        self.assertIn('ACME_fnc_preparedComponents',s)
        self.assertIn('forEach _rows',s)
    def test_panel_geometry_does_not_overlap_other_rows(self):
        # Six safe-zone geometries, including a 5120/1440 wide viewport approximation.
        for zone in [(0,0,1,1),(-1,0,3,1),(-1.3,-.2,3.6,1.4),(-.4,-.3,1.8,1.6),
                     (-.5,-.1,2,1.2),(0,-.5,1,2)]:
            with self.subTest(zone=zone):
                size,header,body,button_y=tally_rectangles(*zone)
                self.assertGreater(header[1],size[1]+size[3])
                self.assertAlmostEqual(body[1],header[1]+header[3])
                self.assertLess(body[1]+body[3],button_y)
                self.assertGreater(body[3],0)
                self.assertEqual(size[0],header[0])
                self.assertEqual(size[2],body[2])
    def test_layout_ratios_match_source(self):
        patch=sqf('patchDrawDialog')
        self.assertIn('safeZoneH / 1.19',patch)
        self.assertIn('safeZoneH / 40',patch)
        self.assertIn('safeZoneH / 28',patch)
        self.assertIn('ctrlPosition (_display displayCtrl 84130)',patch)
        # Current Narc Box geometry deliberately widens the two source columns while preserving
        # their inner edges. The tally then reads the actual size-list bounds rather than duplicating ratios.
        inj=sqf('skInject')
        self.assertIn('private _listW = _uiW / 5.25',inj)
        self.assertIn('private _columnInner = _uiW / 3.3',inj)
        self.assertIn('private _leftX = (_uiX + (_uiW / 2) - _columnInner) - _listW',inj)
        self.assertIn('private _sizeListH = safeZoneH / 5',inj)
        self.assertIn('private _nativeMedGeometry = _display displayCtrl 84006',inj)
        self.assertNotIn('ACME_SK_MedMeterH',inj)

if __name__ == '__main__':
    unittest.main()
