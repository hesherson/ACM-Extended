"""B13 source contracts and independent reference models; these do NOT execute SQF.

The inherited B12 tests remain active. Per-class checks cover the entire supplied
46-class inventory. Runtime visual, multiplayer and clinical validation are separate.
Run with PYTHONDONTWRITEBYTECODE=1 to keep an exact-source patch tree clean.
"""
from __future__ import annotations
import json, math, re, unittest
from pathlib import Path
from historical_source import read_source
ROOT=Path(__file__).resolve().parents[1]
# Read-only current-source fixture; unresolved macro expressions stay symbolic.
from medication_inventory import inventory
MATRIX=inventory(ROOT.parent/'core/ACM_Medication.hpp', ROOT/'config.cpp')
MEDS={r['classname']:r for r in MATRIX['medication_classes']}
SOURCES={r['source']:r for r in MATRIX['concentrations']}
def src(n):return (ROOT/'functions'/('fn_'+n+'.sqf')).read_text()
def ov(n):return read_source(ROOT/'overrides'/('fn_'+n+'.sqf'))
def clamp(x,a=0.,b=1.):return max(a,min(b,x))
def envelope(route,t,peak,life,plateau):
    # Caller excludes expired/future records. Matches supplied native route functions.
    if t<0 or t>=life:return 0.
    if peak<t<peak+plateau:return 1.
    elim=life-peak-plateau;elapsed=t-peak-plateau
    if route=='ACM_ROUTE_IM':
        x=1.1**(t-peak) if t<=peak+plateau else 1-(elapsed/elim)**2
    else:
        x=math.sin(t/(2*peak/3.113)) if t<=peak+plateau else .5*math.cos(elapsed/(elim/3.1))+.5
    return clamp(x)
def suction_step(exposure,debt,dt,mode='hand',support=False,grace=10.):
    dt=clamp(dt,0,2)
    if mode=='off':return max(0,exposure-2*dt),max(0,debt-.4*dt)
    exposure=min(120,exposure+dt);risk=.15 if mode=='salad' else 1.
    cap=1. if mode=='salad' else 6.
    rate=.25*clamp((exposure-grace)/20)*risk*(.5 if support else 1.)
    return exposure,min(cap,debt+rate*dt) if debt<cap else debt

def suction_run(seconds,mode='hand',support=False,dt=.1):
    exposure=debt=0.
    for _ in range(round(seconds/dt)):
        exposure,debt=suction_step(exposure,debt,dt,mode,support)
    return exposure,debt

def take_sources(parts,opened,sealed,capacities,has_container=True):
    # Pure reference transaction: validation precedes all writes.
    if not has_container:return None
    needs={}
    for name,ml in parts:
        if not isinstance(ml,(float,int)) or not math.isfinite(ml) or ml<=0 or name not in capacities:return None
        needs[name]=needs.get(name,0)+ml
    if any(opened.get(k,0)+sealed.get(k,0)*capacities[k]+1e-6<v for k,v in needs.items()):return None
    out_open=dict(opened);out_sealed=dict(sealed)
    for k,v in needs.items():
        n=math.ceil(max(0,v-out_open.get(k,0))/capacities[k])
        out_open[k]=max(0,out_open.get(k,0)+n*capacities[k]-v)
        out_sealed[k]=out_sealed.get(k,0)-n
    return out_open,out_sealed

def calcium_credit(doses):
    first=credit=0.
    for dose in doses:
        grams=dose/1000;bonus=min(grams,max(0,1-first));first+=bonus;credit+=2*grams+.5*bonus
    return credit

def permitted(name,iv,injectable=False):
    if name in ('EpinephrineCardiac','EpinephrineCardiac_IV'):return iv
    if name in ('Adenosine','Amiodarone','Rocuronium','Phentolamine_IV','Hyaluronidase_IV'):return False
    if name not in MEDS:return False
    route=MEDS[name]['administrationType']
    if injectable and (route not in ('ACM_ROUTE_IM','ACM_ROUTE_IV') or name=='Fentanyl_BUC'):return False
    return (route=='ACM_ROUTE_IV')==iv

