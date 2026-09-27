"""Offline pleural-context contracts and scenarios; does not execute SQF/Arma."""
from historical_source import read_source
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def source(name):
    return read_source(ROOT / 'functions' / f'fn_{name}.sqf', encoding='utf-8')


def coverage(holes=(), tracked=0, processed=0, native_records=-1, native_holes=-1):
    """Boundary scenarios for persisted generated holes plus not-yet-generated wounds."""
    pending = max(0, tracked - processed)
    covered = sum(sealed or i < native_holes for i, sealed in enumerate(holes))
    covered += min(pending, max(0, native_records - processed))
    total = len(holes) + pending
    return total - covered, total, covered


def outflow(open_holes, covered, occlusion=0, ncd=0, drain=False):
    result = .1 * open_holes
    if covered:
        result += (1.5 if open_holes == 0 else .15) * (1 - occlusion)
    return max(result, 1.4 * ncd, 5 if drain else 0)


class ContextScenarios(unittest.TestCase):
    def test_closed_residual_ptx_has_no_external_outlet(self):
        self.assertEqual(coverage(), (0, 0, 0))
        self.assertEqual(outflow(0, 0), 0)

    def test_covered_entry_unfound_exit_is_not_full_coverage(self):
        open_holes, total, covered = coverage([True, False], tracked=1, processed=1)
        self.assertEqual((open_holes, total, covered), (1, 2, 1))
        self.assertAlmostEqual(outflow(open_holes, covered), .25)
        self.assertGreater(.35 * open_holes, outflow(open_holes, covered))

    def test_generated_pair_and_pending_new_injury_are_distinct(self):
        self.assertEqual(coverage([True, True], tracked=2, processed=1), (1, 3, 2))

    def test_native_treatment_survives_later_minigame_open(self):
        self.assertEqual(coverage(tracked=2, native_records=2), (0, 2, 2))
        # The generator later creates a covered entry/exit pair for one record.
        self.assertEqual(coverage([True, True, True], tracked=2, processed=2,
                                  native_records=2), (0, 3, 3))

    def test_native_seal_cannot_cover_a_new_injury(self):
        self.assertEqual(coverage(tracked=3, native_records=2), (1, 3, 2))
        self.assertEqual(coverage([False, False, False], tracked=2, processed=2,
                                  native_records=1, native_holes=2), (1, 3, 2))

    def test_drain_capacity_does_not_stack_with_duplicate_icons(self):
        self.assertEqual(outflow(0, 1), outflow(0, 8))
        self.assertEqual(outflow(0, 8, ncd=1, drain=True), 5)
        self.assertEqual(outflow(4, 2, ncd=1, drain=True), 5)

    def test_partial_ncd_remains_useful_without_becoming_full_drain(self):
        self.assertAlmostEqual(outflow(0, 0, ncd=.5), .7)
        self.assertLess(outflow(0, 0, ncd=1), 3)
        self.assertGreaterEqual(outflow(4, 0, drain=True), 3 + 1.4)

    def test_dry_patent_seal_can_outflow_a_moderate_persistent_leak(self):
        self.assertGreater(outflow(0, 2), 1)
        self.assertEqual(outflow(0, 2, occlusion=1), 0)


