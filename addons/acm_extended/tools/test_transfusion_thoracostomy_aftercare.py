"""Source contracts for transfusion selection and surgical-seal aftercare.
These checks complement HEMTT; they do not replace an Arma multiplayer test.
"""
from pathlib import Path
import re

from source_scan import lex, matching, split_args

ADDON = Path(__file__).resolve().parents[1]
ADDONS = ADDON.parent


def read(path):
    return (ADDON / path).read_text(encoding="utf-8-sig")


def calls(text, function):
    tokens = lex(text)
    pairs = matching(tokens)
    result = []
    for i, token in enumerate(tokens):
        if token.kind == "ident" and token.value == function:
            if i >= 2 and tokens[i - 1].value == "call" and tokens[i - 2].value == "]":
                start = pairs[i - 2]
                result.append(split_args(tokens, start + 1, i - 2, pairs))
    return result


def test_selected_access_passes_one_changes_array_to_state_writer():
    selection = read("functions/fn_selectTransfusionAccess.sqf")
    invocations = calls(selection, "ACM_circulation_fnc_setLocalUiState")
    assert len(invocations) == 1
    assert len(invocations[0]) == 1, "params expects one array of changes, not three arguments"
    changes = invocations[0][0]
    entries = split_args(changes, 1, len(changes) - 1, matching(changes))
    assert len(entries) == 3
    assert [entry[1].value for entry in entries] == [
        "transfusionSelectIV", "transfusionSelectedBodyPart", "transfusionSelectedAccessSite"
    ]
    write_at = selection.index("call ACM_circulation_fnc_setLocalUiState")
    assert write_at < selection.index("call ACM_circulation_fnc_TransfusionMenu_UpdateSelection")
    assert write_at < selection.index("call ACM_circulation_fnc_TransfusionMenu_UpdateBagList")


def test_access_selection_still_validates_exact_site_and_route():
    source = read("functions/fn_selectTransfusionAccess.sqf")
    assert '[_patient, _bodyPart, 0, _site] call ACM_circulation_fnc_hasIV' in source
    assert '[_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO' in source
    assert 'if (!_valid) exitWith {};' in source
    assert 'ACME_infusion_ActiveInfusionListSignature' in source
    assert 'ACME_infusion_PreparedListSignature' in source


def test_route_toggle_is_removed_without_removing_inventory_switch():
    dialog = (ADDONS / "circulation/TransfusionMenu_Dialog.hpp").read_text()
    assert not re.search(r"class\s+ToggleIV\b", dialog)
    assert "idc = 86009;" not in dialog
    assert "class SwitchTargetInventory: RscButtonMenu" in dialog
    assert "call FUNC(TransfusionMenu_SwitchTargetInventory)" in dialog


def test_access_hotspot_plays_default_click_sound():
    config = read("config.cpp")
    hotspot = config.split("class ACME_EJTransfusionHotspot: RscButton {", 1)[1].split("\n};", 1)[0]
    assert r'soundClick[] = {"\a3\ui_f\data\sound\rscbutton\soundClick", 0.09, 1};' in hotspot


def test_retired_transfusion_toggle_cannot_affect_runtime():
    for relative in ["XEH_preInit.sqf", "functions/fn_applyHardcore.sqf"]:
        source = read(relative)
        assert "ACME_hc_transfusion" not in source
        assert "ACME_hcEff_transfusion" not in source
    volume = (ADDONS / "circulation/functions/fnc_getBloodVolumeChange.sqf").read_text()
    assert "ACME_hcEff_transfusion" not in volume
    assert "ACME_YLineUnitsSinceFlush" in volume
    assert "ACME_YLineVolSinceFlush" in volume
    config = read("config.cpp")
    tubing = config.split("class ACME_YTubing:", 1)[1].split("class ItemInfo:", 1)[0]
    assert "Hardcore" not in tubing
    assert ">=250" not in tubing


def test_standard_calcium_values_survive_toggle_removal():
    defaults = read("functions/fn_initResuscitationConfig.sqf")
    expected = {
        "ACME_ca_citrateThreshold": 2.0,
        "ACME_ca_citratePerLiter": 0.22,
        "ACME_ca_floor": 0.45,
        "ACME_ca_coagMaxMult": 1.4,
    }
    for name, value in expected.items():
        match = re.search(r"\b" + name + r"\s*=\s*([0-9.]+)\s*;", defaults)
        assert match and float(match[1]) == value
    assert "ACME_ca_citrateThreshold =" not in read("functions/fn_applyHardcore.sqf")