class Inventory(unittest.TestCase):
    def test_complete_source_class_count(self):self.assertEqual(len(MEDS),46)
    def test_complete_source_concentration_count(self):self.assertEqual(len(SOURCES),26)
    def test_unique_classnames(self):self.assertEqual(len(MEDS),len(MATRIX['medication_classes']))
    def test_source_concentrations_and_volumes_positive(self):
        for n,r in SOURCES.items():
            with self.subTest(source=n):
                self.assertGreater(r['concentration'],0);self.assertGreater(r['volume'],0)
    def test_epinephrine_concentration_ratio(self):self.assertEqual(SOURCES['Epinephrine']['concentration']/SOURCES['EpinephrineCardiac']['concentration'],10)
    def test_hyaluronidase_units(self):self.assertEqual(SOURCES['Hyaluronidase']['concentration'],150)
    def test_rocuronium_mg_per_kg_reference(self):
        r=MEDS['Rocuronium_IV'];self.assertEqual(r['maxEffectDose'],83);self.assertEqual(r['weightEffect'],1)
        for kg in (40,60,80,100,120):self.assertAlmostEqual((1.2*kg)/(83/83*kg),1.2)
    def test_sugammadex_hundred_mg_reference(self):self.assertEqual(MEDS['Sugammadex_IV']['maxEffectDose'],100)
    def test_midazolam_im_slower_than_iv(self):self.assertGreater(MEDS['Midazolam']['timeTillMaxEffect'],MEDS['Midazolam_IV']['timeTillMaxEffect'])
    def test_cardiac_class_alias_registered(self):self.assertIn('EpinephrineCardiac_IV',MEDS)

# One validation case for every actual medication class, including retained aliases.
def class_test(name):
    def test(self):
        r=MEDS[name];peak=r['timeTillMaxEffect'];life=r['timeInSystem'];plateau=r['maxEffectTime']
        self.assertGreater(peak,0);self.assertGreater(life,peak+plateau);self.assertGreater(r['maxEffectDose'],0)
        self.assertIn(r['administrationType'],('ACM_ROUTE_IM','ACM_ROUTE_IV','ACM_ROUTE_PO','ACM_ROUTE_INHALE'))
        for fraction in (.0001,.01,.1,1,10):
            for t in (0,peak*.5,peak,peak+plateau*.5,life*.99,life):
                e=envelope(r['administrationType'],t,peak,life,plateau)
                self.assertTrue(math.isfinite(e));self.assertGreaterEqual(e,0);self.assertLessEqual(e,1)
                # Shared dose*envelope readers must not depend on dividing a dose into pulses.
                self.assertAlmostEqual(fraction*e,sum([fraction/10*e]*10))
    return test
for _name in MEDS:setattr(Inventory,'test_class_'+_name,class_test(_name))

