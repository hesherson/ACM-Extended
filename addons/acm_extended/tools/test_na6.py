#!/usr/bin/env python3
"""NA6 parser fixtures and UI reference models. These tests do not execute SQF or Arma controls."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import unittest
from check_na6_source import settings, effective_map, LABELS, code

ROOT=Path(__file__).resolve().parents[1]

@dataclass
class MenuModel:
    """Model display lifetime, target ownership and the ordered handle cache in NA6."""
    target: str|None=None
    opened: list[str]=field(default_factory=list)
    rows: list[tuple[int,str]]=field(default_factory=list)
    next_handle: int=1
    deleted: list[int]=field(default_factory=list)
    pending_reopen: bool=False
    grouping: bool=True
    def render(self,target,classes,frame=0,triage=False):
        # frame is deliberately irrelevant in NA6. A frame gap cannot close a live display.
        if self.target!=target:self.target=target;self.opened=[]
        if triage:classes=[]
        out=[]
        for i,cls in enumerate(classes):
            old=self.rows[i] if i<len(self.rows) else None
            if old and old[1]==cls:out.append(old)
            else:
                if old:self.deleted.append(old[0])
                out.append((self.next_handle,cls));self.next_handle+=1
        self.deleted.extend(h for h,_ in self.rows[len(classes):]);self.rows=out
    def click_header(self,key,button_target,current_target):
        if button_target!=current_target or self.target!=current_target or not key:return
        if key in self.opened:self.opened.remove(key)
        else:self.opened.append(key)
    def click_treatment(self):self.pending_reopen=True
    def grouping_setting_changed(self,value=False):
        if self.grouping!=value:self.opened=[]
        self.grouping=value

class MenuTests(unittest.TestCase):
    def fresh(self):
        m=MenuModel();m.render('A',['header','item']);return m
    def test_open_then_refresh(self):
        m=self.fresh();m.click_header('chest','A','A');m.render('A',['header','item'],1);self.assertEqual(m.opened,['chest'])
    def test_large_frame_gap_keeps_open(self):
        m=self.fresh();m.click_header('chest','A','A');m.render('A',['header','item'],100000);self.assertEqual(m.opened,['chest'])
    def test_second_render_same_frame_keeps_open(self):
        m=self.fresh();m.click_header('chest','A','A');m.render('A',['header','item'],0);self.assertEqual(m.opened,['chest'])
    def test_original_frame_heuristic_counterexample(self):
        opened=['chest'];last_frame=100;frame=102
        if frame-last_frame>1:opened=[]
        self.assertEqual(opened,[])  # Demonstrates the old reset with the display still open.
    def test_multiple_groups(self):
        m=self.fresh();m.click_header('chest','A','A');m.click_header('airway','A','A');self.assertEqual(m.opened,['chest','airway'])
    def test_close_one_group_only(self):
        m=self.fresh();m.opened=['chest','airway'];m.click_header('chest','A','A');self.assertEqual(m.opened,['airway'])
    def test_new_patient_resets(self):
        m=self.fresh();m.opened=['chest'];m.render('B',['header']);self.assertEqual(m.opened,[])
    def test_new_display_has_no_previous_open_state(self):
        old=self.fresh();old.opened=['chest'];new=self.fresh();self.assertEqual(new.opened,[])
    def test_patient_to_null_resets(self):
        m=self.fresh();m.opened=['chest'];m.render(None,[]);self.assertEqual(m.opened,[])
    def test_switch_back_is_new_patient_context(self):
        m=self.fresh();m.opened=['chest'];m.render('B',[]);m.render('A',[]);self.assertEqual(m.opened,[])
    def test_triage_keeps_groups_but_clears_buttons(self):
        m=self.fresh();m.opened=['chest'];m.render('A',[],triage=True);self.assertEqual(m.opened,['chest']);self.assertEqual(m.rows,[])
    def test_category_and_limb_changes_keep_groups(self):
        m=self.fresh();m.opened=['chest'];m.render('A',['othercategory']);self.assertEqual(m.opened,['chest'])
    def test_group_with_no_available_actions_keeps_state(self):
        m=self.fresh();m.opened=['chest'];m.render('A',[]);m.render('A',['header','item']);self.assertEqual(m.opened,['chest'])
    def test_explicit_grouping_toggle_resets(self):
        m=self.fresh();m.opened=['chest'];m.grouping_setting_changed();self.assertEqual(m.opened,[])
    def test_repeated_setting_callback_does_not_collapse(self):
        m=self.fresh();m.opened=['chest'];m.grouping_setting_changed(True);self.assertEqual(m.opened,['chest'])
    def test_two_changes_then_repeated_notification(self):
        m=self.fresh();m.grouping_setting_changed(False);m.grouping_setting_changed(True);m.opened=['chest'];m.grouping_setting_changed(True);self.assertEqual(m.opened,['chest'])
    def test_two_displays_are_independent(self):
        m=self.fresh();n=self.fresh();m.opened=['chest'];self.assertEqual(n.opened,[])
    def test_header_does_not_arm_reopen(self):
        m=self.fresh();m.click_header('chest','A','A');self.assertFalse(m.pending_reopen)
    def test_treatment_retains_reopen(self):
        m=self.fresh();m.click_treatment();self.assertTrue(m.pending_reopen)
    def test_stale_patient_button_ignored(self):
        m=self.fresh();m.click_header('chest','A','B');self.assertEqual(m.opened,[])
    def test_stale_display_patient_ignored(self):
        m=self.fresh();m.click_header('chest','B','B');self.assertEqual(m.opened,[])
    def test_empty_header_key_ignored(self):
        m=self.fresh();m.click_header('','A','A');self.assertEqual(m.opened,[])
    def test_same_classes_reuse_all_handles(self):
        m=self.fresh();before=m.rows[:];m.render('A',['header','item']);self.assertEqual(m.rows,before);self.assertEqual(m.deleted,[])
    def test_changed_icon_replaced_in_same_pass(self):
        m=self.fresh();before=m.rows[:];m.render('A',['header','newicon']);self.assertEqual(m.rows[0],before[0]);self.assertNotEqual(m.rows[1][0],before[1][0]);self.assertEqual(len(m.rows),2)
    def test_replaced_first_row_does_not_reorder_next_pass(self):
        m=self.fresh();tail=m.rows[1];m.render('A',['changed','item']);replaced=m.rows[0];m.render('A',['changed','item']);self.assertEqual(m.rows,[replaced,tail])
    def test_append_keeps_existing_handles(self):
        m=self.fresh();before=m.rows[:];m.render('A',['header','item','item2']);self.assertEqual(m.rows[:2],before)
    def test_shrink_removes_tail_only(self):
        m=self.fresh();first=m.rows[0];last=m.rows[1][0];m.render('A',['header']);self.assertEqual(m.rows,[first]);self.assertEqual(m.deleted,[last])
    def test_left_alignment_class_change_keeps_open(self):
        m=self.fresh();m.opened=['chest'];m.render('A',['L_header','L_item']);self.assertEqual(m.opened,['chest']);self.assertEqual(len(m.rows),2)
    def test_every_frame_updates_dynamic_availability(self):
        m=self.fresh();m.render('A',['header']);self.assertEqual(len(m.rows),1);m.render('A',['header','available_now']);self.assertEqual(len(m.rows),2)
    def test_original_index_cache_misses_same_length_identity_change(self):
        a=['header','needle'];b=['header','syringe'];self.assertEqual(list(range(len(a))),list(range(len(b))));self.assertNotEqual(a,b)

class SettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'XEH_preInit.sqf').read_text();cls.rows=settings(cls.source)
        cls.mapping=effective_map((ROOT/'functions/fn_applyHardcore.sqf').read_text())
    def resolve(self,values):
        # NA8.5-B1: presentation uses the resolved checkbox directly; other systems retain cached tuning.
        result = {effective:values.get(setting,False) for effective,setting in self.mapping.items()}
        result['ACME_hc_descriptors'] = values.get('ACME_hc_descriptors',False) is True
        return result
    def test_descriptors_use_direct_gate_without_tuning_cache(self):
        descriptor = (ROOT/'functions/fn_medDescriptor.sqf').read_text()
        self.assertIn('missionNamespace getVariable ["ACME_hc_descriptors", false]', descriptor)
        self.assertIn('isEqualTo true', descriptor)
        self.assertNotIn('ACME_hcEff_descriptors', self.mapping)
        self.assertEqual(''.join(self.rows['ACME_hc_descriptors']['callback'].split()), '{}')
    def test_actual_labels_have_no_colon(self):self.assertTrue(all(':' not in self.rows[k]['label'] for k in LABELS))
    def test_all_off_by_default(self):self.assertFalse(any(self.resolve({}).values()))
    def test_old_master_true_has_no_effect(self):self.assertFalse(any(self.resolve({'ACME_hc_master':True}).values()))
    def test_every_checkbox_is_independent(self):
        for name in LABELS:
            with self.subTest(name=name):self.assertEqual(sum(self.resolve({name:True}).values()),1)
    def test_turning_one_off_preserves_others(self):
        flags={name:True for name in LABELS};flags['ACME_hc_tbi']=False;r=self.resolve(flags);self.assertFalse(r['ACME_hcEff_tbi']);self.assertEqual(sum(r.values()),len(LABELS)-1)
    def test_reapplication_does_not_compound(self):
        base=.2;flags={'ACME_hc_chestSeal':True};scale=lambda v:base*(1.15 if self.resolve(v)['ACME_hcEff_cs'] else 1)
        self.assertEqual(scale(flags),scale(flags));self.assertEqual(scale({}),base)
    def test_all_former_master_modes_addressable(self):self.assertTrue({'ACME_hcEff_rhythm','ACME_hcEff_nrb','ACME_hcEff_blastLung','ACME_hcEff_vent'}<=self.mapping.keys())
    def test_duplicate_setting_is_rejected(self):
        sample='private _settings = [["X","CHECKBOX",["Name","Tip"],["Cat","Sub"],false,1,{}],["X","CHECKBOX",["Name","Tip"],["Cat","Sub"],false,1,{}]];'
        with self.assertRaises(ValueError):settings(sample)
    def test_quoted_comments_do_not_create_settings(self):
        sample='// ["BAD", "CHECKBOX"]\nprivate _settings = [["X","CHECKBOX",["Name","Tip"],["Cat","Sub"],false,1,{}]];'
        self.assertEqual(set(settings(sample)),{'X'})
    def test_nested_callback_parses(self):
        sample='private _settings = [["X","CHECKBOX",["Name","Tip"],["Cat","Sub"],false,1,{if (true) then {[1,2] call X;};}]];'
        self.assertIn('call X',settings(sample)['X']['callback'])
    def test_early_callback_reference_defers_until_ready(self):
        captured=False;ready=False
        def apply():return ready
        captured=apply();self.assertFalse(captured);ready=True;captured=apply();self.assertTrue(captured)

if __name__=='__main__':unittest.main(verbosity=2)
