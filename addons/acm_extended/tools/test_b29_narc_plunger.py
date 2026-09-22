"""Numerical cursor-feedback regression using the production SQF expressions.

This evaluates only the cursor/control arithmetic, not an Arma UI runtime.
Control heights sample ACM's 0.9 GUI-grid-unit grab band across UI scales.
"""
from pathlib import Path
from functools import lru_cache
from historical_source import assignment_expression, array_command_arguments
from source_scan import lex
import operator
import re
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'functions/fn_skCompoundBegin.sqf').read_text()
OPS = {'+': (1, operator.add), '-': (1, operator.sub), '*': (2, operator.mul),
       '/': (2, operator.truediv), 'min': (1, min), 'max': (1, max)}


def expression(code):
    """Compile the small scalar-arithmetic subset used by the actual mover."""
    scanned = lex(code)
    for token in scanned:
        if not (token.kind == 'number' or
                token.kind == 'ident' and (token.value.startswith('_') or token.value in OPS) or
                token.kind == 'symbol' and token.value in '()+*/-'):
            raise AssertionError(f'Unsupported arithmetic token: {token.value!r}')
    tokens = [token.value for token in scanned]
    assert tokens, 'Empty arithmetic expression'
    index = 0

    def parse(level=0):
        nonlocal index
        token = tokens[index]
        index += 1
        if token == '(':
            left = parse()
            assert tokens[index] == ')'
            index += 1
        else:
            left = (lambda env, name=token: env[name]) if token.startswith('_') else (lambda env, value=float(token): value)
        while index < len(tokens) and tokens[index] in OPS and OPS[tokens[index]][0] >= level:
            precedence, operation = OPS[tokens[index]]
            index += 1
            right = parse(precedence + 1)
            left = lambda env, a=left, b=right, op=operation: op(a(env), b(env))
        return left

    result = parse()
    assert index == len(tokens), code
    return result


@lru_cache(maxsize=1)
def current_cursor_program():
    # Compile lazily so a changed UI expression fails this test, not every module
    # importing the small scalar evaluator for another geometry check.
    names = ('_mouseOffset', '_bottomMouse', '_floorYMouse', '_mouseYClamped', '_rawY')
    calculations = [(name, expression(assignment_expression(SOURCE, name))) for name in names]
    cursor_args = array_command_arguments(SOURCE, 'setMousePosition')
    assert len(cursor_args) == 2, 'Cursor command requires X and Y'
    return calculations, expression(cursor_args[1])


def tick(mouse, floor, limit, height):
    env = {'_mouseY': mouse, '_floorY': floor, '_maxY': limit, '_plungerH': height}
    calculations, cursor = current_cursor_program()
    for name, calculate in calculations:
        env[name] = calculate(env)
    return cursor(env), env['_rawY']


class NarcPlunger(unittest.TestCase):
    def test_stationary_cursor_and_floor_vial_capacity_stops(self):
        cases = 0
        for scale in (.47, .55, .7, .85, 1):
            height = .9 * .04 * min(.55 / scale, 1)
            for size in (1, 3, 5, 10):
                for floor_ml, limit_ml in ((0, size), (.2*size, size), (.2*size, .55*size), (.6*size, .6*size)):
                    floor, limit = [.3 + .4 * ml / size for ml in (floor_ml, limit_ml)]
                    for initial, expected in ((floor, floor), ((floor+limit)/2, (floor+limit)/2), (limit, limit), (-10, floor), (10, limit)):
                        with self.subTest(scale=scale, size=size, floor=floor_ml, limit=limit_ml, initial=initial):
                            mouse = initial + height / 2
                            for frame in range(360):
                                mouse, position = tick(mouse, floor, limit, height)
                                self.assertAlmostEqual(position, expected, places=12)
                        cases += 1
        self.assertEqual(cases, 400)

    def test_deliberate_draw_and_return_follow_the_mouse(self):
        for height in (.012, .024, .036):
            for target in (.4, .5, .6, .5, .4):
                mouse, position = tick(target + height/2, .3, .7, height)
                self.assertAlmostEqual(position, target)
                self.assertAlmostEqual(mouse, target + height/2)

    def test_legacy_padding_feedback_reproduces_the_reported_full_draw(self):
        # B28 wrote Y + bottom-bound padding back to the mouse every frame.
        for scale in (.47, .55, .7, .85, 1):
            height = .9 * .04 * min(.55 / scale, 1)
            mouse = .5 + height / 2
            for frame in range(360):
                position = min(.7, max(.3, mouse - height/2))
                mouse = position + .026 * .55 / scale
            self.assertEqual(position, .7)


if __name__ == '__main__':
    unittest.main()
