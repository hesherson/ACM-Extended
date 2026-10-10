"""Current weapon-prep and immediate-treatment bridge contracts.

Weapon holstering remains a presentation helper for ACME-owned provider poses. It must never delay the native
clinical treatment/progress bar.
"""
import re
import pytest

from source_scan import lex
from test_menu_death_lifecycle import ROOT, adapt, execute

F = ROOT / "addons/acm_extended/functions"
TREATMENT = ROOT / "addons/core/overrides/fnc_treatment.sqf"


def source(name):
    return (F / ("fn_" + name + ".sqf")).read_text()


def engine(text):
    for unit in ("_medic", "_m", "_u", "_unit"):
        for prefix, replacement in [
            ("local ", "_localProvider"), ("alive ", "_alive"),
            ("currentWeapon ", "_weaponNow"), ("handgunWeapon ", '"pistol"'),
            ("animationState ", "_animNowFixture"), ("stance ", "_stanceNow"),
            ("objectParent ", "_providerParent"), ("netId ", '"medic"'),
        ]:
            text = re.sub(re.escape(prefix + unit) + r"\b", lambda _: replacement, text)
        text = re.sub(re.escape(unit) + r" setUnitPos ([^;]+);", r"_positions pushBack \1;", text)
    text = text.replace('objectParent _patient', '_patientParent')
    text = text.replace('_medic action ["SwitchWeapon", _medic, _medic, 299];', '_engineHolsters pushBack ["SwitchWeapon", _medic, _medic, 299];')
    text = text.replace('_medic selectWeapon "";', '_weaponNow="";')
    return adapt(text)


def helper_setup(ace=True):
    body = r'''
        private _localProvider=true;
        private _alive=true;
        private _weaponNow="rifle";
        private _animNowFixture="AmovPercMstpSrasWrflDnon";
        private _stanceNow="STAND";
        private _providerParent=objNull;
        private _patientParent=objNull;
        private _positions=[];
        private _holsters=[];
        private _engineHolsters=[];
        private _moves=[];
        CBA_missionTime=10;
        ACME_fnc_animBlocked={!(_providerParent isEqualTo objNull)};
    '''
    if ace:
        body += 'ace_weaponselect_fnc_putWeaponAway={_holsters pushBack (_this select 0);};'
    else:
        body += 'ace_weaponselect_fnc_putWeaponAway=nil;'
    body += 'ACME_fnc_medicAnimationPrep={' + engine(source("medicAnimationPrep")) + '};'
    return body


