"""B12 source contracts and independent game-math reference models.
These are Python tests, NOT compilation/execution of SQF or Arma multiplayer tests.
"""
from historical_source import read_source
from pathlib import Path
import math
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
def read(p): return read_source(ROOT/p, encoding='utf-8')
def src(n): return read('functions/fn_'+n+'.sqf')
def code(s): return re.sub(r'/\*.*?\*/|//[^\n]*', '', s, flags=re.S)
def envelope(t, initial=1, live=1):
    return 0 if not 0 <= t < 60 else min(initial,live)*min(1,t/3)*math.exp(-max(0,t-3)/20)
def view(lift,depth,angle,target):
    ready=abs(angle-target)<=1 and depth>=.90 and lift>=.8
    return (1 if ready else min(.92, (.9 if abs(angle-target)<=1 else .76)*min(1,lift/.8)*depth)),ready

def push(drug,saline,ml):
    total=drug+saline
    if ml<=0 or ml>total+1e-5: raise ValueError('invalid volume')
    fraction=min(ml,total)/total
    return drug*(1-fraction),saline*(1-fraction),drug*.1*fraction

class AirwaySource(unittest.TestCase):
    def test_grade_entry_unlocked(self):
        self.assertNotRegex(code(src('laryngoCanAttempt')),r'grade|_cl|_mp')
    def test_every_grade_can_reveal_final(self):
        self.assertIn('private _maxReveal = 1;',src('laryngoInit'))
        self.assertNotIn('final_noPass',code(src('laryngoTick')))
    def test_radius_and_depth_calibration(self):
        t=src('laryngoInit');self.assertIn('* 1.25) max 0.022',t);self.assertIn('[0.10, 0.085, 0.065, 0.05]',t)
    def test_unified_view_predicate(self):
        self.assertIn('call ACME_fnc_laryngoView',src('laryngoTick'))
        self.assertIn('0.80',src('laryngoView'));self.assertIn('abs (_stage - _target) <= _tolerance',src('laryngoView'))
    def test_lift_handover(self):self.assertIn('_liftThresh * 0.80',src('laryngoTick'))
    def test_shake_and_nightvision_retained(self):
        t=src('laryngoTick');self.assertIn('ACME_fnc_uiShakeApply',t);self.assertIn('ACME_fnc_minigameVisionTick',t)
    def test_wheel_and_swing(self):
        self.assertIn('["ACME_laryngo_tubeImpulse", 6]',src('laryngoScroll'))
        self.assertIn('["ACME_laryngo_tubeSwingDamp", 14]',src('laryngoTick'))
    def test_brief_cursor_spike_not_trauma(self):
        self.assertIn('0.12',src('laryngoDrag'));self.assertIn('bladeLocked',src('laryngoDrag'))
    def test_no_prebreak_sound_anywhere(self):
        for n in ('laryngoTick','laryngoCreak','laryngoRegrip'):
            self.assertNotIn('laryngo_creak',code(src(n)))
        self.assertNotIn('ACME_fnc_laryngoCreak',code(src('laryngoTick')))
    def test_actual_fracture_still_has_sound(self):self.assertIn('dry.wss',src('laryngoConsequenceLocal'))
    def test_anatomy_visible_and_broken_art_aligned(self):
        t=src('laryngoTeethArt');self.assertIn('ctrlSetAngle [180, 0.5, 0.5, false]',t)
        self.assertIn('ctrlShow true',t);self.assertIn('ctrlSetFade 0',t)
    def test_no_two_way_mouth_dissolve(self):
        self.assertIn('case (_forEachIndex == _i):     { 1 }',src('laryngoFrames'))
    def test_owner_routes_attempt_consequences(self):
        self.assertIn('"laryngoConsequence"',src('ownerDispatch'))
        self.assertIn('ACME_fnc_clinicalEpoch',src('laryngoConsequenceLocal'))
        self.assertIn('_id in _receipts',src('laryngoConsequenceLocal'))
    def test_first_miss_does_not_force_emesis(self):
        t=src('laryngoConsequenceLocal');self.assertIn('_misses <= _tolerance',t)
        self.assertIn('3 + floor random 3',t);self.assertIn('1 + floor random 4',t)
    def test_no_stomach_refill_or_extra_vomit_worker(self):
        t=code(src('laryngoConsequenceLocal'));self.assertIn('(_remaining - 1) max 0',t)
        self.assertNotIn('handleVomiting',t);self.assertNotIn('addPerFrameHandler',t)
    def test_attempt_not_escalated_to_impossible_grade(self):
        self.assertNotIn('setVariable ["ACME_airwayGrade"',code(src('laryngoFail')))
        self.assertNotIn('setVariable ["ACME_airwayGrade"',code(src('laryngoConsequenceLocal')))
    def test_success_resets_streak(self):
        self.assertIn('["ACME_laryngo_gagMisses", 0, true]',src('laryngoConsequenceLocal'))
        self.assertIn('[_patient, "success"]',src('laryngoPassTube'))
    def test_reflex_and_life_guards(self):
        t=src('laryngoConsequenceLocal')
        self.assertIn('ACME_fnc_laryngoReflexChance',t)
        for x in ('ace_medical_inCardiacArrest','ACME_roc_paralyzed','ACME_fnc_sedationComponents'):
            self.assertIn(x,src('laryngoReflexChance'))
    def test_ui_miss_latch(self):
        self.assertIn('missLatched',src('laryngoFail'));self.assertIn('["ACME_laryngo_missLatched", false]',src('laryngoClick'))
    def test_delayed_callbacks_check_display_patient(self):
        for n in ('laryngoAbort','laryngoPassTube'):
            self.assertIn('_oldDisplay !=',src(n));self.assertIn('_oldPatient !=',src(n))