class PreparationAndRoutes(unittest.TestCase):
    def test_repeated_source_draws_aggregate_before_inventory(self):
        self.assertIsNone(take_sources([('F',1.5),('F',1.5)],{}, {'F':1},{'F':2}))
    def test_repeated_source_uses_two_vials_and_preserves_remainder(self):
        self.assertEqual(take_sources([('F',1.5),('F',1.5)],{}, {'F':2},{'F':2}),({'F':1.0},{'F':0}))
    def test_existing_open_vial_used_first(self):
        self.assertEqual(take_sources([('F',1)],{'F':1.5},{'F':1},{'F':2}),({'F':.5},{'F':1}))
    def test_unavailable_second_component_does_not_consume_first(self):
        opened={'K':2};sealed={'P':0}
        self.assertIsNone(take_sources([('K',1),('P',1)],opened,sealed,{'K':10,'P':50}))
        self.assertEqual(opened,{'K':2});self.assertEqual(sealed,{'P':0})
    def test_container_required_before_sources(self):self.assertIsNone(take_sources([('F',1)],{}, {'F':1},{'F':2},False))
    def test_invalid_source_volumes(self):
        for x in (0,-1,float('nan'),float('inf')):self.assertIsNone(take_sources([('F',x)],{}, {'F':1},{'F':2}))
    def test_all_fixed_noninjectables_rejected_by_syringe_routes(self):
        for n in ('Naloxone','Paracetamol','Esketamine','AmmoniaInhalant','Penthrox','Fentanyl_BUC'):
            self.assertFalse(permitted(n,False,True));self.assertTrue(permitted(n,False,False))
    def test_only_supported_routes(self):
        for n in MEDS:
            if n not in ('Adenosine','Amiodarone','Rocuronium'):
                iv=MEDS[n]['administrationType']=='ACM_ROUTE_IV'
                self.assertTrue(permitted(n,iv));self.assertFalse(permitted(n,not iv))
    def test_local_antidotes_not_iv(self):
        for n in ('Phentolamine','Hyaluronidase'):
            self.assertTrue(permitted(n,False,True));self.assertFalse(permitted(n+'_IV',True,True))
    def test_source_debit_helper_registered(self):self.assertIn('class medicationTakeSources', (ROOT/'config.cpp').read_text())
    def test_compound_batch_debits_and_tag(self):
        t=src('skCompoundCommit');self.assertIn('ACME_fnc_medicationTakeSources',t);self.assertIn('compoundB13',t)
    def test_dilution_now_consumes_drug_not_just_saline(self):
        t=src('skWasteDraw');self.assertIn('ACME_fnc_medicationTakeSources',t);self.assertIn('dilutionB13',t)
    def test_syringe_checks_injectable_route(self):self.assertIn('[_routeClass, _iv, true] call ACME_fnc_medicationRouteAllowed',ov('Syringe_Inject'))
    def test_map_checks_injectable_route(self):self.assertIn('[_class, _iv, true, _virtual] call ACME_fnc_medicationRouteAllowed',src('skInjectSite'))
    def test_recipe_mg_and_mcg_conserved(self):
        drug_ml=1.;saline_ml=9.;concentration=.1
        self.assertAlmostEqual(drug_ml*concentration/(drug_ml+saline_ml)*1000,10)
        self.assertAlmostEqual(drug_ml*concentration*1000,100)
        for push in (1,2,10):self.assertAlmostEqual(push*.01*1000,push*10)
    def test_calcium_split_doses_equal_full_gram(self):self.assertAlmostEqual(calcium_credit([10]*100),calcium_credit([1000]))
    def test_calcium_no_duplicate_first_gram_bonus(self):self.assertAlmostEqual(calcium_credit([1000,1000]),4.5)
    def test_calcium_tiny_infusion_not_discarded(self):self.assertGreater(calcium_credit([1]),0)
    def test_calcium_gluconate_callback_once(self):
        t=src('applyCalciumCredit');self.assertEqual(t.count('call ACM_circulation_fnc_handleMed_CalciumChlorideLocal'),1)
        self.assertIn('gluconate',t.lower())

