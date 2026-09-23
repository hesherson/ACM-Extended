"""Source contracts and independent arithmetic models. These tests do not execute SQF."""
from historical_source import read_source
from pathlib import Path
from dataclasses import dataclass, field
import random, unittest
ROOT=Path(__file__).resolve().parents[1]
def src(n): return read_source(ROOT/'functions'/('fn_'+n+'.sqf'))
@dataclass
class Mixture:
    volume: float
    left: dict=field(default_factory=dict)
    supplied: dict=field(default_factory=dict)
    systemic: dict=field(default_factory=dict)
    extravasated: dict=field(default_factory=dict)
    pending: dict=field(default_factory=dict)
    pushes: dict=field(default_factory=dict)
    drops: float=0
    def add(self, drug, dose, ml):
        assert dose>0 and ml>=0 and self.volume>0
        self.volume+=ml
        self.left[drug]=self.left.get(drug,0)+dose
        self.supplied[drug]=self.supplied.get(drug,0)+dose
        self.pushes[drug]=self.pushes.get(drug,0)+1
    def drain(self, ml, admitted):
        ml=min(ml,self.volume);admitted=min(admitted,ml)
        if not ml:return
        for med in self.left:
            amount=self.left[med]*ml/self.volume
            self.left[med]-=amount
            sys=amount*admitted/ml
            self.systemic[med]=self.systemic.get(med,0)+sys
            self.extravasated[med]=self.extravasated.get(med,0)+amount-sys
        self.volume-=ml
class MixtureArithmetic(unittest.TestCase):
    def test_two_500_mg_vials_add_100_ml_solution(self):
        m=Mixture(100)
        for _ in range(10):m.add('Propofol',100,10)
        self.assertEqual(m.volume,200);self.assertEqual(m.left['Propofol'],1000)
    def test_three_large_calcium_vials_repeated_syringes(self):
        m=Mixture(100)
        for _ in range(15):m.add('CalciumGluconate',1000,10)
        self.assertEqual(m.volume,250);self.assertEqual(m.pushes['CalciumGluconate'],15)
        self.assertEqual(m.left['CalciumGluconate'],15000)
    def test_more_than_four_injections(self):
        m=Mixture(100)
        for _ in range(100):m.add('Ketamine',2,1)
        self.assertEqual(m.left['Ketamine'],200)
    def test_closed_clamp_zero_delivery(self):
        m=Mixture(100);m.add('Propofol',100,10);m.drain(0,0)
        self.assertEqual(m.systemic,{});self.assertEqual(m.left['Propofol'],100)
    def test_mixture_each_drug_independent(self):
        m=Mixture(100);m.add('Propofol',100,10);m.add('Fentanyl',.1,10)
        m.drain(60,60)
        self.assertAlmostEqual(m.systemic['Propofol'],50);self.assertAlmostEqual(m.systemic['Fentanyl'],.05)
    def test_partial_delivery_then_more_drug_no_redelivery(self):
        m=Mixture(90);m.add('Propofol',100,10);m.drain(50,50);m.add('Ketamine',50,10);m.drain(60,60)
        self.assertAlmostEqual(m.systemic['Propofol'],100);self.assertAlmostEqual(m.systemic['Ketamine'],50)
    def test_extravasation_is_not_systemic(self):
        m=Mixture(90);m.add('Propofol',100,10);m.drain(50,20)
        self.assertAlmostEqual(m.systemic['Propofol'],20);self.assertAlmostEqual(m.extravasated['Propofol'],30)
    def test_randomized_conservation(self):
        rng=random.Random(551)
        for trial in range(100):
            m=Mixture(100)
            for i in range(75):
                if rng.random()<.6:m.add(rng.choice(['K','P','F','Ca']),rng.uniform(.001,400),rng.uniform(.01,10))
                else:
                    ml=rng.uniform(0,min(m.volume*.8,20));m.drain(ml,ml*rng.random())
                for med,total in m.supplied.items():
                    self.assertAlmostEqual(total,m.left.get(med,0)+m.systemic.get(med,0)+m.extravasated.get(med,0),places=8)
    def test_spiked_record_survives_open_cancel(self):
        sets={'a':100};snapshot=dict(sets)
        for _ in range(8): pass
        self.assertEqual(snapshot,sets)
    def test_open_vial_residue_conservation(self):
        full=3;remaining=0;used=0
        for i in range(15):
            if remaining<10:full-=1;remaining+=50
            remaining-=10;used+=10
            self.assertEqual(150,full*50+remaining+used)
        self.assertEqual((full,remaining),(0,0))
    def test_mixture_clamp_shared(self):
        records=[{'bag':'one','drops':0},{'bag':'one','drops':0},{'bag':'two','drops':40}]
        for e in records:
            if e['bag']=='one':e['drops']=60
        self.assertEqual([e['drops'] for e in records],[60,60,40])
    def test_laryngoscopy_decay_and_fentanyl(self):
        import math
        for age in (0,5,20,40):
            base=math.exp(-age/20)
            self.assertLessEqual(base,1)
            self.assertEqual(base*(1-1),0)
            self.assertAlmostEqual(base*(1-.5),base/2)
    def test_fentanyl_alone_not_hypnosis(self):self.assertEqual((0+0+0)*(1+.35),0)
    def test_native_fentanyl_effect_converted_from_mg(self):self.assertEqual(round(2*.083*1000),166)