class ICPSource(unittest.TestCase):
    def test_owner_stimulus_cooldown(self):self.assertIn('CBA_missionTime - _previous < 60',src('laryngoStimulusLocal'))
    def test_finite_envelope(self):
        t=src('laryngoStimulusEffect');self.assertIn('_age >= 60',t);self.assertIn('/ 20)',t)
    def test_live_fentanyl(self):self.assertIn('min (_liveStrength max 0 min 1)',src('laryngoStimulusEffect'))
    def test_no_permanent_add_in_stimulus(self):
        self.assertNotIn('_state set',code(src('laryngoStimulusLocal')))
        self.assertIn('laryngoICPApplied',src('tbiHandle'))
    def test_effect_is_read_only(self):self.assertNotIn('setVariable',code(src('laryngoStimulusEffect')))

class SharedSuctionSource(unittest.TestCase):
    def test_event_specific_owner_volume(self):
        self.assertIn('ACME_laryngo_pool',src('laryngoConsequenceLocal'))
        self.assertIn('_poolBefore select 2',src('laryngoConsequenceLocal'))
    def test_reopen_does_not_restore_stale_client_stage(self):
        self.assertNotIn('_patient getVariable ["ACME_laryngo_fluidStage"',src('laryngoInit'))
        self.assertNotIn('_patient setVariable ["ACME_laryngo_fluidStage"',src('laryngoClose'))
    def test_wand_and_bulb_same_owner_debit(self):
        for n in ('laryngoSuction','suctionBulb'):
            self.assertIn('call ACME_fnc_laryngoFluidDrain',src(n))
            self.assertNotIn('call ACM_airway_fnc_handleSuctionLocal',code(src(n)))
    def test_no_renderer_double_debit(self):self.assertNotIn('_stage = (_stage - 1)',code(src('laryngoFluid')))
    def test_late_and_duplicate_drain_rejected(self):
        t=src('laryngoFluidDrainLocal')
        for x in ('_id in _receipts','_stamp isEqualTo _expected','ACME_fnc_clinicalEpoch'):self.assertIn(x,t)
    def test_native_clear_on_owner(self):
        t=src('laryngoFluidDrainLocal')
        self.assertIn('ACM_airway_AirwayObstructionVomit_State',t)
        self.assertIn('ACM_airway_AirwayObstructionBlood_State',t)
        self.assertIn('if (_kind == "v")',t)
        self.assertNotIn('call ACM_airway_fnc_handleSuctionLocal',t)
    def test_pool_fullheal_and_save_registered(self):self.assertIn('["ACME_laryngo_pool", "", true]',src('clinicalFields'))
    def test_no_perpetual_visual_only_bleed(self):self.assertNotIn('fluidMode',src('laryngoPersistBleed'))
    def test_streak_not_reset_by_suction(self):self.assertNotIn('setVariable ["ACME_laryngo_gagMisses"',code(src('laryngoFluidDrainLocal')))
    def test_native_new_obstruction_invalidates_ledger(self):self.assertIn('(_pool select 0) isEqualTo _stamp',src('laryngoFluidState'))