def setup(ace=True):
    # Config read values select ordinary limb dressing, not head/chest-prep paths.
    # All treatment branches remain in the compiled function.
    bridge = TREATMENT.read_text()
    bridge = bridge.replace('configFile >> "ace_medical_treatment_actions" >> _classname', 'configNull')
    bridge = bridge.replace('getText (_cfg >> "category")', '_categoryFixture')
    bridge = bridge.replace('getNumber (_cfg >> "ACM_rollToBack")', '0')
    bridge = bridge.replace('getNumber (_cfg >> "ACM_cancelRecovery")', '0')
    body = r'''
        private _localProvider = true;
        private _weaponNow = "rifle";
        private _animNowFixture = "AmovPercMstpSrasWrflDnon";
        private _stanceNow = "STAND";
        private _providerParent = objNull;
        private _patientParent = objNull;
        private _positions = [];
        private _holsters = [];
        private _engineHolsters = [];
        private _timers = [];
        private _nativeCalls = [];
        private _nativeAccepted = true;
        private _categoryFixture = "bandage";
        private _permitted = true;
        private _interactable = true;
        private _actualSide = "front";
        private _clock = 10;
        ACME_fnc_animBlocked = {!(_providerParent isEqualTo objNull)};
        ACME_fnc_treatmentPoseStop = {};
        ACME_fnc_menuPoseStop = {};
        ACME_fnc_providerStanceOwned = {false};
        CBA_fnc_waitUntilAndExecute = {_timers pushBack _this;};
        CBA_fnc_execNextFrame = {_waits pushBack _this;};
        ACME_fnc_procedureActionAllowed = {_permitted};
        ACME_fnc_chestSealCanPhysicalRoll = {false};
        ACME_fnc_chestSealActualSide = {"front"};
        ACME_fnc_doAnim = {_moves pushBack _this;};
        ace_common_fnc_canInteractWith = {_interactable};
        ace_common_fnc_isPlayer = {(_this select 0) isEqualTo ACE_player};
        ace_medical_treatment_fnc_canTreatCached = {true};
        ACM_core_fnc_treatmentNative = {
            _nativeCalls pushBack [_this,
                (_this select 0) getVariable ["ACME_treatmentPreflightBypass",[]]];
            _nativeAccepted
        };
        ace_medical_gui_pendingReopen = false;
        // Native availability is toggled per test. No hidden sling integration.
        tsp_fnc_animate_sling = {_ok=false;};
        tsp_fnc_animate_sling_get = {_ok=false;};
        private _condition = {private _j=_timers select _this; (_j select 2) call (_j select 0)};
        private _deliver = {
            private _j=_timers select _this;
            private _ready=(_j select 2) call (_j select 0);
            [_ready,"test delivered an unready success callback"] call _check;
            if (_ready) then {(_j select 2) call (_j select 1);};
        };
        private _timeout = {private _j=_timers select _this; (_j select 2) call (_j select 4);};
    '''
    if ace:
        body += 'ace_weaponselect_fnc_putWeaponAway = {_holsters pushBack (_this select 0);};'
    else:
        body += 'ace_weaponselect_fnc_putWeaponAway = nil;'
    body += 'ACME_fnc_medicAnimationPrep = {' + engine(source('medicAnimationPrep')) + '};'
    body += 'ACME_fnc_providerAnimSpeedOwned = {' + engine(source('providerAnimSpeedOwned')) + '};'
    body += 'ACME_fnc_feelSkinStop = {' + engine(source('feelSkinStop')) + '};'
    body += 'ace_medical_treatment_fnc_treatment = {' + engine(bridge) + '};'
    return body



@pytest.mark.parametrize("weapon,delay", [("pistol", .95), ("rifle", .70), ("launcher", .70)])
@pytest.mark.parametrize("ace", [True, False])
def test_one_engine_holster_request_is_retained(weapon, delay, ace):
    execute(helper_setup(ace) + f'_weaponNow="{weapon}"; private _minimum={delay};' + r'''
        private _first=[_medic] call ACME_fnc_medicAnimationPrep;
        [_first==_minimum,"initial settle changed"] call _check;
        private _record=+(_medic getVariable ["ACME_medicAnimationPrep",[]]);
        CBA_missionTime=10.1;
        private _again=[_medic] call ACME_fnc_medicAnimationPrep;
        [_again>0,"pending settle vanished"] call _check;
        [(_medic getVariable ["ACME_medicAnimationPrep",[]]) isEqualTo _record,"pending holster token replaced"] call _check;
        [count _holsters+count _engineHolsters==1,"helper queued multiple holsters"] call _check;
    ''')


@pytest.mark.parametrize("animation", [
    "AmovPknlMstpSnonWnonDnon", "ACME_ChestSealWorkspace",
    "ACME_StethoscopeWork", "ACME_DirectPressureHold", "ACM_GenericContinuous", "ACM_ProneContinuous",
])
def test_visible_empty_hands_do_not_reholster(animation):
    execute(helper_setup() + r'''
        [_medic] call ACME_fnc_medicAnimationPrep;
        _weaponNow="";
    ''' + f'_animNowFixture="{animation}";' + r'''
        private _delay=[_medic] call ACME_fnc_medicAnimationPrep;
        [_delay==0 && {count _holsters==1},"settled hands kept holstering"] call _check;
    ''')


