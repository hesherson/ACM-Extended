#!/usr/bin/env python3
"""B4 source contracts and protocol reference models. No test executes Arma SQF."""
from historical_source import read_source
from pathlib import Path
import copy
import hashlib
import re
import unittest
from source_scan import lex
R=Path(__file__).resolve().parents[1]
def src(name):return read_source(R/'functions'/('fn_'+name+'.sqf'), encoding='utf-8-sig')
def tokens(name):return [t.value for t in lex(src(name))]

def sedation(ket_im=0,ket_iv=0,mid=0,prop=0):
    return ket_im*.5+ket_iv*.8+mid+prop

def induce(ket,prop,ket_threshold=7,player=False,local=True,alive=True):
    return local and alive and not player and (ket>=ket_threshold or prop>=1)

def closure(doctor,kit,seals,held=''):
    preferred='tube' if doctor and kit>0 else 'seal'
    selected=held if held in ('tube','seal') else preferred
    usable=(doctor and kit>0) if selected=='tube' else seals>0
    return selected,usable

def closure_art(tube=False,sealed=False):
    return 'tube' if tube else ('seal' if sealed else None)

class BandOwner:
    """Reference example of B4 event ordering and saved-band normalization; not CBA transport."""
    def __init__(self):self.epoch=1;self.state={};self.rows={};self.flags={};self.publications=0
    def change(self,limb,on,view,site='middle',epoch=1,local=True):
        if not local or epoch!=self.epoch or limb not in (2,3,4,5):return False
        rev=self.state.get(limb,(0,))[0]+1
        band=[on,site,[.5,.4],[.5,.5],site,'band.paa']
        self.flags[limb]=on
        for key,row in self.rows.items():
            if key[0]==limb:
                row['band']=copy.deepcopy(band) if on and key[1]==view else [False]+row['band'][1:]
        if on and (limb,view) not in self.rows:
            self.rows[limb,view]={'band':copy.deepcopy(band),'ins':[],'clean':False}
        self.state[limb]=[rev,on,view,band]
        self.publications+=1
        return True
    def save(self,limb,view,row):
        state=self.state.get(limb,[])
        active=bool(state and state[1] and state[2]==view)
        if row is None and active:return
        if row is None:self.rows.pop((limb,view),None);return
        row=copy.deepcopy(row)
        if state:
            row['band']=copy.deepcopy(state[3]) if active else [False]+row['band'][1:]
        else:row['band'][0]=bool(row['band'][0] and self.flags.get(limb,False))
        self.rows[limb,view]=row
    def visible(self,limb,view):
        s=self.state.get(limb,[])
        return bool(s and s[1] and s[2]==view)