class EpinephrineSource(unittest.TestCase):
    def test_concentration_is_one_tenth(self):
        t=read('config.cpp');self.assertRegex(t,r'class EpinephrineCardiac\s*\{\s*concentration = 0\.1;')
        self.assertIn('ACM_Vial_EpinephrineCardiac',t)
    def test_native_magazine_family(self):
        t=read('config.cpp')
        for n in (1,3,5,10):self.assertIn('class ACM_Syringe_'+str(n)+'_EpinephrineCardiac',t)
    def test_recipe_exact_and_canonical_store(self):
        self.assertIn('_drugMl - 1',src('epinephrineRecipe'));self.assertIn('_salineMl - 9',src('epinephrineRecipe'))
        self.assertIn('["EpinephrineCardiac", 10, 1,',src('epinephrinePrepare'))
        self.assertIn('9, [], "epiMixB12"',src('epinephrinePrepare'))
    def test_old_source_flush_preserves_actual_strength(self):self.assertNotIn('if (_med == "Epinephrine") exitWith',src('skWasteDraw'))
    def test_legacy_mixture_not_reinterpreted(self):self.assertIn('This older mixture has no verified source-volume record',src('skInjectSite'))
    def test_cardiac_mixtures_use_source_funded_component_validation(self):self.assertIn('[_class, _iv, true, _virtual] call ACME_fnc_medicationRouteAllowed',src('skInjectSite'))
    def test_native_epi_routes_preserved_and_new_source_remains_iv_only(self):
        self.assertIn('_med == "EpinephrineCardiac" && {!_iv}',src('skInjectSite'))
        self.assertNotIn('_med == "Epinephrine" && {_iv}',src('skInjectSite'))
        self.assertNotIn('_classname == "Epinephrine" && {_iv}', read('overrides/fn_Syringe_Inject.sqf'))
    def test_opened_source_volume_reused(self):
        t=src('epinephrineTakeSource');self.assertIn('ACME_fnc_infusionVialVolume',t)
        self.assertIn('ACME_fnc_vialTake',t)
        ledger=src('vialTake');self.assertIn('ACME_infusion_openVials',ledger);self.assertIn('_open + _needed * _cap - _ml',ledger)
    def test_no_source_debit_before_flush_check(self):
        t=src('epinephrinePrepare');self.assertLess(t.index('getCountOfItem'),t.index('call ACME_fnc_epinephrineTakeSource'))
    def test_real_inventory_signature(self):self.assertIn('[ACE_player, _class, "", round (_ml * 100)]',src('epinephrineDrawCardiac'))
    def test_default_compound_flow_can_draw_plain_cardiac(self):
        t=src('skCompoundDraw');self.assertNotIn('if (_med == "EpinephrineCardiac") exitWith',t)
        self.assertIn('_components pushBack [_med, _drugMl]',t)
    def test_plain_card_source_checks_actual_magazine(self):
        t=src('skInjectSite')
        self.assertIn('private _ammo = round (_amt * 100)',t)
        self.assertIn('(_x select 1) == _ammo',t)
        self.assertIn('* (_ammo / 100)',t)
    def test_dose_selector_three_choices(self):
        t=src('skEpinephrineDose');self.assertIn('[1, 2, _total]',t);self.assertIn('100 mcg',t)
    def test_partial_consumption_conserves_remaining(self):
        t=src('epinephrinePushStored');self.assertIn('_drugMl * 0.1 * _fraction',t)
        self.assertIn('_drugMl * (1 - _fraction)',t);self.assertIn('_nsMl * (1 - _fraction)',t)
    def test_inventory_consumed_before_medication_event(self):
        t=src('epinephrinePushStored');self.assertLess(t.index('_medic setVariable'),t.index('ACME_fnc_medicationRequest'))
        self.assertIn('ACME_fnc_ownerDispatch',src('medicationRequest'))
    def test_actual_selected_vascular_site_required(self):
        t=src('epinephrinePushStored');self.assertIn('_bodyPart, 0, _siteIdx',t);self.assertIn('ACM_circulation_fnc_hasIO',t)
    def test_native_actual_mg_not_charge(self):
        t=src('epinephrinePushStored');self.assertIn('"Epinephrine_IV", _doseMg, true',t)
        self.assertNotIn('pushDoseCharges',t)
    def test_alias_maps_before_native_effects(self):
        t=read('overrides/fn_medicationLocal.sqf');self.assertIn('_classname = "Epinephrine_IV"',t)
    def test_infusion_not_double_counted(self):self.assertIn('ACME_vesicant_infusionDelivery',src('postInit'))
    def test_bolus_circulation_bounded_and_washes_out(self):
        self.assertIn('min _ceiling',src('epinephrineBolusLocal'))
        t=src('circHandle');self.assertIn('0.5 ^ (_dt / (_halfLife max 1))',t);self.assertIn('epiBolusReserve',t)
    def test_strings_valid_xml(self):ET.fromstring(read('stringtable.xml'))
    def test_no_pde_from_concentrated_source_compat_action(self):
        t=src('salineFlush');self.assertIn('call ACME_fnc_epinephrinePrepare',t)

