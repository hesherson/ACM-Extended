"""B35 pressure-change contracts and gas-law invariants; no SQF runtime."""
from pathlib import Path
import math
import random
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / 'functions' / f'fn_{name}.sqf').read_text(encoding='utf-8')


def pressure(altitude):
    # Independent arithmetic oracle; B281 executes production layers and checks
    # published ISA boundary pressures in test_b281_flight_physiology.
    altitude = min(1000000, max(0, altitude))
    value, temperature, base = 1, 288.15, 0
    for top, lapse in ((11000,-.0065),(20000,0),(32000,.001),
                       (47000,.0028),(51000,0),(71000,-.0028),(84852,-.002)):
        distance = max(0,min(altitude,top)-base)
        if lapse:
            updated = temperature + lapse*distance
            value *= (temperature/updated)**(.034163195/lapse)
            temperature = updated
        else:
            value *= math.exp(-.034163195*distance/temperature)
        base = top
    if altitude > base:
        value *= math.exp(-.034163195*(altitude-base)/temperature)
    return min(1,max(1e-9,value))


def expansion(previous_altitude, current_altitude):
    return max(.2, min(5, pressure(previous_altitude) / pressure(current_altitude)))


def usable_sample(sample, owner, epoch, now):
    if not isinstance(sample, list) or len(sample) != 4:
        return False
    p, last_owner, last_epoch, at = sample
    return (isinstance(p, (int, float)) and math.isfinite(p) and 1e-9 <= p <= 1
            and last_owner == owner and last_epoch == epoch
            and isinstance(at, (int, float)) and math.isfinite(at)
            and 0 <= now - at <= 5)


class AmbientPressureMath(unittest.TestCase):
    def test_stationary_altitude_never_accumulates_air(self):
        for altitude in (0, 500, 2400, 5500, 11000):
            air = 1.3
            for _ in range(14400):
                air *= expansion(altitude, altitude)
            self.assertEqual(air, 1.3)

    def test_climb_changes_existing_gas_once(self):
        climbed = expansion(0, 2400)
        self.assertGreater(climbed, 1.3)
        self.assertLess(climbed, 1.4)
        self.assertEqual(climbed * expansion(2400, 2400), climbed)

    def test_descent_reverses_unvented_expansion(self):
        for altitude in (200, 500, 2400, 6000, 11000):
            self.assertAlmostEqual(expansion(0, altitude) * expansion(altitude, 0), 1)

    def test_gas_scaling_cannot_create_air_in_healthy_patient(self):
        self.assertEqual(0 * expansion(0, 11000), 0)

    def test_subdividing_a_climb_does_not_multiply_the_injury(self):
        rng = random.Random(35)
        for _ in range(50):
            steps = [0] + sorted(rng.uniform(0, 6000) for _ in range(100)) + [6000]
            product = math.prod(expansion(a, b) for a, b in zip(steps, steps[1:]))
            self.assertAlmostEqual(product, expansion(0, 6000), places=12)

    def test_extreme_positions_keep_formula_finite(self):
        for altitude in (-1e9, -100, 0, 11000, 50000, 1e9):
            self.assertTrue(math.isfinite(pressure(altitude)))
            self.assertGreaterEqual(pressure(altitude), 1e-9)
            self.assertLessEqual(pressure(altitude), 1)
        self.assertGreater(pressure(11000),pressure(20000))
        self.assertGreater(pressure(20000),pressure(50000))

    def test_reset_migration_and_stall_have_no_replayed_climb(self):
        self.assertFalse(usable_sample([], 2, 3, 10))
        self.assertFalse(usable_sample([1, 1, 3, 9], 2, 3, 10))
        self.assertFalse(usable_sample([1, 2, 2, 9], 2, 3, 10))
        self.assertFalse(usable_sample([1, 2, 3, 4], 2, 3, 10))
        self.assertFalse(usable_sample([1, 2, 3, 11], 2, 3, 10))
        self.assertTrue(usable_sample([1, 2, 3, 9], 2, 3, 10))

    def test_invalid_saved_samples_cannot_supply_a_ratio(self):
        for sample in (None, 1, {}, ['bad', 2, 3, 9], [0, 2, 3, 9],
                       [float('nan'), 2, 3, 9], [1, 2, 3, float('inf')]):
            self.assertFalse(usable_sample(sample, 2, 3, 10))


