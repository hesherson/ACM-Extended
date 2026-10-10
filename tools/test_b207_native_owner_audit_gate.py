"""Positive and negative controls for the strict literal native-write gate."""
from pathlib import Path
import subprocess
import sys

import pytest

from audit_acme_native_owner_writes import PREFIXES, main, scan_source


@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("statement", [
    '_p setVariable ["KEY", false];',
    "missionNamespace setVariable ['KEY', false];",
    'uiNamespace setVariable\n [\n "KEY",\n false\n ];',
    '[_p, "KEY", false] call ACME_fnc_setVarNet;',
    "[\n_p,\n'KEY',\n0.5,0.1,2\n]\ncall ACME_fnc_setVarNetApprox;",
])
def test_real_literal_writes_fail_independent_of_quote_style_or_lines(prefix, statement):
    findings = scan_source(statement.replace("KEY", prefix + "Test"))
    assert len(findings) == 1
    assert findings[0].key == prefix + "Test"


@pytest.mark.parametrize("source", [
    '// _p setVariable ["ACM_core_Test", false];',
    '/*\n[_p,"ACM_airway_Test",0] call ACME_fnc_setVarNet;\n*/',
    'diag_log "_p setVariable [\'ACM_core_Test\', false]";',
    '_v = _p getVariable ["ACM_core_Test", false];',
    '[_p, [["ACM_core_Test",false]]] call ACM_core_fnc_setRuntimeState;',
    '[_p, false] call ACM_core_fnc_setContinuousActionActive;',
    '[_p, "ACME_circ_Test", false] call ACME_fnc_setVarNet;',
    '_p setVariable ["ACME_ownState", ["ACM_core_Test",false]];',
])
def test_comments_reads_text_and_owner_api_calls_are_not_violations(source):
    assert scan_source(source) == []


def test_executable_callback_string_is_checked_without_treating_ordinary_text_as_code():
    findings = scan_source('call compile "_p setVariable [\'ACM_core_Test\',false]";')
    assert len(findings) == 1


def test_strict_cli_rejects_a_real_write_and_accepts_its_native_setter_fix(tmp_path):
    function = tmp_path / "fn_example.sqf"
    function.write_text('[_p,"ACM_airway_Test",0] call ACME_fnc_setVarNet;')
    script = Path(__file__).with_name("audit_acme_native_owner_writes.py")
    command = [sys.executable, str(script), "--strict", "--functions-dir", str(tmp_path)]
    failed = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert failed.returncode == 1 and "strict gate: FAIL (1 violations)" in failed.stdout
    function.write_text('[_p,[["Test",0]]] call ACM_airway_fnc_setAirwayState;')
    passed = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert passed.returncode == 0 and "strict gate: PASS (0 violations)" in passed.stdout


def test_missing_scan_input_fails_instead_of_reporting_zero(tmp_path):
    assert main(["--strict", "--functions-dir", str(tmp_path / "missing")]) == 2


def test_ci_invokes_strict_mode_and_runs_positive_control_tests():
    workflow = Path(__file__).resolve().parents[1] / ".github/workflows/b204-network-audit.yml"
    source = workflow.read_text()
    assert "python tools/audit_acme_native_owner_writes.py --strict" in source
    from run_sharded_regressions import current_selection
    assert "tools/test_b207_native_owner_audit_gate.py" in current_selection(workflow.parents[2])
    assert "run_sharded_regressions.py aggregate" in source
