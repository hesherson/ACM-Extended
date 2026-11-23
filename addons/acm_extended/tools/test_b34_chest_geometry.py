"""Chest-seal source contracts and arithmetic geometry checks.

The small evaluator reads scalar layout expressions from the shipped SQF; these
checks do not run Arma, render controls, or claim multiplayer runtime coverage.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / ("fn_" + name + ".sqf")).read_text(encoding="utf-8")


INIT = source("chestSealInit")


def scalar(name, values):
    expression = re.search(r"private\s+" + re.escape(name) + r"\s*=\s*([^;]+);", INIT)[1]

    def arithmetic(part):
        node = ast.parse(part.strip(), mode="eval")
        for child in ast.walk(node):
            if not isinstance(child, (ast.Expression, ast.BinOp, ast.Add, ast.Sub,
                                      ast.Mult, ast.Div, ast.Name, ast.Load,
                                      ast.Constant)):
                raise ValueError("Unsupported layout expression: " + part)
        return eval(compile(node, "<SQF layout arithmetic>", "eval"), {"__builtins__": {}}, values)

    return min(arithmetic(part) for part in expression.split(" min "))


def layout(aspect=16 / 9, height=1, x=0, y=0):
    values = dict(_szW=height, _szH=height, _szX=x, _szY=y,
                  _af=1 / aspect, _cx=x + height / 2,
                  _toolYOffset=.065, _fingerFactor=.0125)
    for name in ("_bodyH", "_layoutH", "_bodyW", "_slotH", "_slotW", "_gap",
                 "_bodyX", "_bodyY", "_colX", "_colY", "_countH", "_slotGap",
                 "_spearY", "_btnH", "_pad", "_rakeY", "_rakeH", "_flipY", "_dotH"):
        values[name] = scalar(name, values)
    return values


class ChestLayout(unittest.TestCase):
    def test_widescreen_full_body_is_larger_with_balanced_margins(self):
        values = layout()
        self.assertAlmostEqual(values["_bodyH"], .92)
        self.assertAlmostEqual(values["_bodyH"] / .78, 1.1794871794871795)
        self.assertAlmostEqual(values["_bodyY"], .04)
        self.assertAlmostEqual(values["_bodyY"] + values["_bodyH"], .96)

    def test_complete_body_trays_and_done_fit_narrow_and_ultrawide_displays(self):
        for aspect in (1, 4 / 3, 16 / 10, 16 / 9, 21 / 9, 32 / 9):
            for height, x, y in ((1, 0, 0), (1.5, -.25, -.25), (.8, .1, .1)):
                with self.subTest(aspect=aspect, height=height):
                    values = layout(aspect, height, x, y)
                    self.assertGreaterEqual(values["_bodyX"], x)
                    self.assertGreaterEqual(values["_bodyY"], y)
                    self.assertLessEqual(values["_bodyY"] + values["_bodyH"], y + height)
                    self.assertLessEqual(values["_colX"] + values["_slotW"], x + height)
                    done_bottom = values["_flipY"] + 2 * values["_btnH"] + values["_pad"]
                    self.assertLessEqual(done_bottom, y + height)

    def test_square_pixels_and_relative_tool_sizes_survive_fit(self):
        reference = layout()
        for aspect in (1, 4 / 3, 16 / 9, 32 / 9):
            values = layout(aspect)
            self.assertAlmostEqual(values["_bodyW"] * aspect, values["_bodyH"])
            self.assertAlmostEqual(values["_slotW"] * aspect, values["_slotH"])
            for size in ("_slotH", "_dotH", "_countH", "_btnH"):
                self.assertAlmostEqual(values[size] / values["_bodyH"],
                                       reference[size] / reference["_bodyH"])

    def test_render_hit_tests_and_peer_positions_share_body_rectangle(self):
        for name in ("chestSealRender", "chestSealMouseDown", "chestSealSealAt",
                     "chestSealTick"):
            self.assertIn('getVariable ["ACME_CS_BodyRect"', source(name))
        self.assertIn('call ACME_fnc_chestSealSealAt', source("chestSealScroll"))
        self.assertIn('[_bx, _by, _bw, _bh]', source("chestSealRender"))
        self.assertIn('_bx + (_bw * _hx)', source("chestSealRender"))
        self.assertIn('_by + (_bh * _hy)', source("chestSealRender"))
        self.assertIn('call ACME_fnc_chestSealPresenceRender', source("chestSealTick"))
        for field in ("HoleH", "ClickR", "FindRadius", "ApplyR", "DragMaxSpeed",
                      "SealH", "NCDPlaceR", "NCDFadeR"):
            statement = next(line for line in INIT.splitlines()
                             if 'setVariable ["ACME_CS_' + field + '"' in line)
            self.assertIn('_bodyH *', statement)

    def test_apply_condition_matches_actual_treatment_gate_for_corpses(self):
        config = (ROOT / "config.cpp").read_text(encoding="utf-8")
        action = config.split('class ACME_ApplyChestSeal: CheckPulse {', 1)[1].split('\n    };', 1)[0]
        self.assertIn('condition = "[_patient] call ACME_fnc_chestSealCanApply";', action)
        self.assertNotIn('alive _patient', action)
        self.assertIn('(_patient isKindOf "CAManBase")', source("chestSealCanApply"))
        self.assertNotIn('alive _patient', source("chestSealCanApply"))
        self.assertIn('items[] = {"ACME_ChestSeal"};', action)
        self.assertIn('consumeItem = 0;', action)

    def test_corpse_open_keeps_discrete_owner_state_and_animation_guards(self):
        for name in ("chestSealOpen", "chestSealInit", "chestSealTick"):
            text = source(name)
            self.assertNotIn('call ACME_fnc_chestSealReset', text)
            self.assertNotIn('call ACME_fnc_clearAllAilments', text)
        self.assertIn('call ACME_fnc_chestSealRequest', source("chestSealApply"))
        self.assertIn('"ACME_ownerCommand"', source("chestSealEdit"))
        self.assertIn('private _dead = (!alive _patient)', source("chestSealFlip"))
        self.assertIn('_willAnimate = (!_dead)', source("chestSealFlip"))


if __name__ == "__main__":
    unittest.main()
