#!/usr/bin/env python3
"""Stable B189: Seconds-to-Push owns keyboard focus even on the first Narc Box display."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_deferred_pending_tag_repair_checks_page_before_creating_controls():
    s = read("addons/acm_extended/functions/fn_skPendingTagRender.sqf")

    view = s.index('private _view = uiNamespace getVariable ["ACME_SK_View", "syringe"];')
    body_exit = s.index('if (!_showSetup) exitWith {', view)
    ensure = s.index("call ACME_fnc_skPendingTagEnsure;", body_exit)

    # First-open repair must not ctrlCreate Draw-page tag controls after Body Map owns keyboard input.
    assert view < body_exit < ensure

    guarded = s[body_exit:ensure]
    assert "skPendingTagEnsure" not in guarded
    assert "ctrlCreate" not in guarded
    assert "84610" in guarded


def test_push_duration_edit_acquires_namespace_lease_before_focus_resolution():
    s = read("addons/acm_extended/functions/fn_skBodyActionRender.sqf")
    mouse = s.split('ctrlAddEventHandler ["MouseButtonDown", {', 1)[1].split("}];", 1)[0]

    lease = mouse.index('uiNamespace setVariable ["ACME_SK_PushDurationEditing",true];')
    focus = mouse.index("ctrlSetFocus _ctrl;")
    assert lease < focus

    assert 'ctrlAddEventHandler ["SetFocus"' in s
    assert 'ctrlAddEventHandler ["KillFocus"' in s


def test_list_rebuild_is_forbidden_while_duration_editor_owns_keyboard():
    s = read("addons/acm_extended/functions/fn_skListRefresh.sqf")

    guard = s.index('private _durationEditing = (uiNamespace getVariable ["ACME_SK_PushDurationEditing", false])')
    exit_ = s.index("if (_durationEditing) exitWith {};", guard)
    first_create = s.index("ctrlCreate", exit_)
    assert guard < exit_ < first_create


def test_hidden_native_medication_list_cannot_clear_or_reselect_while_typing():
    s = read("addons/acm_extended/functions/fn_skMedicationSync.sqf")

    guard = s.index('private _durationEditing = (uiNamespace getVariable ["ACME_SK_PushDurationEditing", false])')
    exit_ = s.index("if (_durationEditing) exitWith {", guard)
    lbclear = s.index("lbClear _list;", exit_)
    lbselect = s.index("_list lbSetCurSel", exit_)
    assert guard < exit_ < lbclear
    assert exit_ < lbselect
    assert 'ACME_SK_MedicationRows' in s[exit_:lbclear]


def test_ui_tick_suspends_all_focus_sensitive_stock_refreshes():
    s = read("addons/acm_extended/functions/fn_skUiTick.sqf")
    assert "private _durationEditOwnsFocus" in s

    assert 'if (!_durationEditOwnsFocus && {!_infusion} && {_now >= (_d getVariable ["ACME_SK_NextStockRefresh", 0])}) then {' in s
    assert 'if (!_durationEditOwnsFocus && {_now >= (_d getVariable ["ACME_SK_NextRefresh", 0])}) then {' in s
    assert 'if (!_durationEditOwnsFocus && {_now >= (_d getVariable ["ACME_SK_NextMedStock", 0])}) then {' in s


def test_first_open_delayed_tag_repaint_remains_safe_after_body_switch():
    inject = read("addons/acm_extended/functions/fn_skInject.sqf")
    pending = read("addons/acm_extended/functions/fn_skPendingTagRender.sqf")

    # The delayed repair still exists for the Draw page, but the callee now exits before creation on Body Map.
    assert "call ACME_fnc_skPendingTagRender;" in inject
    assert "0.03] call CBA_fnc_waitAndExecute;" in inject
    assert pending.index('if (!_showSetup) exitWith {') < pending.index("call ACME_fnc_skPendingTagEnsure;")


def test_build_identity_is_b189_stable():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B189 first-open Narc Box focus regression: PASS")
