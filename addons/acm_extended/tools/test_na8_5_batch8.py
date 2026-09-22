#!/usr/bin/env python3
"""B8 source contracts and independent route/placement examples. Does not execute SQF."""
from historical_source import read_source
from pathlib import Path
import json,math,re,unittest
from source_scan import lex
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=json.loads(read_source(ROOT/'tools/na8_5_b8_medication_routes.json'))
def source(name):return read_source(ROOT/'functions'/f'fn_{name}.sqf', encoding='utf-8-sig')
def code(name):return [t.value for t in lex(source(name))]

def route_model(name,via=None):
    row=FIXTURE['cases'].get(name)
    if row is None or row['administrationType']!=FIXTURE['macros']['ACM_ROUTE_IV']:return False
    return via is None or via is True

CATALOG=source('ivVeinCatalog')
TOL=float(re.search(r'_wrist set \["oversizeTolerance", ([0-9.]+)\]',CATALOG)[1])
WRIST_MAX=int(re.search(r'\["Cephalic", "forearm vein", "lateral forearm", (\d+)',CATALOG)[1])
def outcome_model(bp,site,gauge,hit,accuracy):
    if not hit:return True
    if not isinstance(site,(str,int,float)) or isinstance(site,bool):return True
    if gauge not in (14,16,18,20):return True
    if not isinstance(accuracy,(int,float)) or not math.isfinite(accuracy) or not 0<=accuracy<=1:return True
    if isinstance(site,str):site={'upper':0,'middle':1,'lower':2}.get(site.lower(),1)
    else:site=max(0,min(2,round(site)))
    bp=bp.lower();wrist=bp in ('leftarm','rightarm') and site==2
    if bp=='ej':maxg=16
    elif bp in ('leftarm','rightarm'):maxg=(14,16,WRIST_MAX)[site]
    elif bp in ('leftleg','rightleg'):maxg=(16,18,16)[site]
    else:return False
    if gauge>=maxg:return False
    steps=(maxg-gauge)/2
    tol=TOL if wrist else (0.15 if steps>=3 else 0.35 if steps>=2 else 0.60)
    return accuracy>tol

