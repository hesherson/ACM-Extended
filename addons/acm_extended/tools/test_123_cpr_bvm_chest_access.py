from pathlib import Path
from historical_source import read_source, assert_release_identity

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent


def acme(rel: str) -> str:
    return read_source(ROOT / rel, encoding="utf-8-sig", errors="strict")


def raw(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")


def test_123_release_identity_and_hemtt_version():
    assert_release_identity()
    assert 'version = "1.2.3";' in acme("config.cpp")
    startup = acme("functions/fn_initForkStartupRuntime.sqf")
    assert 'ACME_infusion_version = "1.2.3";' in startup
    assert 'ACME_buildBatch = "B147";' in startup
    assert 'ACME_debugRevision = "rc4";' in startup
    script = raw(ADDONS / "main" / "script_version.hpp")
    for line in ("#define MAJOR 1", "#define MINOR 2", "#define PATCH 3", "#define BUILD 0"):
        assert line in script


def test_preparing_banner_is_real_top_screen_control_and_registered():
    cfg = acme("config.cpp")
    ui = acme("functions/fn_chestAccessPreparing.sqf")
    assert "class chestAccessPreparing {};" in cfg
    assert 'findDisplay 46' in ui
    assert 'ctrlCreate ["RscStructuredText", -1]' in ui
    assert "Preparing..." in ui
    assert "safeZoneY + safeZoneH * 0.025" in ui
    assert 'ACME_ChestAccessPreparing' in ui


def test_long_chest_prep_is_one_click_closes_menu_and_is_cancellable():
    treatment = raw(ADDONS / "core" / "overrides" / "fnc_treatment.sqf")
    gui = raw(ADDONS / "gui" / "overrides" / "fnc_updateActions.sqf")
    assert 'ACME_chestAccessPreflightActive' in treatment
    assert 'if (dialog) then {closeDialog 0;};' in treatment
    assert '[true, _medic, _patient, _token] call ACME_fnc_chestAccessPreparing;' in treatment
    assert 'ACME_chestAccessPreflightCancel' in treatment
    assert '[0x01, [false,false,false], _cancelCode' in treatment
    assert '[0xF0, [false,false,false], _cancelCode' in treatment
    assert '["ACM_core_openMedicalMenu", _p] call CBA_fnc_localEvent;' in treatment
    assert 'if !(ACE_player getVariable ["ACME_chestAccessPreflightActive", false]) then {' in gui


def test_provider_pose_is_retired_locally_before_native_intervention_launch():
    treatment = raw(ADDONS / "core" / "overrides" / "fnc_treatment.sqf")
    acquire = acme("functions/fn_chestAccessVestAcquire.sqf")
    handoff = '[_m, _p, "stop", true, _tok] call ACME_fnc_chestAccessVestProvider;'
    launch = 'private _started = _args call ACM_core_fnc_treatmentNative;'
    assert handoff in treatment and launch in treatment
    assert treatment.index(handoff) < treatment.index(launch)
    # The casualty owner must never send a late provider-stop packet after publishing readiness.
    assert '"chestAccessVestProvider", [_medic, _p, "stop"' not in acquire


def test_bvm_variants_and_cpr_share_one_stable_maneuver_lease():
    runtime = acme("functions/fn_registerChestAccessVestRuntime.sqf")
    for cls in ("cpr", "usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"):
        assert f'"{cls}"' in runtime
    assert 'ACME_chestAccess_maneuverClasses' in runtime
    assert '_samePatient && {_existingId != ""} && {_existingClass in _maneuvers} && {_class in _maneuvers}' in runtime
    assert '[_patient, _class, _existingId]' in runtime
    assert 'ACME_chestAccessManeuverWatch' in runtime
    assert '!_maneuverActive && {!_handoffActive} && {!_ownerHandoffActive} && {!_preparing}' in runtime


def test_middle_mouse_swaps_publish_provider_and_owner_handoff_before_cleanup():
    cpr = raw(ADDONS / "circulation" / "functions" / "fnc_beginCPR.sqf")
    bvm = raw(ADDONS / "breathing" / "functions" / "fnc_useBVM.sqf")

    for source in (cpr, bvm):
        assert 'ACME_chestAccessManeuverHandoff' in source
        assert 'CBA_missionTime + 1.00' in source
        assert '"chestAccessManeuverHandoff", [1.00]' in source

    cpr_swap = cpr.index('private _swapToBVM = GVAR(SwapToBVM);')
    assert cpr.index('"chestAccessManeuverHandoff", [1.00]', cpr_swap) < cpr.index('call FUNC(cprCleanupLocal)', cpr_swap)

    bvm_swap = bvm.index('private _swapToCPR')
    assert bvm.index('"chestAccessManeuverHandoff", [1.00]', bvm_swap) < bvm.index('call FUNC(bvmCleanupLocal)', bvm_swap)


def test_patient_owner_blocks_restore_during_roles_and_transfer_window():
    owner = acme("functions/fn_ownerDispatch.sqf")
    restore = acme("functions/fn_chestAccessVestRestore.sqf")
    assert 'case "chestAccessManeuverHandoff"' in owner
    assert 'ACME_chestAccess_maneuverHandoffUntil' in owner
    assert 'private _maneuverBusy = ([_patient] call ACM_core_fnc_cprActive)' in restore
    assert '|| {[_patient] call ACM_core_fnc_bvmActive};' in restore
    assert 'private _handoffBusy' in restore
    assert 'serverTime < _handoffUntil' in restore


def test_direct_pressure_yields_before_pose_for_native_cpr_bvm_and_chest_prep():
    start = acme("functions/fn_directPressureStart.sqf")
    stop = acme("functions/fn_directPressureStop.sqf")
    tick = acme("functions/fn_directPressureTick.sqf")
    pose = acme("functions/fn_directPressurePose.sqf")
    stance = acme("functions/fn_registerProviderStanceReleaseRuntime.sqf")
    for source in (start, stop):
        assert 'ACM_circulation_isPerformingCPR' in source
        assert 'ACM_breathing_isUsingBVM' in source
        assert 'ACM_core_fnc_cprActive' in source
        assert 'ACM_core_fnc_bvmActive' in source
    assert 'private _nativeCpr = [_patient] call ACM_core_fnc_cprActive;' in tick
    assert 'private _nativeBvm = [_patient] call ACM_core_fnc_bvmActive;' in tick
    assert 'ACME_chestAccessPreflightActive' in tick
    assert tick.index('if (_mustYieldClinical) exitWith {') < tick.index('call ACME_fnc_directPressurePose')
    assert '[_patient] call ACM_core_fnc_cprActive' in pose
    assert '[_patient] call ACM_core_fnc_bvmActive' in pose
    assert '[_patient] call ACM_core_fnc_cprActive' in stance
    assert '[_patient] call ACM_core_fnc_bvmActive' in stance


def test_cpr_and_bvm_yield_direct_pressure_instead_of_destroying_episode():
    cpr = raw(ADDONS / "circulation" / "functions" / "fnc_beginCPR.sqf")
    bvm = raw(ADDONS / "breathing" / "functions" / "fnc_useBVM.sqf")
    treatment = raw(ADDONS / "core" / "overrides" / "fnc_treatment.sqf")
    tick = acme("functions/fn_directPressureTick.sqf")

    assert 'call ACME_fnc_directPressureStop' not in bvm
    for source, cls in ((cpr, "cpr"), (bvm, "usebvm")):
        assert '_medic setVariable ["ACME_DP_Paused", true, false];' in source
        assert f'_medic setVariable ["ACME_DP_PauseTreatmentClass", "{cls}", false];' in source
        assert '_medic setVariable ["ACME_DP_InPose", false, false];' in source

    branch = 'if (_nativeContinuousClass in ["usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"]) exitWith {'
    branch_pos = treatment.index(branch)
    native_pos = treatment.index('private _startedContinuous = _this call ACM_core_fnc_treatmentNative;', branch_pos)
    pause_pos = treatment.index('call _fnc_dpPauseForManeuver;', branch_pos)
    assert pause_pos < native_pos

    assert 'ACME_chestAccessManeuverHandoff' in tick
    assert 'ACME_chestAccess_maneuverHandoffUntil' in tick
    assert '_providerHandoffActive' in tick
    assert '_ownerHandoffActive' in tick


def test_semifowler_is_lower_priority_and_never_resumes_under_cpr_bvm():
    suspend = acme("functions/fn_headElevSuspend.sqf")
    resume = acme("functions/fn_headElevTryResume.sqf")
    assert 'private _interventionOwnsPatient' in suspend
    assert '_lockPriority >= 2' in suspend
    assert '"head-elev-lower", objNull, _lowerTime + 0.3, 1' in suspend
    assert '"head-elev-flat", objNull, 0.8, 1' in suspend
    assert 'if (isNull objectParent _patient && {!_interventionOwnsPatient}) then {' in suspend
    assert '[_patient] call ACM_core_fnc_cprActive' in resume
    assert '[_patient] call ACM_core_fnc_bvmActive' in resume
    assert 'ACME_chestAccess_maneuverHandoffUntil' in resume


def test_cancelled_prep_invalidates_patient_callbacks_and_can_resume_semifowler():
    event = acme("functions/fn_chestAccessVestEvent.sqf")
    assert '(_busy find "vest:access:") == 0' in event
    assert '_patient setVariable ["ACME_chestAccess_vestBusy", "", false];' in event
    assert 'ACME_headElev_ResumePending' in event
    assert 'ACME_fnc_headElevTryResume' in event


def test_new_intervention_queues_behind_inflight_carrier_return():
    event = acme("functions/fn_chestAccessVestEvent.sqf")
    assert '(_busyBefore find "restore:access:") == 0' in event
    assert 'ACME_chestAccess_leases' in event
    assert 'call ACME_fnc_chestAccessVestAcquire' in event
    assert 'CBA_fnc_waitUntilAndExecute' in event


def test_carrier_off_choreography_finishes_before_medic4_freeze():
    cfg = acme("functions/fn_initPatientPositioningConfig.sqf")
    acquire = acme("functions/fn_chestAccessVestAcquire.sqf")
    pose = acme("functions/fn_initChestSealProcedureRuntime.sqf")
    for token in (
        'ACME_chestAccess_vestLiftTime = 0.70;',
        'ACME_chestAccess_vestLowerTime = 0.78;',
        'ACME_chestAccess_vestLiftHold = 0.04;',
        'ACME_chestAccess_vestRemoveAnimSpeed = 1.80;',
        'ACME_chestAccess_providerAnimSpeed = 1.50;',
    ):
        assert token in cfg
    assert 'ACME_chestAccess_removeSpeedToken' in acquire
    assert '["ace_common_setAnimSpeedCoef", [_p, _removeAnimSpeed]] call CBA_fnc_globalEvent;' in acquire
    assert 'private _sequenceTime = _liftTime + _holdTime + _lowerTime;' in acquire
    assert '["chestAccess", 2.2]' in pose
    assert (0.70 + 0.04 + 0.78) < 2.2


def test_carrier_return_uses_faster_patient_animation_and_guaranteed_reset():
    cfg = acme("functions/fn_initPatientPositioningConfig.sqf")
    restore = acme("functions/fn_chestAccessVestRestore.sqf")
    for token in (
        'ACME_chestAccess_vestRestoreLiftTime = 0.75;',
        'ACME_chestAccess_vestRestoreLowerTime = 0.88;',
        'ACME_chestAccess_vestRestoreHold = 0.02;',
        'ACME_chestAccess_vestRestoreAnimSpeed = 1.60;',
    ):
        assert token in cfg
    assert '["ace_common_setAnimSpeedCoef", [_p, _animSpeed]] call CBA_fnc_globalEvent;' in restore
    assert 'ACME_chestAccess_restoreSpeedToken' in restore
    assert '["ace_common_setAnimSpeedCoef", [_p, 1]] call CBA_fnc_globalEvent;' in restore
    assert 'private _total = _liftTime + _holdTime + _lowerTime;' in restore
    assert (0.75 + 0.02 + 0.88) < (1.20 + 0.18 + 1.40 + 0.08)
