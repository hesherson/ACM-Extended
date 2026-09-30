"""Release-gate regressions: new failures, collection errors and duplicate IDs."""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from compare_pytest_outcomes import compare_reports, main, read_report, require_all_pass


def report(tmp_path, label, rows, exit_code=None):
    suite = ET.Element("testsuite", name=label)
    states = []
    for name, state, *classname in rows:
        case = ET.SubElement(suite, "testcase", classname=classname[0] if classname else "suite", name=name)
        if state == "collection":
            ET.SubElement(case, "error", message="collection failure").text = "ImportError: missing dependency"
            states.append("error")
        else:
            tag = {"failed": "failure", "error": "error", "skipped": "skipped"}.get(state)
            if tag:
                ET.SubElement(case, tag, message=state)
            states.append(state)
    path = tmp_path / f"{label}.xml"
    ET.ElementTree(suite).write(path, encoding="unicode")
    if exit_code is None:
        exit_code = int(any(state in {"failed", "error"} for state in states))
    return read_report(path, exit_code)


@pytest.mark.parametrize("state", ["failed", "error", "collection", "skipped"])
def test_every_new_nonpassing_test_fails_even_outside_focused_lists(tmp_path, state):
    before = report(tmp_path, "before", [("existing", "passed")])
    after = report(tmp_path, "after", [("existing", "passed"), ("unfocused_new", state)])
    result = compare_reports(before, after)
    assert not result.passed
    assert any("new testcase must pass" in problem and "unfocused_new" in problem for problem in result.problems)


def test_new_passing_case_and_repaired_legacy_failures_are_reported(tmp_path):
    before = report(tmp_path, "before", [("legacy", "failed"), ("collection", "collection")])
    after = report(tmp_path, "after", [("legacy", "passed"), ("collection", "passed"), ("new", "passed")])
    result = compare_reports(before, after)
    assert result.passed
    assert len(result.improvements) == 2
    assert len(result.new_passing) == 1


@pytest.mark.parametrize("old", ["passed", "skipped", "failed", "error"])
@pytest.mark.parametrize("new", ["passed", "skipped", "failed", "error"])
def test_existing_outcome_transitions_fail_closed(tmp_path, old, new):
    before = report(tmp_path, "before", [("existing", old)])
    after = report(tmp_path, "after", [("existing", new)])
    allowed = old == new or new == "passed" or (old == "error" and new == "failed")
    result = compare_reports(before, after)
    assert result.passed is allowed


def test_unchanged_legacy_failures_errors_collection_and_skips_remain_visible(tmp_path, capsys):
    rows = [("old_fail", "failed"), ("old_error", "error"), ("old_collection", "collection"), ("old_skip", "skipped")]
    before = report(tmp_path, "before", rows)
    after = report(tmp_path, "after", rows)
    result = compare_reports(before, after)
    assert result.passed
    assert len(result.known_baseline_failures) == 3
    assert any("collection error" in item for item in result.known_baseline_failures)
    status = main(["compare", "--before", before.path, "--before-exit-code", "1",
                   "--after", after.path, "--after-exit-code", "1"])
    output = capsys.readouterr().out
    assert status == 0
    assert "NOT A GREEN SUITE: 3" in output
    assert all(name in output for name in ("old_fail", "old_error", "old_collection"))


def test_new_collection_error_cannot_hide_behind_old_setup_error(tmp_path):
    before = report(tmp_path, "before", [("existing", "error")])
    after = report(tmp_path, "after", [("existing", "collection")])
    result = compare_reports(before, after)
    assert not result.passed
    assert any("new collection error" in problem for problem in result.problems)


@pytest.mark.parametrize("exit_code", [2, 3, 4, 5, -9, 124])
@pytest.mark.parametrize("side", ["before", "after"])
def test_fatal_pytest_exit_fails_even_with_valid_unchanged_xml(tmp_path, exit_code, side):
    before = report(tmp_path, "before", [("existing", "passed")], exit_code if side == "before" else 0)
    after = report(tmp_path, "after", [("existing", "passed")], exit_code if side == "after" else 0)
    result = compare_reports(before, after)
    assert not result.passed
    assert any(f"fatal pytest exit code {exit_code}" in problem for problem in result.problems)


