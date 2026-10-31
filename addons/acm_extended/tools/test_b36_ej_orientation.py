"""Actual-art direction and source integration checks; these do not run the Arma renderer."""
from historical_source import assert_release_identity
from pathlib import Path
import math
import re
import unittest

from paa import read_paa

ROOT = Path(__file__).resolve().parents[1]

def src(name):
    return (ROOT / 'functions' / f'fn_{name}.sqf').read_text(encoding='utf-8-sig')


def family(is_ej, patient_left):
    tick = src('ivMinigameTick')
    limb = re.search(r'private _artSide = if \(_patientLeft\) then \{"(\w+)"\} else \{"(\w+)"\};', tick)
    ej = re.search(r'if \(_isEJ\) then \{_artSide = if \(_patientLeft\) then \{"(\w+)"\} else \{"(\w+)"\};\};', tick)
    if limb is None or ej is None:
        raise AssertionError('Limb and EJ artwork must have explicit independent side selection')
    side = (ej if is_ej else limb).groups()[0 if patient_left else 1]
    return ('_ej_15_' if is_ej else '_15_') + side


def vector_for(frame, table):
    text = src('ivMinigameInit').split('"' + table + '"', 1)[1]
    match = re.search(r'\["' + frame + r'",\s*\[\s*([-\d.]+),\s*([-\d.]+)\]\]', text)
    if match is None:
        raise AssertionError(f'Missing {frame} in {table}')
    return tuple(map(float, match.groups()))


class EJOrientation(unittest.TestCase):
    def test_neutral_handle_lean_matches_patient_side_in_real_art(self):
        # At the vein the positional and settled hand-motion angles are zero.
        # The default texture itself, not a signed movement equation, must match.
        for is_ej in (False, True):
            for patient_left in (False, True):
                frame = family(is_ej, patient_left)
                u, v = vector_for(frame, 'ACME_IV_FrameAnchors')
                for gauge in (14, 16, 18, 20):
                    with self.subTest(ej=is_ej, patient_left=patient_left, gauge=gauge):
                        name = frame[1:]
                        _, alpha = read_paa(ROOT/'ui/iv'/f'{gauge}g'/name/f'iv_catheter_{gauge}g_{name}_frame_00_ready_ca.paa', want=256)
                        ys, xs = (alpha > 127).nonzero()
                        dx, dy = xs.mean()/alpha.shape[1]-u, ys.mean()/alpha.shape[0]-v
                        # Screen-right handle on patient-left, screen-left handle
                        # on patient-right for both upward limb and downward EJ art.
                        self.assertGreater(dx if patient_left else -dx, .01)
                        self.assertGreater(-dy if is_ej else dy, .05)

    def test_only_ej_family_changes_and_zeus_matches(self):
        self.assertEqual(family(False, True), '_15_left')
        self.assertEqual(family(False, False), '_15_right')
        self.assertEqual(family(True, True), '_ej_15_right')
        self.assertEqual(family(True, False), '_ej_15_left')
        self.assertIn('if (_siteName isEqualTo "left") then { "_ej_15_right" } else { "_ej_15_left" }', src('zeusIVDialogConfirm'))
        self.assertIn('if (_bp in ["leftarm", "leftleg"]) then {"_15_left"} else {"_15_right"}', src('ivSeedHub'))
        self.assertIn('["ACME_IV_EJAnatomicalSide", (["right", "left"] select _nearL)]', src('ivMinigameTick'))

    def test_ej_outer_rotation_adds_to_corrected_default_and_stays_rigid(self):
        tick = src('ivMinigameTick')
        self.assertIn('_displayAngle = _span * (missionNamespace getVariable ["ACME_iv_ejTiltDeg", 15]);', tick)
        self.assertIn('private _angle = ((_displayAngle + _motionTilt) max -15) min 15;', tick)
        for patient_left in (False, True):
            ax, ay = vector_for(family(True, patient_left), 'ACME_IV_FrameAxis')
            outward = 1 if patient_left else -1
            for fraction in (0, .25, .5, .75, 1):
                angle = math.radians(outward*15*fraction)
                c, s = math.cos(angle), math.sin(angle)
                rx, ry = ax*c-ay*s, ax*s+ay*c
                self.assertAlmostEqual(rx*rx+ry*ry, ax*ax+ay*ay)
                handle_angle = math.degrees(math.atan2(-rx*outward, ry))
                self.assertAlmostEqual(handle_angle, 15+15*fraction, delta=2)

    def test_physical_pose_and_saved_insertions_keep_their_angle(self):
        self.assertIn('ctrlSetAngle [_angle, _u, _v, false]', src('ivCathPose'))
        self.assertIn('pixelW / (pixelH max 1e-9)', src('ivCathGeometry'))
        for name in ('ivMinigameSaveState', 'ivMinigameInsertStart'):
            self.assertIn('ACME_IV_InsAngle', src(name))
        self.assertIn('_x param [13,0]', src('ivMinigameRenderMarks'))

    def test_requested_public_version_is_consistent(self):
        config = (ROOT/'config.cpp').read_text(encoding='utf-8-sig')
        startup = src('initForkStartupRuntime')
        # Explicit shared build contract supersedes the historical B36 patch literal.
        import runpy
        expected = runpy.run_path(str(ROOT.parents[1]/"tools/build_contract.py"))["assert_current_build"]()
        self.assertIn('version = "'+expected['version']+'";', config)
        self.assertIn('ACME_infusion_version = getText', startup)
        assert_release_identity()

if __name__ == '__main__':
    unittest.main()