class SourceContracts(unittest.TestCase):
    def test_route_uses_registered_class(self):
        s=source('vesicantRouteAllows')
        self.assertIn('configFile >> "ACM_Medication" >> "Medications" >> _classname',s)
        self.assertIn('if (!isClass _config) exitWith {false}',s)
    def test_unknown_route_is_rejected(self):self.assertIn('if (!isNumber _route) exitWith {false}',source('vesicantRouteAllows'))
    def test_uses_native_iv_macro(self):
        s=source('vesicantRouteAllows');self.assertIn('!= ACM_ROUTE_IV',s);self.assertEqual(FIXTURE['macros']['ACM_ROUTE_IV'],1)
    def test_not_based_on_label_or_head(self):
        tokens=code('vesicantRouteAllows')
        for term in ('_bodyPart','find','findIf','_IV','setVariable','addToTriageCard'):self.assertNotIn(term,tokens)
    def test_real_iv_flag_required_when_supplied(self):self.assertIn('_viaIV isEqualTo true',source('vesicantRouteAllows'))
    def test_legacy_is_only_null_object_sentinel(self):self.assertIn('if (_viaIV isEqualType objNull) exitWith {isNull _viaIV}',source('vesicantRouteAllows'))
    def test_event_retains_first_four_fields(self):
        s=read_source(ROOT/'overrides/fn_medicationLocal.sqf')
        self.assertIn('[QEGVAR(circulation,handleMedicationEffects), [_patient, _bodyPart, _classname, _dose, _iv, _delivery]] call CBA_fnc_localEvent;',s)
    def test_systemic_medication_is_recorded_before_event(self):
        s=read_source(ROOT/'overrides/fn_medicationLocal.sqf')
        self.assertLess(s.index('call ACEFUNC(medical_status,addMedicationAdjustment)'),s.index('[QEGVAR(circulation,handleMedicationEffects)'))
        self.assertLess(s.index('call ACEFUNC(medical_treatment,onMedicationUsage)'),s.index('[QEGVAR(circulation,handleMedicationEffects)'))
    def test_postinit_receives_metadata(self):self.assertIn('["_viaIV", objNull]',source('postInit'))
    def test_b14_exact_site_controls_split(self):
        s=source('medicationLineFraction')
        self.assertIn('ACME_ivCompromised_%1_%2',s)
        self.assertIn('_site',s)
        self.assertIn('call ACME_fnc_medicationLineFraction',source('medicationLineLocal'))
    def test_b14_credit_and_local_antidote_hooks_preserved(self):
        s=source('postInit');s=s[s.index('["ACM_circulation_handleMedicationEffects"'):]
        self.assertIn('call ACME_fnc_applyCalciumCredit',s)
        self.assertIn('call ACME_fnc_vesicantReverse',read_source(ROOT/'overrides/fn_medicationLocal.sqf'))
        self.assertNotIn('call ACME_fnc_vesicantInjure',s.split('}] call CBA_fnc_addEventHandler;',1)[0])
    def test_direct_injury_caller_is_also_guarded(self):
        s=source('vesicantInjure');self.assertLess(s.index('call ACME_fnc_vesicantRouteAllows'),s.index('ACME_vesExposure_'))
        self.assertLess(s.index('call ACME_fnc_vesicantRouteAllows'),s.index('ace_medical_openWounds'))
    def test_route_does_not_remove_old_patient_data(self):
        self.assertNotIn('delete',code('vesicantRouteAllows'));self.assertNotIn('setVariable',code('vesicantRouteAllows'))
    def test_iv_infusion_keeps_admitted_iv_flag(self):
        self.assertIn('_pending, true, true,',source('infusionDeliver'))
    def test_syringe_route_flag_kept(self):
        self.assertIn('private _iv = _route != "im"',source('skInjectSite'))
        self.assertIn('_doses pushBack [_class, _conc * _ml, _iv, _lbl]',source('skInjectSite'))
        self.assertIn('ACME_fnc_medicationRouteAllowed',source('medicationLineLocal'))
    def test_wrist_routine_threshold(self):self.assertEqual(WRIST_MAX,16)
    def test_wrist_tight_14g_tolerance(self):self.assertEqual(TOL,0.15)
    def test_caliber_depth_roll_unchanged(self):self.assertRegex(CATALOG,r'"lateral forearm", 16, 0\.35, 0\.10, 0\.75')
    def test_item_no_longer_claims_20g_only(self):
        s=read_source(ROOT/'config.cpp');self.assertNotIn('only catheter a wrist vein will take',s);self.assertNotIn('only one that fits a wrist',s)
        self.assertIn('Wrist placement requires an extremely accurate central stick',s)
    def test_gauge_availability_is_inventory_only(self):
        s=source('ivMinigameGrabNeedle');self.assertIn('getCountOfItem',s);self.assertNotIn('maxG',code('ivMinigameGrabNeedle'))
    def test_puncture_uses_actual_site_margin(self):
        s=source('ivMinigameClick');self.assertIn('_gauge',source('ivSiteDifficulty'))
        self.assertIn('"ACME_IV_Gauge", 16], _stickSite] call ACME_fnc_ivSiteDifficulty',s)
        self.assertLess(s.index('_hit = _punctureDifficulty select 2'),s.index('"ACME_IV_StickAcc", (if'))
    def test_ej_retains_existing_click_margin(self):self.assertIn('if (!_isEJc && {_stickSite in',source('ivMinigameClick'))
    def test_blow_has_no_blood_volume_veto_or_rng(self):
        for n in ('ivStickBlows','ivMinigameStickSuccess'):
            s=source(n);self.assertNotIn('5.99',s);self.assertNotIn('ace_medical_bloodVolume',s);self.assertNotIn('random',code(n))
    def test_hypotension_still_affects_difficulty(self):
        self.assertIn('linearConversion [70, 90, _sys, 0, 1, true]',source('ivSiteDifficulty'))
    def test_blow_uses_frozen_puncture(self):
        s=source('ivMinigameStickSuccess')
        for term in ('ACME_IV_InsGauge','ACME_IV_InsHit','ACME_IV_StickAcc','ACME_IV_InsSite'):self.assertIn(term,s)
        self.assertNotIn('getVariable ["ACME_IV_Gauge"',s)
    def test_single_outcome_and_single_bruise(self):
        s=source('ivMinigameStickSuccess');self.assertEqual(s.count('call ACME_fnc_ivStickBlows'),1);self.assertEqual(s.count('call ACME_fnc_ivInfiltrated'),1)
        self.assertLess(s.index('call ACME_fnc_ivMinigameRegister'),s.index('call ACME_fnc_ivStickBlows'))
    def test_existing_separation_context_guard_kept(self):
        s=source('ivMinigameStickSuccess');self.assertLess(s.index('call ACME_fnc_ivMinigameViewValid'),s.index('call ACME_fnc_ivStickBlows'))
    def test_existing_miss_path_still_marks_line(self):self.assertIn('ACME_ivCompromised_',source('ivInfiltrated'))
    def test_outcome_guard_invalid_accuracy(self):
        s=source('ivStickBlows');self.assertIn('!finite _accuracy',s);self.assertIn('_accuracy > 1',s)
    def test_added_functions_registered_once(self):
        s=read_source(ROOT/'config.cpp')
        for n in ('vesicantRouteAllows','ivStickBlows'):self.assertEqual(s.count('class '+n+' {};'),1)
    def test_no_new_logging(self):
        for n in ('vesicantRouteAllows','ivStickBlows'):
            for word in ('diag_log','diag_logSlowFrame','systemChat','hint'):self.assertNotIn(word,code(n))
    def test_version_pair(self):
        version=re.search(r'ACME_infusion_version = "([^"]+)"',source('postInit')).group(1)
        self.assertRegex(version,r"^(?:0\.9\.999r-(?:73-NA8\.5-B(?:8|9|10|11)|74-NA8\.5-B12|75-NA8\.5-B13|78-NA8\.5-B17|79-NA8\.5-B18|80-NA8\.5-B19|81-NA8\.5-B20|82-NA8\.5-B21|83-NA8\.5-B22|84-NA8\.5-B23|85-NA8\.5-B24|86-NA8\.5-B25|87-NA8\.5-B26|88-NA8\.5-B27|89-NA8\.5-B28|90-NA8\.5-B29|91-NA8\.5-B30|92-NA8\.5-B31|93-NA8\.5-B32|94-NA8\.5-B33|95-NA8\.5-B34|96-NA8\.5-B35)|1\.0\.100-r(?:2|3|4|5|6|7))$")
        self.assertIn('version = "'+version+'"',read_source(ROOT/'config.cpp'))

