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
    assert 'ACME_buildBatch = "B144";' in startup
    assert 'ACME_debugRevision = "rc1";' in startup
    script = raw(ADDONS / "main" / "script_version.hpp")
    assert "#define MAJOR 1" in script
    assert "#define MINOR 2" in script
    assert "#define PATCH 3" in script
    assert "#define BUILD 0" in script


def test_bvm_variants_share_the_exact_chest_access_preflight():
    runtime = acme("functions/fn_registerChestAccessVestRuntime.sqf")
    for cls in ("cpr", "usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"):
        assert f'"{cls}"' in runtime
    assert 'ACME_chestAccess_maneuverClasses' in runtime
    # The generic treatment bridge already performs chest-access preparation before its native CPR/BVM fast paths.
    treatment = raw(ADDONS / "core" / "overrides" / "fnc_treatment.sqf")
    assert 'private _needsChestAccess = _nativeContinuousClass in _chestClasses;' in treatment
    assert 'call ACME_fnc_chestAccessVestEvent;' in treatment
    assert 'if (_nativeContinuousClass in ["usebvm"' in treatment
    assert 'if (_nativeContinuousClass == "cpr") exitWith {' in treatment


def test_chest_access_lease_survives_until_both_cpr_and_bvm_are_finished():
    runtime = acme("functions/fn_registerChestAccessVestRuntime.sqf")
    assert 'ACM_core_fnc_cprActive' in runtime
    assert 'ACM_core_fnc_bvmActive' in runtime
    assert 'ACME_chestAccessManeuverHandoff' in runtime
    assert '!_maneuverActive && {!_handoffActive}' in runtime
    assert '[_p, _m, _id, false, _stored] call ACME_fnc_chestAccessVestEvent;' in runtime


def test_middle_mouse_swaps_publish_and_consume_one_bounded_handoff():
    cpr = raw(ADDONS / "circulation" / "functions" / "fnc_beginCPR.sqf")
    bvm = raw(ADDONS / "breathing" / "functions" / "fnc_useBVM.sqf")

    for source in (cpr, bvm):
        assert 'ACME_chestAccessManeuverHandoff' in source
        assert 'CBA_missionTime + 0.75' in source
        assert 'setVariable ["ACME_chestAccessManeuverHandoff", [], false]' in source

    # CPR marks the handoff before its cleanup can make cprActive false.
    assert cpr.index('CBA_missionTime + 0.75') < cpr.index('call FUNC(cprCleanupLocal)')
    # BVM marks the handoff before its cleanup and consumes it only after On Start owns a real session.
    cancel = bvm.index('private _swapToCPR')
    assert bvm.index('CBA_missionTime + 0.75', cancel) < bvm.index('call FUNC(bvmCleanupLocal)', cancel)


def test_patient_owner_never_restores_carrier_under_active_cpr_or_bvm():
    restore = acme("functions/fn_chestAccessVestRestore.sqf")
    assert 'private _maneuverBusy = ([_patient] call ACM_core_fnc_cprActive)' in restore
    assert '|| {[_patient] call ACM_core_fnc_bvmActive};' in restore
    assert '!([_p] call ACM_core_fnc_cprActive)' in restore
    assert '!([_p] call ACM_core_fnc_bvmActive)' in restore


def test_carrier_off_choreography_finishes_before_the_medic4_freeze():
    cfg = acme("functions/fn_initPatientPositioningConfig.sqf")
    acquire = acme("functions/fn_chestAccessVestAcquire.sqf")
    pose = acme("functions/fn_initChestSealProcedureRuntime.sqf")

    assert 'ACME_chestAccess_vestLiftTime = 0.70;' in cfg
    assert 'ACME_chestAccess_vestLowerTime = 0.78;' in cfg
    assert 'ACME_chestAccess_vestLiftHold = 0.04;' in cfg
    assert 'missionNamespace getVariable ["ACME_chestAccess_vestLiftTime", 0.70]' in acquire
    assert 'missionNamespace getVariable ["ACME_chestAccess_vestLowerTime", 0.78]' in acquire
    assert 'missionNamespace getVariable ["ACME_chestAccess_vestLiftHold", 0.04]' in acquire
    assert 'private _sequenceTime = _liftTime + _holdTime + _lowerTime;' in acquire
    assert '_lowerTime + 0.08' not in acquire
    assert '_sequenceTime = _liftTime + _holdTime + _lowerTime + 0.08' not in acquire
    assert '["chestAccess", 2.2]' in pose
    assert (0.70 + 0.04 + 0.78) < 2.2
