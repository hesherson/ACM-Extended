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
    return float(re.search(r'ACME_junctionalBleedNorm\s*=\s*([.\d]+);', source(name))[1])


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
        self.assertIn('["ACME_junctionalPackControl", 0.0]', source('junctionalStartBleed'))

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
        self.assertIn('[_newUnit] call ACME_fnc_clearAllAilments', resp)
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
        image = source('updateJunctionalImage')
        self.assertIn('_woundC ctrlShow (_state in ["open", "packed", "xstat"]);', image)
        self.assertIn('_packedC ctrlShow (_state in ["packed", "xstat"]);', image)
        self.assertIn('_wrapC ctrlShow (_state == "wrapped");', image)
        self.assertNotIn('alive _target', image)
        self.assertIn('alive _target,', source('junctionalGuiSyncTick'))
        self.assertIn('if (alive _target && {(time - _at) > _xDwell})', source('junctionalInjuryEntry'))

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
