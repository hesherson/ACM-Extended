"""Execute the production pure Y-row relation in SQF-VM; no UI or patient mutations."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "addons/acm_extended/functions/fn_transfusionYRows.sqf").read_text()


def bag(kind, site=1, iv=True, remaining=250):
    return [kind, remaining, 0, site, iv, -1, 500, -1, 10]


@pytest.fixture(scope="module")
def vm():
    binary = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not binary:
        pytest.skip("SQF-VM required")
    return binary


def check(vm, selection, row_values, *, part="leftarm", iv=True, site=1,
          y_lines=("leftarm#true#1",), rows=(0, 1), key="leftarm#true#1"):
    args = [selection, row_values, part, iv, site, list(y_lines)]
    expected = [list(rows), key]
    # This older VM exposes the same ASCII casing operation as toLower; all relation logic runs unchanged.
    code = "ACME_fnc_transfusionYRows={" + SOURCE.replace("toLowerANSI", "toLower") + "};\n"
    code += "private _actual=" + json.dumps(args) + " call ACME_fnc_transfusionYRows;\n"
    code += "diag_log (if (_actual isEqualTo " + json.dumps(expected) + ") then {\"Y_ROWS_OK\"} else {format [\"Y_ROWS_FAIL %1\",_actual]});"
    with tempfile.TemporaryDirectory(prefix="acme-y-rows-") as temp:
        path = Path(temp) / "test.sqf"
        path.write_text(code)
        result = subprocess.run([vm, "--automated", "--suppress-welcome", "--no-execute-print",
                                 "--no-work-print", "--input-sqf", str(path)],
                                capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and "[ERR]" not in output and "[FAT]" not in output, output
    assert "Y_ROWS_OK" in output and "Y_ROWS_FAIL" not in output, output


@pytest.mark.parametrize("blood", ["Blood", "FreshBlood", "ACME_Empty"])
@pytest.mark.parametrize("saline", ["Saline", "ACME_SalineY", "ACME_EmptySaline"])
def test_all_real_and_empty_native_branches_link_without_merging_rows(vm, blood, saline):
    check(vm, [bag(blood, remaining=0), bag(saline, remaining=0)], [0, 1])


def test_lb_value_mapping_follows_visible_row_order_instead_of_selection_order(vm):
    selection = [bag("Saline", site=0), bag("Blood"), bag("ACME_SalineY")]
    check(vm, selection, [2, 1])


def test_neighboring_site_cannot_claim_selected_y_branches(vm):
    selection = [bag("Blood", site=0), bag("Saline", site=0), bag("Blood"), bag("Saline")]
    check(vm, selection, [0, 1], rows=())
    check(vm, selection, [2, 3])


@pytest.mark.parametrize("iv", [True, False])
def test_iv_and_io_at_same_body_part_and_index_are_distinct_lines(vm, iv):
    selection = [bag("Blood", site=0, iv=True), bag("Saline", site=0, iv=True),
                 bag("Blood", site=0, iv=False), bag("Saline", site=0, iv=False)]
    indexes = [0, 1] if iv else [2, 3]
    key = "rightleg#" + str(iv).lower() + "#0"
    check(vm, selection, indexes, part="rightleg", iv=iv, site=0, y_lines=[key], key=key)
    other_key = "rightleg#" + str(not iv).lower() + "#0"
    check(vm, selection, indexes, part="rightleg", iv=iv, site=0, y_lines=[other_key], rows=(), key="")


def test_body_and_membership_key_casing_do_not_change_exact_relation(vm):
    check(vm, [bag("Blood"), bag("Saline")], [0, 1], part="LEFTARM", y_lines=["LeftArm#TRUE#1"])


@pytest.mark.parametrize("y_lines", [[], ["rightarm#true#1"], ["leftarm#true#0"], ["leftarm#false#1"]])
def test_two_bags_cannot_create_y_relation_without_exact_hardware_membership(vm, y_lines):
    check(vm, [bag("Blood"), bag("Saline")], [0, 1], y_lines=y_lines, rows=(), key="")


def test_nonadjacent_y_branches_do_not_bracket_an_unrelated_visible_bag(vm):
    check(vm, [bag("Blood"), bag("Saline"), bag("Plasma")], [0, 2, 1], rows=())


@pytest.mark.parametrize("selection,values", [
    ([bag("Blood"), bag("FreshBlood"), bag("Saline")], [0, 1, 2]),
    ([bag("Blood"), bag("Saline"), bag("ACME_SalineY")], [0, 1, 2]),
    ([bag("Blood"), bag("Saline")], [0, 0, 1]),
    ([bag("Blood"), bag("Saline")], [0, 1, 1]),
])
def test_duplicate_or_ambiguous_visible_branches_preserve_only_hardware_key(vm, selection, values):
    check(vm, selection, values, rows=())


@pytest.mark.parametrize("kind", ["Blood", "FreshBlood", "ACME_Empty", "Saline", "ACME_SalineY", "ACME_EmptySaline"])
def test_single_surviving_branch_remains_identified_with_existing_y_hardware(vm, kind):
    check(vm, [bag(kind)], [0], rows=[0])


def test_invalid_native_row_values_do_not_index_another_bag(vm):
    selection = [bag("Blood"), bag("Saline")]
    check(vm, selection, [-1, 9, 0, 1], rows=[2, 3])
    check(vm, selection, [0, 9, 1], rows=[])
    check(vm, selection, [-1, 9], rows=[])


def test_empty_visible_list_preserves_real_y_hardware_key(vm):
    check(vm, [], [], rows=[])


@pytest.mark.parametrize("part,site", [("", 1), ("leftarm", -1)])
def test_unselected_access_does_not_link_visible_rows(vm, part, site):
    check(vm, [bag("Blood"), bag("Saline")], [0, 1], part=part, site=site, rows=[], key="")
