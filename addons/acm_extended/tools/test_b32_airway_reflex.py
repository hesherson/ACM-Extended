"""B32 offline source contracts + independent math/compartment reference checks.
These do not execute SQF, render Arma, or prove clinical accuracy.
"""
from historical_source import read_source
from pathlib import Path
import math
import unittest

ROOT = Path(__file__).resolve().parents[1]
def source(name):
    return read_source(ROOT / 'functions' / ('fn_' + name + '.sqf'), encoding='utf-8')

def response(ket=0, prop=0, mid=0, factor=1, stimulus=1,
             alive=True, arrest=False, paralyzed=False, native=True, owned=False):
    if not alive or arrest or paralyzed:
        return 0.0
    if not native and not (owned and ket + prop + mid > 0):
        return 0.0
    suppression = (max(ket, 0) * .45 + max(prop, 0) + max(mid, 0) * .8) * max(factor, 1)
    sensitivity = math.exp(-2.5 * suppression)
    return min(1, max(0, 1 - math.exp(-2.3 * sensitivity * min(3, max(0, stimulus)))))


def pool(vomit=0, blood=0, emesis=(), secretions=(), ledger=()):
    """Independent compartment oracle: native fluids take precedence, not ownership."""
    stamp = (vomit, 0, emesis) if vomit > 0 else (0, blood, ())
    kind = 'v' if vomit > 0 else 'b' if blood > 0 else ''
    target = min(8, vomit * 2) if vomit > 0 else min(6, blood * 2)
    if not kind and len(secretions) == 2 and secretions[1] > 0:
        kind, target = 's', min(4, secretions[1])
        stamp += (secretions[0],)
    if kind == 'v' and len(emesis) == 3 and emesis[1] == vomit:
        target = min(8, max(1, emesis[2]))
    if ledger:
        old_stamp = ledger[0]
        if len(old_stamp) == 3:
            if kind == 'v':
                old_stamp = (old_stamp[0], 0, old_stamp[2])
            elif kind == 'b' and old_stamp[0] == 0:
                old_stamp = (0, old_stamp[1], ())
        if old_stamp == stamp:
            target = min(target, max(0, ledger[1]))
    return stamp, kind, target if kind else 0


class ReflexBehavior(unittest.TestCase):
    def test_each_hypnotic_continuously_attenuates(self):
        for drug in ('ket', 'prop', 'mid'):
            curve = [response(**{drug: x / 100}) for x in range(401)]
            self.assertTrue(all(a >= b for a, b in zip(curve, curve[1:])))
            self.assertGreater(curve[0], curve[-1])

    def test_old_point_eight_boundary_has_no_jump(self):
        for drug in ('ket', 'prop', 'mid'):
            self.assertLess(abs(response(**{drug: .79999}) - response(**{drug: .80001})), .0001)

    def test_repeated_rough_instrumentation_can_still_provoke(self):
        for exposure in (.5, 1, 2):
            self.assertGreater(response(prop=exposure, stimulus=3), response(prop=exposure, stimulus=1))
            self.assertGreater(response(prop=exposure, stimulus=3), 0)

    def test_ketamine_not_equated_to_reliable_reflex_abolition(self):
        self.assertGreater(response(ket=1), response(prop=1))

    def test_arrest_death_and_paralysis_always_zero(self):
        for flag in ({'arrest': True}, {'alive': False}, {'paralyzed': True}):
            for depth in (0, .5, 1, 10):
                self.assertEqual(response(prop=depth, stimulus=3, **flag), 0)

    def test_absent_reflex_requires_owned_active_hypnotic_exception(self):
        self.assertEqual(response(native=False, stimulus=3), 0)
        self.assertEqual(response(native=False, prop=1, stimulus=3), 0)
        self.assertEqual(response(native=False, owned=True, stimulus=3), 0)
        self.assertGreater(response(native=False, owned=True, prop=1, stimulus=3), 0)

    def test_opioid_factor_remains_an_adjunct(self):
        self.assertEqual(response(factor=1.35), response(factor=1))
        self.assertLess(response(prop=1, factor=1.35), response(prop=1, factor=1))

    def test_stimulus_is_bounded(self):
        self.assertEqual(response(stimulus=99), response(stimulus=3))
        self.assertEqual(response(stimulus=-1), 0)


