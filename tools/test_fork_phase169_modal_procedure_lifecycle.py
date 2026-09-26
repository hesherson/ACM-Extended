#!/usr/bin/env python3
"""RC25: modal procedures must own ACE menu lifecycle and the ACM treatment bridge."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_treatment_bridge_is_reconciled_after_ace_startup():
    post = read("addons/core/XEH_postInit.sqf")
    compat = read("addons/acm_extended/functions/fn_compatCheck.sqf")

    assert 'missionNamespace getVariable ["ace_medical_treatment_fnc_treatment", {}]' in post
    assert '"acme_applychestseal"' in post.lower()
    assert 'ace_medical_treatment_fnc_treatment = compile preprocessFileLineNumbers QPATHTOF(overrides\\fnc_treatment.sqf);' in post
    assert '["ace_medical_treatment_fnc_treatment", "ACME_ApplyChestSeal"]' in compat

def test_chest_seal_takes_ace_menu_ownership_before_remote_prep():
    s = read("addons/acm_extended/functions/fn_chestSealOpen.sqf")
    pending = s.index("ace_medical_gui_pendingReopen = false;")
    pause = s.index("call ACM_GUI_fnc_pauseMedicalMenuPFH;")
    begin = s.index('"chestSealPatientBegin"')
    assert pending < begin
    assert pause < begin
    assert 'uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull]' in s
    assert "_medicalMenu closeDisplay 2" in s

def test_thoracostomy_takes_menu_ownership_and_all_preopen_aborts_cleanup():
    s = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    lease = s.index('private _vestSerial')
    assert s.index("ace_medical_gui_pendingReopen = false;") < lease
    assert s.index("call ACM_GUI_fnc_pauseMedicalMenuPFH;") < lease
    assert 'uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull]' in s

    # Invalid provider/locality, failed createDialog and prep timeout all converge on the real close path.
    assert s.count("[] call ACME_fnc_thoraClose;") >= 3
    timeout = s.index("[ACME THORACOSTOMY] Chest-access preparation timed out")
    assert s.index("[] call ACME_fnc_thoraClose;", timeout) > timeout

def test_iv_suppresses_stale_menu_pfh_and_recovers_generation_race():
    open_fn = read("addons/acm_extended/functions/fn_ivMinigameOpen.sqf")
    close_fn = read("addons/acm_extended/functions/fn_ivMinigameClose.sqf")

    assert "ace_medical_gui_pendingReopen = false;" in open_fn
    assert "call ACM_GUI_fnc_pauseMedicalMenuPFH;" in open_fn
    assert 'private _session = +(uiNamespace getVariable ["ACME_IV_Session", []]);' in open_fn
    assert 'if !([_session] call ACME_fnc_ivUiValid) exitWith' in open_fn
    assert 'uiNamespace setVariable ["ACME_IV_Session", []];' in open_fn
    assert "_return call ACME_fnc_reopenMedicalMenu" in open_fn
    assert "call ACM_GUI_fnc_resumeMedicalMenuPFH;" in close_fn

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc25: modal treatment bridge and ACE menu lifecycle")
