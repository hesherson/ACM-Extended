"""B168 root regression: medical-menu renderer PFH ownership is display-generation scoped.

The failure signature was a visible medical menu with stale/dead treatment buttons after CPR/continuous-action
handoffs. Direct Pressure forced one updateActions pass and made the buttons work again; recreating the menu via
another treatment also recovered it. That is a renderer-driver lifetime defect, not a treatment-specific lock.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GUI = ROOT / "addons" / "gui"


def read(rel):
    return (GUI / rel).read_text(encoding="utf-8")


def test_close_override_is_actually_wired():
    cfg = read("CfgFunctions.hpp")
    assert "class onMenuClose" in cfg
    assert r"overrides\fnc_onMenuClose.sqf" in cfg


def test_open_replaces_old_renderer_pfh_instead_of_reusing_global_handle():
    source = read("overrides/fnc_onMenuOpen.sqf")
    assert 'private _menuEpoch = (missionNamespace getVariable ["ACME_medicalMenuPFHEpoch", 0]) + 1;' in source
    assert 'missionNamespace setVariable ["ACME_medicalMenuPFHEpoch", _menuEpoch];' in source
    assert 'private _oldPFH = missionNamespace getVariable [QACEGVAR(medical_gui,menuPFH), -1];' in source
    assert '[_oldPFH] call CBA_fnc_removePerFrameHandler;' in source
    assert 'if (ACEGVAR(medical_gui,menuPFH) != -1) exitWith' not in source
    assert '_display setVariable ["ACME_medicalMenuPFH", _menuPFH];' in source


def test_renderer_pfh_self_retires_when_its_display_is_superseded():
    source = read("overrides/fnc_onMenuOpen.sqf")
    assert 'private _currentDisplay = uiNamespace getVariable [QACEGVAR(medical_gui,menuDisplay), displayNull];' in source
    assert 'private _currentEpoch = missionNamespace getVariable ["ACME_medicalMenuPFHEpoch", -1];' in source
    assert '_display isNotEqualTo _currentDisplay' in source
    assert '_epoch != _currentEpoch' in source
    assert 'call ACEFUNC(medical_gui,menuPFH);' in source


def test_stale_unload_returns_before_touching_current_global_renderer_state():
    source = read("overrides/fnc_onMenuClose.sqf")
    stale = 'if (isNull _display || {_display isNotEqualTo _currentDisplay} || {_closingEpoch != _currentEpoch}) exitWith {};'
    assert stale in source
    assert source.index(stale) < source.index('ACEGVAR(medical_gui,pendingReopen) = false;')
    assert source.index(stale) < source.index('ACEGVAR(medical_gui,menuPFH) = -1;')
    assert source.index(stale) < source.index('uiNamespace setVariable [QACEGVAR(medical_gui,menuDisplay), displayNull];')


def test_current_close_removes_only_the_pfh_owned_by_that_display():
    source = read("overrides/fnc_onMenuClose.sqf")
    assert 'private _ownedPFH = _display getVariable ["ACME_medicalMenuPFH", -1];' in source
    assert 'private _currentPFH = missionNamespace getVariable [QACEGVAR(medical_gui,menuPFH), -1];' in source
    assert '_ownedPFH == _currentPFH' in source
    assert '[_ownedPFH] call CBA_fnc_removePerFrameHandler;' in source


def test_action_renderer_itself_is_not_patched_again_for_this_fix():
    # B168 fixes who owns/drives updateActions, not treatment callbacks or row semantics.
    source = read("overrides/fnc_updateActions.sqf")
    assert 'ACME_medicalMenuPFHEpoch' not in source
    assert '_ctrl ctrlRemoveAllEventHandlers \'ButtonClick\';' in source
    assert "_ctrl ctrlAddEventHandler ['ButtonClick', _statement];" in source


def test_lifecycle_model_old_close_cannot_kill_new_renderer():
    """Pure lifecycle model for the CPR fast-close/reopen ordering that caused the live bug."""
    state = {"epoch": 0, "current": None, "pfh": -1, "removed": []}

    def open_display(name):
        state["epoch"] += 1
        epoch = state["epoch"]
        if state["pfh"] >= 0:
            state["removed"].append(state["pfh"])
        pfh = 100 + epoch
        state["current"] = name
        state["pfh"] = pfh
        return {"name": name, "epoch": epoch, "pfh": pfh}

    def close_display(display):
        if display["name"] != state["current"] or display["epoch"] != state["epoch"]:
            return
        if display["pfh"] == state["pfh"]:
            state["removed"].append(display["pfh"])
        state["pfh"] = -1
        state["current"] = None

    old = open_display("old")
    new = open_display("new")  # CPR/menu return races ahead of old onUnload
    close_display(old)          # late old onUnload must be harmless

    assert state["current"] == "new"
    assert state["pfh"] == new["pfh"]
    assert new["pfh"] not in state["removed"]

    close_display(new)
    assert state["pfh"] == -1
    assert new["pfh"] in state["removed"]


def test_narc_box_return_uses_normal_medical_menu_open_lifecycle():
    sk_close = (ROOT / "addons" / "acm_extended" / "functions" / "fn_skClose.sqf").read_text(encoding="utf-8")
    reopen = (ROOT / "addons" / "acm_extended" / "functions" / "fn_reopenMedicalMenu.sqf").read_text(encoding="utf-8")

    # Narc Box does not own or repair action controls itself. Its close handler returns through ACE's normal
    # openMenu entry point, so B168's display-generation renderer ownership is the single shared fix.
    assert '[_patient, "medication"] call ACME_fnc_reopenMedicalMenu;' in sk_close
    assert '[_patient] call ace_medical_gui_fnc_openMenu;' in reopen
    assert 'updateActions' not in sk_close
    assert 'menuPFH' not in sk_close
    assert 'updateActions' not in reopen
    assert 'menuPFH' not in reopen


def test_narc_box_close_reopen_model_keeps_new_renderer_alive():
    """Model the exact medical menu -> Narc Box -> returned medical menu lifecycle."""
    state = {"epoch": 0, "current": None, "pfh": -1, "removed": []}

    def open_medical(name):
        state["epoch"] += 1
        epoch = state["epoch"]
        if state["pfh"] >= 0:
            state["removed"].append(state["pfh"])
        pfh = 200 + epoch
        state["current"] = name
        state["pfh"] = pfh
        return {"name": name, "epoch": epoch, "pfh": pfh}

    def unload_medical(display):
        if display["name"] != state["current"] or display["epoch"] != state["epoch"]:
            return
        if display["pfh"] == state["pfh"]:
            state["removed"].append(display["pfh"])
        state["pfh"] = -1
        state["current"] = None

    before_narc = open_medical("before-narc")
    unload_medical(before_narc)
    assert state["pfh"] == -1

    returned = open_medical("after-narc")
    assert state["pfh"] == returned["pfh"]

    # A delayed duplicate unload from the pre-Narc display cannot kill the returned menu.
    unload_medical(before_narc)
    assert state["current"] == "after-narc"
    assert state["pfh"] == returned["pfh"]
    assert returned["pfh"] not in state["removed"]