def test_aftercare_is_owner_routed_and_epoch_guarded():
    owner=read('functions/fn_ownerDispatch.sqf')
    aftercare=read('functions/fn_thoraAftercareLocal.sqf')
    assert 'case "thoraAftercare": {_args call ACME_fnc_thoraAftercareLocal;};' in owner
    for gate in ['!local _patient','!alive _medic','ACME_fnc_clinicalEpoch','["left", "right"]',
                 'ACME_fnc_procedureAllowed','ACME_thora_incision_%1','ACME_thora_tube_%1']:
        assert gate in aftercare
    # Availability must not reveal death; the physiology call alone is live-only.
    from test_historical_airway_execution import test_aftercare_remains_available_on_dead_patients_without_resuming_physiology
    for operation in ['peel','burp','sweep']:
        test_aftercare_remains_available_on_dead_patients_without_resuming_physiology(False,operation)


def test_peel_reopens_only_the_selected_surgical_tract():
    source = read("functions/fn_thoraAftercareLocal.sqf")
    writes = calls(source, "ACME_fnc_thoraSideStateCommit")
    assert len(writes) == 3
    assert all(len(args) == 4 and args[1][0].value == "_side" for args in writes)
    assert [(args[2][0].value, args[3][0].value) for args in writes] == [
        ("sealed", "false"), ("closed", "false"), ("open", "finger")
    ]
    assert 'if (_operation == "peel") then {' in source
    # Do not remove traumatic-wound seals or reset the opposite side's native tube state.
    for forbidden in ["ACME_CS_holeData", "Thoracostomy_State", "removeItem", "addItem",
                      "ACM_breathing_fnc_Thoracostomy_start"]:
        assert forbidden not in source


def test_repeat_finger_sweep_precedes_disposable_kit_consumption():
    mouse = read("functions/fn_thoraMouseDown.sqf")
    finger = mouse.split('if (_held isEqualTo "finger") exitWith {', 1)[1].split(
        'if (_held in ["seal", "tube"]) exitWith {', 1
    )[0]
    assert finger.index('if (_tract == "finger") exitWith {') < finger.index(
        "call ACME_fnc_treatmentSupplyTake"
    )
    assert '"sweep"' in finger and "ACME_fnc_ownerDispatch" in finger
    for path in ["functions/fn_thoraMouseDown.sqf", "functions/fn_thoraSelectTool.sqf"]:
        source = read(path)
        assert "ACME_fnc_thoraCanSweep" in source
        assert "&& {!_repeatFinger}" in source
    gate = read("functions/fn_thoraCanSweep.sqf")
    assert '== "finger"' in gate
    assert "ACME_thora_sealed_%1" in gate
    assert "ACME_thora_tube_%1" in gate
    assert "ACME_thora_closed_%1" in gate


def test_seal_hit_test_and_scroll_are_wired_to_visible_art():
    hit = read("functions/fn_thoraSealAt.sqf")
    assert "ctrlPosition _seal" in hit
    assert "ACME_fnc_chestSealMouseCoords" in hit
    assert "ACME_Thora_Held" in hit
    mouse = read("functions/fn_thoraMouseDown.sqf")
    assert 'if (call ACME_fnc_thoraSealAt) exitWith {' in mouse
    assert '"peel"' in mouse
    init = read("functions/fn_thoraInit.sqf")
    assert 'displayAddEventHandler ["MouseZChanged"' in init
    assert 'ctrlAddEventHandler ["MouseZChanged"' in init
    scroll = read("functions/fn_thoraSealScroll.sqf")
    assert '_frame >= 5 && {!_fired}' in scroll
    assert '"burp"' in scroll
    assert "ACME_fnc_ownerDispatch" in scroll
    assert "ACME_fnc_thoraRenderTube" in scroll
    assert "chest_seal_burp_%1_frame_0%2_ca.paa" in read("functions/fn_thoraRenderTube.sqf")


def test_new_functions_are_registered():
    config = read("config.cpp")
    for function in ["thoraAftercareLocal", "thoraCanSweep", "thoraSealAt", "thoraSealScroll"]:
        assert f"class {function} {{}};" in config
        assert (ADDON / "functions" / f"fn_{function}.sqf").is_file()


def test_changed_sqf_delimiters_are_balanced():
    names = [
        "selectTransfusionAccess", "applyHardcore", "initResuscitationConfig", "thoraAftercareLocal",
        "thoraCanSweep", "thoraSealAt", "thoraSealScroll", "thoraMouseDown", "thoraSelectTool",
        "thoraInit", "thoraFlip", "thoraRenderTube", "thoraTick", "thoraCanOpen", "ownerDispatch",
    ]
    for name in names:
        tokens = lex(read(f"functions/fn_{name}.sqf"))
        pairs = matching(tokens)
        for index, token in enumerate(tokens):
            if token.kind == "symbol" and token.value in "[]{}()":
                assert index in pairs, f"{name}: unmatched {token.value} on line {token.line}"