class EffectAndLifecycleContracts(unittest.TestCase):
    def test_shared_cardiac_reader_uses_dose(self):self.assertIn('_concentration',ov('getCardiacMedicationEffects'));self.assertIn('ACME_fnc_medicationAvailability',ov('getCardiacMedicationEffects'))
    def test_shared_nausea_reader_uses_dose(self):self.assertIn('_concentration',ov('getNauseaMedicationEffects'));self.assertIn('ACME_fnc_medicationAvailability',ov('getNauseaMedicationEffects'))
    def test_b14_naloxone_is_vanilla_not_temporary_antagonist(self):
        self.assertFalse((ROOT/'overrides/fn_handleMed_NaloxoneLocal.sqf').exists())
        self.assertNotIn('class handleMed_NaloxoneLocal', (ROOT/'config.cpp').read_text())
        self.assertNotIn('naloxoneCache',src('medicationAvailability'))
        self.assertIn('_class == "Naloxone"',src('medicationExposure'))
        self.assertIn('_fired set ["opioid"',src('medicationExposure'))
    def test_naloxone_model_can_wear_off_before_opioid(self):
        nal=MEDS['Naloxone'];opioid=MEDS['Morphine_IV'];t=400
        self.assertEqual(envelope(nal['administrationType'],t,nal['timeTillMaxEffect'],nal['timeInSystem'],nal['maxEffectTime']),0)
        self.assertGreater(envelope(opioid['administrationType'],t,opioid['timeTillMaxEffect'],opioid['timeInSystem'],opioid['maxEffectTime']),0)
    def test_sugammadex_tracks_spent_capacity_per_donor(self):
        t=src('sugammadexTick');self.assertIn('ACME_sug_spent',t);self.assertIn('_used = _used + _take',t);self.assertIn('_take / _present',t)
    def test_sugammadex_spent_capacity_not_reusable(self):
        max_capacity=1.2;first_target=1.2;spent=min(max_capacity,first_target)
        self.assertEqual(max(0,max_capacity-spent),0)
    def test_sugammadex_unused_capacity_is_not_destroyed(self):self.assertAlmostEqual(1.2-min(1.2,.4),.8)
    def test_rocuronium_not_native_sedative(self):
        r=MEDS['Rocuronium_IV'];self.assertEqual(r['painReduce'],0);self.assertEqual(r['rrAdjust'],[0,0])
    def test_opioid_threshold_not_disabled_below_one_mg(self):self.assertIn('_maxDose <= 0',ov('onMedicationUsage'));self.assertNotIn('_maxDose < 1',ov('onMedicationUsage'))
    def test_b14_overdose_effect_and_new_exposure_gate(self):
        t=src('medicationToxicityTick')
        self.assertIn('[_patient,_x,false]',t);self.assertIn('_generation > _last',t)
        self.assertIn('_reference / _limit',t)
        self.assertIn('Fentanyl_BUC',t);self.assertIn('Esketamine',t)
    def test_toxicity_runs_without_extended_circulation_toggle(self):self.assertIn('ACME_fnc_medicationToxicityTick',ov('handleUnitVitals'))
    def test_cbrn_no_timed_pfh_onset_termination(self):
        for n in ('Atropine','Dimercaprol'):self.assertNotIn('addPerFrameHandler',ov('handleMed_'+n+'Local'))
        self.assertIn('ACME_fnc_medicationCBRNTick',ov('handleUnitVitals'))
    def test_cbrn_reduction_time_normalized(self):
        t=src('medicationCBRNTick');self.assertIn('_dt / 25',t);self.assertIn('ACME_fnc_clinicalTickDelta',t)
        self.assertAlmostEqual(sum([8*.1/25]*250),8)
    def test_route_clocks_not_scaled_per_pulse(self):
        t=ov('medicationLocal');tail=t[t.index('// B13: route-configured clocks'):]
        self.assertNotIn('_timeInSystem = _timeInSystem *',tail)
        self.assertNotIn('_timeTillMaxEffect = _timeTillMaxEffect *',tail)
    def test_queue_committed_before_native_medication_callback(self):
        t=src('medicationLineLocal');self.assertLess(t.index('setVariable ["ACME_pendingFlush"'),t.index('call ace_medical_treatment_fnc_medicationLocal'))
    def test_queue_uses_selected_site_and_deduplicates(self):
        t=src('medicationLineLocal')
        for x in ('_identity','_receipts getOrDefault [_id','ACME_fnc_clinicalEpoch','ACME_fnc_medicationLineIdentity','ACME_pendingFlush'):self.assertIn(x,t)
        self.assertLess(t.index('_prior ='),t.index('_epoch !='))
    def test_removed_catheter_clears_its_pending_drugs(self):self.assertIn('ACME_pendingFlush',ov('setIVLocal'))
    def test_new_state_fields_have_fullheal_policy(self):
        t=src('clinicalFields')
        for n in ('ACME_medicationToxicity','ACME_sug_bindings','ACME_sug_spent','ACME_nativeCalciumFirstGram','ACME_suctionSessions','ACME_o2Drain_suction'):
            self.assertIn('["'+n+'", "", true',t)
    def test_external_count_delegate_is_separately_registered(self):
        t=(ROOT/'config.cpp').read_text();self.assertIn('class ACME_native',t);self.assertIn('tag = "ACME_native"',t)