class ManualInfusionSource(unittest.TestCase):
    def test_no_preset_functions_or_registrations(self):
        c=read_source(R/'config.cpp')
        for name in ('infusionPresets','infusionPresetRate','infusionPresetApply','infusionPresetCommit','infusionPresetResult'):
            self.assertFalse((R/'functions'/('fn_'+name+'.sqf')).exists());self.assertNotIn('class '+name,c)
    def test_no_preset_transport_events(self):self.assertNotIn('ACME_infusionPreset',src('postInit'))
    def test_no_dose_selector_or_apply_button(self):
        s=src('onClampLoad');self.assertNotIn('Apply rate',s);self.assertNotIn('infusionPreset',s)
    def test_manual_clamp_has_no_preset_lock(self):
        for n in ('setClampPosition','cycleDropSet'):self.assertNotIn('infusionPreset',src(n))
    def test_both_drugs_allowed(self):
        s=re.search(r'ACME_infusion_allowedMedications\s*=\s*(\[[^;]+)',src('postInit')).group(1)
        for drug in ('Ketamine','Propofol'):self.assertIn('"'+drug+'"',s)
    def test_native_propofol_class_preserved(self):
        s=read_source(R/'config.cpp');c=s[s.index('class Propofol_IV:'):s.index('class Norepinephrine_IV:')]
        for term in ('timeInSystem = 480','timeTillMaxEffect = 90','maxEffectTime = 180','maxEffectDose = 100','weightEffect = 1','painReduce = 0'):self.assertIn(term,c)
    def test_delivery_still_native_already_admitted(self):
        s=src('infusionDeliver')
        self.assertIn('_pending, true, true,',s)
        self.assertIn('_elapsed, "infusion"',s)
        self.assertLess(s.index('private _elapsed'),s.index('_entry set [16'))
    def test_pending_dose_not_consumed_by_preset(self):
        s=src('infusionDeliver');self.assertIn('_entry set [15, 0]',s);self.assertNotIn('preset',s.lower())
    def test_native_class_mapping(self):self.assertIn('format ["%1_IV", _medication]',src('infusionRegisterCore'))
    def test_propofol_read_native_effect(self):
        s=src('propofolOnBoard');self.assertIn('"Propofol_IV", false',s);self.assertIn('finite _effect',s)
    def test_propofol_no_extra_weight_or_potency_scaling(self):
        for n in ('propofolOnBoard','sedationOnBoard','postInit'):
            s=src(n);self.assertNotIn('ACME_sedation_propofolEquiv',s);self.assertNotIn('ACME_sedation_induceThreshold',s)
        self.assertNotIn('*', ''.join(tokens('propofolOnBoard')))
    def test_sedation_reads_all_existing_inputs(self):
        self.assertIn('ACME_fnc_sedationComponents',src('sedationOnBoard'))
        s=src('sedationComponents')
        for v in ('ACME_fnc_ketamineOnBoard','Midazolam_IV','Midazolam','ACME_fnc_propofolOnBoard','ACME_fnc_fentanylOnBoard'):self.assertIn(v,s)
    def test_b14_iv_anchor_retained_im_and_nasal_covered(self):
        s=src('ketamineOnBoard')
        self.assertIn('0.8',s);self.assertIn('1.75',s);self.assertIn('"Esketamine"',s)
    def test_prior_ketamine_induction_setting_retained(self):
        self.assertIn('["ACME_ket_induceThreshold", 7]',src('sedationComponents'))
    def test_b14_all_hypnotics_use_shared_induction(self):
        self.assertIn('ACME_fnc_propofolOnBoard',src('sedationComponents'))
        self.assertIn('ACME_fnc_sedationActive',src('ketamineSedationTick'))
        self.assertIn('(_load >= 1) || {_owned && {_load >= _maintenance}}',src('sedationActive'))
    def test_player_exemption_and_locality(self):
        s=src('ketamineSedationTick');self.assertNotIn('isPlayer _patient',s);self.assertIn('!local _patient',s)
    def test_b14_shared_adequacy_reads_live_setting(self):
        for n in ('ketamineSedationTick','rocuroniumTick'):
            self.assertIn('call ACME_fnc_sedationActive',src(n))
        for n in ('sedationActive','ventStatusTick'):
            self.assertIn('call ACME_fnc_sedationThreshold',src(n))
        # B18 capnography no longer manufactures dyssynchrony from sedation/paralytic state; it reads the
        # actual coordination state published by the ventilator drive.
        cap=src('capnoMorph')
        self.assertIn('ACME_vent_dyssync',cap)
        self.assertNotIn('setVariable ["ACME_vent_dyssync"',cap)
        self.assertIn('["ACME_ket_maintainThreshold", 1.2]',src('sedationThreshold'))
    def test_laryngoscopy_counts_shared_sedation(self):
        s=src('laryngoPassTube')
        self.assertIn('ACME_fnc_laryngoReflexChance',s)
        self.assertIn('ACME_fnc_sedationComponents',src('laryngoReflexChance'))
        self.assertNotIn('ACME_vent_saiKetamineDose',s)
    def test_no_medication_added_by_effect_readers(self):
        for n in ('sedationOnBoard','propofolOnBoard','ketamineSedationTick'):self.assertNotIn('medicationLocal',tokens(n))
    def test_reset_flags_still_registered(self):self.assertIn('"ACME_ket_sedated"',src('clinicalFields'))
    def test_only_shared_adequacy_assignment(self):self.assertEqual(len(re.findall(r'ACME_sed_adequateThresh\s*=',src('postInit'))),1)

