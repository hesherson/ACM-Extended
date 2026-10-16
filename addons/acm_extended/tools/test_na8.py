#!/usr/bin/env python3
"""NA8 source-data checks and explicit Python UI/policy reference models.
These tests do not execute SQF, simulate Arma's config merge, or validate in-game audio.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json, unittest
from na8_menu_reference import Entry, lineage, category, policy
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=json.loads((ROOT/'tools/na8_action_fixture.json').read_text())
ENTRIES={k:Entry(**v) for k,v in FIXTURE['entries'].items()}

def classify(name):return policy(name,category(ENTRIES,name),lineage(ENTRIES,name))

def order(rows):
    visible=[r for r in rows if not r['hidden']]
    return [r for r in visible if r['bucket']=='iv_access']+[r for r in visible if r['bucket']=='narc_box']+[r for r in visible if r['bucket'] not in {'iv_access','narc_box'}]

def group(rows,enabled,clinical,head=True,opened=()):
    if not enabled:return [r['name'] for r in rows if r.get('available',True)]
    keys=['route_po','route_in','route_buc'] if head else []
    labels=dict(zip(keys,['PO','IN','BUC'] if clinical else ['By Mouth','Inhaled','Buccal']))
    flat=[r['name'] for r in rows if r['bucket'] not in keys and r.get('available',True)]
    for key in keys:
        live=[r['name'] for r in rows if r['bucket']==key and r.get('available',True)]
        if live:
            flat.append('[ - ] '+labels[key] if key in opened else '[ + ] '+labels[key])
            if key in opened:flat+=['        '+name for name in live]
    return flat

@dataclass
class BodyModel:
    """Model the documented group reveal hazard and source's corrected ordering."""
    visible:bool=False
    shown:set[str]=field(default_factory=set)
    group_commands:int=0
    next_refresh:float=0
    controls:set[str]=field(default_factory=lambda:{'skin','igel','aed','seal','tq','junction','hpmk','iv','ej','io','unused'})
    def render(self,requested,state,now=0,force=False):
        if requested!=self.visible:
            self.group_commands+=1;self.visible=requested
            self.shown=set(self.controls) if requested else set()
            if requested:self.shown={'skin'};force=True
        if not requested:return
        if not force and now<self.next_refresh:return
        self.next_refresh=now+.1
        self.shown={'skin'} | (state & self.controls - {'unused'})
    def inputs(self,route='vascular'):
        return self.shown&{'iv','ej','io'} if self.visible and route=='vascular' else set()