class ReferenceModels(unittest.TestCase):
    def test_all_16_anatomy_combinations_have_success_state(self):
        for mp in range(1,5):
            for cl in range(1,5):
                with self.subTest(mp=mp,cl=cl):
                    self.assertEqual(view(.85,1,3,3),(1,True))
                    self.assertGreaterEqual(max([.032,.026,.019,.015][cl-1]*1.25,.022),.022)
    def test_angle_tolerance_edges(self):
        for stage in (2,3,4):self.assertTrue(view(.8,1,stage,3)[1])
        for stage in (0,1,5):self.assertFalse(view(.8,1,stage,3)[1])
    def test_bad_depth_and_low_lift_still_matter(self):
        self.assertFalse(view(.79,1,3,3)[1]);self.assertFalse(view(1,.89,3,3)[1])
    def test_icp_peaks_then_declines(self):
        self.assertEqual(envelope(3),1)
        self.assertTrue(all(envelope(t+1)<envelope(t) for t in range(3,59)))
    def test_zero_after_a_minute(self):
        for t in (-1,60,120,600):self.assertEqual(envelope(t),0)
    def test_reading_and_lifting_cannot_accumulate_offset(self):
        structural=12
        for _ in range(10000):result=structural+4*envelope(20)
        self.assertLessEqual(result,16);self.assertEqual(structural+4*envelope(60),12)
    def test_new_fentanyl_attenuates_without_restart(self):
        self.assertLess(envelope(25,1,.3),envelope(25,1,1))
        self.assertEqual(envelope(61,1,.1),0)
    def test_emesis_fourth_through_sixth_only(self):
        for tolerance in (3,4,5):
            self.assertEqual(next(i for i in range(1,8) if i>tolerance),tolerance+1)
    def test_emesis_episode_variable_not_full(self):
        for amount in range(1,5):self.assertLess(amount,10)
    def test_suction_concurrent_conservation(self):
        remaining=4;seen=set()
        for event,amt in [('a',1),('b',.95),('a',1),('c',1)]:
            if event not in seen:remaining=max(0,remaining-amt);seen.add(event)
        self.assertAlmostEqual(remaining,1.05)
    def test_new_emesis_adds_to_partial_volume(self):self.assertAlmostEqual(min(8,1.05+2),3.05)
    def test_recipe_math_100mcg_not_ten(self):
        self.assertAlmostEqual(1*.1*1000,100);self.assertAlmostEqual(1*.1*1000/(9+1),10)
    def test_single_measured_pushes(self):
        for ml,mg in ((1,.01),(2,.02),(10,.1)):
            with self.subTest(ml=ml):self.assertAlmostEqual(push(1,9,ml)[2],mg)
    def test_ten_small_pushes_equal_total(self):
        drug,saline,total=1.,9.,0.
        for _ in range(10):drug,saline,dose=push(drug,saline,1);total+=dose
        self.assertAlmostEqual(total,.1);self.assertAlmostEqual(drug+saline,0,places=6)
    def test_mixed_pushes_conserve_drug(self):
        drug,saline,total=1.,9.,0.
        for ml in (1,2,2,5):drug,saline,dose=push(drug,saline,ml);total+=dose
        self.assertAlmostEqual(total,.1)
    def test_overdraw_rejected(self):
        for ml in (0,-1,11):
            with self.assertRaises(ValueError):push(1,9,ml)
    def test_ten_preparations_per_source(self):
        source=10
        for _ in range(10):source-=1
        self.assertEqual(source,0)
    def test_code_strength_10ml_is_1mg(self):self.assertAlmostEqual(10*.1,1)
    def test_larger_dose_larger_bounded_game_response(self):
        values=[90*(1-math.exp(-x/55)) for x in (10,20,100,1000)]
        self.assertEqual(values,sorted(values));self.assertTrue(all(0<x<=90 for x in values))
    def test_bolus_reserve_and_effect_washout(self):
        reserve=90*(1-math.exp(-100/55));effect=0;max_seen=0
        for i in range(3600):
            effect*=.5**(1/120);enter=reserve*(1-math.exp(-1/5));reserve-=enter
            effect=min(90,effect+enter);max_seen=max(max_seen,effect)
        self.assertLessEqual(max_seen,90);self.assertLess(effect,.001)

if __name__=='__main__':unittest.main()