class FluidBehavior(unittest.TestCase):
    def test_secretions_are_visible_without_native_vomit_or_blood(self):
        self.assertEqual(pool(secretions=('a', 3))[1:], ('s', 3))

    def test_pending_secretions_do_not_refill_partly_suctioned_blood(self):
        stamp, _, _ = pool(blood=1)
        self.assertEqual(pool(blood=1, secretions=('new', 3), ledger=(stamp, .5))[1:], ('b', .5))

    def test_added_blood_does_not_refill_partially_suctioned_vomit(self):
        event = ('vomit-event', 1, 4)
        stamp, _, _ = pool(vomit=1, emesis=event)
        self.assertEqual(pool(vomit=1, blood=1, emesis=event, ledger=(stamp, 1))[1:], ('v', 1))

    def test_b31_ledger_retains_partial_vomit_after_stamp_upgrade(self):
        event = ('vomit-event', 1, 4)
        self.assertEqual(pool(vomit=1, blood=1, emesis=event, ledger=((1, 1, event), 1))[1:], ('v', 1))

    def test_partial_secretions_survive_intervening_native_contamination(self):
        stamp, _, _ = pool(secretions=('a', 3))
        self.assertEqual(pool(secretions=('a', 2), ledger=(stamp, 2))[2], 2)
        self.assertEqual(pool(blood=1, secretions=('a', 2))[1:], ('b', 2))
        self.assertEqual(pool(secretions=('a', 2))[1:], ('s', 2))

    def test_native_vomit_precedence_and_emesis_identity_retained(self):
        self.assertEqual(pool(vomit=1, blood=1, secretions=('a', 3), emesis=('v1', 1, 4))[1:], ('v', 4))

    def test_late_old_episode_suction_cannot_apply_to_new_secretions(self):
        old_stamp, _, _ = pool(secretions=('old', 2))
        new_stamp, _, amount = pool(secretions=('new', 3), ledger=(old_stamp, .5))
        self.assertNotEqual(old_stamp, new_stamp)
        self.assertEqual(amount, 3)

    def test_secretions_are_finite_and_capped(self):
        self.assertEqual(pool(secretions=('a', 40))[2], 4)
        self.assertEqual(pool(secretions=('a', 0))[1:], ('', 0))


