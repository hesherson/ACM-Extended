"""B264: plate-carrier owner completion and modded-loadout preservation."""
from pathlib import Path
from test_menu_death_lifecycle import execute, adapt

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / "addons/acm_extended/functions"

def source(name):
    return (F / ("fn_" + name + ".sqf")).read_text(encoding="utf-8-sig")

def test_manual_success_worker_is_idempotent_and_rejects_late_lease():
    s=source("manualPlateCarrierCompleteRemoval")
    # Preserve source decision and state transition; replace only Arma engine
    # object/gear/time boundaries not supported by SQF-VM.
    s=s.replace("vest _p", "_wornVest").replace("backpack _p", "_backpack")
    s=s.replace("serverTime", "_clock")
    execute(r"""
        private _p=profileNamespace;
        private _medic=uiNamespace;
        private _wornVest="";
        private _backpack="B_AssaultPack";
        private _clock=100;
        private _logs=0;
        ace_medical_treatment_fnc_addToLog={_logs=_logs+1;};
        _p setVariable ["ACME_manualPlateCarrierState","removing"];
        _p setVariable ["ACME_manualPlateCarrierLease","manualpc:A"];
        _p setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[]]];
        _p setVariable ["ACME_chestAccess_readyServer",99];
        _p setVariable ["ACME_chestAccess_vestBusy",""];
        _p setVariable ["ACME_headElevated",false];
    """+"ACME_fnc_manualPlateCarrierCompleteRemoval={"+adapt(s)+"};"+r"""
        [[_p,_medic,"manualpc:A"] call ACME_fnc_manualPlateCarrierCompleteRemoval,
            "ready carrier removal never committed"] call _check;
        [(_p getVariable ["ACME_manualPlateCarrierState",""]) == "off"
            && {_logs == 1}, "completion failed to publish one exact successful remove"] call _check;
        [!([_p,_medic,"manualpc:A"] call ACME_fnc_manualPlateCarrierCompleteRemoval)
            && {_logs == 1}, "duplicate completion produced another log"] call _check;
        _p setVariable ["ACME_manualPlateCarrierState","removing"];
        _p setVariable ["ACME_manualPlateCarrierLease","manualpc:B"];
        [!([_p,_medic,"manualpc:A"] call ACME_fnc_manualPlateCarrierCompleteRemoval),
            "stale owner completion mutated a replacement lease"] call _check;
        _p setVariable ["ACME_chestAccess_readyServer",-1];
        [!([_p,_medic,"manualpc:B"] call ACME_fnc_manualPlateCarrierCompleteRemoval),
            "unacknowledged patient animation produced false success"] call _check;
    """)

def test_manual_remove_cannot_expire_provider_wait_or_fake_a_return():
    acquire=source("chestAccessVestAcquire")
    commit=source("manualPlateCarrierCommit")
    auto=source("manualPlateCarrierAutoReturn")
    abort=source("manualPlateCarrierAbortRemoval")
    runtime=source("registerManualPlateCarrierRuntime")
    assert 'if (_treatmentClass == "manualplatecarrier") exitWith {' in acquire
    block=acquire.split('if (_treatmentClass == "manualplatecarrier") exitWith {',1)[1].split('// Stable thoracostomy deliberately',1)[0]
    assert "_patientArgs call _beginPatient;" in block
    assert "_startProvider" not in block
    assert "20, {" in commit and 'call ACME_fnc_manualPlateCarrierAbortRemoval;' in commit
    assert '[_p, _medic, _lease] call ACME_fnc_manualPlateCarrierCompleteRemoval;' in commit
    assert '_reason != "remove-timeout"' in auto
    assert 'if (_restored && {_hadCustody} && {(vest _patient) != ""}) then {' in auto
    assert 'if (_hadCustody && {!_restored}) exitWith {' in auto
    assert 'if ((_p getVariable ["ACME_manualPlateCarrierLease", ""]) != _lease' in abort
    assert 'call ACME_fnc_manualPlateCarrierCompleteRemoval' in runtime
    assert 'serverTime - _started >= 20' in runtime

def test_modded_hidden_selection_not_rebuilt_by_hangbag_or_legacy_vest():
    prep=source("hangBagPrep")
    restore=source("hangBagRestoreWeapons")
    carrier=source("carrierInventoryRestore")
    assert "_medic setUnitLoadout" not in prep and "_medic setUnitLoadout" not in restore
    assert "removeWeapon (primaryWeapon _medic)" in prep
    assert "removeWeapon (secondaryWeapon _medic)" in prep
    assert "addWeapon _weapon;" in restore
    assert "addWeaponItem [_weapon" in restore
    assert "getUnitLoadout _medic" in restore
    assert "_allRestored" in restore and "ACME_hang_savedWeaponSlots" in restore
    assert "setUnitLoadout _ld" not in restore
    assert "_patient setUnitLoadout" not in carrier
    assert "_patient addVest _class;" in carrier
    assert "addMagazineAmmoCargo" in carrier and "addItemCargoGlobal" in carrier

def test_owner_dispatch_and_registration_for_manual_abort():
    cfg=(ROOT/"addons/acm_extended/config.cpp").read_text()
    dispatch=source("ownerDispatch")
    for name in ("manualPlateCarrierCompleteRemoval","manualPlateCarrierAbortRemoval"):
        assert f"class {name} {{}};" in cfg
    assert 'case "manualPlateCarrierAbortRemoval": {_args call ACME_fnc_manualPlateCarrierAbortRemoval;};' in dispatch
    assert 'case "manualPlateCarrier": {_args call ACME_fnc_manualPlateCarrierCommit;};' in dispatch
