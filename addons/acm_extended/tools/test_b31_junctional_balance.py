"""Offline balance/state contracts; these do not execute Arma animation or physiology."""
from historical_source import read_source
from pathlib import Path
import math
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PARTS = ('leftarm', 'rightarm', 'leftleg', 'rightleg')


def source(name):
    return read_source(ROOT / 'functions' / f'fn_{name}.sqf', encoding='utf-8-sig')


def configured_norm(name):
    # Baselines are named settings now; applyHardcore composes them with the user's multiplier.
    # Read canonical numeric defaults for the retained isolated reference model. Execution tests below
    # separately exercise the real runtime assignment rather than treating this parser as physiology proof.
    key = 'ACME_junctionalBleedHardcoreNorm' if name == 'applyHardcore' else 'ACME_junctionalBleedBaseNorm'
    text = source('initJunctionalConfig')
    values = re.findall(r'\b'+key+r'\s*=\s*([.\d]+);', text)
    assert len(values) == 1, (key, values)
    return float(values[0])


def isolated_two_litre_time(norm, parts, compensation=False):
    """6->4 L, isolated junctions: ref80, resistance100, coeff1, fixed vaso0.

    Fine integration independently checks the expected treatment window. There is no
    native wound, changing resistance/HR, transfusion, arrest or treatment in this model.
    """
    blood, elapsed, step = 6.0, 0.0, 0.01
    while blood > 4.0:
        shape = (elapsed / 12 if elapsed < 12 else 1 if elapsed < 57
                 else 1 - (elapsed - 57) / 105 if elapsed < 162 else 0)
        control = 1 - 0.55 * shape * 0.4 if compensation else 1
        stroke = 0.095 * 80 / 60 * max(0, min((blood - 3) / 3, 1))
        blood -= norm * parts * control * max(stroke, 0.02) * step
        elapsed += step
    return elapsed


def retained_evidence():
    """Read the literal evidence policy to exercise reset fixtures against its fields."""
    text = source('clinicalReset')
    block = text[text.index('private _junctionalEvidence'):text.index('_x params ["_name"')]
    literals = re.findall(r'"(ACME_[^"]+)"', block)
    return {name.replace('%1', part) for name in literals for part in PARTS}


