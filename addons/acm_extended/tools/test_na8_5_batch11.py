"""B11 source contracts and independent numerical/lifecycle reference models.
These tests do not compile or execute SQF and do not replace Arma multiplayer tests.
"""
from historical_source import read_source
from pathlib import Path
import math
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT / rel, encoding='utf-8')
def src(name): return read('functions/fn_' + name + '.sqf')
def code(text): return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
def offset(age, strength=1):
    if age < 0 or age >= 60: return 0
    return min(1,max(0,strength)) * min(1,age/3) * math.exp(-max(0,age-3)/20)

def support(has_pack, has_vest): return 'passive' if has_pack or has_vest else 'held'
def held_effect(alive=True, awake=True, player=True, match=True, same_parent=True, distance=1, same_vehicle=False):
    return alive and awake and player and match and same_parent and (same_vehicle or distance <= 3)
def anchor_distance(native, medic, anchor, helper, patient, valid_helper=True, elevated=True, vehicle=False):
    if not valid_helper or not elevated or vehicle: return native
    if len(anchor)!=3 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in anchor): return native
    if math.dist(helper,anchor)>2 or math.dist(patient,anchor)>3:return native
    return min(native,math.dist(medic,anchor))

class Leases:
    def __init__(self):self.token='a';self.active=True;self.leases={}
    def event(self,token,key,start):
        if token!=self.token:return
        if start:
            if self.active:self.leases[key]=True
        else:self.leases.pop(key,None)
    def resume(self):return self.active and not self.leases

class SettingsTests(unittest.TestCase):
    def test_personal_setting_mode_two(self):
        t=read('XEH_preInit.sqf'); self.assertRegex(t,r'(?s)\["ACME_hc_descriptors".*?false,\s*2,\s*\{\}')
    def test_other_hardcore_stays_global(self):
        t=read('XEH_preInit.sqf');self.assertRegex(t,r'\["ACME_hc_junc"[^\n]+false,\s*1,')
    def test_setting_id_preserved(self):self.assertEqual(read('XEH_preInit.sqf').count('["ACME_hc_descriptors", "CHECKBOX"'),1)
    def test_personal_policy_documented(self):self.assertIn('Cannot be forced',read('XEH_preInit.sqf'))
    def test_no_new_cache_switch(self):self.assertNotRegex(code(src('postInit')),r'setVariable\s*\[\s*"ACME_hc_descriptors"')

class ConnectorTests(unittest.TestCase):
    def test_native_delegate_exact(self):self.assertIn('class treatment { file = "\\x\\ACM\\addons\\core\\overrides\\fnc_treatment.sqf"; };',read('config.cpp'))
    def test_checks_permissions(self):self.assertIn('_this call ace_medical_treatment_fnc_canTreat',read('overrides/fn_treatment.sqf'))
    def test_checks_interaction(self):self.assertIn('call ace_common_fnc_canInteractWith',read('overrides/fn_treatment.sqf'))
    def test_checks_distance(self):self.assertIn('call ACME_fnc_ventRecoveryNear',read('overrides/fn_treatment.sqf'))
    def test_no_direct_item_debit(self):self.assertNotIn('removeItem',code(read('overrides/fn_treatment.sqf')))
    def test_no_progress_dialog(self):self.assertNotIn('progressBar',code(read('overrides/fn_treatment.sqf')))
    def test_cursor_menu_defers(self):self.assertIn('CBA_fnc_execNextFrame',read('overrides/fn_treatment.sqf'))
    def test_connector_uses_server_reservation(self):self.assertIn('CBA_fnc_serverEvent',src('ventConnectPatient'));self.assertIn('"attach", _medic, _patient',src('ventConnectPatient'))
    def test_clears_pending_reopen_next_frame(self):self.assertIn('[{ace_medical_gui_pendingReopen = false;}, []] call CBA_fnc_execNextFrame',src('ventConnectPatient'))

