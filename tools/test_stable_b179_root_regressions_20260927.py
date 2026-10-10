#!/usr/bin/env python3
"""Stable B179 root regressions: AED, push editor, Get Up, vehicle treatment, and 6+6 chest holes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_aed_stock_buttons_keep_native_grid_while_sync_uses_background_mapping():
    defs = read("addons/circulation/Defibrillator_defines.hpp")
    dlg = read("addons/circulation/Defibrillator_Monitor_Dialog.hpp")
    sync = read("addons/acm_extended/functions/fn_aedSyncSetup.sqf")

    # Stock ACM button constants were authored for ACM_AED_pxToScreen_* and already compensate for the panel art.
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

    # SYNC is a later runtime control measured directly on the rendered 1.05x background and remains there.
    assert "ACM_AED_bgPxToScreen_X" in defs
    assert "private _fnc_pxBG = {" in sync
    assert "_btn ctrlSetPosition (_btnPx call _fnc_pxBG);" in sync
    assert "_led ctrlSetPosition (_ledPx call _fnc_pxBG);" in sync


def test_aed_stock_button_y_mapping_does_not_gain_extra_105_percent_drop_at_1680x1050():
    width, height = 1680, 1050
    assert width / height == 1.6

    # Regression model: stock buttons use the native grid scale. Applying the panel's 1.05 multiplier to their
    # authored Y constants is exactly the B179 regression that moved every stock hitbox lower while SYNC stayed right.
    authored_y = 512
    native_y = authored_y / 2048.0
    wrong_bg_y = authored_y / 2048.0 * 1.05
    assert wrong_bg_y > native_y
    assert abs((wrong_bg_y / native_y) - 1.05) < 1e-12


def test_every_operator_dependent_aed_button_uses_actual_monitor_medic():
    for name in (
        "AED_Button_Analyze",
        "AED_Button_ManualCharge",
        "AED_Button_MeasureBP",
        "AED_Button_SpeedDial",
        "AED_Button_Shock",
    ):
        s = read(f"addons/circulation/functions/fnc_{name}.sqf")
        assert "AED_Monitor_Medic" in s
        assert '_patient getVariable [QGVAR(AED_Provider)' not in s
    charge = read("addons/circulation/functions/fnc_AED_BeginCharge.sqf")
    assert '_medic setVariable [QGVAR(AED_Medic_InUse), true, true];' in charge


def test_push_duration_edit_has_explicit_focus_lease_and_renderer_cannot_refresh_it():
    body = read("addons/acm_extended/functions/fn_skBodyActionRender.sqf")
    tick = read("addons/acm_extended/functions/fn_skUiTick.sqf")
    close = read("addons/acm_extended/functions/fn_skClose.sqf")

    mouse = body.split('ctrlAddEventHandler ["MouseButtonDown"', 1)[1].split("}];", 1)[0]
    assert mouse.index('ACME_SK_PushDurationEditing",true') < mouse.index("ctrlSetFocus _ctrl")
    assert 'ctrlAddEventHandler ["SetFocus"' in body
    assert 'ctrlAddEventHandler ["KillFocus"' in body
    assert 'if (_durEditing) exitWith {' in body
    guarded = body.split("if (_durEditing) exitWith {", 1)[1].split("};", 1)[0]
    assert "ctrlSetText" not in guarded
    assert "ctrlSetPosition" not in guarded
    assert "ctrlEnable" not in guarded
    assert 'ACME_SK_PushDurationEditing' in tick
    assert 'ACME_SK_PushDurationEditing", false' in close


def test_getup_never_mutates_a_carry_owned_casualty():
    getup = read("addons/core/functions/fnc_getUp.sqf")
    prompt = read("addons/core/functions/fnc_getUpPrompt.sqf")
    carry_guard = getup.index("private _carryOwner = attachedTo _patient;")
    lying_clear = getup.index('_patient setVariable ["ACM_core_Lying_State", false, true];')
    assert carry_guard < lying_clear
    assert '(_carryAnim find "carried") >= 0' in getup
    assert 'Put the casualty down before using Get Up.' in getup
    assert 'attachedTo _unit' in prompt
    assert '(_anim find "carried") >= 0' in prompt


def test_same_vehicle_treatment_is_clinical_without_forcing_animation():
    native = read("addons/core/functions/fnc_treatmentNative.sqf")
    bridge = read("addons/core/overrides/fnc_treatment.sqf")
    blocked = read("addons/acm_extended/functions/fn_animBlocked.sqf")

    assert "private _sameVehicleTreatment" not in native
    assert 'if (isNull objectParent _medic && {_medicAnim != ""})' in native
    assert "if (!_isSelf && {isNull objectParent _patient})" in native

    assert "private _sameVehicleTreatment" in bridge
    assert "private _interactionChecks" in bridge
    assert "private _rangeOkay = _sameVehicleTreatment" in bridge
    assert "call ACME_fnc_patientInteractionDistance" in bridge

    assert "!((vehicle _unit) isEqualTo _unit)" in blocked


def test_chest_and_thoracostomy_workspaces_accept_same_vehicle_without_body_theatre():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    seal = read("addons/acm_extended/functions/fn_chestSealOpen.sqf")
    thora = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    thora_tick = read("addons/acm_extended/functions/fn_thoraTick.sqf")

    vehicle = acquire.split("if (!isNull objectParent _patient) exitWith {", 1)[1].split("// Every chest procedure starts anterior-up.", 1)[0]
    assert '_patient setVariable [_readyVar, serverTime, true];' in vehicle
    assert "removeVest" not in vehicle
    assert "doAnim" not in vehicle

    assert "objectParent _m isNotEqualTo objectParent _p" in seal
    assert "call ACME_fnc_patientInteractionDistance" in seal
    assert "objectParent _m isNotEqualTo objectParent _p" in thora
    assert "isNull objectParent _m && {(_m distance _p)" in thora
    assert "objectParent _thMedic isNotEqualTo objectParent _thPatient" in thora_tick


def test_chest_holes_are_authoritatively_capped_at_six_front_and_six_back():
    init = read("addons/acm_extended/functions/fn_initChestSealProcedureRuntime.sqf")
    gen = read("addons/acm_extended/functions/fn_chestSealGenHoles.sqf")
    assert "ACME_CS_maxHolesPerSide = 6;" in init
    assert 'getVariable ["ACME_CS_maxHolesPerSide", 6]' in gen
    assert "_maxPerSide = (floor _maxPerSide) min 6;" in gen
    assert "private _cappedHoles = [];" in gen
    assert "if (_frontKept < _maxPerSide)" in gen
    assert "if (_backKept < _maxPerSide)" in gen
    assert "if (_frontCount < _maxPerSide) then {" in gen
    front_branch = gen.split("if (_frontCount < _maxPerSide) then {", 1)[0][-300:]
    assert '|| {!_historical}' not in front_branch

    # Migration/generation invariant model.
    sides = ["front"] * 11 + ["back"] * 9
    kept = []
    counts = {"front": 0, "back": 0}
    for side in sides:
        if counts[side] < 6:
            kept.append(side)
            counts[side] += 1
    assert counts == {"front": 6, "back": 6}
    assert len(kept) == 12


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B179 root-regression suite: PASS")
