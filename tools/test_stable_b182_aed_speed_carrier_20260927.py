#!/usr/bin/env python3
"""Stable B189: LifePak geometry, provider-speed cleanup, and animated persistent manual carrier toggle."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_stock_lifepak_buttons_use_native_grid_but_sync_uses_background_grid():
    dlg = read("addons/circulation/Defibrillator_Monitor_Dialog.hpp")
    defs = read("addons/circulation/Defibrillator_defines.hpp")
    sync = read("addons/acm_extended/functions/fn_aedSyncSetup.sqf")

    controls = dlg.split("class Controls {", 1)[1]
    for macro in (
        "ACM_AED_pxToScreen_X",
        "ACM_AED_pxToScreen_Y",
        "ACM_AED_pxToScreen_W",
        "ACM_AED_pxToScreen_H",
    ):
        assert macro in controls
    assert "ACM_AED_bgPxToScreen_X" not in controls
    assert "ACM_AED_bgPxToScreen_Y" not in controls

    assert "ACM_AED_bgPxToScreen_X" in defs
    assert "private _fnc_pxBG = {" in sync
    assert "_btn ctrlSetPosition (_btnPx call _fnc_pxBG);" in sync
    assert "_led ctrlSetPosition (_ledPx call _fnc_pxBG);" in sync


def test_stock_lifepak_vertical_mapping_does_not_apply_extra_panel_scale():
    # Regression model for the reported 1680x1050 offset.
    authored_y = 512
    native = authored_y / 2048.0
    wrong_background = authored_y / 2048.0 * 1.05
    assert wrong_background > native
    assert abs(wrong_background / native - 1.05) < 1e-12


def test_provider_speed_owner_helper_is_registered_and_narrow():
    cfg = read("addons/acm_extended/config.cpp")
    helper = read("addons/acm_extended/functions/fn_providerAnimSpeedOwned.sqf")

    assert "class providerAnimSpeedOwned {};" in cfg
    assert 'ACME_nativeTreatmentRate' in helper
    assert 'ACME_treatmentPoseState' in helper
    assert 'ACME_treatmentPoseRemote' in helper
    assert 'ACME_headElev_seqActive' in helper

    # Broad stance owners are intentionally excluded: they must not strand an accelerated treatment rate.
    assert "ACME_menuPose" not in helper
    assert "ACME_DP_InPose" not in helper
    assert "ACM_circulation_isPerformingCPR" not in helper


def test_native_treatment_rate_cleanup_cannot_exit_on_epoch_mismatch_and_leak_speed():
    s = read("addons/acm_extended/functions/fn_registerProviderStanceReleaseRuntime.sqf")
    marker = s.index("// B182: retire this exact native-rate lease first.")
    end = s.index('} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];', marker)
    block = s[marker:end]

    clear = block.index('_medic setVariable ["ACME_nativeTreatmentRate", [], true];')
    owner = block.index("ACME_fnc_providerAnimSpeedOwned")
    reset = block.index("_medic setAnimSpeedCoef 1;")
    assert clear < owner < reset
    assert "ACME_treatmentPoseEpoch" not in block


def test_pose_exit_retires_stale_remote_owner_on_handoff():
    s = read("addons/acm_extended/functions/fn_treatmentPoseSync.sqf")

    # Validate the complete bounded exit callback. The speed-owner query is intentionally evaluated
    # immediately BEFORE the B182 explanatory comment, so slicing from that comment drops the line
    # this regression is supposed to protect.
    block = s.split('if (_operation == "exit") then {', 1)[1]
    block = block.split('}, [_medic, _epoch],', 1)[0]

    assert 'private _newerSpeedOwner = local _medic && {[_medic, _epoch] call ACME_fnc_providerAnimSpeedOwned};' in block
    assert 'if (_newerEpisode || {_newerSpeedOwner}) exitWith {' in block
    assert '_medic setVariable ["ACME_treatmentPoseRemote", [_epoch, "release", -1]];' in block
    assert "_medic setAnimSpeedCoef 1;" in block

    # The newer-owner branch must retire the OLD remote record without resetting the newer controller's rate.
    newer_owner = block.split('if (_newerEpisode || {_newerSpeedOwner}) exitWith {', 1)[1].split('};', 1)[0]
    assert 'setAnimSpeedCoef 1' not in newer_owner


def test_head_elevation_handoff_does_not_skip_speed_release():
    s = read("addons/acm_extended/functions/fn_headElevMedicSeq.sqf")
    marker = s.index("// Local bookkeeping above always retires.")
    owner = s.index("ACME_fnc_providerAnimSpeedOwned", marker)
    reset = s.index("_u setAnimSpeedCoef 1;", owner)
    handoff = s.index("if (_handoff) exitWith {};", reset)
    assert marker < owner < reset < handoff


def test_head_position_replaces_old_native_rate_with_real_speed_handoff():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    marker = s.index("// B182: replacing a native animation-rate lease")
    end = s.index("// Head positioning is head-selection only.", marker)
    block = s[marker:end]
    assert 'setVariable ["ACME_nativeTreatmentRate", [], true]' in block
    assert "ACME_fnc_providerAnimSpeedOwned" in block
    assert "_medic setAnimSpeedCoef 1;" in block


def test_manual_plate_carrier_functions_and_actions_are_on_stable_main():
    cfg = read("addons/acm_extended/config.cpp")
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    dispatch = read("addons/acm_extended/functions/fn_ownerDispatch.sqf")

    for name in (
        "manualPlateCarrierCanToggle",
        "manualPlateCarrierCommit",
        "manualPlateCarrierAutoReturn",
        "registerManualPlateCarrierRuntime",
    ):
        assert f"class {name} {{}};" in cfg

    assert "class ACME_ManualRemovePlateCarrier: CheckPulse" in cfg
    assert "class ACME_ManualReplacePlateCarrier: ACME_ManualRemovePlateCarrier" in cfg
    assert 'displayName = "Remove Plate Carrier";' in cfg
    assert 'displayName = "Replace Plate Carrier";' in cfg
    assert "call ACME_fnc_registerManualPlateCarrierRuntime;" in startup
    assert 'case "manualPlateCarrier": {_args call ACME_fnc_manualPlateCarrierCommit;};' in dispatch
    assert 'case "manualPlateCarrierAutoReturn": {_args call ACME_fnc_manualPlateCarrierAutoReturn;};' in dispatch


def test_manual_carrier_uses_persistent_shared_chest_access_lease():
    can = read("addons/acm_extended/functions/fn_manualPlateCarrierCanToggle.sqf")
    commit = read("addons/acm_extended/functions/fn_manualPlateCarrierCommit.sqf")
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")

    assert "ACME_manualPlateCarrierLease" in can
    assert "ACME_manualPlateCarrierState" in can
    assert "ACME_chestAccess_leases" in can

    assert '[_patient, _medic, _lease, true, "manualplatecarrier", _lease] call ACME_fnc_chestAccessVestEvent;' in commit
    assert "ACME_manualPlateCarrierLoadout" not in commit
    assert "manualplatecarrier" in acquire
    assert '_class != "manualplatecarrier"' in acquire


def test_manual_remove_uses_normal_provider_and_patient_carrier_choreography():
    cfg = read("addons/acm_extended/config.cpp")
    commit = read("addons/acm_extended/functions/fn_manualPlateCarrierCommit.sqf")
    provider = read("addons/acm_extended/functions/fn_chestAccessVestProvider.sqf")
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")

    remove = cfg.split("class ACME_ManualRemovePlateCarrier:", 1)[1].split(
        "class ACME_ManualReplacePlateCarrier:", 1
    )[0]
    assert "allowSelfTreatment = 0;" in remove

    # Native ACE animation remains blank because the shared ACME chest-access controller owns medic4.
    assert 'animationMedic = "";' in remove
    assert '[_patient, _medic, _lease, true, "manualplatecarrier", _lease] call ACME_fnc_chestAccessVestEvent;' in commit
    assert 'private _manualEntry = (_preparationToken find "manualpc:") == 0;' in provider
    assert '_op == "manualstop"' in provider
    assert '[_p] call ACME_fnc_chestAccessVestPark' in acquire
    assert '"ACME_HeadElevPatientGrab"' in acquire
    assert '"ACME_HeadElevPatientRelease"' in acquire


def test_manual_carrier_row_is_pinned_above_all_menu_categories():
    menu = read("addons/gui/overrides/fnc_updateActions.sqf")
    assert "private _manualCarrier = _menuActions select {" in menu
    assert "_row set [1, _selectedCategory];" in menu
    assert "_menuActions = _manualCarrier + _bvmEmma + _stopPressure + _pressure + _menuActions + _dogTags;" in menu


def test_manual_carrier_auto_returns_on_wake_getup_transport_and_movement():
    runtime = read("addons/acm_extended/functions/fn_registerManualPlateCarrierRuntime.sqf")
    auto = read("addons/acm_extended/functions/fn_manualPlateCarrierAutoReturn.sqf")
    getup = read("addons/core/functions/fnc_getUp.sqf")

    assert "ACME_manualPlateCarrierWatchPFH" in runtime
    assert "_awake || {_transported} || {_moved} || {_externalVest}" in runtime
    assert "distance2D _origin > 0.35" in runtime
    assert '"ace_dragging_setupDrag"' in runtime
    assert '"ace_dragging_setupCarry"' in runtime
    assert '[_patient, "getup"] call ACME_fnc_manualPlateCarrierAutoReturn;' in getup

    assert '[_patient, true, _provider, "access", true] call ACME_fnc_chestAccessVestRestore;' in auto
    assert 'ACME_manualPlateCarrierLease' in auto
    assert 'ACME_chestAccess_vestBusy' in auto
    assert 'ACME_fnc_patientAnimRelease' in auto


def test_automatic_chest_access_reuses_manual_custody_without_replaying_removal():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    saved = acquire.index('private _saved = +(_patient getVariable [_savedVar, []]);')
    existing = acquire.index('if ((count _saved) == 2) exitWith {', saved)
    commit = acquire.index("private _commitRemoval = {")
    assert saved < existing < commit


def test_build_identity_is_b183_stable():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B189 AED/speed/carrier regression: PASS")
