"""B169 medical-menu renderer owner regression contracts.

B168 tried to repair ACE onMenuOpen/onMenuClose overrides. The runtime RPT proved those ACE functions are final in
this load order ("Attempt to override final function"). B169 therefore owns the renderer from ACME's existing
ace_medicalMenuOpened event instead of relying on replacing ACE final functions.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "addons" / "acm_extended" / "functions" / "fn_registerMedicalMenuOpenRuntime.sqf"
NARC_CLOSE = ROOT / "addons" / "acm_extended" / "functions" / "fn_skClose.sqf"
NARC_REOPEN = ROOT / "addons" / "acm_extended" / "functions" / "fn_reopenMedicalMenu.sqf"


def text(path):
    return path.read_text(encoding="utf-8")


def test_renderer_is_owned_from_medical_menu_open_event_not_final_ace_override():
    s = text(RUNTIME)
    assert '["ace_medicalMenuOpened", {' in s
    assert 'ACME_medicalMenuRendererEpoch' in s
    assert 'ACME_medicalMenuRendererPFH' in s
    assert 'call ace_medical_gui_fnc_menuPFH;' in s


def test_action_rows_are_bound_synchronously_on_each_new_display():
    s = text(RUNTIME)
    event = s.index('["ace_medicalMenuOpened", {')
    bind = s.index('[_display] call ace_medical_gui_fnc_updateActions;', event)
    add_pfh = s.index('call CBA_fnc_addPerFrameHandler;', bind)
    assert event < bind < add_pfh


def test_acme_renderer_uses_its_own_handle_not_ace_global_handle():
    s = text(RUNTIME)
    add = s.index('private _rendererPFH = [{')
    retire_stock = s.index('private _acePFH = missionNamespace getVariable ["ace_medical_gui_menuPFH", -1];')
    block = s[add:retire_stock]
    assert 'ACME_medicalMenuRendererPFH' in block
    assert 'ace_medical_gui_menuPFH' not in block


def test_stock_ace_renderer_is_retired_only_after_onload_finishes():
    s = text(RUNTIME)
    assert 'call CBA_fnc_execNextFrame;' in s
    assert 'missionNamespace setVariable ["ace_medical_gui_menuPFH", -1];' in s
    assert '[_acePFH] call CBA_fnc_removePerFrameHandler;' in s


def test_old_display_unload_cannot_remove_new_renderer_generation():
    s = text(RUNTIME)
    unload = s.index('_display displayAddEventHandler ["Unload", {')
    body = s[unload:s.index('}];', unload) + 3]
    assert 'ACME_medicalMenuRendererEpoch' in body
    assert '_epoch != (uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", -2])' in body
    assert '_pfh == (uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -1])' in body


def test_narc_box_returns_through_same_menu_open_event():
    close = text(NARC_CLOSE)
    reopen = text(NARC_REOPEN)
    assert '[_patient, "medication"] call ACME_fnc_reopenMedicalMenu;' in close
    assert '[_patient] call ace_medical_gui_fnc_openMenu;' in reopen


def test_lifecycle_model_narc_close_reopen_keeps_renderer_owner():
    state = {"epoch": 0, "renderer": -1, "display": None, "removed": []}

    def event_open(display):
        state["epoch"] += 1
        if state["renderer"] >= 0:
            state["removed"].append(state["renderer"])
        state["display"] = display
        state["renderer"] = 500 + state["epoch"]
        return {"display": display, "epoch": state["epoch"], "renderer": state["renderer"]}

    def unload(owner):
        if owner["epoch"] != state["epoch"]:
            return
        if owner["renderer"] == state["renderer"]:
            state["removed"].append(owner["renderer"])
            state["renderer"] = -1
            state["display"] = None

    first = event_open("before-narc")
    unload(first)
    returned = event_open("after-narc")

    # Late duplicate unload from the pre-Narc display is harmless.
    unload(first)
    assert state["display"] == "after-narc"
    assert state["renderer"] == returned["renderer"]
    assert returned["renderer"] not in state["removed"]