def test_missing_existing_case_is_a_failure(tmp_path):
    before = report(tmp_path, "before", [("keep", "passed"), ("missing", "failed")])
    after = report(tmp_path, "after", [("keep", "passed")])
    result = compare_reports(before, after)
    assert not result.passed
    assert any("missing existing testcase" in problem and "missing" in problem for problem in result.problems)


def test_fixed_module_collection_error_requires_executed_passing_tests(tmp_path, capsys):
    before = report(tmp_path, "before", [("tools.test_original", "collection", "")])
    after = report(tmp_path, "after", [("test_all_original_assertions", "passed", "tools.test_original")])
    result = compare_reports(before, after)
    assert result.passed
    assert len(result.resolved_collection_errors) == 1
    assert "1 passing tests executed" in result.resolved_collection_errors[0]
    assert result.improvements == ()  # Distinct from an executed test's error -> pass.
    assert len(result.new_passing) == 1
    assert main(["compare", "--before", before.path, "--before-exit-code", "1",
                 "--after", after.path, "--after-exit-code", "0"]) == 0
    assert "RESOLVED COLLECTION ERROR: tools.test_original" in capsys.readouterr().out


@pytest.mark.parametrize("candidates", [
    [],  # Deleted module or removed all assertions without adding an executed test.
    [("test_original", "passed", "tools.test_original_renamed")],
    [("test_original", "passed", "other.test_original")],
    [("test_original", "passed", "tools.test_original.renamed")],
    [("test_original", "skipped", "tools.test_original")],
    [("test_original", "failed", "tools.test_original")],
    [("test_original", "error", "tools.test_original")],
    [("test_pass", "passed", "tools.test_original"), ("test_skip", "skipped", "tools.test_original")],
    [("test_pass", "passed", "tools.test_original"), ("test_fail", "failed", "tools.test_original.TestCases")],
    [("test_pass", "passed", "tools.test_original"), ("tools.test_original.TestCases", "collection", "")],
])
def test_missing_collection_row_is_not_resolved_by_deletion_rename_or_partial_success(tmp_path, candidates):
    before = report(tmp_path, "before", [("tools.test_original", "collection", "")])
    after = report(tmp_path, "after", [("test_unrelated", "passed", "tools.test_unrelated")] + candidates)
    result = compare_reports(before, after)
    assert not result.passed
    assert result.resolved_collection_errors == ()
    assert any("missing existing testcase" in problem for problem in result.problems)


def test_unchanged_collection_error_cannot_be_reported_resolved_by_added_tests(tmp_path):
    error = ("tools.test_original", "collection", "")
    before = report(tmp_path, "before", [error])
    after = report(tmp_path, "after", [error, ("test_pass", "passed", "tools.test_original")])
    result = compare_reports(before, after)
    assert result.passed  # The known failure remains visible, not falsely fixed.
    assert result.resolved_collection_errors == ()
    assert len(result.known_baseline_failures) == 1


def test_duplicate_collection_errors_do_not_share_one_resolution(tmp_path):
    error = ("tools.test_original", "collection", "")
    before = report(tmp_path, "before", [error, error])
    after = report(tmp_path, "after", [("test_pass", "passed", "tools.test_original")])
    result = compare_reports(before, after)
    assert not result.passed
    assert result.resolved_collection_errors == ()


def test_missing_runtime_error_is_not_a_resolved_collection_error(tmp_path):
    before = report(tmp_path, "before", [("tools.test_original", "error", "")])
    after = report(tmp_path, "after", [("test_pass", "passed", "tools.test_original")])
    result = compare_reports(before, after)
    assert not result.passed
    assert result.resolved_collection_errors == ()


