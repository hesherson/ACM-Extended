"""B38 numerical acceptance model and SQF integration contracts, not an Arma runtime"""
from historical_source import read_source
import math
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return read_source(ROOT / name, encoding="utf-8-sig")


def clean(value):
    return min(16.0, max(0.0, value)) if isinstance(value, (float, int)) and math.isfinite(value) else 0.0


def interaction(ket=0, prop=0, mid=0, opioid=0, amio=0, esmolol=0, phent=0, reserve=1, arrest=False):
    """Numerical acceptance model for bounded output targets, separate from native effects"""
    ket, prop, mid, opioid, amio, esmolol, phent = map(clean, (ket, prop, mid, opioid, amio, esmolol, phent))
    reserve = min(1, max(0, reserve)) if isinstance(reserve, (float, int)) and math.isfinite(reserve) else 1
    vulnerability = 1 + 0.4 * (1 - reserve)
    resp = opioid * (prop + mid + .25 * ket) + .7 * prop * mid + .2 * ket * mid
    dep = opioid * (prop + mid) + .6 * prop * mid
    nodal = amio * esmolol
    resp, dep, nodal, phent = resp / (1 + resp), dep / (1 + dep), nodal / (1 + nodal), phent / (.5 + phent)
    return (0 if arrest else -26 * nodal + 12 * phent, -14 * dep * vulnerability - 8 * nodal * vulnerability - 28 * phent, -8 * resp, -.20 * resp)


def hypnosis(ket=0, prop=0, mid=0, fent_adjunct=0, morphine=0):
    factor = 1 + min(1, fent_adjunct + .5 * morphine) * .35
    cross = min(16, prop) * min(16, mid)
    return (ket + prop + mid + .25 * cross / (.5 + cross)) * factor


def native_iv_effect(age, onset, plateau, duration):
    """ACM native IV envelope used only to exercise onset/overlap/washout scenarios"""
    if age < 0 or age >= duration:
        return 0.0
    if onset < age < onset + plateau:
        return 1.0
    if age > onset + plateau:
        return .5 * math.cos((age - onset - plateau) / ((duration - plateau - onset) / 3.1)) + .5
    return max(0, min(1, math.sin(age * 3.113 / (2 * onset))))