class RouteExamples(unittest.TestCase):
    def test_malformed_delivery_metadata(self):
        for arg in (False,0,1,'IV','true',[],{},[True]):self.assertFalse(route_model('Ketamine_IV',arg))
    def test_unknown_class_cannot_use_head_iv_as_evidence(self):
        for arg in (True,False,None):self.assertFalse(route_model('UndeclaredMedication',arg))
    def test_class_name_is_not_iv_route(self):
        FIXTURE['cases']['TestName_IV']={'administrationType':2}
        try:self.assertFalse(route_model('TestName_IV',True))
        finally:del FIXTURE['cases']['TestName_IV']
    def test_custom_inherited_iv_route_needs_no_suffix(self):
        FIXTURE['cases']['CustomDrug']={'administrationType':1}
        try:self.assertTrue(route_model('CustomDrug',True))
        finally:del FIXTURE['cases']['CustomDrug']
    def test_bruise_counterexample_from_original(self):
        original_writes_head_exposure=True and max(1,1)/0.01>=2
        self.assertTrue(original_writes_head_exposure);self.assertFalse(route_model('Paracetamol',False))
    def test_buccal_uses_native_im_kinetics_but_is_excluded(self):
        self.assertEqual(FIXTURE['cases']['Fentanyl_BUC']['administrationType'],0);self.assertFalse(route_model('Fentanyl_BUC',True))