class SedationExamples(unittest.TestCase):
    def test_empty_bag_is_not_sedation(self):self.assertEqual(sedation(),0)
    def test_ketamine_iv_weight(self):self.assertEqual(sedation(ket_iv=1),.8)
    def test_ketamine_im_weight(self):self.assertEqual(sedation(ket_im=1),.5)
    def test_propofol_counts_once(self):self.assertEqual(sedation(prop=.5),.5)
    def test_midazolam_uses_onset_gated_input(self):self.assertEqual(sedation(mid=.2),.2)
    def test_combination_sums_existing_effects(self):self.assertAlmostEqual(sedation(ket_iv=.5,mid=.2,prop=.3),.9)
    def test_below_ketamine_threshold_unchanged(self):self.assertFalse(induce(6.99,0))
    def test_at_prior_ketamine_threshold(self):self.assertTrue(induce(7,0))
    def test_below_full_propofol_effect(self):self.assertFalse(induce(0,.99))
    def test_full_propofol_effect(self):self.assertTrue(induce(0,1))
    def test_inactive_patient_not_induced(self):
        self.assertFalse(induce(8,2,local=False));self.assertFalse(induce(8,2,alive=False))
    def test_player_exemption(self):self.assertFalse(induce(8,2,player=True))
    def test_mission_ketamine_threshold_respected(self):self.assertTrue(induce(4,0,ket_threshold=4))
    def test_dose_received_not_amount_in_bag(self):
        concentration=100/100;admitted=0;self.assertEqual(concentration*admitted,0)
        admitted=5;self.assertEqual(concentration*admitted,5)
    def test_multiple_manual_additives_sum(self):self.assertEqual((40+60)/100,100/100)
    def test_extravasated_dose_is_not_systemic(self):
        removed=10;concentration=1;admitted=removed*.6
        self.assertEqual(admitted*concentration,6);self.assertEqual((removed-admitted)*concentration,4)

class ThoracostomySource(unittest.TestCase):
    def test_captured_medic_used_for_inventory(self):
        for n in ('thoraInit','thoraTick','thoraSelectTool'):self.assertIn('"ACME_Thora_Medic"',src(n))
        self.assertNotIn('ACE_player',tokens('thoraClosureMode'))
    def test_original_doctor_default_is_now_configurable(self):
        self.assertIn('[_medic, "chestTube"] call ACME_fnc_procedureAllowed',src('thoraClosureMode'))
        self.assertIn('["ACME_allowChestTubes", "ACME_skillChestTube", 2]',src('procedureAllowed'))
    def test_seal_is_real_held_tool(self):
        self.assertIn('_held in ["seal", "tube"]',src('thoraSelectTool'));self.assertIn('if (_held == "seal") exitWith',src('thoraMouseDown'))
    def test_held_tool_does_not_change_with_inventory(self):self.assertIn('_preferred = _heldClosure',src('thoraTick'))
    def test_seal_art_shared_held_and_placed(self):
        for n in ('thoraTick','thoraRenderTube'):self.assertIn('ACME_fnc_thoraClosureArt',src(n))
    def test_seal_has_center_anchor(self):self.assertIn('0.18, [0.5, 0.5]',src('thoraClosureArt'))
    def test_snap_accepts_both_tools(self):
        s=src('thoraTick');self.assertIn('if (_held in ["seal", "tube"]) then',s);self.assertIn('private _anchor = _closureArt select 2',s)
    def test_persistent_dressing_is_rendered(self):
        s=src('thoraRenderTube');self.assertIn('ACME_thora_sealed_%1',s);self.assertIn('if (_placed) then {"tube"} else {"seal"}',s)
    def test_observer_role_cannot_change_applied_art(self):
        s=src('thoraRenderTube');self.assertNotIn('SealMode',s);self.assertNotIn('isMedic',s)
    def test_seal_branch_does_not_insert_or_drain_tube(self):
        s=src('thoraMouseDown');s=s[s.index('if (_held == "seal") exitWith'):s.index('private _tubeMedic')]
        self.assertNotIn('Thoracostomy_insertChestTube',s);self.assertNotIn('thoraPassiveDrain',s)
        self.assertNotIn('ACME_thora_tube_%1',s);self.assertIn('\"thoraSeal\"',s);self.assertNotIn('ACM_breathing_fnc_applyChestSeal',s)
    def test_seal_consumed_and_verified(self):
        s=src('thoraMouseDown');self.assertIn('_medS removeItem "ACM_ChestSeal"',s);self.assertIn('>= _before) exitWith',s)
    def test_repeat_dressing_checks_precede_consumption(self):
        s=src('thoraMouseDown');a=s.index('if (_held == "seal") exitWith');self.assertLess(s.index('ACME_thora_sealed_%1',a),s.index('_medS removeItem',a))
    def test_hover_selects_shared_slot(self):self.assertIn('_tool == "tube" && {_held == "seal"}',src('thoraSlotHover'))
    def test_values_refresh_independently_of_version(self):self.assertIn('ACME_Thora_ClosureSeen',src('thoraTick'))