class InteractionBehavior(unittest.TestCase):
    def test_no_drugs_has_no_added_effect(self):
        self.assertEqual(interaction(), (0, 0, 0, 0))

    def test_each_interaction_drug_alone_retains_native_effect_only(self):
        for name in ("ket", "prop", "mid", "opioid", "amio", "esmolol"):
            with self.subTest(name=name):
                self.assertEqual(interaction(**{name: 2}), (0, 0, 0, 0))

    def test_unrelated_supported_families_do_not_invent_generic_penalty(self):
        self.assertEqual(interaction(ket=1, amio=1), (0, 0, 0, 0))

    def test_opioid_benzo_has_respiratory_and_pressure_risk(self):
        hr, svr, rr, co2 = interaction(mid=1, opioid=1)
        self.assertEqual(hr, 0)
        self.assertLess(svr, 0)
        self.assertLess(rr, -3)
        self.assertLess(co2, -.09)

    def test_opioid_propofol_has_respiratory_and_pressure_risk(self):
        _, svr, rr, co2 = interaction(prop=1, opioid=1)
        self.assertLess(svr, 0)
        self.assertLess(rr, 0)
        self.assertLess(co2, 0)

    def test_propofol_midazolam_interacts_without_any_opioid(self):
        _, svr, rr, co2 = interaction(prop=1, mid=1)
        self.assertLess(svr, 0)
        self.assertLess(rr, 0)
        self.assertLess(co2, 0)

    def test_ketamine_opioid_cross_effect_is_more_restrained(self):
        self.assertGreater(interaction(ket=1, opioid=1)[2], interaction(prop=1, opioid=1)[2])
        self.assertEqual(interaction(ket=1, opioid=1)[1], 0)

    def test_ketamine_midazolam_can_also_depress_breathing(self):
        self.assertLess(interaction(ket=1, mid=1)[2], 0)

    def test_hypovolemia_or_acidosis_proxy_increases_hypotension(self):
        normal = interaction(prop=1, opioid=1, reserve=1)
        vulnerable = interaction(prop=1, opioid=1, reserve=.05)
        self.assertLess(vulnerable[1], normal[1])
        self.assertEqual(vulnerable[2:], normal[2:])

    def test_larger_overlapping_exposure_has_monotonic_added_risk(self):
        a = interaction(prop=.1, mid=.1, opioid=.1, amio=.1, esmolol=.1)
        b = interaction(prop=1, mid=1, opioid=1, amio=1, esmolol=1)
        c = interaction(prop=4, mid=4, opioid=4, amio=4, esmolol=4)
        self.assertTrue(all(x > y > z for x, y, z in zip(a, b, c)))

    def test_huge_exposures_remain_bounded(self):
        hr, svr, rr, co2 = interaction(ket=1e38, prop=1e38, mid=1e38, opioid=1e38, amio=1e38, esmolol=1e38, phent=1e38, reserve=0)
        self.assertTrue(all(math.isfinite(x) for x in (hr, svr, rr, co2)))
        self.assertGreaterEqual(hr, -26)
        self.assertGreaterEqual(svr, -58.8)
        self.assertGreaterEqual(rr, -8)
        self.assertGreaterEqual(co2, -.20)

    def test_bad_inputs_cannot_produce_nan(self):
        self.assertEqual(interaction(prop=float("nan"), mid=float("inf"), opioid=-1, reserve=None), (0, 0, 0, 0))

    def test_nodal_combination_lowers_rate_and_resistance(self):
        self.assertEqual(interaction(amio=1, esmolol=1), (-13, -4, 0, 0))

    def test_arrest_does_not_create_a_heart_rate(self):
        self.assertEqual(interaction(amio=2, esmolol=2, phent=2, arrest=True)[0], 0)

    def test_systemic_phentolamine_is_not_an_inert_local_class(self):
        hr, svr, rr, co2 = interaction(phent=1)
        self.assertGreater(hr, 0)
        self.assertLess(svr, -18)
        self.assertEqual((rr, co2), (0, 0))

    def test_phentolamine_and_depressants_add_pressure_risk(self):
        self.assertLess(interaction(phent=1, prop=1, mid=1)[1], interaction(prop=1, mid=1)[1])

    def test_opioids_alone_do_not_become_hypnotics(self):
        self.assertEqual(hypnosis(fent_adjunct=1, morphine=8), 0)

    def test_morphine_potentiates_an_existing_hypnotic(self):
        self.assertGreater(hypnosis(mid=.5, morphine=1), hypnosis(mid=.5))

    def test_morphine_fentanyl_adjunct_is_capped_together(self):
        self.assertEqual(hypnosis(ket=1, fent_adjunct=1, morphine=20), 1.35)

    def test_propofol_benzo_hypnosis_exceeds_simple_sum(self):
        self.assertGreater(hypnosis(prop=.5, mid=.5), 1)

    def test_no_overlap_has_no_interaction(self):
        for now in range(0, 1700, 10):
            prop = native_iv_effect(now, 90, 180, 480)
            opioid = native_iv_effect(now - 500, 10, 840, 960)
            self.assertEqual(interaction(prop=prop, opioid=opioid), (0, 0, 0, 0))

    def test_overlap_follows_onset_and_fades_without_latch(self):
        def effect(now):
            return interaction(prop=native_iv_effect(now, 90, 180, 480), opioid=native_iv_effect(now, 10, 840, 960))
        self.assertEqual(effect(0), (0, 0, 0, 0))
        self.assertLess(effect(100)[2], 0)
        self.assertGreater(effect(450)[2], effect(100)[2])
        self.assertEqual(effect(480), (0, 0, 0, 0))

    def test_same_admitted_exposure_is_container_and_order_independent(self):
        orders = ((.2, .3, .5), (.5, .3, .2))
        results = [interaction(prop=sum(order), opioid=1) for order in orders]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], interaction(prop=1, opioid=1))

    def test_repeated_tick_evaluation_does_not_stack_effects(self):
        original = interaction(prop=1, mid=1, opioid=1)
        for _ in range(1000):
            self.assertEqual(interaction(prop=1, mid=1, opioid=1), original)

    def test_vanilla_naloxone_removal_eliminates_opioid_cross_term(self):
        self.assertLess(interaction(mid=1, opioid=1)[2], 0)
        self.assertEqual(interaction(mid=1, opioid=0), (0, 0, 0, 0))
        # The other depressants remain active if there is also propofol onboard
        self.assertLess(interaction(mid=1, prop=1, opioid=0)[2], 0)


