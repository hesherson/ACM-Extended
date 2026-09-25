"""The startup bootstrap preserves compiled functions and registers one runtime."""
import json
import re

from source_scan import lex
from test_menu_death_lifecycle import ROOT, adapt, execute, read


FUNCTIONS = (
    "pulsePerfusionProfile", "preoxygenationTick", "shockSetPhenotype",
    "shockPhenotypeTick", "coagulationTick", "aspirationTick",
    "megacodeAARRecord", "megacodeAARReset", "megacodeAARTick",
    "megacodeAARShow", "expansionRegisterRuntime",
)


def test_cfgfunctions_is_the_only_compilation_owner():
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    for name in FUNCTIONS:
        assert len(re.findall(r"\bclass\s+" + name + r"\s*\{", config)) == 1
        assert (ROOT / "addons/acm_extended/functions" / f"fn_{name}.sqf").is_file()
    tokens = lex(read("expansionBootstrap"))
    assert not {t.value for t in tokens} & {"compile", "compileFinal", "setVariable"}


def test_repeated_bootstrap_keeps_bindings_and_registers_handlers_once():
    names = json.dumps(["ACME_fnc_" + name for name in FUNCTIONS])
    setup = f"""
        private _names = {names};
        private _tickCalls = 0;
        {{missionNamespace setVariable [_x, {{_tickCalls = _tickCalls + 1;}}];}} forEach _names;
        private _eventRegistrations = [];
        CBA_fnc_addEventHandler = {{_eventRegistrations pushBack _this;}};
        ACME_fnc_expansionRegisterRuntime = {{ {adapt(read('expansionRegisterRuntime'))} }};
        private _before = _names apply {{str (missionNamespace getVariable _x)}};
        private _bootstrap = {{ {read('expansionBootstrap')} }};
    """
    execute(setup + """
        call _bootstrap;
        call _bootstrap;
        [count _handlers == 0, "registration lost its startup deferral"] call _check;
        [count _waits == 2, "bootstrap did not schedule registration"] call _check;
        {(_x select 1) call (_x select 0);} forEach _waits;
        [(_names apply {str (missionNamespace getVariable _x)}) isEqualTo _before,
            "bootstrap replaced a compiled binding"] call _check;
        [count _handlers == 5, "missing or duplicate expansion tick handlers"] call _check;
        [count _eventRegistrations == 1, "missing or duplicate reset event handler"] call _check;
        [(_eventRegistrations select 0 select 0) == "ACME_megacodeAARReset", "wrong reset event"] call _check;
        {(_x select 1) call (_x select 0);} forEach _handlers;
        [_tickCalls == 5, "registered tick callbacks did not run"] call _check;
    """)