class DogtagTests(unittest.TestCase):
    def test_spawn_is_civilian_and_marked(self):self.assertIn('createUnit ["C_man_1"',src('megacodeSpawn'));self.assertIn('["ACME_isMegacode", true, true]',src('megacodeSpawn'))
    def test_spawn_exception_uses_existing_marker(self):self.assertIn('getVariable ["ACME_isMegacode", false]',src('canCheckPatientDogtags'))
    def test_other_patients_delegate(self):self.assertIn('_this call ACM_core_fnc_canCheckDogtag',src('canCheckPatientDogtags'))
    def test_no_global_faction_edit(self):self.assertNotIn('disabledFactions',code(src('canCheckPatientDogtags')))
    def test_null_denied(self):self.assertIn('if (isNull _patient) exitWith {false}',src('canCheckPatientDogtags'))
    def test_config_overrides_action_only(self):self.assertIn('class CheckDogTags: CheckResponse {\n        condition = "ACME_fnc_canCheckPatientDogtags";',read('config.cpp'))
    def test_cache_checks_shape(self):self.assertIn('count _cached >= 3',read('overrides/fn_getDogtagData.sqf'));self.assertIn('_x isEqualType ""',read('overrides/fn_getDogtagData.sqf'))
    def test_cache_generated_by_native(self):self.assertIn('call ACME_native_fnc_getDogtagData',read('overrides/fn_getDogtagData.sqf'))

class ManualSupportTests(unittest.TestCase):
    def test_empty_requires_hold(self):self.assertEqual(support(False,False),'held')
    def test_pack_is_passive(self):self.assertEqual(support(True,False),'passive')
    def test_vest_is_passive(self):self.assertEqual(support(False,True),'passive')
    def test_both_is_passive(self):self.assertEqual(support(True,True),'passive')
    def test_normal_hold_effect(self):self.assertTrue(held_effect())
    def test_dead_no_effect(self):self.assertFalse(held_effect(alive=False))
    def test_unconscious_no_effect(self):self.assertFalse(held_effect(awake=False))
    def test_disconnect_no_effect(self):self.assertFalse(held_effect(player=False))
    def test_old_token_no_effect(self):self.assertFalse(held_effect(match=False))
    def test_different_vehicles_no_effect(self):self.assertFalse(held_effect(same_parent=False,same_vehicle=True))
    def test_walk_away_no_effect(self):self.assertFalse(held_effect(distance=4))
    def test_same_vehicle_allows_distant_seat(self):self.assertTrue(held_effect(distance=5,same_vehicle=True))
    def test_uses_native_continuous_action(self):self.assertIn('call ACM_core_fnc_beginContinuousAction',src('headElevHoldStart'))
    def test_does_not_reimplement_animation_lock(self):self.assertNotIn('switchMove',code(src('headElevHoldStart')))
    def test_waits_for_old_dialog(self):self.assertIn('!dialog &&',src('headElevHoldStart'));self.assertIn('CBA_fnc_waitUntilAndExecute',src('headElevHoldStart'))
    def test_timeout_releases_reservation(self):self.assertIn('], 3, {',src('headElevHoldStart'));self.assertGreaterEqual(src('headElevHoldStart').count('headElevHoldRelease'),3)
    def test_player_disconnect_gate(self):self.assertIn('!isPlayer _medic',src('headElevWatch'));self.assertIn('isPlayer _medic',src('headElevEffective'))
    def test_provider_stop_exact_token(self):self.assertIn('isEqualTo [_patient, _token]',src('headElevHoldStop'))
    def test_release_checks_pose(self):self.assertIn('ACME_headElev_poseToken',src('headElevHoldRelease'))
    def test_manual_cannot_auto_resume(self):self.assertIn('if (_manual && {_auto',src('headElevateStart'))
    def test_suspending_manual_releases(self):
        t=src('headElevSuspend');self.assertLess(t.index('ACME_headElev_hold'),t.index('ACME_headElev_Suspended'))
    def test_stop_and_death_clear_hold(self):
        for n in ('headElevateStop','headElevDeathRelease'):self.assertIn('call ACME_fnc_headElevHoldClear',src(n))
    def test_reset_clear_hold(self):self.assertIn('call ACME_fnc_headElevHoldClear',src('clinicalReset'))
    def test_tbi_checks_actual_support(self):self.assertIn('call ACME_fnc_headElevEffective',src('tbiHandle'))
    def test_local_irritant_checks_actual_support(self):self.assertIn('call ACME_fnc_headElevEffective',src('vesicantTick'))
    def test_no_automatic_message_in_hold(self):
        for n in ('headElevHoldStart','headElevHoldRelease','headElevHoldStop','headElevEffective'):self.assertNotRegex(code(src(n)),r'diag_log|systemChat|hint\s|displayTextStructured')