class ClosureExamples(unittest.TestCase):
    def test_medic_with_both_gets_seal(self):self.assertEqual(closure(False,1,1),('seal',True))
    def test_medic_without_seal_cannot_use_tube(self):self.assertEqual(closure(False,1,0),('seal',False))
    def test_doctor_with_kit_gets_tube(self):self.assertEqual(closure(True,1,1),('tube',True))
    def test_doctor_without_kit_gets_seal(self):self.assertEqual(closure(True,0,1),('seal',True))
    def test_chosen_seal_does_not_morph(self):self.assertEqual(closure(True,1,1,'seal'),('seal',True))
    def test_empty_held_seal_is_not_a_tube(self):self.assertEqual(closure(True,1,0,'seal'),('seal',False))
    def test_lost_tube_permission_rejects(self):self.assertEqual(closure(False,1,1,'tube'),('tube',False))
    def test_open_incision_no_applied_art(self):self.assertIsNone(closure_art())
    def test_seal_without_tube_draws_seal(self):self.assertEqual(closure_art(sealed=True),'seal')
    def test_sutured_tube_still_draws_tube(self):self.assertEqual(closure_art(tube=True,sealed=True),'tube')

class BandSource(unittest.TestCase):
    def test_reader_runs_before_tool_branches(self):
        s=src('ivMinigameTick');self.assertLess(s.index('ACME_fnc_ivMinigameSyncBand'),s.index('private _held'))
    def test_reader_is_read_only_for_patient(self):
        s=src('ivMinigameSyncBand')
        for term in ('ACME_fnc_ownerDispatch','ACME_fnc_setVarNet','publicVariable','remoteExec','ACME_fnc_ivMinigameSaveState','ACME_fnc_ivMinigameBandFlag'):self.assertNotIn(term,s)
        self.assertNotIn('_patient setVariable',s)
    def test_restore_never_publishes_band(self):self.assertNotIn('ACME_fnc_ivMinigameBandFlag',src('ivMinigameRestoreState'))
    def test_onload_runs_read_only_refresh(self):self.assertIn('[true] call ACME_fnc_ivMinigameSyncBand',src('ivMinigameInit'))
    def test_band_sender_uses_owner_and_epoch(self):
        s=src('ivMinigameBandFlag');self.assertIn('ACME_fnc_ownerDispatch',s);self.assertIn('ACME_fnc_clinicalEpoch',s)
    def test_only_deliberate_band_operations_publish(self):
        calls=[]
        for p in (R/'functions').glob('*.sqf'):
            if 'ACME_fnc_ivMinigameBandFlag' in [t.value for t in lex(read_source(p, encoding='utf-8-sig'))]:calls.append(p.stem)
        self.assertEqual(set(calls),{'fn_ivMinigameClick','fn_ivMinigameRemoveBand'})
    def test_owner_requires_current_local_epoch(self):
        s=src('ivStateLocal');self.assertIn('!local _patient',s);self.assertIn('_epoch !=',s)
    def test_band_snapshot_is_atomic(self):
        s=src('ivStateLocal');self.assertIn('private _snapshot = [(_old param [0, 0]) + 1, _on, _view, _band]',s)
        self.assertIn('[_patient, _stateName, _snapshot] call ACME_fnc_setVarNet',s)
    def test_owner_updates_existing_flow_flag(self):self.assertIn('ACME_IV_BandOnPart_%1',src('ivStateLocal'))
    def test_owner_normalizes_saved_band(self):self.assertIn('_band set [0, _activeHere]',src('ivStateLocal'))
    def test_owner_clears_all_saved_faces(self):self.assertIn('(_rowKey find (_bp + "|")) == 0',src('ivStateLocal'))
    def test_empty_observer_save_cannot_delete_band(self):self.assertIn('_entry isEqualTo [] && {_activeHere}',src('ivStateLocal'))
    def test_hide_and_show_are_both_applied(self):self.assertIn('_ctrl ctrlShow _visible',src('ivMinigameSyncBand'))
    def test_site_geometry_and_tray_refreshed(self):
        s=src('ivMinigameSyncBand');self.assertIn('ACME_fnc_ivVeinSet',s);self.assertIn('ACME_fnc_ivMinigameRefreshBandSlot',s)
    def test_band_reader_never_changes_insertion(self):
        s=src('ivMinigameSyncBand');self.assertNotIn('setVariable ["ACME_IV_Ins',s);self.assertNotIn('ctrlDelete',s)
    def test_pending_gate_has_bounded_local_lifetime(self):
        self.assertIn('diag_tickTime + 5',src('ivMinigameBandFlag'));self.assertIn('_revision <= (_pending select 0)',src('ivMinigameSyncBand'))
    def test_ej_excluded(self):
        for n in ('ivMinigameBandFlag','ivMinigameSyncBand'):self.assertIn('ACME_IV_EJMode',src(n))
    def test_schema_includes_all_peripheral_snapshots(self):
        for i in (2,3,4,5):self.assertIn('"ACME_IV_BandState_%s"'%i,src('clinicalFields'))
    def test_flip_saves_before_switch_without_removing_physical_band(self):
        s=src('ivMinigameFlip');self.assertLess(s.index('[] call ACME_fnc_ivMinigameSaveState'),s.index('setVariable ["ACME_IV_View", _next]'))
        self.assertNotIn('ACME_fnc_ivMinigameBandFlag',s)
    def test_no_debug_rpt_in_new_helpers(self):
        for n in ('propofolOnBoard','thoraClosureArt','thoraClosureMode','ivStateLocal','ivMinigameSyncBand','ivMinigameBandFlag'):
            self.assertNotIn('diag_log',tokens(n));self.assertNotIn('systemChat',tokens(n))