class PressureSourceContracts(unittest.TestCase):
    def test_altitude_delegates_only_actual_pressure_changes(self):
        s = source('altitudeTick')
        self.assertIn('((_sample select 0) / _pRatio)', s)
        self.assertIn('if (_factor != 1) then', s)
        self.assertIn('[_patient, _factor] call ACME_fnc_ptxAmbientChange', s)
        self.assertNotIn('ACME_altitude_ptxGrowRate', s)
        self.assertNotIn('ACME_altitude_ptxTensionAt', s)
        self.assertNotIn('call ACM_breathing_fnc_handlePneumothorax', s)
        self.assertNotIn('call ACME_fnc_ptxInjury', s)

    def test_pressure_sources_have_no_independent_ptx_state_writer(self):
        for name in ('altitudeTick', 'ventDriveTick'):
            s = source(name)
            self.assertNotRegex(s, r'\[_patient,\s*"ACM_breathing_(?:Tension)?Pneumothorax_State",[^\n]*call ACME_fnc_setVarNet')
            self.assertNotRegex(s, r'setVariable\s*\["ACM_breathing_(?:Tension)?Pneumothorax_State"')

    def test_sampling_is_local_reset_aware_and_cleared_when_disabled(self):
        s = source('altitudeTick')
        self.assertIn('ACME_alt_ptxSample", nil, false', s)
        self.assertIn('ACME_alt_ptxSample", [_pRatio, clientOwner, _epoch, _now], false', s)
        self.assertIn('call ACME_fnc_clinicalEpoch', s)
        self.assertIn('_now - _lastTime <= 5', s)
        self.assertIn('_lastOwner isEqualTo clientOwner', s)
        self.assertIn('ACME_alt_ptxSample", nil, false', source('ownerInit'))

    def test_vent_retains_measured_pressure_and_discrete_injury(self):
        s = source('ventDriveTick')
        self.assertIn('ACME_vent_pip", round _pip', s)
        self.assertIn('ACME_vent_driving", true', s)
        self.assertIn('if (_pip > _pipDanger)', s)
        self.assertIn('if (_dose >= 1)', s)
        self.assertIn('call ACM_breathing_fnc_handlePneumothorax', s)
        self.assertNotIn('ACME_vent_ptxPushRate', s)
        self.assertNotIn('private _dt = 0.25', s)

    def test_genuine_blast_or_pressure_injury_can_renew_a_tension_leak(self):
        for name in ('blastLungInflict', 'ventDriveTick'):
            s = source(name)
            self.assertIn('call ACM_breathing_fnc_handlePneumothorax', s)
            self.assertNotIn('ACM_breathing_TensionPneumothorax_State', s)

    def test_simple_vent_and_hypobaric_oxygen_still_use_effective_settings(self):
        from source_scan import lex
        def has_call(name, call):
            actual = [token.value for token in lex(source(name))]
            expected = [token.value for token in lex(call)]
            return any(actual[start:start + len(expected)] == expected
                       for start in range(len(actual) - len(expected) + 1))
        self.assertIn('call ACME_fnc_ventEffectiveSettings', source('ventDriveTick'))
        self.assertIn('call ACME_fnc_altitudeOxygenCeiling', source('altitudeTick'))
        self.assertTrue(has_call('altitudeOxygenCeiling',
                             '[_patient, _exposure] call ACME_fnc_flightDeliveredFiO2'))
        self.assertTrue(has_call('flightDeliveredFiO2',
                             '[_patient] call ACME_fnc_ventEffectiveSettings'))
        self.assertIn('(_fio2 * _pRatio) / 21', source('altitudeOxygenCeiling'))
        self.assertNotIn('call ACM_core_fnc_setTargetVitalsState',source('altitudeTick'))

    def test_changes_add_no_provider_hints(self):
        for name in ('altitudeTick', 'ventDriveTick'):
            self.assertNotRegex(source(name), r'\b(?:hint|hintSilent|systemChat|cutText)\b')


if __name__ == '__main__':
    unittest.main()
