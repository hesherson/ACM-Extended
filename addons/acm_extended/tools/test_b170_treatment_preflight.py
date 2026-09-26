"""B170 treatment-preflight root regression contracts.

The runtime RPT showed the menu was not simply losing its renderer: after Narc Box completed and its continuous
controller cancelled, ACME later logged "Cleared stale treatment preflight." That presentation-only preflight used a
global Boolean as a hard treatment mutex. B170 makes it tokenized, supersedable, and fail-open to clinical treatment.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TREATMENT = ROOT / "addons" / "core" / "overrides" / "fnc_treatment.sqf"
STANCE = ROOT / "addons" / "acm_extended" / "functions" / "fn_providerStanceOwned.sqf"
RECONCILE = ROOT / "addons" / "acm_extended" / "functions" / "fn_providerStateReconcile.sqf"


def read(path):
    return path.read_text(encoding="utf-8")


def test_preflight_boolean_is_not_a_hard_treatment_mutex_anymore():
    s = read(TREATMENT)
    assert 'if (_medic getVariable ["ACME_treatmentPreflightActive", false]) exitWith {false};' not in s
    assert 'if (_medic getVariable ["ACME_treatmentPreflightActive", false]) then {' in s
    assert 'ACME_treatmentPreflightStartedAt' in s


def test_post_treatment_menu_pose_is_authoritative_readiness_not_animation_frame():
    s = read(TREATMENT)
    assert 'private _genericMenuPoseReady = (count _menuPose) >= 3' in s
    assert 'ACME_menuPoseGenericEpoch' in s
    preflight = s[s.index('private _preflightReady ='):s.index('// Presentation preflight may never become a clinical mutex.')]
    assert '_genericMenuPoseReady' in preflight


def test_one_helper_retires_preflight_before_recursive_treatment_launch():
    s = read(TREATMENT)
    helper = s[s.index('private _launchAfterPreflight = {'):s.index('[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;')]
    clear_active = helper.index('setVariable ["ACME_treatmentPreflightActive", false')
    recursive = helper.index('_callArgs call ace_medical_treatment_fnc_treatment')
    assert clear_active < recursive
    assert 'setVariable ["ACME_treatmentPreflightStartedAt", -1' in helper
    assert 'ACME_treatmentPreflightBypass' in helper


def test_both_visual_timeouts_fail_open_to_the_real_treatment():
    s = read(TREATMENT)
    assert s.count('[_u, _callArgs, _token] call _launch;') >= 1
    assert s.count('[_m, _args, _tok] call _launch;') >= 1
    assert 'presentation failure, not a clinical-action failure' in s
    assert 'Clinical treatment still owns the accepted click' in s


def test_stale_preflight_does_not_own_provider_stance_forever():
    s = read(STANCE)
    assert 'ACME_treatmentPreflightStartedAt' in s
    assert 'ACME_treatmentPreflightToken' in s
    assert '(CBA_missionTime - _preflightStarted) <= 4' in s
    assert 'if (_preflightOwned) exitWith {true};' in s


def test_reconcile_uses_real_preflight_generation_age():
    s = read(RECONCILE)
    assert 'ACME_treatmentPreflightStartedAt' in s
    assert 'CBA_missionTime - _startedAt' in s
    assert 'ACME_reconcilePreflightSeen' not in s


def test_latest_click_supersedes_presentation_only_generation_model():
    state = {"token": "old", "active": True, "launched": []}

    def click(token):
        if state["active"]:
            state["active"] = False
            state["token"] = ""
        state["token"] = token
        state["active"] = True

    def completion(token):
        if state["token"] != token:
            return
        state["active"] = False
        state["launched"].append(token)
        state["token"] = ""

    click("new")
    completion("old")
    assert state["active"] is True
    assert state["launched"] == []

    completion("new")
    assert state["active"] is False
    assert state["launched"] == ["new"]