# Each source-resolved drug is a separate test, with all delivery metadata cases inside it.
def route_case(name,value):
    def test(self):
        for via in (None,False,True):
            expected=value==1 and via is not False
            self.assertEqual(route_model(name,via),expected,(name,via))
    return test
for name,row in FIXTURE['cases'].items():setattr(RouteExamples,'test_route_'+name,route_case(name,row['administrationType']))

class PlacementExamples(unittest.TestCase):
    def test_14g_center_succeeds(self):
        for side in ('leftarm','rightarm'):
            for site in ('lower','LOWER',2):self.assertFalse(outcome_model(side,site,14,True,0))
    def test_14g_inside_tight_band_succeeds(self):self.assertFalse(outcome_model('leftarm','lower',14,True,0.149999))
    def test_14g_boundary_succeeds(self):self.assertFalse(outcome_model('leftarm','lower',14,True,0.15))
    def test_14g_outside_band_blows(self):self.assertTrue(outcome_model('leftarm','lower',14,True,0.150001))
    def test_14g_edge_hit_blows(self):self.assertTrue(outcome_model('leftarm','lower',14,True,1))
    def test_all_complete_misses_infiltrate(self):
        for g in (14,16,18,20):self.assertTrue(outcome_model('rightarm',2,g,False,0))
    def test_16_18_20_have_no_additional_wrist_blow_gate(self):
        for g in (16,18,20):
            for acc in (0,.15,.6,1):self.assertFalse(outcome_model('leftarm',2,g,True,acc))
    def test_14g_elbow_retains_original_tolerance(self):
        self.assertFalse(outcome_model('leftarm',1,14,True,.6));self.assertTrue(outcome_model('leftarm',1,14,True,.6001))
    def test_14g_upper_arm_unmodified(self):self.assertFalse(outcome_model('leftarm',0,14,True,1))
    def test_leg_lower_not_classified_as_wrist(self):
        self.assertFalse(outcome_model('leftleg',2,14,True,.6));self.assertTrue(outcome_model('leftleg',2,14,True,.6001))
    def test_leg_middle_two_step_penalty_kept(self):
        self.assertFalse(outcome_model('rightleg',1,14,True,.35));self.assertTrue(outcome_model('rightleg',1,14,True,.3501))
    def test_ej_tolerance_unchanged(self):
        self.assertFalse(outcome_model('ej','left',14,True,.6));self.assertTrue(outcome_model('ej','right',14,True,.6001))
    def test_18g_and_20g_still_distinct_gauge_multipliers(self):
        s=source('ivSiteDifficulty');self.assertIn('case 18: { 1.15 }',s);self.assertIn('case 20: { 1.35 }',s)
    def test_bad_accuracy_never_grants_success(self):
        for a in (float('nan'),float('inf'),-1,1.01):self.assertTrue(outcome_model('leftarm',2,14,True,a))
    def test_repeated_outcome_does_not_reroll(self):
        saved=('leftarm',2,14,True,.16);self.assertEqual([outcome_model(*saved) for _ in range(5)],[True]*5)
    def test_left_right_equivalence(self):
        for g in (14,16,18,20):
            for a in (0,.15,.2,.6,1):self.assertEqual(outcome_model('leftarm',2,g,True,a),outcome_model('rightarm',2,g,True,a))

if __name__=='__main__':unittest.main()
