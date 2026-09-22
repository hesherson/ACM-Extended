"""ACE interaction initialization contracts. Version and syntax checks collect normally.

The subject moved out of postInit; no broad diagnostic ban is applied to unrelated
startup modules. Structural checks are not a replacement for HEMTT compilation.
"""
from pathlib import Path
from historical_source import read_source, assert_release_consistent

ROOT = Path(__file__).resolve().parents[1]


def test_current_release_is_consistent():
    assert_release_consistent()


def interaction_source():
    source = ROOT / "functions/fn_initMinigameInteractionRuntime.sqf"
    direct = source.read_text(encoding="utf-8-sig")
    called = read_source(ROOT / "functions/fn_postInit.sqf")
    assert "called module initMinigameInteractionRuntime" in called
    assert direct in called
    return direct


def test_flashlight_guard_is_a_comment_not_executable_text():
    text = interaction_source()
    assert '\n the flashlight filter flag must never strand ACE.' not in text
    assert '// the flashlight filter flag must never strand ACE.' in text


def test_interaction_extension_close_and_watchdog_remain():
    text = interaction_source()
    assert '["notOnMap", {' in text
    assert 'call ace_common_fnc_addCanInteractWithCondition;' in text
    assert '["ace_interactMenuClosed", {' in text
    assert 'missionNamespace setVariable ["ACME_flashlightMenuActive", false];' in text
    assert 'call CBA_fnc_addPerFrameHandler;' in text


def test_retired_interaction_diagnostics_stay_retired():
    text = interaction_source()
    for forbidden in ('diag_log', 'systemChat', 'hintSilent', 'ACME_flashlight_diag'):
        assert forbidden not in text, forbidden


def strip_sqf(s: str) -> str:
    out=[]; i=0; in_str=False
    while i < len(s):
        c=s[i]
        if in_str:
            if c == '"':
                if i+1 < len(s) and s[i+1] == '"':
                    i += 2; continue
                in_str=False
            i += 1; continue
        if c == '"':
            in_str=True; i += 1; continue
        if c == '/' and i+1 < len(s) and s[i+1] == '/':
            j=s.find('\n', i+2)
            if j == -1: break
            out.append('\n'); i=j+1; continue
        if c == '/' and i+1 < len(s) and s[i+1] == '*':
            j=s.find('*/', i+2)
            assert j != -1, 'unterminated block comment'
            i=j+2; continue
        out.append(c); i += 1
    assert not in_str, 'unterminated string'
    return ''.join(out)


def test_interaction_module_delimiters_are_balanced():
    clean = strip_sqf(interaction_source())
    pairs={')':'(',']':'[','}':'{'}; stack=[]
    for ch in clean:
        if ch in '([{': stack.append(ch)
        elif ch in ')]}':
            assert stack and stack[-1] == pairs[ch], (ch, stack[-5:])
            stack.pop()
    assert not stack, stack[-10:]