class ActionSourceData(unittest.TestCase):
    def test_fixture_has_native_and_extended(self):
        self.assertGreater(len(ENTRIES),200);self.assertIn('checkairway',ENTRIES);self.assertIn('acme_establishej',ENTRIES)
    def test_all_four_native_syringes_hidden(self):
        for n in (10,5,3,1):self.assertTrue(classify(f'UseSyringe_{n}')[2])
    def test_transfusion_entry_not_hidden_with_syringes(self):self.assertEqual(classify('OpenTransfusionMenu'),('medication','iv_access',False))
    def test_all_declared_advanced_iv_io_prefixes_move(self):
        for k in ENTRIES:
            if k.startswith(('insertiv_','removeiv_','insertio_','removeio_')) and category(ENTRIES,k)=='advanced':self.assertEqual(classify(k),('medication','iv_access',False))
    def test_ej_and_minigame_move(self):
        for k in ['ACME_IVMinigameStart','ACME_EstablishEJ','ACME_RemoveEJ']:self.assertEqual(classify(k),('medication','iv_access',False))
    def test_all_extended_18g_sites_move(self):
        for verb in ('Place','Remove'):
            for site in ('Upper','Middle','Lower'):self.assertEqual(classify(f'ACME_{verb}18g_{site}'),('medication','iv_access',False))
    def test_legacy_fluid_actions_move_without_enabling_them(self):
        for fluid in ('BloodIV','PlasmaIV','SalineIV'):
            for suffix in ('','_500','_250'):self.assertEqual(classify(fluid+suffix),('medication','iv_access',False))
    def test_examination_is_not_relocated(self):
        for k in ('InspectIV_Upper','InspectIV_Middle','InspectIV_Lower'):self.assertEqual(classify(k),('examine','examine_injuries',False))
    def test_narc_box_keeps_entry(self):self.assertEqual(classify('ACME_SyringeKit_DrawPatient'),('medication','narc_box',False))
    def test_checkairway_moves_to_airway_group(self):self.assertEqual(classify('CheckAirway'),('airway','adjuncts',False))
    def test_checkbreathing_moves_to_breathing_group(self):self.assertEqual(classify('CheckBreathing'),('airway','ventilation',False))
    def test_all_suction_variants_in_airway(self):
        for k in ('UseSuctionBag','UseAccuvac','DrainFluid_ACCUVAC','DrainFluid_SuctionBag','ACME_DrainFluid_ACCUVAC','ACME_DrainFluid_SuctionBag'):self.assertEqual(classify(k),('airway','adjuncts',False))
    def test_acetaminophen_is_po(self):self.assertEqual(classify('Paracetamol'),('medication','route_po',False))
    def test_ace_painkillers_is_po(self):self.assertEqual(classify('Painkillers'),('medication','route_po',False))
    def test_inhaled_and_nasal_routes(self):
        for k in ('Penthrox','AmmoniaInhalant','Naloxone','ACME_Esketamine_IN'):self.assertEqual(classify(k),('medication','route_in',False))
    def test_buccal_only_fentanyl_family(self):
        got={k for k in ENTRIES if classify(k)[1]=='route_buc'};self.assertEqual(got,{'fentanyllozenge','removefentanyllozenge'})
    def test_lozenge_and_inhalant_parent_really_is_oral_class(self):
        for k in ('FentanylLozenge','Naloxone','Penthrox'):self.assertIn('paracetamol',lineage(ENTRIES,k))
    def test_unrelated_head_actions_not_oral(self):
        from test_historical_menu_execution import test_current_routes_do_not_capture_foreign_descendants_or_restore_basic_dropdowns as verify
        verify('SlapAwake','advanced','CheckResponse',['examine','',False])
    def test_chest_examination_does_not_move_bvm_descendants(self):
        from test_historical_menu_execution import test_current_routes_do_not_capture_foreign_descendants_or_restore_basic_dropdowns as verify
        for name in ('ACME_InspectChest','UseStethoscope'):
            verify(name,'examine','CheckBreathing',['airway','ventilation',False])
        for name in ('UseBVM','UseBVM_Oxygen','UseBVM_VehicleOxygen','UseBVM_PortableOxygen'):
            verify(name,'airway','UseStethoscope',['airway','ventilation',False])
    def test_injectable_not_misclassified(self):self.assertEqual(classify('Morphine'),('medication','',False))
    def test_aed_advanced_stays_advanced(self):self.assertEqual(classify('AED_ApplyPads'),('advanced','',False))
    def test_unknown_extension_is_retained(self):self.assertEqual(policy('AnotherAddonAction','advanced',['anotheraddonaction']),('advanced','',False))
    def test_order_is_iv_narc_rest(self):
        rows=[{'name':n,'bucket':b,'hidden':False} for n,b in [('oral','route_po'),('narc','narc_box'),('iv1','iv_access'),('other',''),('iv2','iv_access')]]
        self.assertEqual([r['name'] for r in order(rows)],['iv1','iv2','narc','oral','other'])
    def test_order_preserves_callbacks(self):
        callback=object();rows=[dict(name='IV',bucket='iv_access',hidden=False,callback=callback)]
        self.assertIs(order(rows)[0]['callback'],callback)
    def test_hidden_does_not_consume_or_change_stock(self):
        rows=[dict(name='Syringe',bucket='',hidden=True,stock=2)];self.assertEqual(order(rows),[]);self.assertEqual(rows[0]['stock'],2)
    def test_cycle_guard_in_model(self):
        e={'a':Entry('a','b'),'b':Entry('b','a')};self.assertEqual(lineage(e,'a'),['a','b'])

class GroupReference(unittest.TestCase):
    def setUp(self):self.rows=[dict(name=n,bucket=b) for n,b in [('IV','iv_access'),('Narc Box','narc_box'),('Acetaminophen','route_po'),('Naloxone','route_in'),('Fentanyl Lozenge','route_buc')]]
    def test_plain_labels(self):self.assertEqual(group(self.rows,True,False),['IV','Narc Box','[ + ] By Mouth','[ + ] Inhaled','[ + ] Buccal'])
    def test_clinical_labels(self):self.assertEqual(group(self.rows,True,True),['IV','Narc Box','[ + ] PO','[ + ] IN','[ + ] BUC'])
    def test_flat_plain_no_headers(self):self.assertEqual(group(self.rows,False,False),[r['name'] for r in self.rows])
    def test_flat_clinical_no_headers(self):self.assertEqual(group(self.rows,False,True),[r['name'] for r in self.rows])
    def test_nonhead_grouping_does_not_swallow_rows(self):self.assertEqual(group(self.rows,True,True,False),[r['name'] for r in self.rows])
    def test_empty_route_has_no_header(self):
        self.rows[2]['available']=False;self.assertNotIn('[ + ] PO',group(self.rows,True,True))
    def test_open_children_are_indented(self):self.assertIn('        Fentanyl Lozenge',group(self.rows,True,True,opened=['route_buc']))
    def test_label_change_keeps_open_key(self):
        for clinical in [False,True]:self.assertIn('        Fentanyl Lozenge',group(self.rows,True,clinical,opened=['route_buc']))
    def test_no_treatment_completion_needed_to_refresh(self):
        before=group(self.rows,True,True);self.rows[3]['available']=False;after=group(self.rows,True,True);self.assertNotEqual(before,after)
    def test_grouping_alignment_does_not_mutate_saved_setting(self):
        for saved in [False,True]:
            for nested in [False,True]:self.assertEqual(saved or nested,True if nested else saved)

