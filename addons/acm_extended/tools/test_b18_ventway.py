from backlog_clinical_probes import rosc_stress_probe
from historical_source import read_source, assert_release_identity
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B18Source(unittest.TestCase):
    def test_no_med_transaction_chatter(self):
        tree='\n'.join(read_source(p, encoding='utf-8-sig',errors='ignore') for p in (ROOT/'functions').glob('*.sqf'))
        for text in ('Awaiting patient-owner confirmation','submitted to %2','Medication not accepted (','Reserved syringe/solution returned'):
            self.assertNotIn(text,tree)
    def test_pc_has_real_pinsp_control(self):
        drive=read('functions/fn_ventDriveTick.sqf')
        live=read('functions/fn_ventPanelLiveEdit.sqf')
        refresh=read('functions/fn_ventPanelRefresh.sqf')
        self.assertIn('call ACME_fnc_ventEffectiveSettings',drive)
        self.assertIn('ACME_vent_pinsp',read('functions/fn_ventEffectiveSettings.sqf'))
        self.assertIn('_pipMand = _pinsp',drive)
        self.assertIn('((_pinsp - _peep) max 0)',drive)
        self.assertIn('ACME_vent_pinsp',live)
        self.assertIn('ctrlSetText "PInsp"',refresh)
    def test_mode_screen_resumes_actual_mode(self):
        s=read('functions/fn_ventPanelShowScreen.sqf')
        self.assertIn('private _modeIdx = _modesNow find _modeNow',s)
        self.assertIn('setVariable ["ACME_vent_selIdx", _modeIdx]',s)
    def test_simv_supports_spontaneous_ps_breaths(self):
        s=read('functions/fn_ventDriveTick.sqf')
        self.assertIn('_vtiSpont = [_intrinsic, _psup, _compEff] call _spontVtFor',s)
        self.assertIn('_mandatoryBpm + _spontBpm',s)
        self.assertIn('ACME_vent_mvDelivered',s)
        self.assertNotIn('private _spontRR = _patient getVariable ["ACM_breathing_RespirationRate", 0]',read('functions/fn_ventStatusTick.sqf'))
    def test_pressure_support_and_trigger_travel_with_device(self):
        fields=read('functions/fn_ventDeviceFields.sqf')
        for key in ('ACME_vent_pinsp','ACME_vent_psup','ACME_vent_trigSensCmH2O'):
            self.assertIn(key,fields)
        self.assertNotIn('ACME_vent_pSupport',fields)
    def test_capno_only_reads_dyssync(self):
        s=read('functions/fn_capnoMorph.sqf')
        self.assertIn('ACME_vent_dyssync',s)
        self.assertNotIn('_para =',s)
        self.assertNotIn('setVariable ["ACME_vent_dyssync"',s)
    def test_fighting_decompensates_respiratory_first(self):
        s=read('functions/fn_ventDriveTick.sqf')
        for key in ('ACME_vent_dyssyncRiseSec','ACME_vent_fightHRAdjust','ACME_vent_fightResistAdjust','ACME_vent_fightO2PenaltyMax','ACME_vent_mvAdequacy'):
            self.assertIn(key,s)
        for forbidden in ('ACME_fnc_rhythmSet','ACME_fnc_onCardiacArrest','setUnconscious'):
            # These should not appear in the newly rewritten dyssync block.
            a=s.index('// Dyssynchrony is actual unresolved respiratory effort')
            b=s.index('// exact BPM.')
            self.assertNotIn(forbidden,s[a:b])
    def test_rocuronium_cannot_bank_arrest_stress(self):
        s=read('functions/fn_rocuroniumTick.sqf')
        for key in ('ace_medical_inCardiacArrest','ACME_roc_postROSCGraceUntil','ACME_roc_awakeHRMax'):
            self.assertIn(key,s)
        self.assertIn('ACME_roc_postROSCStressDelay = 15',read('functions/fn_postInit.sqf'))
        # The real registered ROSC callback delegates the reset to its actual single writer.
        rosc_stress_probe()
    def test_vitals_stress_is_bounded_additive(self):
        s=read('overrides/fn_handleUnitVitals.sqf')
        self.assertIn('ACME_vent_fightHRAdjust',s)
        self.assertIn('ACME_vent_fightResistAdjust',s)
    def test_registry_has_new_fields_as_rows(self):
        s=read('functions/fn_clinicalFields.sqf')
        for key in ('ACME_vent_pinsp','ACME_vent_mvDelivered','ACME_vent_fightHRAdjust','ACME_roc_postROSCGraceUntil'):
            self.assertRegex(s,rf'"{key}",\s*"(?:cba)?",\s*true')
    def test_version_pair(self):
        assert_release_identity()
        assert_release_identity()

class B18Reference(unittest.TestCase):
    def test_pc_vt_falls_with_compliance(self):
        def vt(pinsp=20,peep=5,comp=1): return 500*max(pinsp-peep,0)/15*comp
        self.assertAlmostEqual(vt(comp=1),500)
        self.assertAlmostEqual(vt(comp=.5),250)
        self.assertEqual(vt(pinsp=15,peep=15),0)
    def test_simv_total_rate_includes_spontaneous(self):
        def rates(set_bpm,intrinsic,can=True):
            spont=max(intrinsic-set_bpm,0) if can and intrinsic>set_bpm else 0
            return set_bpm+spont,spont
        self.assertEqual(rates(12,20),(20,8))
        self.assertEqual(rates(12,8),(12,0))
    def test_dyssync_ramp_is_not_instant(self):
        cur=0; target=1; dt=.25; tau=18
        cur += (target-cur)*min(dt/tau,1)
        self.assertGreater(cur,0); self.assertLess(cur,.02)
    def test_stress_caps_are_sub_arrest(self):
        self.assertLessEqual(18,20)
        self.assertLessEqual(9,10)

    def test_tbi_uses_actual_vent_dyssync_not_spontaneous_rr_as_fighting(self):
        t=read('functions/fn_tbiHandle.sqf')
        self.assertIn('getVariable ["ACME_vent_dyssync", 0]',t)
        a=t.index("// Use the ventilator's actual unresolved dyssynchrony state.")
        b=t.index('_state set ["mechCeil"',a)
        self.assertNotIn('ACME_resp_neuralRR',t[a:b])

if __name__=='__main__': unittest.main()