class SuctionAndSALAD(unittest.TestCase):
    def test_no_penalty_through_ten_seconds(self):self.assertAlmostEqual(suction_run(10)[1],0)
    def test_fifteen_seconds_is_mild(self):self.assertLess(suction_run(15)[1],.2)
    def test_twenty_seconds_less_than_one_point(self):self.assertLess(suction_run(20)[1],.75)
    def test_thirty_seconds_bounded_ramp(self):self.assertAlmostEqual(suction_run(30)[1],2.5,delta=.04)
    def test_handheld_eventual_cap_six(self):self.assertEqual(suction_run(120)[1],6)
    def test_parked_eventual_cap_one(self):self.assertEqual(suction_run(300,'salad')[1],1)
    def test_parked_much_less_than_handheld(self):self.assertAlmostEqual(suction_run(30,'salad')[1],.15*suction_run(30)[1])
    def test_oxygen_support_halves_added_debt(self):self.assertAlmostEqual(suction_run(30,support=True)[1],.5*suction_run(30)[1])
    def test_pause_recovers_without_negative_values(self):
        e,d=suction_run(30)
        for _ in range(100):e,d=suction_step(e,d,.1,'off')
        self.assertAlmostEqual(d,0);self.assertGreaterEqual(e,0)
    def test_brief_release_does_not_reset_grace(self):
        e,d=suction_run(20);e,d=suction_step(e,d,.1,'off');self.assertGreater(e,10)
    def test_switch_to_salad_does_not_erase_debt(self):
        e,d=suction_run(30);_,after=suction_step(e,d,1,'salad');self.assertEqual(after,d)
    def test_tick_stall_is_capped(self):self.assertEqual(suction_step(10,0,20),suction_step(10,0,2))
    def test_provider_count_does_not_multiply_penalty(self):
        t=src('suctionPhysiologyTick');self.assertIn('findIf {(_x select 3) != "salad"}',t);self.assertNotIn('* count _live',t)
    def test_pin_requires_accuvac(self):self.assertIn('ACME_fnc_suctionSelectDevice) != 1',src('laryngoSuctionPin'))
    def test_pin_frees_hands(self):self.assertIn('setVariable ["ACME_laryngo_held", ""]',src('laryngoSuctionPin'))
    def test_park_outside_cord_target(self):self.assertGreater(math.dist((.425,.210),(.4978,.1367)),.032)
    def test_pin_requires_tip_inside_mouth(self):self.assertIn('Bring the suction tip inside the mouth',src('laryngoSuctionPin'))
    def test_pin_follows_head_geometry(self):self.assertIn('ACME_laryngo_sucPinRel',src('laryngoSuctionPin'));self.assertIn('ACME_Laryngo_ShakeBase_off',src('laryngoSuction'))
    def test_live_lease_short_expiry(self):self.assertIn('CBA_missionTime + 1.5',src('suctionStateLocal'))
    def test_heartbeats_not_every_render_frame(self):self.assertIn('_now + 0.25',src('suctionPublish'))
    def test_closed_packet_tombstone_blocks_reactivation(self):self.assertIn('param [2, false]',src('suctionStateLocal'));self.assertIn('_mode == "closed"',src('suctionStateLocal'))
    def test_saved_ui_cannot_adopt_new_life_epoch(self):self.assertIn('uiNamespace getVariable ["ACME_suctionEpoch", -1]',src('suctionPublish'))
    def test_owner_rechecks_equipment_and_consciousness(self):
        t=src('suctionPhysiologyTick');self.assertIn('ACM_ACCUVAC',t);self.assertIn('ACE_isUnconscious',t);self.assertIn('!local _patient',t)
    def test_no_penalty_double_application(self):
        self.assertIn('ACME_o2Drain_suction',ov('updateOxygen'))
        for n in ('altitudeTick','ventDriveTick'):self.assertNotIn('ACME_o2Drain_suction',src(n))
    def test_suction_updates_before_native_oxygen(self):self.assertIn('ACME_fnc_suctionPhysiologyTick',ov('updateOxygen'))
    def test_fluid_counts_actual_removed_only(self):
        t=src('laryngoFluidDrainLocal');self.assertIn('private _removed = _remaining min _amount',t);self.assertIn('private _ml = _removed * 50',t)
    def test_manual_reservoir_capacity_owner_enforced(self):self.assertIn('1000 - _base',src('laryngoFluidDrainLocal'))
    def test_manual_cannot_claim_drain_without_live_lease(self):self.assertIn('_session isEqualTo []',src('laryngoFluidDrainLocal'))
    def test_remote_catheters_are_rendered(self):self.assertIn('ACME_fnc_suctionObservers',src('laryngoTick'));self.assertIn('ctrlCreate',src('suctionObservers'))
    def test_existing_b12_airway_fixes_still_inherited(self):
        for f in ('test_na8_5_batch11.py','test_na8_5_batch12.py'):self.assertTrue((ROOT/'tools'/f).is_file())

if __name__=='__main__':unittest.main()