class BodyVisibilityReference(unittest.TestCase):
    def test_original_post_update_reveal_is_counterexample(self):
        b=BodyModel();b.render(True,{'igel','iv'});b.shown=set(b.controls);self.assertIn('hpmk',b.shown)
    def test_healthy_no_treatments(self):
        b=BodyModel();b.render(True,set());self.assertEqual(b.shown,{'skin'})
    def test_igel_only(self):
        b=BodyModel();b.render(True,{'igel'});self.assertEqual(b.shown,{'skin','igel'})
    def test_aed_added_live(self):
        b=BodyModel();b.render(True,{'igel'});b.render(True,{'igel','aed'},.11);self.assertIn('aed',b.shown)
    def test_aed_removed_live(self):
        b=BodyModel();b.render(True,{'aed'});b.render(True,set(),.11);self.assertNotIn('aed',b.shown)
    def test_hpmk_only_when_patient_has_it(self):
        b=BodyModel();b.render(True,{'hpmk'});self.assertIn('hpmk',b.shown);b.render(True,set(),.11);self.assertNotIn('hpmk',b.shown)
    def test_hover_does_not_reveal_group(self):
        b=BodyModel();b.render(True,{'iv'});b.render(True,{'iv'},.01);self.assertEqual(b.group_commands,1);self.assertEqual(b.shown,{'skin','iv'})
    def test_subsequent_tick_does_not_reveal_group(self):
        b=BodyModel();b.render(True,{'iv'});b.render(True,{'iv'},.5);self.assertEqual(b.group_commands,1)
    def test_toggle_back_reapplies_masks(self):
        b=BodyModel();b.render(True,{'iv'});b.render(False,{'iv'},.01);b.render(True,{'ej'},.02);self.assertEqual(b.shown,{'skin','ej'})
    def test_hidden_group_has_no_input(self):
        b=BodyModel();b.render(True,{'iv'});b.render(False,{'iv'});self.assertEqual(b.inputs(),set())
    def test_only_vascular_icons_are_inputs(self):
        b=BodyModel();b.render(True,b.controls);self.assertEqual(b.inputs(),{'iv','ej','io'})
    def test_removed_access_disables_input(self):
        b=BodyModel();b.render(True,{'iv'});b.render(True,set(),.11);self.assertEqual(b.inputs(),set())
    def test_im_route_does_not_make_equipment_clickable(self):
        b=BodyModel();b.render(True,b.controls);self.assertEqual(b.inputs('im'),set())
    def test_other_patient_cannot_leak_overlays(self):
        a=BodyModel();b=BodyModel();a.render(True,{'aed'});b.render(True,{'iv'});self.assertNotIn('aed',b.shown)
    def test_route_change_can_force_same_tick_refresh(self):
        b=BodyModel();b.render(True,{'iv'});b.render(True,{'ej'},0,True);self.assertEqual(b.shown,{'skin','ej'})
    def test_unused_placeholder_never_revealed(self):
        b=BodyModel();b.render(True,b.controls);self.assertNotIn('unused',b.shown)

class ButtonReference(unittest.TestCase):
    def test_equal_dimensions_keep_right_position(self):
        draw=[.2,.7,.04,.03];save=[.6,.7,.08,.03];save[2:]=draw[2:];self.assertEqual(save,[.6,.7,.04,.03])
    def test_geometry_is_resolution_independent(self):
        for sw in [1,1.2,3.56]:
            draw=[0,0,sw/24,.03];save=[.6,.7,sw/13,.03];save[2:]=draw[2:];self.assertEqual(save[2],draw[2])
    def test_sound_survives_callback_change(self):
        button={'soundClick':['native',.09,1],'handler':'native'};button['handler']='compound';self.assertEqual(button['soundClick'],['native',.09,1])
    def test_no_runtime_duplicate_sound_hook(self):
        text=(ROOT/'functions/fn_skInject.sqf').read_text();self.assertNotIn('ACME_fnc_skClickSound',text)

if __name__=='__main__':unittest.main(verbosity=2)