class JunctionalB31(unittest.TestCase):
    def test_active_and_fallback_balance_match(self):
        self.assertEqual(configured_norm('postInit'), 0.10)
        self.assertEqual(configured_norm('applyHardcore'), 0.15)
        self.assertIn('["ACME_junctionalBleedNorm", 0.10]', source('junctionalStartBleed'))
        from test_historical_junctional_execution import test_junctional_difficulty_uses_current_base_and_multiplier_without_compounding
        for hardcore in (False,True):
            for multiplier in (0.5,1.0,2.0):
                test_junctional_difficulty_uses_current_base_and_multiplier_without_compounding(hardcore,multiplier)

    def test_isolated_loss_matches_analytic_stroke_curve(self):
        for parts in (1, 2):
            for norm in (0.35, 0.10, 0.45, 0.15):
                analytic = 3 * math.log(3) / (norm * parts * 0.095 * 80 / 60)
                self.assertAlmostEqual(isolated_two_litre_time(norm, parts), analytic, delta=0.03)

    def test_compensated_two_junction_window_is_materially_longer(self):
        old = isolated_two_litre_time(0.35, 2, True)
        new = isolated_two_litre_time(configured_norm('postInit'), 2, True)
        hardcore = isolated_two_litre_time(configured_norm('applyHardcore'), 2, True)
        self.assertAlmostEqual(old, 45.96, delta=0.03)
        self.assertAlmostEqual(new, 152.78, delta=0.03)
        self.assertGreater(new, old * 3)
        self.assertLess(hardcore, new)
        self.assertGreater(hardcore, old * 2)

    def test_death_and_respawn_choose_the_correct_reset_mode(self):
        life = source('registerClinicalLifecycleRuntime')
        resp = source('registerRhythmLifecycleRuntime')
        death = source('deathFreeze')
        self.assertRegex(life, r'EntityKilled[\s\S]*?ACME_fnc_deathFreeze')
        self.assertIn('["ace_medical_FullHeal", {_this call ACME_fnc_clearAllAilments}]', life)
        self.assertNotRegex(life, r'EntityKilled[\s\S]{0,220}?ACME_fnc_clearAllAilments')
        self.assertIn('[_oldUnit] call ACME_fnc_deathFreeze', resp)
        self.assertIn('[_newUnit, _issuedAt] call ACME_fnc_respawnClinicalReset', resp)
        self.assertIn('[_newUnit] call ACME_fnc_clearAllAilments', source('respawnClinicalReset'))
        self.assertNotIn('forEach [_oldUnit, _newUnit]', resp)
        self.assertIn('[_patient, "begin", true] call ACME_fnc_clinicalReset', death)
        self.assertNotIn('ACME_fnc_clearAllAilments', death)

    def test_corpse_keeps_wounds_devices_but_not_in_progress_treatment(self):
        death = source('deathFreeze')
        reset = source('clinicalReset')
        # Death runs only the worker-invalidating begin half. Durable injury/intervention fields are therefore
        # never iterated through the reset table, while PFHs and active scheduler membership are stopped.
        self.assertIn('[_patient, "begin", true] call ACME_fnc_clinicalReset', death)
        self.assertNotIn('"finish"', death)
        self.assertNotIn('ACME_fnc_clearAllAilments', death)
        begin = reset[:reset.index('// Physical equipment is detached')]
        self.assertIn('if (_phase == "begin") exitWith', begin)
        self.assertIn('ACME_fnc_aajtDownedStop', begin)
        self.assertIn('ACME_AAJT_painPFH', begin)
        self.assertNotIn('forEach (call ACME_fnc_clinicalFields)', begin)
        self.assertNotIn('ACME_Junc_leftarm', death)

    def test_death_invalidates_workers_and_silences_leak(self):
        reset = source('clinicalReset')
        self.assertIn('ACME_fnc_clinicalEpoch) + 1, true', reset)
        self.assertIn('"ACME_juncPFH"', reset)
        self.assertIn('["ACME_juncWorker", [], false]', reset)
        self.assertIn('["ACME_JuncBleedActive", false, false]', reset)
        clear = source('clearAllAilments')
        self.assertIn('deleteVehicle _juncLeakSrc', clear)
        self.assertIn('["ACME_JuncLeakSfxSrc", objNull, true]', clear)
        for name in ('junctionalStartBleed', 'junctionalResume'):
            self.assertIn('!alive _unit', source(name))

    def test_corpse_render_keeps_evidence_without_rebleed_progression(self):
        from test_historical_junctional_execution import test_junctional_body_evidence_uses_current_layers_on_live_and_dead_patients, test_junctional_injury_label_reads_frozen_state_without_advancing_rebleed
        for state in ('open','packed','xstat','wrapped',''):
            test_junctional_body_evidence_uses_current_layers_on_live_and_dead_patients(state,False)
        for rebled in (True,False):
            test_junctional_injury_label_reads_frozen_state_without_advancing_rebleed(False,rebled)
        self.assertIn('alive _target,', source('junctionalGuiSyncTick'))

    def test_packing_layers_over_wound_without_fade(self):
        image = source('updateJunctionalImage')
        self.assertIn('base wound', image.lower())
        self.assertIn('treatment overlay', image.lower())
        self.assertIn('junctionalwound_packed_leftarm_ca.paa', image)
        self.assertIn('junctionalwound_xstat_leftarm_ca.paa', image)
        self.assertIn('ctrlSetFade 0', image)
        self.assertNotIn('ACME_JuncVisualFadeStart', image)
        self.assertNotIn('ACME_junctionalImageFadeInSec', image)
        self.assertNotIn('ctrlCommit _left', image)


if __name__ == '__main__':
    unittest.main()