class InteractionIntegration(unittest.TestCase):
    def test_only_current_native_effect_records_are_read(self):
        text = source("functions/fn_medicationInteractions.sqf")
        self.assertIn('[_patient, _class, false] call ace_medical_status_fnc_getMedicationCount', text)
        for forbidden in ('ACME_medicationAdmitted', 'ACME_infusions', 'ACME_Narc', 'ACME_serum_'):
            self.assertNotIn(forbidden, text)

    def test_no_new_state_or_forced_disease(self):
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', source("functions/fn_medicationInteractions.sqf"), flags=re.S)
        for forbidden in ('setVariable', 'setVarNet', 'addMedicationAdjustment', 'random', 'rhythmToggle', 'setCardiacArrest', 'remoteExec', 'waitAndExecute'):
            self.assertNotIn(forbidden, text)

    def test_sedation_physiology_is_owner_only_and_applies_each_output_once(self):
        text = source("functions/fn_sedationPhysiology.sqf")
        self.assertIn('!local _patient', text)
        self.assertEqual(text.count('call ACME_fnc_medicationInteractions'), 1)
        for index in range(4):
            self.assertEqual(text.count(f'_interactions select {index}'), 1)
        self.assertNotIn('-0.12 *', text)

    def test_native_vitals_consume_single_shared_target(self):
        text = source("overrides/fn_handleUnitVitals.sqf")
        self.assertEqual(text.count('call ACME_fnc_sedationPhysiology'), 1)
        for index in range(4):
            self.assertEqual(text.count(f'_sedPhys select {index}'), 1)
        self.assertLess(text.index('!local _unit'), text.index('call ACME_fnc_sedationPhysiology'))

    def test_naloxone_remains_vanilla_and_is_not_reimplemented(self):
        text = source("functions/fn_medicationAvailability.sqf")
        self.assertNotIn('Naloxone', text)
        self.assertNotIn('Opioid', text)
        self.assertNotIn('Naloxone', source("functions/fn_medicationInteractions.sqf").split('params [')[1])

    def test_new_helpers_do_not_disclose_treatment_hints(self):
        for name in ('functions/fn_medicationInteractions.sqf', 'functions/fn_sedationComponents.sqf', 'functions/fn_sedationPhysiology.sqf'):
            text = source(name)
            for forbidden in ('displayTextStructured', 'hint ', 'systemChat', 'addToLog'):
                self.assertNotIn(forbidden, text)

    def test_sedation_six_field_contract_and_existing_fentanyl_reader_remain(self):
        text = source("functions/fn_sedationComponents.sqf")
        self.assertIn('[_ket, _prop, _mid, _fent, _factor,', text)
        self.assertIn('call ACME_fnc_fentanylOnBoard', text)
        self.assertIn('forEach ["Morphine", "Morphine_IV"]', text)

    def test_phentolamine_native_reference_and_local_route_are_preserved(self):
        cfg = source('config.cpp')
        block = cfg.split('class Phentolamine: ACM_IM_Medication')[1].split('};')[0]
        self.assertIn('maxEffectDose = 5', block)
        local = source('overrides/fn_medicationLocal.sqf')
        self.assertIn('!_preparedMixture', local)
        self.assertIn('call ACME_fnc_medicationExposure', local)

    def test_game_target_coefficients_match_reviewed_bounds(self):
        text = source('functions/fn_medicationInteractions.sqf')
        for fragment in ('private _rr = -8 * _respFraction', 'private _co2 = -0.20 * _respFraction',
                         'private _svr = -14 * _depressantFraction', 'private _hr = -26 * _nodalFraction',
                         '_svr = _svr - 8 * _nodalFraction', '_svr = _svr - 28 * _phentFraction'):
            self.assertIn(fragment, text)

    def test_legacy_amiodarone_reference_is_normalized_before_bounding(self):
        text = source('functions/fn_medicationInteractions.sqf')
        self.assertIn('["Amiodarone", "Amiodarone_IV"] call _get', text)
        self.assertLess(text.index('_value = _value *'), text.index('_value max 0 min 16'))
        self.assertEqual(150 * (1 / 150), 1)


if __name__ == '__main__':
    unittest.main()
