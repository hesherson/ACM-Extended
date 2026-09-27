"""Keep compatibility warnings actionable without hiding missing fork functions.

The source check verifies each expected marker exists as executable source. The
SQF-VM cases run the checker with valid, upstream, absent and mistyped bindings;
Arma's actual compilation/load order still requires an in-game smoke test.
"""
import json
import re

import pytest

from source_scan import lex
from test_menu_death_lifecycle import ROOT, adapt, execute


CHECKER = ROOT / "addons/acm_extended/functions/fn_compatCheck.sqf"


def marker_pairs():
    return re.findall(r'\["((?:ACM|ace)_\w+_fnc_\w+)",\s*"([^"]+)"\]', CHECKER.read_text())


def test_expected_fork_markers_exist_in_executable_sources():
    pairs = marker_pairs()
    assert len(pairs) == 13
    for name, marker in pairs:
        owner, function = name.split("_fnc_")
        if owner.startswith("ACM_"):
            source = ROOT / "addons" / owner[4:] / "functions" / f"fnc_{function}.sqf"
        else:
            source = ROOT / "addons/core/overrides" / f"fnc_{function}.sqf"
        assert marker in [t.value for t in lex(source.read_text()) if t.kind == "string"], name


@pytest.mark.parametrize("state", ["current", "upstream", "missing", "wrong_type"])
def test_checker_preserves_real_failures_and_never_replaces_a_binding(state):
    source = CHECKER.read_text()
    pairs = marker_pairs()
    chosen = "ACM_circulation_fnc_getBloodVolumeChange"
    required = re.findall(r'"((?:ACM|ace)_\w+_fnc_\w+)"', source)
    setup = "".join(f'missionNamespace setVariable [{json.dumps(name)}, {{true}}];'
                    for name in sorted(set(required)) if not (state == "missing" and name == chosen))
    for name, marker in pairs:
        if state == "missing" and name == chosen:
            continue
        value = "{private _marker=" + json.dumps(marker) + ";true}"
        if name == chosen and state != "current":
            value = {"upstream": "{true}", "wrong_type": "17"}[state]
        setup += f'missionNamespace setVariable [{json.dumps(name)}, {value}];'
    setup += f'private _before = str (missionNamespace getVariable ["{chosen}", "ABSENT"]);'
    setup += 'private _messages=[]; ace_common_fnc_displayTextStructured={_messages pushBack (_this select 0);};'
    setup += 'ACME_infusion_version="test"; ACME_buildBatch="test";'
    expected = [] if state == "current" else [f"STALE/OVERRIDDEN {chosen}"]
    execute(setup + 'private _checkCompat={' + adapt(source) + '};call _checkCompat;' +
        f'[(missionNamespace getVariable "ACME_compatMissing") isEqualTo {json.dumps(expected)}, "checker hid or invented a conflict"] call _check;' +
        f'[str (missionNamespace getVariable ["{chosen}", "ABSENT"]) == _before, "checker replaced another runtime binding"] call _check;' +
        f'[count _waits == {int(bool(expected))}, "incorrect warning schedule"] call _check;' +
        '''
        if !(_waits isEqualTo []) then {
            private _job=_waits select 0; (_job select 1) call (_job select 0);
            [count _messages==1,"warning was not displayed"] call _check;
            [((_messages select 0) find "complete ACM Extended fork")>=0,"warning lost install guidance"] call _check;
            [((_messages select 0) find "ACM_circulation_fnc_getBloodVolumeChange")>=0,"warning lost failed binding"] call _check;
        };
        call _checkCompat;
        ''' + f'[count _waits == {int(bool(expected))}, "checker scheduled duplicate warnings"] call _check;')
