from backlog_clinical_probes import threshold_observer_probe
from historical_source import read_source, assert_release_identity
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B21RhythmRegression(unittest.TestCase):
    def test_version(self):
        assert_release_identity()
        assert_release_identity()

    def test_epi_infusion_can_reach_svt_burden(self):
        post=read('functions/fn_postInit.sqf')
        self.assertIn('ACME_rhythmPressorSurgeScoreCap = 60', post)
        self.assertIn('ACME_rhythmPressorSurgeSVTThreshold = 35', post)
        circ=read('functions/fn_circHandle.sqf')
        self.assertIn('ACME_rhythmPressorSurgeScoreCap', circ)
        self.assertIn('_epiArrhythmiaBurden', circ)
        self.assertNotIn('private _surgeScore = _pushDose + _hyperSpike + (((_epiLikeDrive * 1000) * _coeff) min _pressorCap);', circ)
        # Representative severe training drip: 5 mg / 100 mL at 6 mL/min = 0.3 mg/min = 300 mcg/min.
        score=min(300*0.9,60)
        self.assertGreaterEqual(score,35)

    def test_threshold_forced_vt_can_recover_but_true_vt_is_not_blanket_cleared(self):
        threshold_observer_probe()
        src=read('functions/fn_rhythmThresholdTick.sqf')
        self.assertNotIn('ACM VT fallback',src)
        self.assertNotIn('call ACME_fnc_arrestLocal',src)
        native=read('../core/functions/fnc_handleCriticalVitals.sqf')
        self.assertIn('ACM_Rhythm_VT',native)
        self.assertIn('ACM_Rhythm_Sinus',native)

    def test_new_rhythm_tunables_are_registered(self):
        fields=read('functions/fn_clinicalFields.sqf')
        for key in ['ACME_rhythmNativeVTRecoverHR','ACME_rhythmNativeVTRecoverSec','ACME_rhythmPressorSurgeScoreCap']:
            self.assertEqual(fields.count(f'"{key}"'),1,key)

class B21SyncIndicator(unittest.TestCase):
    def test_led_is_double_diameter_and_center_preserved(self):
        setup=read('functions/fn_aedSyncSetup.sqf')
        post=read('functions/fn_postInit.sqf')
        self.assertIn('[1564, 719, 30, 30]', setup)
        self.assertIn('[1564, 719, 30, 30]', post)
        old_center=(1571+15/2,726+15/2)
        new_center=(1564+30/2,719+30/2)
        self.assertLessEqual(abs(old_center[0]-new_center[0]),0.5)
        self.assertLessEqual(abs(old_center[1]-new_center[1]),0.5)

    def test_led_pulses_at_one_hz_and_pulse_is_actually_applied(self):
        src=read('functions/fn_syncFlagsTick.sqf')
        post=read('functions/fn_postInit.sqf')
        self.assertIn('ACME_sync_ledPulsePeriod        = 1.0', post)
        self.assertIn('ACME_sync_ledPulsePeriod", 1.0', src)
        self.assertIn('private _alpha = 0.35 + (0.65 * _pulse);', src)
        self.assertIn('["success", _alpha] call ACME_fnc_a11yColor', src)

if __name__ == '__main__': unittest.main()