class ContextSourceContracts(unittest.TestCase):
    def test_context_is_read_only_and_does_not_reveal_diagnosis(self):
        s = source('ptxContext')
        for forbidden in ('setVariable', 'setVarNet', 'displayText', 'hint ', 'medLog', 'globalEvent', 'addPerFrameHandler'):
            self.assertNotIn(forbidden, s)
        self.assertIn('[_open, _total, _ventCapacity, _bleedSource, _ppvFactor max 1 min 3, _hasDrain, _hasSealOutlet]', s)

    def test_discovery_flag_cannot_change_physiology(self):
        s = source('ptxContext')
        self.assertIn('_x param [4, false, [false]]', s)
        self.assertNotIn('_x param [3,', s)
        self.assertNotIn('_x select 3', s)
        self.assertIn('"ACME_CS_processedPenetratingCount"', s)
        self.assertIn('"ACME_CS_penetratingWounds"', s)
        self.assertIn('private _pending = ((count _tracked) - _processed) max 0;', s)

    def test_generation_does_not_invent_skin_holes_from_closed_disease(self):
        s = source('chestSealGenHoles')
        for disease in ('ACM_breathing_Pneumothorax_State', 'ACM_breathing_TensionPneumothorax_State',
                        'ACM_breathing_Hemothorax_State', 'ACM_breathing_Hemothorax_Fluid'):
            self.assertNotIn(disease, s)
        self.assertIn('for "_recordIndex" from _processed', s)
        self.assertNotIn('_frontExisting + _backExisting', s)
        self.assertIn('_holes = _holes select {(_x select 0) in ["front", "back"]};', s)

    def test_native_covered_holes_reappear_sealed_without_reordering(self):
        s = source('chestSealGenHoles')
        self.assertIn('_forEachIndex < _nativeHoleCount', s)
        self.assertIn('_hole set [3, true]; _hole set [4, true];', s)
        self.assertIn('_recordIndex < _nativeCount', s)
        self.assertIn('_nativeCount >= 0 && {_historical}', s)
        self.assertIn('["front", _coveredRecord] call _fnc_mkHole', s)
        self.assertIn('["back", _coveredRecord] call _fnc_mkHole', s)
        self.assertNotIn('ACME_fnc_ptxInjury', s)

    def test_new_penetration_is_not_lost_to_old_visual_cap(self):
        s = source('chestSealGenHoles')
        self.assertIn('if (_frontCount < _maxPerSide || {!_historical}) then', s)
        self.assertIn('_tracked pushBack [_id, -1, -1]', s)
        self.assertIn('private _wanted = ((ceil _amount) max 1) min _maxPerSide', s)

    def test_side_state_overrides_stale_native_aggregate(self):
        s = source('ptxContext')
        self.assertIn('if (!_hasSideState) then', s)
        self.assertIn('_nativeThora in [1, 2]', s)
        self.assertIn('_tract == "finger" && {!_sealed}', s)
        self.assertIn('_ventCapacity max 5.0', s)
        self.assertIn('_ventCapacity max (1.4 * _ncdPatency)', s)

    def test_seal_clog_source_is_current_external_bleeding(self):
        s = source('ptxContext')
        self.assertIn('_openWounds getOrDefault ["body", []]', s)
        self.assertIn('_x param [2, 0, [0]]', s)
        self.assertIn('_id in _injuryMap', s)
        self.assertIn('((_amount max 0) * (_bleeding max 0))', s)
        self.assertNotIn('Hemothorax_Fluid', s)
        self.assertNotIn('Hemothorax_State', s)
        self.assertNotIn('ace_medical_woundBleeding', s)

    def test_ppv_needs_actual_delivery_and_recent_active_bvm(self):
        s = source('ptxContext')
        for key in ('ACME_vent_connected', 'ACME_vent_driving', 'ACME_vent_pip',
                    'ACM_breathing_BVM_provider', 'ACME_bvm_lastBreathServer'):
            self.assertIn(key, s)
        self.assertIn('serverTime - _lastBreath', s)
        self.assertIn('_breathAge <= 12', s)
        self.assertIn('call ACME_fnc_ventEffectiveSettings', s)
        self.assertIn('alive _provider && {_breathAge >= 0} && {_breathAge <= 12}', s)
        for forbidden in ('ACE_isUnconscious', 'hasStableVitals', 'respirationRate', 'bloodPressure', 'ACME_vent_mode'):
            self.assertNotIn(forbidden, s)

    def test_native_coverage_snapshots_do_not_use_global_seal_boolean(self):
        s = source('ptxContext')
        self.assertIn('ACME_ptx_nativeSealCount', s)
        self.assertIn('ACME_ptx_nativeSealHoleCount', s)
        self.assertNotIn('ACM_breathing_ChestSeal_State', s)


if __name__ == '__main__':
    unittest.main()