class DistanceTests(unittest.TestCase):
    def setUp(self):self.args=(3.2,(0,0,0),(2.9,0,0),(2.9,0,0.2),(3.2,0,0))
    def test_valid_pose_can_use_anchor(self):self.assertEqual(anchor_distance(*self.args),2.9)
    def test_unrelated_helper_cannot_bypass(self):self.assertEqual(anchor_distance(*self.args,valid_helper=False),3.2)
    def test_no_elevation_no_exception(self):self.assertEqual(anchor_distance(*self.args,elevated=False),3.2)
    def test_vehicle_keeps_native_distance(self):self.assertEqual(anchor_distance(*self.args,vehicle=True),3.2)
    def test_map_origin_helper_rejected(self):self.assertEqual(anchor_distance(100,(0,0,0),(50,50,0),(0,0,0),(50,50,1)),100)
    def test_transported_anchor_rejected(self):self.assertEqual(anchor_distance(10,(0,0,0),(1,0,0),(1,0,0),(10,0,0)),10)
    def test_upper_floor_anchor(self):self.assertEqual(anchor_distance(3.2,(0,0,10),(2.9,0,10),(2.9,0,10.2),(3.2,0,10)),2.9)
    def test_invalid_anchor_rejected(self):self.assertEqual(anchor_distance(5,(0,0,0),(float('nan'),0,0),(0,0,0),(0,0,0)),5)
    def test_native_nearer_is_retained(self):self.assertEqual(anchor_distance(.5,(0,0,0),(1,0,0),(1,0,0),(1,0,0)),.5)
    def test_helper_created_at_patient(self):self.assertNotIn('"ACME_RopeHelper" createVehicle [0,0,0]',code(src('headElevApplyTilt')));self.assertIn('"CAN_COLLIDE"',src('headElevApplyTilt'))
    def test_floor_restore_uses_asl(self):
        for n in ('headElevateStop','headElevSuspend'):self.assertIn('_patient setPosASL _base',src(n))
    def test_no_unconditional_menu_true(self):
        t=read('overrides/fn_canOpenMenu.sqf');self.assertIn('ace_medical_gui_maxDistance',t);self.assertIn('ace_medical_gui_enableMedicalMenu',t);self.assertIn('call ace_common_fnc_isAwake',t)

class LeaseTests(unittest.TestCase):
    def test_first_provider(self):m=Leases();m.event('a','A',True);self.assertFalse(m.resume())
    def test_last_finish(self):m=Leases();m.event('a','A',True);m.event('a','A',False);self.assertTrue(m.resume())
    def test_two_providers(self):m=Leases();m.event('a','A',True);m.event('a','B',True);m.event('a','A',False);self.assertFalse(m.resume())
    def test_both_finish(self):m=Leases();m.event('a','A',True);m.event('a','B',True);m.event('a','A',False);m.event('a','B',False);self.assertTrue(m.resume())
    def test_duplicate_finish_idempotent(self):m=Leases();m.event('a','A',False);m.event('a','A',False);self.assertTrue(m.resume())
    def test_old_episode_cannot_add(self):m=Leases();m.event('old','A',True);self.assertTrue(m.resume())
    def test_old_episode_cannot_remove(self):m=Leases();m.event('a','A',True);m.event('old','A',False);self.assertFalse(m.resume())
    def test_stopped_does_not_restore(self):m=Leases();m.active=False;m.event('a','A',False);self.assertFalse(m.resume())
    def test_source_pairs_identified_events(self):self.assertIn('ACME_headElev_treatmentSerial',src('postInit'));self.assertIn('netId _medic',src('postInit'))
    def test_source_checks_token(self):self.assertIn('!= _token',src('headElevTreatmentEvent'))
    def test_source_waits_other_provider(self):self.assertIn('if (count _leases > 0) exitWith',src('headElevTryResume'))
    def test_native_cpr_wait_retained(self):self.assertIn('call ACM_core_fnc_cprActive',src('headElevTryResume'))
    def test_owner_routed_resume(self):self.assertIn('"headElevTryResume", [_patient, _token]',src('headElevTryResume'))
    def test_vehicle_guard_retained(self):self.assertIn('objectParent',src('headElevSuspend'))

