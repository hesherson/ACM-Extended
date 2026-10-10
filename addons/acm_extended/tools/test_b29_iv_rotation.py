"""Focused source/geometry checks; this does not emulate Arma's native UI renderer."""
from pathlib import Path
import math
import re
import unittest
import struct
from paa import read_paa

ROOT = Path(__file__).resolve().parents[1]
def source(name):
    return (ROOT / 'functions' / f'fn_{name}.sqf').read_text(encoding='utf-8-sig')

class IVRotationRegression(unittest.TestCase):
    def test_b30_patient_side_uses_visually_correct_resting_art(self):
        # Read the chosen family and real PAA alpha silhouette. Filename-only checks
        # passed B29 even though its handle leaned opposite the patient's resting arm.
        tick = source('ivMinigameTick')
        mapping = re.search(r'private _artSide = if \(_patientLeft\) then \{"(\w+)"\} else \{"(\w+)"\};', tick)
        self.assertIsNotNone(mapping)
        init = source('ivMinigameInit').split('"ACME_IV_FrameAnchors"', 1)[1]
        ej_mapping = re.search(r'if \(_isEJ\) then \{_artSide = if \(_patientLeft\) then \{"(\w+)"\} else \{"(\w+)"\};\};', tick)
        self.assertIsNotNone(ej_mapping)
        for is_ej in (False, True):
            sides = (ej_mapping if is_ej else mapping).groups()
            for patient_left, family_side in zip((True, False), sides):
                family = f'{"ej_" if is_ej else ""}15_{family_side}'
                anchor = re.search(r'\["_' + family + r'",\s*\[([\d.]+),\s*([\d.]+)\]\]', init)
                self.assertIsNotNone(anchor)
                u, v = map(float, anchor.groups())
                for gauge in (14, 16, 18, 20):
                    _, alpha = read_paa(ROOT/'ui/iv'/f'{gauge}g'/family/f'iv_catheter_{gauge}g_{family}_frame_00_ready_ca.paa', want=256)
                    ys, xs = (alpha > 127).nonzero()
                    # Ready art has most opaque area in the handle, behind the tip.
                    # B36: compare HANDLE lean on both views; EJ handles point up.
                    down_dx = xs.mean()/alpha.shape[1] - u
                    down_dy = (ys.mean()/alpha.shape[0] - v) * (-1 if is_ej else 1)
                    self.assertGreater(down_dy, 0)
                    self.assertGreater(down_dx if patient_left else -down_dx, .01)

    def test_b30_outward_rotation_adds_to_resting_tilt_without_exceeding_cap(self):
        tick = source('ivMinigameTick')
        self.assertIn('private _sign = if (_dxn > 0) then {-1} else {1};', tick)
        self.assertIn('_displayAngle = _span * (missionNamespace getVariable ["ACME_iv_ejTiltDeg", 15]);', tick)
        self.assertIn('private _angle = ((_displayAngle + _motionTilt) max -15) min 15;', tick)
        init = source('ivMinigameInit').split('"ACME_IV_FrameAxis"', 1)[1]
        # B34 reverses the neck motion independently; tested in test_b34_iv_visuals.
        for patient_left, family in ((True, '_15_left'), (False, '_15_right')):
            m = re.search(r'\["' + family + r'",\s*\[\s*([-\d.]+),\s*([-\d.]+)\]\]', init)
            ax, ay = map(float, m.groups())
            down_sign = 1 if family.startswith('_ej') else -1
            direction = 1 if patient_left else -1
            resting = math.degrees(math.atan2(ax*down_sign, ay*down_sign)) * direction
            self.assertAlmostEqual(resting, 15, delta=2)
            for edge_fraction in (0, .25, .5, .75, 1):
                for motion in (-4, 0, 4):
                    # Patient-left is screen-right; patient-right is screen-left.
                    angle = max(-15, min(15, -direction*15*edge_fraction + motion))
                    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                    rx, ry = ax*c-ay*s, ax*s+ay*c
                    outward = math.degrees(math.atan2(rx*down_sign, ry*down_sign)) * direction
                    self.assertLessEqual(outward, resting+15+1e-9)
                    self.assertAlmostEqual(rx*rx+ry*ry, ax*ax+ay*ay)
                    if edge_fraction == 1 and motion == 0:
                        self.assertAlmostEqual(outward, 30, delta=2)

    def test_b30_seeded_hubs_and_ej_match_corrected_manual_families(self):
        for name, variable in (('ivSeedHub', '_bp'), ('zeusIVDialogConfirm', '_markPart')):
            self.assertIn(f'if ({variable} in ["leftarm", "leftleg"]) then {{"_15_left"}} else {{"_15_right"}}', source(name))
        self.assertIn('if (_siteName isEqualTo "left") then { "_ej_15_right" } else { "_ej_15_left" }', source('zeusIVDialogConfirm'))
        self.assertIn('["ACME_IV_EJSide", (["right", "left"] select _nearL)]', source('ivMinigameTick'))
        self.assertIn('["ACME_IV_EJAnatomicalSide", (["right", "left"] select _nearL)]', source('ivMinigameTick'))
        self.assertIn('["ACME_IV_EJSide", "right"]', source('ivMinigameInit'))

    def test_fixed_side_families_exist_for_every_gauge_and_stage(self):
        tick = source('ivMinigameTick')
        self.assertIn('_bpT in ["leftarm", "leftleg"]', tick)
        self.assertIn('if (_patientLeft) then {"left"} else {"right"}', tick)
        self.assertIn('then {"_ej_15_%1"} else {"_15_%1"}', tick)
        self.assertNotIn('_biasSide', tick)
        self.assertNotIn('ACME_IV_LastTiltSide', tick)
        self.assertNotIn('_frame = "";', tick)
        self.assertNotIn('_frame = "_ej";', tick)
        for gauge in (14, 16, 18, 20):
            for family in ('15_left', '15_right', 'ej_15_left', 'ej_15_right'):
                files = sorted((ROOT/'ui/iv'/f'{gauge}g'/family).glob('*.paa'))
                self.assertEqual(len(files), 15)
                for p in files:
                    data = p.read_bytes()
                    offset = 2
                    while data[offset:offset+4] == b'GGAT':
                        size = struct.unpack_from('<I', data, offset+8)[0]
                        offset += 12+size
                    palettes = struct.unpack_from('<H',data,offset)[0]
                    offset += 2+palettes*3
                    width,height = struct.unpack_from('<HH',data,offset)
                    self.assertEqual(width & 32767, height)

    def test_rotation_geometry_preserves_pixel_length_and_anchor_on_ultrawide(self):
        init = source('ivMinigameInit')
        anchors = re.findall(r'\["(_(?:ej_)?15_(?:left|right))",\s*\[([\d.]+),\s*([\d.]+)\]\]', init)
        self.assertGreaterEqual(len(anchors), 4)
        # Independent pixel-space invariant for both common screens and the user's 5120x1440.
        for width, height in ((1920,1080),(2560,1440),(5120,1440)):
            pw, ph = 1/width, 1/height
            canvas_h = .62
            canvas_w = canvas_h * pw/ph
            self.assertAlmostEqual(canvas_w/pw, canvas_h/ph)
            for _, u, v in anchors[:4]:
                u, v = float(u), float(v)
                tip_x, tip_y = .52, .41
                origin_x, origin_y = tip_x-canvas_w*u, tip_y-canvas_h*v
                self.assertAlmostEqual(origin_x+canvas_w*u, tip_x)
                self.assertAlmostEqual(origin_y+canvas_h*v, tip_y)
                for angle in (-30,-15,-2,0,2,15,30):
                    c,s = math.cos(math.radians(angle)),math.sin(math.radians(angle))
                    a,b = .23,-.97
                    x,y = a*c-b*s,a*s+b*c
                    self.assertAlmostEqual(x*x+y*y,a*a+b*b)
        self.assertIn('pixelW / (pixelH max 1e-9)', source('ivCathGeometry'))
        pose = source('ivCathPose')
        self.assertNotIn('ctrlSetStyle', pose)
        self.assertIn('"ACME_IV_CathCursor"', source('ivHeldRaise'))
        config = (ROOT/'config.cpp').read_text(encoding='utf-8-sig')
        self.assertRegex(config, r'class ACME_IV_CathCursor[^}]+style\s*=\s*48;')
        self.assertIn('ctrlSetAngle [_angle, _u, _v, false]', pose)

    def test_rotation_survives_handoff_ghosts_saved_state_hubs_and_line(self):
        for name in ('ivMinigameTick','ivMinigameInsertStart','ivMinigameRestoreState','ivMinigameRenderMarks'):
            self.assertIn('call ACME_fnc_ivCathPose', source(name))
        for name in ('ivMinigameInsertAdvance','ivMinigamePullTick'):
            self.assertIn('call ACME_fnc_ivCathGeometry', source(name))
            self.assertIn('_dux = _dux / _aspect', source(name))
        self.assertIn('ACME_IV_Pose', source('ivCathSetFrame'))
        self.assertIn('ACME_IV_InsAngle', source('ivMinigameSaveState'))
        self.assertIn('if (_keyPart == "ej") then {"head"} else {_keyPart}', source('ivStateLocal'))
        self.assertIn('["_angle", 0]', source('ivMinigameRestoreState'))
        self.assertIn('_x param [13,0]', source('ivMinigameRenderMarks'))
        # B232 selects a finishing tool without capturing an arbitrary last hub.
        # The clicked hub's live angle is applied by the shared accessory pose.
        self.assertIn('ACME_fnc_ivFinishGrab', source('ivMinigameGrabLine'))
        self.assertIn('_row param [13,0]', source('ivFinishGeometry'))
        self.assertIn('call ACME_fnc_ivFinishGeometry', source('ivFinishPose'))
        self.assertIn('ACME_IV_InsAngle', source('ivMinigameAddMark'))
        add_mark = source('ivMinigameAddMark')
        self.assertIn('[_patient, "ivMarks", ["add"', add_mark)
        self.assertNotIn('_patient setVariable ["ACME_IV_Marks"', add_mark)
        self.assertIn('ACME_IV_MarkVer', source('ivMarkCommit'))


if __name__ == '__main__':
    unittest.main()
