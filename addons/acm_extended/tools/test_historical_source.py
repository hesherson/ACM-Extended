"""Fail-closed checks for the historical-test infrastructure, not game behavior."""
from pathlib import Path
import pytest
import historical_source as source


def put(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.mark.parametrize("old,new", sorted(source.ALIASES.items()))
def test_explicit_alias_reads_exact_native_source(old, new):
    assert source.read_source(source.ROOT / old) == (source.ROOT / new).read_text(encoding="utf-8-sig")


def test_no_fuzzy_fallback_or_outside_root_read(tmp_path, monkeypatch):
    monkeypatch.setattr(source, "ROOT", tmp_path)
    put(tmp_path, "elsewhere/fnc_unknown.sqf", "not a fallback")
    with pytest.raises(FileNotFoundError):
        source.read_source(tmp_path / "addons/acm_extended/overrides/fn_unknown.sqf")
    with pytest.raises(ValueError):
        source.read_source(tmp_path.parent / "outside.sqf")


def test_static_bundle_follows_calls_not_strings_comments_or_unrelated_files(tmp_path, monkeypatch):
    monkeypatch.setattr(source, "ROOT", tmp_path)
    top = put(tmp_path, "functions/fn_postInit.sqf", '\n'.join([
        '// call ACME_fnc_initComment;',
        'private _example = "call ACME_fnc_initQuoted;";',
        'call ACME_fnc_initOne;',
        'call ACME_fnc_initOne;',
        'call ACME_fnc_nonStartup;',
    ]))
    put(tmp_path, "functions/fn_initOne.sqf", 'firstMarker; call ACME_fnc_registerTwo;')
    put(tmp_path, "functions/fn_registerTwo.sqf", 'secondMarker; call ACME_fnc_initOne;')
    put(tmp_path, "functions/fn_initUncalled.sqf", 'notReachableMarker;')
    bundled = source.read_source(top)
    assert bundled.count('firstMarker') == 1
    assert bundled.count('secondMarker') == 1
    assert 'notReachableMarker' not in bundled
    assert source.read_source(tmp_path / "functions/fn_initOne.sqf") == 'firstMarker; call ACME_fnc_registerTwo;'


def test_missing_static_called_module_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(source, "ROOT", tmp_path)
    top=put(tmp_path, "fn_postInit.sqf", 'call ACME_fnc_initMissing;')
    with pytest.raises(FileNotFoundError, match="called module missing"):
        source.read_source(top)


def test_debug_bundle_and_startup_bundle_have_separate_expansion_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(source, "ROOT", tmp_path)
    put(tmp_path, "fn_debugMenuClinical.sqf", 'clinicalMarker;')
    debug=put(tmp_path, "fn_debugMenu.sqf", 'call ACME_fnc_debugMenuClinical;')
    startup=put(tmp_path, "fn_postInit.sqf", 'call ACME_fnc_debugMenuClinical;')
    assert 'clinicalMarker' in source.read_source(debug)
    assert 'clinicalMarker' not in source.read_source(startup)


def test_multiline_assignment_extraction_ignores_quoted_and_comment_examples():
    text='// private _answer = 100;\nprivate _quote = "private _answer = 200;";\nprivate _answer =\n    (_value + 1) max (if (_flag) then {2} else {3});'
    assert source.assignment_expression(text, '_answer') == '(_value + 1) max (if (_flag) then {2} else {3})'


@pytest.mark.parametrize("text", [
    'private _other = 1;',
    'private _value = 1; private _value = 2;',
    'private _value = (1;',
    'private _value = 1',
])
def test_ambiguous_or_invalid_assignment_is_not_accepted(text):
    with pytest.raises(AssertionError):
        source.assignment_expression(text, '_value')


def test_command_array_does_not_depend_on_horizontal_expression():
    text='// setMousePosition [0,0];\nprivate _q="setMousePosition [1,1];"; setMousePosition [(_mouse select 0), (_rawY + (_height / 2))];'
    assert source.array_command_arguments(text, 'setMousePosition') == ['(_mouse select 0)', '(_rawY + (_height / 2))']


@pytest.mark.parametrize("text", [
    'setMousePosition _position;',
    'setMousePosition [0,0]; setMousePosition [1,1];',
    'setMousePosition [0,(1];',
])
def test_command_array_is_unambiguous_and_balanced(text):
    with pytest.raises(AssertionError):
        source.array_command_arguments(text, 'setMousePosition')


def test_defined_class_excludes_forward_declarations_and_examples():
    text='// class Own {bad=1;};\nclass Own; class Other {example="class Own {bad=2;};";}; class Own: Parent {version="1.2.3.4"; class Nested {a=1;};};'
    assert source.class_body(text,'Own') == 'version="1.2.3.4"; class Nested {a=1;};'


@pytest.mark.parametrize("text", ['class Own;', 'class Own {a=1;', 'class Own {}; class Own {};'])
def test_missing_or_ambiguous_config_class_fails_closed(text):
    with pytest.raises(AssertionError):
        source.class_body(text,'Own')


def release_fixture(root):
    files={
        'addons/main/script_version.hpp': '#define MAJOR 1\n#define MINOR 2\n#define PATCH 3\n#define BUILD 4\n',
        'addons/acm_extended/config.cpp': 'class CfgPatches {class ACM_Extended {version="1.2.3.4";};};',
        'addons/acm_extended/functions/fn_initForkStartupRuntime.sqf': 'ACME_infusion_version = getText(configFile >> "CfgPatches" >> "ACM_Extended" >> "version"); if (ACME_infusion_version == "") then {ACME_infusion_version = "1.2.3.4";};',
        'addons/acm_extended/functions/fn_postInit.sqf': 'call ACME_fnc_initForkStartupRuntime;',
    }
    for name,text in files.items(): put(root,name,text)
    return files


def test_consistent_release_fixture_and_actual_source(tmp_path):
    release_fixture(tmp_path)
    assert source.assert_release_consistent(tmp_path) == '1.2.3.4'
    assert source.assert_release_consistent().count('.') == 3


@pytest.mark.parametrize("path,old,new", [
    ('addons/main/script_version.hpp', '#define PATCH 3', '#define PATCH 9'),
    ('addons/acm_extended/config.cpp', '1.2.3.4', '1.2.3.5'),
    ('addons/acm_extended/functions/fn_initForkStartupRuntime.sqf', '1.2.3.4', '1.2.3.6'),
    ('addons/acm_extended/functions/fn_initForkStartupRuntime.sqf', '"ACM_Extended"', '"OtherMod"'),
    ('addons/acm_extended/functions/fn_postInit.sqf', 'call ACME_fnc_initForkStartupRuntime;', '// call ACME_fnc_initForkStartupRuntime;'),
])
def test_release_mismatch_and_missing_call_are_detected(tmp_path,path,old,new):
    files=release_fixture(tmp_path)
    put(tmp_path,path,files[path].replace(old,new))
    with pytest.raises(AssertionError):
        source.assert_release_consistent(tmp_path)


@pytest.mark.parametrize("code", ['_value ^ 2', '_value; _other', 'abs _value', '_value + bogus', '_value, 2'])
def test_plunger_evaluator_rejects_unsupported_operators(code):
    from test_b29_narc_plunger import expression
    with pytest.raises((AssertionError,ValueError)):
        expression(code)