class StimulusTests(unittest.TestCase):
    def test_starts_zero(self):self.assertEqual(offset(0),0)
    def test_rises_over_three_seconds(self):self.assertAlmostEqual(offset(1.5),.5)
    def test_peak_one(self):self.assertEqual(offset(3),1)
    def test_timed_decay(self):self.assertAlmostEqual(offset(23),math.exp(-1))
    def test_ends(self):self.assertEqual(offset(60),0)
    def test_future_stamp_ignored(self):self.assertEqual(offset(-1),0)
    def test_fentanyl_attenuates_same_envelope(self):self.assertEqual(offset(3,.3),.3)
    def test_strength_capped(self):self.assertEqual(offset(3,4),1);self.assertEqual(offset(3,-1),0)
    def test_no_total_pressure_cap(self):self.assertNotRegex(code(src('bpCompute')),r'_sys\s*=.*\bmin\s+\d')
    def test_direct_bp_defaults(self):self.assertIn('"ACME_laryngo_systolicSurge", 20',src('bpCompute'));self.assertIn('"ACME_laryngo_diastolicSurge", 10',src('bpCompute'))
    def test_hr_default(self):self.assertIn('"ACME_laryngo_hrSurge", 10',read('overrides/fn_updateHeartRate.sqf'))
    def test_no_permanent_icp_in_event(self):self.assertNotIn('_state set ["icp"',code(src('laryngoStimulusLocal')))
    def test_repeat_grip_cooldown(self):self.assertIn('CBA_missionTime - _previous < 60',src('laryngoStimulusLocal'))
    def test_remove_previous_before_structural_tick(self):
        t=src('tbiHandle');self.assertLess(t.index('getOrDefault ["laryngoICPApplied", 0]'),t.index('private _baseRise'));self.assertGreater(t.index('_state set ["laryngoICPApplied", _laryngoICP]'),t.index('private _riseCap'))
    def test_transient_does_not_accumulate(self):
        icp=15;prior=0
        for t in range(61):
            structural=max(0,icp-prior);prior=4*offset(t);icp=structural+prior
        self.assertAlmostEqual(icp,15)
    def test_all_readers_same_event_clock(self):self.assertIn('CBA_missionTime - _at',src('laryngoStimulusEffect'))
    def test_event_clock_schema(self):self.assertRegex(src('clinicalFields'),r'"ACME_laryngoStimulusAt"[^\n]*"cba"')
    def test_no_provider_announcement(self):
        for n in ('laryngoStimulusLocal','laryngoStimulusEffect'):self.assertNotRegex(code(src(n)),r'diag_log|displayTextStructured|hint\b|addToLog|systemChat')
    def test_probe_is_pure(self):self.assertNotIn('setVariable',code(src('bpCompute')))
    def test_probe_defaults_disabled(self):self.assertIn('["_resistanceProbe", -1, [0]]',src('bpCompute'))
    def test_probe_uses_same_pressure_model(self):self.assertIn('[_patient, true, true, _baseR + 100] call ACME_fnc_bpCompute',src('tbiApplyVitals'))
    def test_controller_uses_measured_gain(self):self.assertIn('_tbiMAPdelta / _slope',src('tbiApplyVitals'));self.assertNotIn('_tbiMAPdelta * (missionNamespace getVariable ["ACME_tbi_svrPerMAP", 2])',src('tbiApplyVitals'))
    def test_zero_gain_has_no_divide(self):self.assertIn('if (_slope > 0.001 && {finite _slope})',src('tbiApplyVitals'))
    def test_slew_rate_retained(self):self.assertIn('"ACME_tbi_resistStepPerSec", 40',src('tbiApplyVitals'))

# Check the controller across changing cardiac-output-derived gains and target MAPs.
# This independent linear model deliberately excludes engine callbacks and timing.
for gain in (.2,.5,1,1.5,2.2):
    for target in (80,110,140):
        def case(self,gain=gain,target=target):
            base_r=100;intercept=-10;base_map=base_r*gain+intercept
            probe_map=(base_r+100)*gain+intercept
            measured=(probe_map-base_map)/100
            added=(target-base_map)/measured
            actual=(base_r+added)*gain+intercept
            self.assertAlmostEqual(actual,target,places=8)
        setattr(StimulusTests,'test_pressure_gain_'+str(gain).replace('.','_')+'_target_'+str(target),case)

if __name__=='__main__':unittest.main()
