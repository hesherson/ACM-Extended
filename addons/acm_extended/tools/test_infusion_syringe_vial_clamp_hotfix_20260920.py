from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUN = ROOT / "functions"
CIRC = ROOT.parent / "circulation" / "functions"


def acme(name: str) -> str:
    return (FUN / name).read_text(encoding="utf-8")


def circ(name: str) -> str:
    return (CIRC / name).read_text(encoding="utf-8")


def test_native_drag_uses_vial_session_limit_in_same_frame():
    src = circ("fnc_Syringe_Draw.sqf")
    moving = src.split("if (GVAR(SyringeDraw_Moving)) then {", 1)[1]
    assert 'if !(isNil "ACME_fnc_vialSession")' in moving
    assert '["limit", _acmeMed, GVAR(SyringeDraw_DrawnAmount), _acmeDisplay] call ACME_fnc_vialSession' in moving
    assert '_effectiveMax = (_effectiveMax max 0) min _size;' in moving
    assert moving.index('ACME_fnc_vialSession') < moving.index('private _bottomLimit = linearConversion')
    assert '_amountDrawn = (_amountDrawn max 0) min _effectiveMax;' in moving
    assert 'GVAR(SyringeDraw_MaxDose) = _effectiveMax;' in moving


def test_acme_ui_no_longer_fights_live_drag_loop():
    src = acme("fn_skUiTick.sqf")
    clamp = src.split('// The native ACM drag loop now consumes this hard limit', 1)[1].split('// Inventory can change', 1)[0]
    assert 'ACME_fnc_syringeDrawSetAmount' in clamp
    assert 'setMousePosition' not in clamp
    assert 'SyringeDraw_Moving' not in clamp
    assert '_drawnNow > _hardMax' in clamp


def test_forced_amount_correction_keeps_numeric_hitbox_and_art_together():
    src = acme("fn_syringeDrawSetAmount.sqf")
    assert '"syringeDrawDrawnAmount", _amount' in src
    assert 'ACM_circulation_fnc_setLocalUiState' in src
    assert '_display displayCtrl 84009' in src
    assert 'ACM_circulation_SyringeDraw_Ctrl_PlungerVisual' in src
    assert '_y - _adjust' in src
    assert '"syringeDrawMoving", false' in src
    assert 'class syringeDrawSetAmount {};' in (ROOT / "config.cpp").read_text(encoding="utf-8")


def test_infusion_uses_native_single_med_mover_and_rechecks_real_stock():
    patch = acme("fn_patchDrawDialog.sqf")
    stock = acme("fn_infusionDrawStock.sqf")
    inject = acme("fn_injectIntoBag.sqf")
    assert 'call ACME_fnc_skCompoundBegin;' not in patch
    assert 'call ACM_circulation_fnc_Syringe_Draw_Move' in patch
    assert 'ACM_circulation_SyringeDraw_DrawnAmount' in stock
    assert 'ACM_circulation_SyringeDraw_Moving' in stock
    assert 'setMousePosition' not in stock
    assert 'ctrlSetPosition' not in stock
    assert 'if (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Moving", false]) exitWith {};' in inject
    assert 'ACME_fnc_infusionVialVolume' in inject
    assert '_sessionMax min _stockMax min _size' in inject
    assert 'ACME_fnc_infusionDrawResolve' in inject
    assert 'Vial contents changed. Check the dose and inject again.' in inject


def test_successful_bag_injection_resets_plunger_and_native_selection_atomically():
    src = acme("fn_injectIntoBag.sqf")
    assert '[0, _display, true] call ACME_fnc_syringeDrawSetAmount;' in src
    assert 'ACM_circulation_SyringeDraw_MaxDose = 0;' in src
    assert 'ACM_circulation_SyringeDraw_MedicationSelected_Index = -1;' in src
    assert 'ACM_circulation_SyringeDraw_Medication = "";' in src
    assert 'ACM_circulation_SyringeDraw_MedicationSelected = false;' in src


def test_infusion_stock_refresh_is_not_a_second_plunger_writer():
    src = acme("fn_infusionDrawStock.sqf")
    assert 'setMousePosition' not in src
    assert 'ctrlSetPosition' not in src
    assert 'SyringeDraw_DrawnAmount =' not in src
    assert 'SyringeDraw_MaxDose =' not in src


def test_infusion_identity_stays_locked_while_solution_is_in_syringe():
    select = acme("fn_skListSelect.sqf")
    medselect = acme("fn_skMedicationSelect.sqf")
    inject = acme("fn_injectIntoBag.sqf")
    assert 'ACM_circulation_SyringeDraw_DrawnAmount' in select
    assert '_data != _currentMed' in select
    assert '_med != _previousMed' in medselect
    assert '_oldIndex' in medselect
    assert 'Do not re-resolve the drug' in inject
    assert 'lbCurSel _medList' not in inject


def test_infusion_close_never_autosaves_transient_compound_syringe():
    close = acme("fn_skClose.sqf")
    assert 'private _infusion = !((_display getVariable ["ACME_SK_Return", []]) isEqualTo []);' in close
    assert '!_infusion' in close
    assert 'call ACME_fnc_skCompoundCommit;' in close


def test_one_ml_prep_uses_native_size_math_and_supports_regrab_return():
    native = circ("fnc_Syringe_Draw.sqf")
    patch = acme("fn_patchDrawDialog.sqf")
    stock = acme("fn_infusionDrawStock.sqf")
    assert 'private _bottomLimit = linearConversion [0, _size, _effectiveMax' in native
    assert 'private _amountDrawn = linearConversion [GVAR(SyringeDraw_Ctrl_LimitTop), GVAR(SyringeDraw_Ctrl_LimitBottom), _newY, 0, _size, true];' in native
    assert 'call ACM_circulation_fnc_Syringe_Draw_Move' in patch
    assert 'ACM_circulation_SyringeDraw_Moving' in stock
    assert '_drawn <= 0.0005' in stock


def test_one_visible_medication_click_cannot_unlock_two_vials():
    select = acme("fn_skListSelect.sqf")
    medselect = acme("fn_skMedicationSelect.sqf")
    assert 'if (_kind == "medication" && {_same}) then {' in select
    assert 'A changed medication selection fires LBSelChanged' in select
    assert '_previousMed != _med || {!_alreadyBound}' in medselect
    assert '["limit", _med, _reserved, _display] call ACME_fnc_vialSession' in medselect
