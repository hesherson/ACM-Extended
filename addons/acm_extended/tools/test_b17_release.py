from backlog_clinical_probes import io_modes_probe
from historical_source import assert_release_consistent
from historical_source import read_source
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')
class B17Release(unittest.TestCase):
    def test_registry_rows_have_valid_shape(self):
        s=read('functions/fn_clinicalFields.sqf')
        # Catch the two concrete malformed rows from B16.
        self.assertNotIn('"ACME_rhythm_torsadesICPThresh",\n    "ACME_rhythm_torsadesStart"',s)
        self.assertNotIn('"ACME_vent_saiKetamineDose",\n    "ACME_procAnalgesiaThreshold"',s)
        self.assertRegex(s,r'"ACME_rhythm_torsadesStart",\s*"cba",\s*true')
    def test_sync_led_and_hitbox_are_aligned_region(self):
        s=read('functions/fn_aedSyncSetup.sqf')
        self.assertIn('[1548, 704, 134, 53]',s)
        self.assertIn('[1564, 719, 30, 30]',s)
        # dot center must be inside hitbox
        bx,by,bw,bh=1548,704,134,53; lx,ly,lw,lh=1571,726,15,15
        self.assertTrue(bx <= lx+lw/2 <= bx+bw and by <= ly+lh/2 <= by+bh)
    def test_torsades_uses_full_time_window(self):
        s=read('functions/fn_genRhythmEKG.sqf')
        self.assertIn('_entrySweeps * _W * 0.03',s)
        self.assertIn('_sampleAhead = (count _arr) * 0.03',s)
        self.assertIn('(_elapsed + _sampleAhead) / (_entryWindow max 0.1)',s)
        self.assertNotIn('_entryLeadIn',s)
    def test_custom_rhythm_does_not_override_cpr_postshock(self):
        s=read('overrides/fn_genEKG.sqf')
        self.assertIn('!(_rhythm in [-1,1,2])',s)
        # Current generator uses the actual audible beat clock, not a second switch-delay timer.
        for key in ('ACM_circulation_AED_Pads_LastBeep','ACME_AED_PreviousRR','ACME_AED_NextRR'):
            self.assertIn(key,s)
        self.assertNotIn('ACME_monitorRhythmSwitchMaxWait',s)
    def test_placement_and_incision_do_not_force_unconsciousness(self):
        io_modes_probe()
        th=read('functions/fn_thoraMouseUp.sqf')
        block=th[th.index('// Incision pain is real'):th.index('// the score:')]
        self.assertNotIn('setUnconscious',block)
        self.assertIn('adjustPainLevel',block)
    def test_local_lidocaine_is_bodypart_specific(self):
        s=read('functions/fn_proceduralAnalgesiaOnBoard.sqf')
        self.assertIn('getMedicationCount',s); self.assertIn('_pi',s)
        self.assertIn('[_patient,"Lidocaine",false,_pi]',s)
    def test_players_not_exempt_from_drug_physiology(self):
        self.assertNotIn('isPlayer _patient',read('functions/fn_ketamineSedationTick.sqf'))
        self.assertNotIn('isPlayer _patient',read('functions/fn_rocuroniumTick.sqf'))
    def test_syringe_rate_is_volume_aware(self):
        s=read('overrides/fn_Syringe_Inject.sqf')
        self.assertIn('ACME_syringe_pushSecPerMl',s)
        self.assertNotIn('_medicationName, 5]]',s)
    def test_compounds_accept_arbitrary_source_funded_combinations(self):
        s=read('functions/fn_skCompoundCommit.sqf')
        self.assertNotIn('verified compatibility list',s)
        self.assertNotIn('_compatible',s)
        self.assertIn('ACME_fnc_medicationTakeSources',s)
    def test_vanilla_naloxone_override_absent(self):
        self.assertFalse((ROOT/'overrides/fn_handleMed_NaloxoneLocal.sqf').exists())
        self.assertNotIn('handleMed_NaloxoneLocal',read('config.cpp'))
    def test_version_pair(self):
        assert_release_consistent()
if __name__=='__main__': unittest.main()
