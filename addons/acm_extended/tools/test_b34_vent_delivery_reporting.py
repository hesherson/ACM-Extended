"""Return-scope and arrest ventilation regressions; no Arma runtime execution."""
from pathlib import Path
import itertools
import re
import unittest

from source_scan import lex

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / ("fn_" + name + ".sqf")).read_text()


class VentDeliveryReporting(unittest.TestCase):
    def test_authoritative_minute_volume_returns_from_the_function(self):
        # SQF exitWith inside an if/then scope does not return from its caller.
        # Protect the actual lexical scope, rather than only checking the string.
        tokens = lex(source("ventMinuteVolume"))
        depth = 0
        exact_returns = []
        for i, token in enumerate(tokens):
            if token.value == "exitWith" and [x.value for x in tokens[i + 1:i + 3]] == ["{", "_exact"]:
                exact_returns.append(depth)
            if token.value == "{":
                depth += 1
            elif token.value == "}":
                depth -= 1
        self.assertEqual(exact_returns, [0])

    def test_bad_or_unavailable_sensor_values_retain_the_fallback(self):
        text = source("ventMinuteVolume")
        self.assertIn('"ACME_vent_driving", false', text)
        self.assertIn('"ACME_vent_mvDelivered", -1', text)
        self.assertIn('} else {-1};', text)
        self.assertIn('_exact isEqualType 0 && {finite _exact} && {_exact >= 0}', text)
        self.assertLess(text.index('exitWith { _exact }'), text.index('private _rr'))
        self.assertIn('finite _rr', text)
        self.assertIn('finite _vte', text)

    def test_only_active_simple_self_owned_vent_bypasses_hand_bvm_floor(self):
        text = source("circHandle")
        match = re.search(r'private _ventOwnsArrest = (.*?);', text, re.S)
        self.assertIsNotNone(match)
        predicate = match[1]
        # Actual Simple AND advanced SIMV modes publish their own measured
        # alveolar minute ventilation. Neither may inherit the manual BVM
        # floor, but idle, disconnected or manual-BVM sessions retain it.
        for simple, driving, provider in itertools.product(
            (False, True), (False, True), ("none", "medic", "patient")
        ):
            expr = predicate
            expr = expr.replace('_patient getVariable ["ACME_vent_driving", false]', repr(driving))
            expr = expr.replace(
                '(_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient',
                repr(provider == "patient"),
            )
            expr = expr.replace('&&', ' and ').replace('{', '(').replace('}', ')')
            actual = eval("(" + expr + ")", {"__builtins__": {}}, {})
            expected = driving and provider == "patient"
            self.assertEqual(actual, expected, (simple, driving, provider))
        branch = text[text.index('if (!_ventOwnsArrest) then {'):]
        self.assertIn('"ACME_circ_bvmVentFrac", 0.75', branch[:branch.index('};')])
        self.assertIn('private _cprEfficiency = linearConversion [12, 40, _actualRR, 1, 0.45, true];', branch)
        self.assertIn('_respDeficit = (1 - (_ventFrac min 1)) max 0 min 1;', branch)
        self.assertIn('_effVent = _targetRR * _ventFrac;', branch)



if __name__ == "__main__":
    unittest.main()