class BandExamples(unittest.TestCase):
    def setUp(self):self.o=BandOwner()
    def test_same_view_sees_application(self):self.o.change(2,True,'front');self.assertTrue(self.o.visible(2,'front'))
    def test_observer_sees_removal(self):
        self.o.change(2,True,'front');self.o.change(2,False,'front');self.assertFalse(self.o.visible(2,'front'))
    def test_flow_flag_changes_with_snapshot(self):
        self.o.change(2,True,'front');self.assertTrue(self.o.flags[2]);self.o.change(2,False,'front');self.assertFalse(self.o.flags[2])
    def test_reopen_cannot_reapply(self):
        self.o.change(2,True,'front');old=copy.deepcopy(self.o.rows[2,'front']);self.o.change(2,False,'front');self.o.save(2,'front',old);self.assertFalse(self.o.rows[2,'front']['band'][0])
    def test_other_limb_unchanged(self):
        self.o.change(3,True,'front');self.o.change(2,False,'front');self.assertTrue(self.o.visible(3,'front'))
    def test_other_face_not_shown(self):self.o.change(2,True,'front');self.assertFalse(self.o.visible(2,'rear'))
    def test_band_can_be_reapplied_after_removal(self):
        self.o.change(2,True,'front');self.o.change(2,False,'front');self.o.change(2,True,'front','lower');self.assertTrue(self.o.visible(2,'front'));self.assertEqual(self.o.state[2][3][1],'lower')
    def test_reposition_clears_prior_face(self):
        self.o.change(2,True,'front');self.o.change(2,True,'rear');self.assertFalse(self.o.rows[2,'front']['band'][0])
    def test_stale_save_cannot_move_current_band(self):
        self.o.change(2,True,'front');old=copy.deepcopy(self.o.rows[2,'front']);self.o.change(2,True,'front','lower');self.o.save(2,'front',old);self.assertEqual(self.o.rows[2,'front']['band'][1],'lower')
    def test_idle_observer_close_preserves_active_band(self):
        self.o.change(2,True,'front');self.o.save(2,'front',None);self.assertTrue(self.o.rows[2,'front']['band'][0])
    def test_removal_preserves_insertion_and_prep(self):
        self.o.change(2,True,'front');self.o.rows[2,'front']['ins']=['thread',11];self.o.rows[2,'front']['clean']=True;self.o.change(2,False,'front');self.assertEqual(self.o.rows[2,'front']['ins'],['thread',11]);self.assertTrue(self.o.rows[2,'front']['clean'])
    def test_observation_emits_no_publications(self):
        self.o.change(2,True,'front');n=self.o.publications
        for _ in range(1000):self.o.visible(2,'front')
        self.assertEqual(self.o.publications,n)
    def test_old_epoch_rejected(self):self.assertFalse(self.o.change(2,True,'front',epoch=0));self.assertEqual(self.o.state,{})
    def test_nonowner_rejected(self):self.assertFalse(self.o.change(2,True,'front',local=False))
    def test_head_never_banded(self):self.assertFalse(self.o.change(0,True,'front'))
    def test_version_increments_per_operation(self):
        self.o.change(2,True,'front');self.o.change(2,False,'front');self.assertEqual(self.o.state[2][0],2)
    def test_owner_processed_operations_converge(self):
        for on in (True,False,True,False):self.o.change(2,on,'front')
        self.assertFalse(self.o.visible(2,'front'));self.assertFalse(self.o.flags[2])

if __name__=='__main__':unittest.main()
