"""Negative fixtures prevent historical expression probes from reading old examples."""
import pytest
from backlog_contract_expression import assignment_expression


def test_multiline_assignment_ignores_comments_and_quotes():
    text = '// private _value = 100;\nprivate _quote = "private _value = 200;";\nprivate _value =\n    (_x + 1) max (if (_flag) then {2} else {3});'
    assert assignment_expression(text, '_value') == '(_x + 1) max (if (_flag) then {2} else {3})'


@pytest.mark.parametrize('text', [
    'private _other = 1;',
    'private _value = 1; private _value = 2;',
    'private _value = (1;',
    'private _value = 1',
])
def test_missing_ambiguous_or_incomplete_assignment_fails(text):
    with pytest.raises(AssertionError):
        assignment_expression(text, '_value')