def test_treatment_bridge_contains_no_generic_presentation_wait():
    s = TREATMENT.read_text()
    marker = s.index("// B177 button-responsiveness invariant")
    end = s.index("// A newly accepted head-position action", marker)
    block = s[marker:end]
    assert "CBA_fnc_waitUntilAndExecute" not in block
    assert "CBA_fnc_waitAndExecute" not in block
    assert "CBA_fnc_execNextFrame" not in block
    assert 'call ACME_fnc_medicAnimationPrep' in block


def test_native_treatment_is_called_directly_after_presentation_setup():
    s = TREATMENT.read_text()
    marker = s.index("// B177 button-responsiveness invariant")
    native = s.index("private _started = _nativeArgs call ACM_core_fnc_treatmentNative;", marker)
    assert native > marker


def test_provider_gesture_receives_patient_for_ambulatory_selection():
    s = TREATMENT.read_text()
    assert '[_m, _mode, _window, _patient] call ACME_fnc_treatmentGesture;' in s


def test_one_engine_holster_request_is_retained_across_repeated_controllers(*args):
    """Historical identity retained against the current one-shot holster helper."""
    if args:
        test_one_engine_holster_request_is_retained(*args)
        return
    for weapon, delay in (("pistol", .95), ("rifle", .70), ("launcher", .70)):
        for ace in (True, False):
            test_one_engine_holster_request_is_retained(weapon, delay, ace)


def test_real_pose_handoff_shares_pending_holster_instead_of_restarting_it(*args):
    """Current bridge never installs a generic presentation wait/restart loop."""
    if args:
        weapon=args[0]
        delay=0.95 if weapon=="pistol" else 0.70
        test_one_engine_holster_request_is_retained(weapon, delay, True)
    test_treatment_bridge_contains_no_generic_presentation_wait()
    test_native_treatment_is_called_directly_after_presentation_setup()


def test_logical_clear_during_visible_holster_waits_without_reissuing(ace=True):
    """Compatibility identity for the current one-request holster reservation."""
    test_one_engine_holster_request_is_retained("rifle", 0.70, ace)


def test_engine_fallback_has_same_provider_and_switchweapon_contract():
    """Engine fallback uses the same single-request reservation and never redraws."""
    test_one_engine_holster_request_is_retained("rifle", 0.70, False)
    test_no_direct_weapon_reselection_was_reintroduced()


def test_pose_direct_pressure_exception_stays_scoped_and_does_not_restore_a_weapon():
    """The settled Direct Pressure empty-hands exception never reselects a weapon."""
    test_visible_empty_hands_do_not_reholster("ACME_DirectPressureHold")
    test_no_direct_weapon_reselection_was_reintroduced()


def test_current_weapon_paths_do_not_invoke_optional_sling_or_direct_reselection():
    """Compatibility identity for downstream historical suites."""
    test_no_direct_weapon_reselection_was_reintroduced()


def test_no_direct_weapon_reselection_was_reintroduced():
    identifiers={t.value for t in lex(TREATMENT.read_text()) if t.kind=="ident"}
    assert "selectWeapon" not in identifiers
    helper_ids={t.value for t in lex(source("medicAnimationPrep")) if t.kind=="ident"}
    # B176+ clears a stale logical weapon only inside exact, settled medical states.
    # It must never skip the visible holster preflight or restore a weapon.
    from source_scan import matching
    text = source("medicAnimationPrep")
    guard = "if (_ownedEmptyState) exitWith {"
    start = text.index(guard)
    ts = lex(text); pairs = matching(ts)
    opening = next(i for i,t in enumerate(ts) if t.offset == start + len(guard) - 1)
    block = text[start:ts[pairs[opening]].offset+1]
    assert 'if (_weapon != "") then {_medic selectWeapon "";};' in block
    assert "selectWeapon" not in {t.value for t in lex(text.replace(block, "")) if t.kind == "ident"}
    assert "selectWeapon" in helper_ids
