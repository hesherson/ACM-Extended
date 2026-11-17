from historical_source import read_source, assert_release_identity
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def src(name): return read_source(ROOT/'functions'/f'fn_{name}.sqf', errors='ignore')
class B28Regression(unittest.TestCase):
    def test_version(self):
        assert_release_identity()
        self.assertIn('CfgPatches',src('postInit'))
        assert_release_identity()
    def test_no_network_blanket_attached_to_wrapped_patient(self):
        from test_historical_state_cleanup import test_immobile_patients_retain_hpmk_without_a_patient_attached_world_object, test_mobile_fallback_drops_once_and_clears_only_hpmk_state
        for state in ('prepped','wrapped','exposed'):
            for condition in ('dead','unconscious','lying'):
                test_immobile_patients_retain_hpmk_without_a_patient_attached_world_object(state,condition)
        for state in ('wrapped','exposed'):
            test_mobile_fallback_drops_once_and_clears_only_hpmk_state(state)
    def test_wrapped_blanket_is_local_simple_object(self):
        from test_historical_state_cleanup import test_hpmk_visuals_are_local_and_pickup_remains_scoped
        test_hpmk_visuals_are_local_and_pickup_remains_scoped()
    def test_obtunded_default_fallback_is_off(self):
        for n in ('obtundedTick','obtundedAuto','consciousnessBudget'):
            self.assertNotIn('getVariable ["ACME_sys_obtunded", true]',src(n))
            self.assertIn('getVariable ["ACME_sys_obtunded", false]',src(n))
    def test_obtunded_tick_can_cleanup_when_master_off(self):
        from test_historical_state_cleanup import test_obtunded_inactive_cleanup_releases_owned_effects_voice_and_input, test_manual_obtundation_remains_active_with_master_disabled
        test_obtunded_inactive_cleanup_releases_owned_effects_voice_and_input('masterOff')
        test_manual_obtundation_remains_active_with_master_disabled()
    def test_voice_true_request_is_clamped_to_actual_state(self):
        t=src('obtundedVoice')
        self.assertIn('private _effectiveMute = _mute',t)
        self.assertIn('ACME_sys_obtunded", false',t)
        self.assertIn('ACME_obtunded", false',t)
        self.assertIn('TFAR_fnc_setForbiddenToSpeak',t)

if __name__=='__main__': unittest.main()
