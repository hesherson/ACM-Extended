"""Negative controls for reviewed inline routes, not a native networking simulation."""
from pathlib import Path
import shutil
import pytest
from current_source_contracts import ROOT, assert_inline_owner_route, inline_case

ROUTES = [
    ("laryngoExtubate", "ettExtubate", "ettAirwayStateCommit"),
    ("laryngoCuffDone", "ettCuffDone", "ettAirwayStateCommit"),
]

@pytest.mark.parametrize("request_fn,operation,writer", ROUTES)
def test_current_route_has_exact_registered_owner_writer(request_fn, operation, writer):
    assert_inline_owner_route(request_fn, operation, writer)

@pytest.mark.parametrize("request_fn,operation,writer", ROUTES)
@pytest.mark.parametrize("mutation", ["request_fn", "dispatch", "case", "writer", "registration", "duplicate"])
def test_source_route_rejects_removed_guards_and_comment_decoys(tmp_path, request_fn, operation, writer, mutation):
    paths = ["addons/acm_extended/config.cpp"] + [
        f"addons/acm_extended/functions/fn_{name}.sqf"
        for name in (request_fn, "ownerDispatch", writer)
    ]
    for name in paths:
        dst = tmp_path / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dst)
    function = tmp_path / "addons/acm_extended/functions"
    if mutation == "request_fn":
        path = function / f"fn_{request_fn}.sqf"
        old, new = f'"{operation}"', '"unknownOperation"'
    elif mutation == "dispatch":
        path = function / "fn_ownerDispatch.sqf"
        old, new = 'if (!local _patient) exitWith', 'if (false) exitWith'
    elif mutation == "case":
        path = function / "fn_ownerDispatch.sqf"
        text = path.read_text()
        block = inline_case(text, operation)
        call = f'call ACME_fnc_{writer};'
        assert call in block
        # Leave the correct writer in OTHER cases and a comment; this case must still fail.
        path.write_text(text.replace(block, block.replace(call, 'call ACME_fnc_wrongWriter;')) + '\n// ' + call)
        with pytest.raises(AssertionError):
            assert_inline_owner_route(request_fn, operation, writer, root=tmp_path)
        return
    elif mutation == "writer":
        path = function / f"fn_{writer}.sqf"
        old, new = 'if (!local _patient) exitWith', 'if (false) exitWith'
    elif mutation == "registration":
        path = tmp_path / paths[0]
        old, new = f'class {writer} {{}};', f'class {writer}Removed {{}};'
    else:
        path = function / "fn_ownerDispatch.sqf"
        path.write_text(path.read_text() + f'\nswitch (_operation) do {{ case "{operation}": {{}}; }};')
        with pytest.raises(AssertionError):
            assert_inline_owner_route(request_fn, operation, writer, root=tmp_path)
        return
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new) + '\n// ' + old)
    with pytest.raises(AssertionError):
        assert_inline_owner_route(request_fn, operation, writer, root=tmp_path)


def test_inline_parser_ignores_strings_comments_and_keeps_nested_scopes():
    source = '''// case "selected": {bad};
        private _label = 'case "selected": {bad};';
        switch (_op) do { case "selected": {if (true) then {call writer;};}; };
    '''
    assert inline_case(source, 'selected').strip() == 'if (true) then {call writer;};'


def test_reviewed_historical_modules_are_mandatory_not_only_baseline_comparisons():
    from run_sharded_regressions import current_selection
    # This independent list guards against accidentally dropping a repaired module.
    reviewed = {
        'addons/acm_extended/tools/test_b156_medication_accuracy.py',
        'addons/acm_extended/tools/test_b157_check_breathing.py',
        'addons/acm_extended/tools/test_b157_native_rate.py',
        'addons/acm_extended/tools/test_bounded_selector_lifetime.py',
        'addons/acm_extended/tools/test_burp_carry_repeat.py',
        'addons/acm_extended/tools/test_historical_medication_retirement.py',
        'tools/test_fork_phase109_upstream_acm_class_gate.py',
        'tools/test_fork_phase126_vent_roc_assessment.py',
        'tools/test_fork_phase127_sedation_debug_consistency.py',
        'tools/test_fork_phase128_pressure_vehicle_pulse.py',
        'tools/test_fork_phase153_nrb_advanced_airway_exclusion.py',
        'tools/test_fork_phase64_ett_airway_state_writer.py',
        'tools/test_fork_phase68_blood_thermal_state_writer.py',
        'tools/test_fork_phase79_aajt_state_owner.py',
    }
    selected = set(current_selection(ROOT))
    assert reviewed <= selected, sorted(reviewed - selected)
    assert all((ROOT / name).is_file() for name in reviewed)