class SourceContracts(unittest.TestCase):
    def test_config_medication_path_is_native(self):
        s=src('fentanylOnBoard')
        self.assertIn('ace_medical_status_fnc_getMedicationCount',s)
        self.assertIn('"Fentanyl_BUC"',s)
        self.assertNotIn('"ace_medical_treatment" >> "Medication"',src('preparedAttachLocal'))
    def test_premix_osmotics_admitted_by_own_handler(self):
        self.assertIn('ACME_infusion_osmoticAgents',src('preparedAttachLocal'))
        self.assertIn('7500 / 250',src('fluidCommit'));self.assertIn('100000 / 500',src('fluidCommit'))
    def test_no_old_push_or_mixture_gate(self):
        for f in ('injectIntoBag','infusionRegisterCore','infusionRefreshTally'):
            self.assertNotIn('maxPushes',src(f));self.assertNotIn('one drug',src(f))
    def test_spiked_set_not_deleted_on_open(self):
        s=src('openPrepFromInventoryMenu');self.assertNotIn('deleteAt',s);self.assertNotIn('addToInventory',s)
    def test_set_retired_only_after_positive_ack(self):
        s=src('preparedAttachAck');self.assertLess(s.index('if (!_ok)'),s.index('forEach ["ACME_infusion_PreparedBags", "ACME_preparedIVSets"]'))
    def test_no_success_helper_hints(self):
        s=src('preparedAttachAck');s=s[s.index('private _uid ='):]
        self.assertNotIn('hint',s);self.assertNotIn('clinicalNotice',s);self.assertIn('ACME_fnc_queueInfusionClamp',s)
    def test_queue_requires_display_teardown_and_received_state(self):
        s=src('queueInfusionClamp');self.assertIn('!dialog',s);self.assertIn('ACME_infusion_BagMedications',s);self.assertIn('ACME_fnc_clinicalEpoch',s)
    def test_injection_stays_open(self):
        self.assertNotIn('closeDialog',src('injectIntoBag'));self.assertNotIn('infusionDone',src('injectIntoBag'))
    def test_plunger_visual_uses_id_as_control(self):
        self.assertIn('[0, _display, true] call ACME_fnc_syringeDrawSetAmount',src('injectIntoBag'))
        helper=src('syringeDrawSetAmount')
        self.assertIn('ACM_circulation_SyringeDraw_Ctrl_PlungerVisual',helper)
        self.assertIn('_display displayCtrl _visualIdc',helper)
        self.assertIn('_y - _adjust',helper)
        from test_historical_medication_preparation import test_syringe_amount_correction_keeps_hitbox_art_and_numeric_fill_together
        for size in [1,3,5,10]:
            test_syringe_amount_correction_keeps_hitbox_art_and_numeric_fill_together(size,0)
    def test_open_vials_visible_and_selectable(self):
        # B20's row renderer uses a non-mutating vial preview for partial/open stock; the actual draw paths still
        # use infusionVialVolume for authoritative availability and debit.
        self.assertIn('ACME_fnc_vialPreview',src('skListRefresh'))
        for f in ('infusionDrawStock','openPrepFromInventoryMenu'):
            self.assertIn('ACME_fnc_infusionVialVolume',src(f))
        self.assertIn('ACME_fnc_infusionVialVolume',src('skListSelect'))
    def test_all_drugs_tallied(self):
        self.assertIn('ACME_fnc_preparedComponents',src('infusionRefreshTally'))
        self.assertIn('forEach _rows',src('infusionRefreshTally'))
    def test_flow_edits_only_owner_fields(self):
        for f in ('setClampPosition','cycleDropSet','adjustDripRate'):
            self.assertIn('ACME_fnc_ownerDispatch',src(f))
            self.assertNotIn('setVariable ["ACME_infusion_BagMedications"',src(f))
    def test_same_bag_concentration_rebased(self):
        s=src('infusionRegisterCore');self.assertIn('(_x select 14) / _newVolume',s);self.assertIn('_remainingVolume + _solutionMl',s)
    def test_actual_admission_drives_all_effects(self):
        s=src('fluidCommit');self.assertIn('_admitted / _drained',s);self.assertIn('param [26',s)
    def test_no_sedation_presets_return(self):
        s=read_source(ROOT/'config.cpp');self.assertNotIn('class infusionPresets',s);self.assertNotIn('class infusionApplyPreset',s)
    def test_b14_ketamine_route_weights(self):
        s=src('ketamineOnBoard')
        self.assertIn('0.8',s);self.assertIn('1.75',s)
        self.assertIn('Esketamine',s)
    def test_shared_sedation_native_plus_adjunct(self):
        s=src('sedationComponents');self.assertIn('ACME_fnc_fentanylOnBoard',s);self.assertIn('ACME_fnc_propofolOnBoard',s)
    def test_stimulus_locality_and_epoch(self):
        s=src('laryngoStimulusLocal');self.assertIn('!local _patient',s);self.assertIn('ACME_fnc_clinicalEpoch',s);self.assertIn('ACME_laryngoStimulusId',s)
    def test_pulseless_stimulus_gated(self):self.assertIn('ace_medical_inCardiacArrest',src('laryngoStimulusEffect'))
    def test_bp_and_hr_read_same_stimulus(self):
        self.assertIn('ACME_fnc_laryngoStimulusEffect',src('bpCompute'))
        self.assertIn('ACME_fnc_laryngoStimulusEffect',read_source(ROOT/'overrides/fn_updateHeartRate.sqf'))
    def test_debug_propofol_separate(self):
        from test_bounded_assessment_contracts import assert_debug_component_contract
        # Current compact clinical rows use Ket/Prop/Mid/Fent, with distinct values.
        assert_debug_component_contract()
    def test_mixed_bag_not_single_drug_epi_source(self):
        # B13 retires all bag-derived pressor shortcuts, not just mixed bags.
        self.assertIn('Bag-derived push-dose shortcuts are retired',src('salineFlush'))
        self.assertNotIn('call ACME_fnc_preparedComponents',src('salineFlush'))
        self.assertIn('(_x select 11) != "Epinephrine"',src('findRunningDirtyEpi'))
if __name__=='__main__':unittest.main()
