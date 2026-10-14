"""B177 treatment-start regression contracts.

B170 originally made presentation preflight bounded and fail-open. B177 removes the remaining invisible latency:
presentation is now strictly non-blocking and native treatment starts on the accepted click.
"""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
TREATMENT = ROOT / "addons" / "core" / "overrides" / "fnc_treatment.sqf"
STANCE = ROOT / "addons" / "acm_extended" / "functions" / "fn_providerStanceOwned.sqf"
RECONCILE = ROOT / "addons" / "acm_extended" / "functions" / "fn_providerStateReconcile.sqf"


def read(path):
    return path.read_text(encoding="utf-8")


def test_presentation_is_not_a_treatment_mutex_or_wait_gate():
    s = read(TREATMENT)
    marker = s.index("// B177 button-responsiveness invariant")
    end = s.index("// A newly accepted head-position action", marker)
    block = s[marker:end]
    assert "provider presentation NEVER gates clinical treatment start" in block
    assert "CBA_fnc_waitUntilAndExecute" not in block
    assert "CBA_fnc_waitAndExecute" not in block
    assert "CBA_fnc_execNextFrame" not in block
    assert 'ACME_treatmentPreflightActive", false' in block
    assert 'ACME_treatmentPreflightToken", ""' in block


def test_old_preflight_generation_is_retired_on_every_new_click():
    s = read(TREATMENT)
    marker = s.index("// Retire any pre-B177 deferred presentation generation immediately")
    end = s.index("// A newly accepted head-position action", marker)
    block = s[marker:end]
    for token in (
        'ACME_treatmentPreflightActive", false',
        'ACME_treatmentPreflightToken", ""',
        'ACME_treatmentPreflightBypass", []',
        'ACME_treatmentPreflightStartedAt", -1',
    ):
        assert token in block


def test_provider_owned_animation_prep_is_nonblocking():
    s = read(TREATMENT)
    marker = s.index("// Presentation begins now but never delays native progress")
    end = s.index("// A newly accepted head-position action", marker)
    block = s[marker:end]
    from test_b241_current_ui_expectations import has
    assert has(block, 'if (_animationsEnabled && {_ownsProviderAnim}) then {')
    assert 'call ACME_fnc_menuPoseStop' in block
    assert 'call ACME_fnc_medicAnimationPrep' in block
    assert "waitUntil" not in block


@pytest.mark.parametrize('old,new', [
    ('if (_animationsEnabled && {_ownsProviderAnim}) then {', 'if (true && {_ownsProviderAnim}) then {'),
    ('if (_animationsEnabled && {_ownsProviderAnim}) then {', 'if (_animationsEnabled && {true}) then {'),
])
def test_nonblocking_prep_contract_rejects_ignored_setting_or_pose_owner(monkeypatch, old, new):
    real=read
    current=real(TREATMENT)
    assert old in current
    broken=current.replace(old,new)
    monkeypatch.setitem(globals(), 'read', lambda path: broken if path==TREATMENT else real(path))
    with pytest.raises(AssertionError):
        test_provider_owned_animation_prep_is_nonblocking()


def test_native_treatment_call_remains_after_nonblocking_presentation_setup():
    s = read(TREATMENT)
    marker = s.index("// B177 button-responsiveness invariant")
    native = s.index("private _started = _nativeArgs call ACM_core_fnc_treatmentNative;", marker)
    assert native > marker


def test_stale_hotload_preflight_still_cannot_own_provider_forever():
    s = read(STANCE)
    assert 'ACME_treatmentPreflightStartedAt' in s
    assert 'ACME_treatmentPreflightToken' in s
    assert '(CBA_missionTime - _preflightStarted) <= 4' in s
    assert 'if (_preflightOwned) exitWith {true};' in s


def test_reconcile_can_still_repair_pre_b177_hotload_state():
    s = read(RECONCILE)
    assert 'ACME_treatmentPreflightStartedAt' in s
    assert 'CBA_missionTime - _startedAt' in s
    assert 'ACME_reconcilePreflightSeen' not in s