def test_duplicate_identity_occurrences_are_not_collapsed(tmp_path):
    before = report(tmp_path, "before", [("same", "passed"), ("same", "passed")])
    after = report(tmp_path, "after", [("same", "failed"), ("same", "passed")])
    assert [case.identity.occurrence for case in after.cases] == [1, 2]
    assert after.counts() == {"failed": 1, "passed": 1}
    result = compare_reports(before, after)
    assert not result.passed
    assert any("occurrence 1" in problem for problem in result.problems)


def test_new_failed_duplicate_occurrence_cannot_replace_passing_identity(tmp_path):
    before = report(tmp_path, "before", [("same", "passed")])
    after = report(tmp_path, "after", [("same", "passed"), ("same", "failed")])
    result = compare_reports(before, after)
    assert not result.passed
    assert any("new testcase must pass" in problem and "occurrence 2" in problem for problem in result.problems)


def test_missing_duplicate_occurrence_is_not_hidden_by_remaining_case(tmp_path):
    before = report(tmp_path, "before", [("same", "passed"), ("same", "passed")])
    after = report(tmp_path, "after", [("same", "passed")])
    result = compare_reports(before, after)
    assert not result.passed
    assert any("missing existing testcase" in problem and "occurrence 2" in problem for problem in result.problems)


@pytest.mark.parametrize("kind", ["missing", "malformed", "empty", "wrong-root", "suite-error"])
def test_unusable_or_unidentified_junit_results_fail_closed(tmp_path, kind):
    path = tmp_path / "bad.xml"
    content = {"malformed": "<testsuite>", "empty": "<testsuite/>",
               "wrong-root": "<success/>",
               "suite-error": '<testsuite><error message="collection failure"/><testcase name="existing"/></testsuite>'}
    if kind != "missing":
        path.write_text(content[kind])
    assert not require_all_pass(read_report(path, 0)).passed


@pytest.mark.parametrize("state,exit_code", [("failed", 0), ("passed", 1)])
def test_exit_code_and_junit_disagreement_is_rejected(tmp_path, state, exit_code):
    current = report(tmp_path, "current", [("existing", state)], exit_code)
    assert not require_all_pass(current).passed


@pytest.mark.parametrize("state", ["failed", "error", "collection", "skipped"])
def test_focused_gate_has_no_legacy_or_skip_exemption(tmp_path, state):
    current = report(tmp_path, "current", [("critical", state)])
    assert not require_all_pass(current).passed


def test_cli_rejects_new_failure_and_writes_reviewable_json(tmp_path):
    before = report(tmp_path, "before", [("existing", "passed")])
    after = report(tmp_path, "after", [("existing", "passed"), ("new", "failed")])
    output = tmp_path / "result.json"
    command = Path(__file__).with_name("compare_pytest_outcomes.py")
    process = subprocess.run([sys.executable, str(command), "compare", "--before", before.path,
                              "--before-exit-code", "0", "--after", after.path,
                              "--after-exit-code", "1", "--json-report", str(output)],
                             capture_output=True, text=True, timeout=10)
    assert process.returncode == 1
    assert '"passed": false' in output.read_text()
    assert "new testcase must pass" in process.stdout


def test_workflow_wires_all_release_generations_and_strict_focused_gate():
    workflow = Path(__file__).resolve().parents[1] / ".github/workflows/b204-network-audit.yml"
    source = workflow.read_text()
    for required in ("test_b205*py", "test_b206*py", "test_b207*py",
                     "test_native_bvm_dp.py", "test_bounded_pressure_contracts.py",
                     "test_b207_pytest_outcome_gate.py", "compare_pytest_outcomes.py require-pass"):
        assert required in source
    assert '"tools/compare_pytest_outcomes.py", "compare"' in source
    assert '"--before-exit-code", str(old_exit)' in source
    assert '"--after-exit-code", str(new_exit)' in source
    assert "states[key] = state" not in source