class SourceContracts(unittest.TestCase):
    def test_all_reflex_paths_share_graded_reader(self):
        for name in ('laryngoPassTube', 'laryngoConsequenceLocal'):
            text = source(name)
            self.assertIn('call ACME_fnc_laryngoReflexChance', text)
            self.assertNotIn('ACME_vent_saiKetamineDose', text)
        text = source('laryngoReflexChance')
        self.assertIn('ACME_ket_sedated', text)
        self.assertIn('_load > 0', text)
        self.assertNotIn('setVariable', text)

    def test_arrest_branch_cannot_play_gag_or_create_vomit(self):
        text = source('laryngoConsequenceLocal')
        start = text.index('if (_patient getVariable ["ace_medical_inCardiacArrest", false]) exitWith')
        end = text.index('private _chance = [_patient, 1 +', start)
        branch = text[start:end]
        for forbidden in ('playSound', 'AirwayObstructionVomit_State', 'AirwayObstructionVomit_Count', 'vomitDislodgeOPA'):
            self.assertNotIn(forbidden, branch)
        self.assertIn('_misses >= _tolerance', branch)
        self.assertIn('_amount min 4', branch)
        self.assertIn('_blood max 1', branch)

    def test_concurrent_and_stale_events_still_rejected(self):
        for name in ('laryngoConsequenceLocal', 'laryngoFluidDrainLocal'):
            text = source(name)
            self.assertIn('ACME_fnc_ownerDispatch', text)
            self.assertIn('ACME_fnc_clinicalEpoch', text)
            self.assertIn('_id in _receipts', text)
        self.assertIn('_stamp isEqualTo _expected', source('laryngoFluidDrainLocal'))

    def test_new_fields_clear_on_heal_and_keep_clock_metadata(self):
        fields = source('clinicalFields')
        self.assertIn('["ACME_laryngo_secretions", "", true]', fields)
        self.assertIn('["ACME_laryngo_lastGagAt", "cba", true]', fields)

    def test_secretion_suction_debits_before_switching_compartments(self):
        text = source('laryngoFluidDrainLocal')
        self.assertIn('["ACME_laryngo_secretions", [_secretions param [0, ""], _remaining], true]', text)
        self.assertIn('if (_kind == "b")', text)
        self.assertIn('if (_kind == "s")', text)
        self.assertNotIn('setVariable ["ACME_laryngo_gagMisses"', text)

    def test_native_vomit_worker_pauses_before_random_sound_and_debit(self):
        text = read_source(ROOT / 'overrides/fn_handleAirwayObstruction_Vomit.sqf')
        guard = text.index('if (_patient getVariable ["ace_medical_inCardiacArrest", false]')
        self.assertIn('ACME_roc_paralyzed', text)
        for operation in ('private _medicationEffect', 'if (random 1 <', 'playSound3D', 'setVariable ["ACM_airway_AirwayObstructionVomit_Count",'):
            self.assertLess(guard, text.index(operation))
        self.assertIn('((0.4 * ACM_airway_airwayObstructionVomitChance) + _medicationEffect)', text)
        self.assertIn('(_vomitCount - 1) max 0', text)
        self.assertIn('(10 + (random 10))', text)
        self.assertNotIn('setVariable ["ACM_airway_AirwayObstructionVomit_State", 0', text)
        self.assertNotIn('setVariable ["ACM_airway_AirwayObstructionVomit_Count", 0', text)

    def test_reopen_and_inactive_vomit_display_retained_pool_at_rest(self):
        text = source('laryngoFluidSync')
        self.assertIn('private _firstView = count _previous != 3', text)
        self.assertIn('if (!_firstView && {_kind == "v"})', text)
        self.assertIn('if (_firstView || {!_newEpisode}', text)
        self.assertIn('_current = _target', text)
        self.assertIn('_kind == "v" && {!_newVomit || {!_canEmesis}}', text)
        self.assertIn('if (_newVomit && {_canEmesis})', text)

    def test_live_arrest_and_paralysis_guard_ejection_without_state_update(self):
        text = source('laryngoFluid')
        self.assertIn('if (_kind == "v" && {!_canEmesis} && {_mode == "fill"})', text)
        self.assertIn('_mode = "rest"', text)
        self.assertIn('if (_kind == "v" && {_mode == "fill"} && {_canEmesis})', text)
        self.assertIn('ace_medical_inCardiacArrest', text)
        self.assertIn('ACME_roc_paralyzed', text)
        self.assertNotIn('setVariable ["ACM_airway_AirwayObstructionVomit_State", 0', text)

    def test_emesis_does_not_relabel_existing_other_fluid_volume(self):
        text = source('laryngoConsequenceLocal')
        self.assertIn('if ((_poolBefore select 1) == "v") then {_poolBefore select 2} else {0}', text)
        self.assertIn('(_previousVomit + _amount) min 8', text)

    def test_supplied_secretion_art_covers_fluid_and_suction(self):
        for stage in range(11):
            for phase in range(4):
                self.assertTrue((ROOT / 'ui/laryngo/fluid' / f's_{stage:02d}_{phase}.paa').exists())
        for mode, count in (('cont', 8), ('out', 12)):
            for frame in range(count):
                self.assertTrue((ROOT / 'ui/laryngo/suction' / f'{mode}_s_{frame:02d}.paa').exists())


if __name__ == '__main__':
    unittest.main()
