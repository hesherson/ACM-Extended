"""B165 regression contracts: restore B161 action execution and keep anatomy fixes presentation-only."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RENDER = (ROOT.parent / "gui" / "overrides" / "fnc_updateActions.sqf").read_text(encoding="utf-8")
COLLECT = (ROOT.parent / "gui" / "overrides" / "fnc_collectActions.sqf").read_text(encoding="utf-8")
GROUPS = (ROOT / "functions" / "fn_initMedicalMenuConfig.sqf").read_text(encoding="utf-8")


def test_renderer_is_back_on_b161_action_pipeline():
    assert "private _paintKey = [_target, _bodyPart, _selectedCategory];" in RENDER
    assert "private _anatomyFiltered" not in RENDER
    assert "private _groupAnatomyAllowed" not in RENDER
    assert "_ctrl ctrlAddEventHandler ['ButtonClick', _statement];" in RENDER
    assert "_child set [2, {true}];" in RENDER


def test_collector_still_compiles_native_treatment_statement_once():
    # Source keeps ACE's macro form until HEMTT preprocessing. Assert the actual source contract rather than the
    # post-preprocessor symbol name, which never appears literally in fnc_collectActions.sqf.
    assert "DACEFUNC(ACE_ADDON(medical_treatment),treatment)" in COLLECT
    assert COLLECT.count("private _statement = compile format") == 1
    assert COLLECT.count("DACEFUNC(ACE_ADDON(medical_treatment),treatment)") == 1
    assert "ACEGVAR(medical_gui,actions) pushBack [_displayName, _category, _condition, _statement" in COLLECT


def test_anatomy_fix_is_group_visibility_only():
    # These group gates do not mutate treatment rows/callbacks.
    assert '["adjuncts", "Airway", "airway"' in GROUPS
    assert '["ventilation", "Breathing", "airway"' in GROUPS
    assert '["chest", "Chest", "airway"' not in GROUPS
    assert '["position", "Positioning", "airway"' not in GROUPS
    assert '"Apply Chest Seal", "Perform Needle-Chest-Decompression", "Perform NCD (NAR SPEAR)"' in GROUPS
    assert '"Establish Recovery Position", "Cancel Recovery Position"' in GROUPS
    assert '["capno", "Capnography", "airway"' in GROUPS
    gates = dict(re.findall(r'\["([^"]+)", "[^"]+", "[^"]+",.*?\], \{([^}]+)\}', GROUPS, re.S))
    assert {name for name, gate in gates.items() if gate == "ace_medical_gui_selectedBodyPart == 0"} == {
        "capno", "route_po", "route_in", "route_buc"
    }
    assert {name for name, gate in gates.items() if gate == "ace_medical_gui_selectedBodyPart == 1"} == set()
    # Chest care and respiratory assessment share Breathing on Head/Body.
    assert gates["ventilation"] == "ace_medical_gui_selectedBodyPart in [0, 1]"
    assert gates["adjuncts"] == "ace_medical_gui_selectedBodyPart in [0, 1]"
    assert "private _anatomyFiltered" not in GROUPS
