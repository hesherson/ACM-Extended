"""Execute Hang Bag production decisions with explicit native inventory adapters.

The adapter models documented addWeapon autoload from carried compatible spares,
LinkedItems, exact class/round cargo mutation (including duplicates/zero rounds),
and native refusals. It does not emulate engine replication, magazine object IDs,
third-party meshes, or physical cargo capacity. Those remain in-engine checks.
B269_HANG_SOURCE_DIR pins Hang Bag and its kit-retirement source to B268.
"""
import os
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, ROOT

F = ROOT / "addons/acm_extended/functions"


def source(name):
    baseline = os.environ.get("B269_HANG_SOURCE_DIR")
    filename = f"fnc_{name}.sqf" if name == "equipmentKitChanged" else f"fn_{name}.sqf"
    directory = ROOT / "addons/core/functions" if name == "equipmentKitChanged" else F
    path = Path(baseline) / filename if baseline else directory / filename
    return path.read_text(encoding="utf-8-sig")


def code(name="hangBagRestoreWeapons"):
    s = source(name).replace("netId _medic", '"medic"')
    # Model only the scheduler boundary. The production wrapper/isNil call,
    # recursive arguments, and returned Boolean execute unchanged.
    s = s.replace("canSuspend", "_scheduled")
    s = s.replace("isNil {_result =", "isNil {_scheduled=false; _result =")
    # Arma object nil writes remove the key. SQF-VM namespace objects retain a
    # nil tombstone instead, so adapt only those native default-read boundaries.
    for key, fallback in (("savedWeaponSlots", "[]"), ("weaponRestoreOwned", "[[], []]"),
                          ("weaponRestoreCargo", "[[], []]"), ("weaponRestoreCargoAnomaly", "false")):
        native = f'_medic getVariable ["ACME_hang_{key}", {fallback}]'
        s = s.replace(native, f'([_medic, "ACME_hang_{key}", {fallback}] call _objectRead)')
    s = s.replace("getUnitLoadout _medic", "(+_loadout)")
    s = s.replace("local _medic", "_ownerLocal")
    s = s.replace("primaryWeapon _medic", '((_loadout select 0) param [0, ""])')
    s = s.replace("secondaryWeapon _medic", '((_loadout select 1) param [0, ""])')
    s = s.replace("compatibleMagazines _weapon", "([_weapon] call _nativeCompatible)")
    for index, native in enumerate(("uniformContainer", "vestContainer", "backpackContainer")):
        s = s.replace(f"{native} _medic", f"(_containers select {index})")
    s = s.replace("isNull _container", "(_container isEqualTo objNull || {_container in _deletedContainers})")
    s = s.replace("magazinesAmmoCargo _container", '(_container getVariable ["testMagCargo", []])')
    s = re.sub(r"_container addMagazineAmmoCargo (\[[^;]+\]);", r"[_container, \1] call _cargoNative;", s)
    s = s.replace("_medic addWeapon _weapon;", "[_weapon] call _addWeapon;")
    s = re.sub(r"_medic addWeaponItem (\[[^;]+\]);", r"\1 call _addWeaponItem;", s)
    s = s.replace("removeAllPrimaryWeaponItems _medic;", "[0] call _removeDefaultItems;")
    s = s.replace("removeAllSecondaryWeaponItems _medic;", "[1] call _removeDefaultItems;")
    s = re.sub(r"_medic removeWeapon ([^;]+);", r"[\1] call _removeWeapon;", s)
    s = s.replace('getArray (configFile >> "CfgWeapons" >> _weapon >> "muzzles")', "(+_muzzles)")
    s = re.sub(r"_medic setUnitPos ([^;]+);", r"_testStance=\1;", s)
    s = s.replace("objectParent _medic", "objNull")
    s = s.replace("values _ivBags", "(keys _ivBags apply {_ivBags get _x})")
    return f"ACME_fnc_{name}={{" + adapt(s) + "};"


FIXTURE = r'''
    private _loadout=[[],[],["Handgun","","","",["Mag_A",5],[],""],
        ["U_Custom",[["seal",2]]],["V_Custom",[["medicalTool",1]]],
        ["B_Custom",[["otherWeapon",1]]],"H_Custom","G_Custom",[],["Map","GPS"]];
    private _rifle=["Rifle","suppressor","laser","scope",["Mag_A",7],["Grenade",1],"bipod"];
    private _launcher=["Launcher","","","sight",["Rocket",1],[],""];
    private _containers=[uiNamespace,profileNamespace,missionNamespace];
    private _objectRead={params ["_unit","_key","_fallback"]; if (isNil {_unit getVariable _key}) then {_fallback} else {_unit getVariable _key};};
    private _deletedContainers=[];
    { _x setVariable ["testMagCargo",[]]; } forEach _containers;
    private _muzzles=["this","GL"];
    private _nativeAutoload=true;
    private _ownerLocal=true;
    private _scheduled=false;
    private _defaultItems=["","","",""];
    private _denied=[]; private _denyAdd=false; private _denyDefaultClear=false;
    private _denyRemove=[]; private _denyReturnContainers=[];
    private _returnMultiplicity=1;
    private _adds=0; private _autoloads=0; private _cargoWrites=0; private _removedWeapons=[];
    private _nativeCompatible={params ["_w"]; if (_w=="Launcher") then {["Rocket"]} else {["Mag_A","Mag_B","Grenade"]};};
    private _weaponIndex={params ["_w"]; [0,1] select (_w=="Launcher");};
    private _cargoNative={
        params ["_c","_args"]; _args params ["_class","_quantity","_ammo"];
        [!_scheduled,"cargo mutation ran in scheduled transaction"] call _check;
        _cargoWrites=_cargoWrites+1;
        private _mags=+(_c getVariable ["testMagCargo",[]]);
        if (_quantity<0) then {
            if ([_class,_ammo] in _denyRemove) exitWith {};
            private _index=_mags findIf {_x isEqualTo [_class,_ammo]};
            if (_index>=0) then {_mags deleteAt _index;};
        } else {
            if (_c in _denyReturnContainers) exitWith {};
            for "_copy" from 1 to _returnMultiplicity do {_mags pushBack [_class,_ammo];};
        };
        _c setVariable ["testMagCargo",_mags];
    };
    private _addWeapon={
        params ["_w"]; _adds=_adds+1;
        [!_scheduled,"weapon mutation ran in scheduled transaction"] call _check;
        if (_denyAdd) exitWith {};
        private _i=[_w] call _weaponIndex;
        private _slot=[_w,_defaultItems select 0,_defaultItems select 1,_defaultItems select 2,[],[],_defaultItems select 3];
        if (_nativeAutoload) then {
            private _classes=[_w] call _nativeCompatible;
            // The native may choose any compatible spare. This deterministic
            // ordering includes a wrong class/ammo and GL spare when present.
            {
                private _magSlot=_x;
                {
                    private _c=_x;
                    private _mags=+(_c getVariable ["testMagCargo",[]]);
                    private _j=_mags findIf {(_x select 0) in _classes && {
                        if (_magSlot==5) then {(_x select 0)=="Grenade"} else {(_x select 0)!="Grenade"}
                    }};
                    if (_j>=0 && {(_slot select _magSlot) isEqualTo []}) then {
                        _slot set [_magSlot,+(_mags select _j)]; _mags deleteAt _j;
                        _c setVariable ["testMagCargo",_mags]; _autoloads=_autoloads+1;
                    };
                } forEach _containers;
            } forEach ([ [4,5], [4] ] select (_w=="Launcher"));
        };
        _loadout set [_i,_slot];
    };
    private _removeDefaultItems={
        params ["_i"]; if (_denyDefaultClear) exitWith {};
        private _slot=+(_loadout select _i); {_slot set [_x,""];} forEach [1,2,3,6];
        _loadout set [_i,_slot];
    };
    private _addWeaponItem={
        params ["_w","_part"]; private _i=[_w] call _weaponIndex;
        [!_scheduled,"loaded magazine mutation ran in scheduled transaction"] call _check;
        private _slot=+(_loadout select _i);
        if (_part isEqualType []) then {
            if ((_part select 0) in _denied) exitWith {};
            private _muzzle=_part param [2,_muzzles select 0];
            _slot set [[4,5] select (_muzzle==(_muzzles param [1,""])),_part select [0,2]];
        } else {
            if (_part in _denied) exitWith {};
            private _j=switch (_part) do {case "suppressor":{1};case "laser":{2};case "bipod":{6};default{3};};
            _slot set [_j,_part];
        };
        _loadout set [_i,_slot];
    };
    private _removeWeapon={params ["_w"]; _removedWeapons pushBack _w; _loadout set [[_w] call _weaponIndex,[]];};
    private _cargoState={_containers apply {private _records=(_x getVariable ["testMagCargo",[]]) apply {str _x}; _records sort true; _records;};};
    private _messages=[];
    ace_common_fnc_displayTextStructured={_messages pushBack _this;};
    ACME_fnc_providerAnimation={_this select 1}; ACME_fnc_medicAnimationPrep={0}; ACME_fnc_doAnimHeld={};
    _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,[]]];
    _medic setVariable ["ACME_hang_weaponRestoreOwned",[[],[]]];
    _medic setVariable ["ACME_hang_weaponRestoreCargo",[[],[]]];
    _medic setVariable ["ACM_circulation_bloodVolume",4.2];
    _medic setVariable ["ace_medical_openWounds",[["body",0.4]]];
    private _handgunBefore=str (_loadout select 2);
    private _equipmentBefore=str (_loadout select [3,7]);
    private _checkUnrelated={
        [str (_loadout select 2)==_handgunBefore,"shared-class loaded handgun changed"] call _check;
        [str (_loadout select [3,7])==_equipmentBefore,"unrelated kit/items/mesh selections rewritten"] call _check;
        [(_medic getVariable ["ACM_circulation_bloodVolume",0])==4.2 && {
            (_medic getVariable ["ace_medical_openWounds",[]]) isEqualTo [["body",0.4]]
        },"medical state overwritten"] call _check;
    };
'''


def run(body, extra=""):
    execute(FIXTURE + code() + extra + body)


@pytest.mark.parametrize("spare", ['["Mag_B",19]', '["Mag_A",30]', '["Mag_A",7]'])
def test_native_autoload_cannot_replace_saved_magazine_or_steal_even_identical_spare(spare):
    run(f'''
        (_containers select 0) setVariable ["testMagCargo",[{spare}]];
        private _before=call _cargoState;
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"exact restore did not finish"] call _check;
        [(_loadout select 0) isEqualTo _rifle,"wrong saved loaded magazine or attachments"] call _check;
        [(call _cargoState) isEqualTo _before,"autoload consumed original spare"] call _check;
        [_autoloads==0,"compatible spare reached native autoload"] call _check;
        call _checkUnrelated;
    ''')


def test_duplicates_zero_rounds_and_all_original_containers_are_conserved():
    run(r'''
        (_containers select 0) setVariable ["testMagCargo",[["Mag_A",7],["Mag_A",7],["Mag_A",0],["Unrelated",4]]];
        (_containers select 1) setVariable ["testMagCargo",[["Mag_A",7],["Mag_B",9],["Grenade",1]]];
        (_containers select 2) setVariable ["testMagCargo",[["Rocket",1],["Mag_B",0],["Grenade",0]]];
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,_launcher]];
        private _before=call _cargoState;
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"two-slot restore failed"] call _check;
        [(_loadout select 0) isEqualTo _rifle && {(_loadout select 1) isEqualTo _launcher},"loaded slot mismatch"] call _check;
        [(call _cargoState) isEqualTo _before,"duplicate/zero-round/container provenance changed"] call _check;
        call _checkUnrelated;
    ''')


@pytest.mark.parametrize("rifle_mags", ['[[],[]]', '[["Mag_A",0],["Grenade",0]]'])
def test_absent_and_loaded_empty_magazines_remain_distinct(rifle_mags):
    run(f'''
        private _saved={rifle_mags}; _rifle set [4,_saved select 0]; _rifle set [5,_saved select 1];
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,[]]];
        (_containers select 1) setVariable ["testMagCargo",[["Mag_A",23],["Grenade",1]]];
        private _before=call _cargoState;
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"empty-state restore failed"] call _check;
        [(_loadout select 0) isEqualTo _rifle,"absent/loaded-empty muzzle changed"] call _check;
        [(call _cargoState) isEqualTo _before,"empty-state restore consumed spare"] call _check;
    ''')


def test_named_primary_muzzle_targets_the_actual_second_muzzle():
    run(r'''
        _muzzles=["RifleMuzzle","GL"];
        _nativeAutoload=false; _defaultItems=["","","",""];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"named-primary GL restore failed"] call _check;
        [(_loadout select 0) isEqualTo _rifle,"GL was added into named primary muzzle"] call _check;
    ''')


def test_fresh_linked_attachments_are_removed_before_exact_saved_attachments():
    run(r'''
        _defaultItems=["defaultSuppressor","defaultLaser","defaultScope","defaultBipod"];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"fresh default attachments blocked exact restoration"] call _check;
        [(_loadout select 0) isEqualTo _rifle,"fresh LinkedItems replaced saved attachments"] call _check;
        call _checkUnrelated;
    ''')


def test_current_spares_acquired_or_spent_while_holding_are_not_replaced_by_old_inventory():
    run(r'''
        // Only weapon slots were captured during Prep. This is inventory at
        // restore time, after a spare was spent and a different spare acquired.
        (_containers select 0) setVariable ["testMagCargo",[["Mag_B",18],["Unrelated",3]]];
        (_containers select 2) setVariable ["testMagCargo",[["Mag_A",4],["Grenade",1]]];
        private _before=call _cargoState;
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"changed current inventory restore failed"] call _check;
        [(call _cargoState) isEqualTo _before,"old inventory snapshot overwrote acquired/spent spare"] call _check;
        call _checkUnrelated;
    ''')


def test_scheduled_entry_returns_actual_result_and_native_transaction_does_not_suspend():
    run(r'''
        _scheduled=true;
        (_containers select 1) setVariable ["testMagCargo",[["Mag_A",17],["Grenade",1]]];
        private _before=call _cargoState;
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"scheduled wrapper lost actual result"] call _check;
        [!_scheduled && {_adds==1} && {(call _cargoState) isEqualTo _before},"scheduled wrapper replayed/lost transaction"] call _check;
    ''')


def test_rejected_suppression_returns_removed_spares_and_never_adds_weapon():
    run(r'''
        (_containers select 0) setVariable ["testMagCargo",[["Mag_A",7],["Mag_B",19]]];
        _denyRemove=[["Mag_B",19]]; private _before=call _cargoState;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"failed suppression acknowledged"] call _check;
        [_adds==0 && {(_loadout select 0) isEqualTo []},"weapon added with compatible spare still present"] call _check;
        [(call _cargoState) isEqualTo _before,"partial suppression lost cargo"] call _check;
        [([_medic,"ACME_hang_savedWeaponSlots",[]] call _objectRead) isEqualTo [_rifle,[]],"rejected suppression discarded snapshot"] call _check;
        _denyRemove=[];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"suppression retry failed"] call _check;
        [(call _cargoState) isEqualTo _before && {_adds==1},"suppression retry duplicated cargo/weapon"] call _check;
    ''')


def test_rejected_native_add_returns_every_suppressed_spare():
    run(r'''
        (_containers select 1) setVariable ["testMagCargo",[["Mag_A",8],["Grenade",1]]];
        _denyAdd=true; private _before=call _cargoState;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"rejected add acknowledged"] call _check;
        [(call _cargoState) isEqualTo _before && {(_loadout select 0) isEqualTo []},"rejected add stranded cargo"] call _check;
        _denyAdd=false;
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"native add retry failed"] call _check;
        [(call _cargoState) isEqualTo _before,"native add retry duplicated cargo"] call _check;
    ''')


@pytest.mark.parametrize("denied", ['"scope"', '"Mag_A"', '"Grenade"'])
def test_partial_attachment_or_loaded_magazine_retries_do_not_steal_spares(denied):
    run(f'''
        (_containers select 0) setVariable ["testMagCargo",[["Mag_A",29],["Grenade",1]]];
        _denied=[{denied}]; private _before=call _cargoState;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"partial restore acknowledged"] call _check;
        [(call _cargoState) isEqualTo _before,"partial restore stranded spare"] call _check;
        _denied=[];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"partial restore could not finish"] call _check;
        [(_loadout select 0) isEqualTo _rifle && {{_adds==1}},"partial retry recreated gun or wrong magazine"] call _check;
        [(call _cargoState) isEqualTo _before,"partial retry duplicated spare"] call _check;
    ''')


def test_rejected_default_attachment_cleanup_keeps_exact_recovery_evidence():
    run(r'''
        _defaultItems=["defaultSuppressor","defaultLaser","defaultScope","defaultBipod"];
        _denyDefaultClear=true;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"default attachment rejection acknowledged"] call _check;
        private _before=str _loadout;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"default attachment conflict erased"] call _check;
        [str _loadout==_before && {_adds==1},"retry clobbered an occupied attachment"] call _check;
        [(_medic getVariable ["ACME_hang_savedWeaponSlots",[]]) isEqualTo [_rifle,[]],"default attachment conflict lost snapshot"] call _check;
    ''')


def test_full_original_container_retains_debt_then_repays_once_without_refilling():
    run(r'''
        (_containers select 1) setVariable ["testMagCargo",[["Mag_A",13],["Mag_A",13]]];
        private _before=call _cargoState; _denyReturnContainers=[_containers select 1];
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"unreturned cargo acknowledged"] call _check;
        [count ((_medic getVariable ["ACME_hang_weaponRestoreCargo",[[],[]]]) select 0)==2,"unreturned duplicate debt lost"] call _check;
        private _gun=str (_loadout select 0);
        [_medic] call ACME_fnc_hangBagRestoreWeapons;
        [_adds==1 && {str (_loadout select 0)==_gun},"full-container retry recreated/refilled gun"] call _check;
        _denyReturnContainers=[];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"cargo debt repayment failed"] call _check;
        [(call _cargoState) isEqualTo _before && {_adds==1},"cargo repayment duplicated/lost original spare"] call _check;
        [isNil {_medic getVariable "ACME_hang_savedWeaponSlots"},"settled snapshot retained"] call _check;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons) && {(call _cargoState) isEqualTo _before},"settled request repaid again"] call _check;
    ''')


def test_deleted_original_container_keeps_debt_and_does_not_redirect_to_new_container():
    run(r'''
        (_containers select 1) setVariable ["testMagCargo",[["Mag_A",13]]];
        _denyReturnContainers=[_containers select 1];
        [_medic] call ACME_fnc_hangBagRestoreWeapons;
        _deletedContainers=[_containers select 1]; _containers set [1,parsingNamespace];
        parsingNamespace setVariable ["testMagCargo",[]]; _denyReturnContainers=[];
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"deleted original container acknowledged"] call _check;
        [(parsingNamespace getVariable ["testMagCargo",[]]) isEqualTo [],"old spare redirected into replacement container"] call _check;
        [count ((_medic getVariable ["ACME_hang_weaponRestoreCargo",[[],[]]]) select 0)==1 && {_adds==1},"deleted container debt lost or gun recreated"] call _check;
    ''')


def test_unexpected_positive_native_return_never_retries_observed_returned_debt():
    run(r'''
        (_containers select 0) setVariable ["testMagCargo",[["Mag_A",13],["Mag_A",13]]];
        _returnMultiplicity=2;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"anomalous native return acknowledged"] call _check;
        [count ((_medic getVariable ["ACME_hang_weaponRestoreCargo",[[],[]]]) select 0)==1,"anomalous first return did not discharge attempted debt and retain unattempted debt"] call _check;
        [count ((_containers select 0) getVariable ["testMagCargo",[]])==2,"repayment continued after anomalous first insertion"] call _check;
        [(_medic getVariable ["ACME_hang_weaponRestoreCargoAnomaly",false]) isEqualTo [_containers select 0,"Mag_A",13,0,2],"native return anomaly lost container/class/round/delta recovery evidence"] call _check;
        private _before=call _cargoState; private _writes=_cargoWrites; private _gun=str _loadout;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"anomaly retry falsely settled"] call _check;
        [(call _cargoState) isEqualTo _before && {_cargoWrites==_writes} && {str _loadout==_gun},"anomaly retry duplicated returned magazine"] call _check;
    ''')


def test_new_owner_repays_replicated_debt_once_without_recreating_owned_weapon():
    run(r'''
        (_containers select 1) setVariable ["testMagCargo",[["Mag_A",12]]];
        private _before=call _cargoState; _denyReturnContainers=[_containers select 1];
        [_medic] call ACME_fnc_hangBagRestoreWeapons;
        private _writes=_cargoWrites; private _gun=str _loadout;
        _ownerLocal=false; _denyReturnContainers=[];
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"old non-owner repaid cargo"] call _check;
        [_cargoWrites==_writes && {str _loadout==_gun},"old owner touched migrated state"] call _check;
        _ownerLocal=true;
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"new owner could not repay replicated debt"] call _check;
        [_adds==1 && {(call _cargoState) isEqualTo _before},"owner handoff duplicated weapon/spare"] call _check;
    ''')


def test_intentional_new_kit_retires_old_pending_cargo_and_anomaly_without_repayment():
    # The carrier boundary is independently tested by B267/B269 access suites;
    # execute the real kit coordinator for these Hang Bag retirement writes.
    s = source("equipmentKitChanged").replace("local _unit", "_ownerLocal").replace("canSuspend", "false")
    extra = 'ACM_core_fnc_carrierKitChanged={}; ACM_core_fnc_equipmentKitChanged={' + adapt(s) + '};'
    run(r'''
        _medic setVariable ["ACME_hang_weaponKitEpoch",0];
        _medic setVariable ["ACME_hang_weaponRestoreCargo",[[[_containers select 0,"Mag_A",12]],[]]];
        _medic setVariable ["ACME_hang_weaponRestoreCargoAnomaly",true];
        (_containers select 0) setVariable ["testMagCargo",[["NewKitMag",30]]];
        _loadout set [0,["NewRifle","","","",["NewKitMag",30],[],""]];
        private _before=call _cargoState; private _gun=str _loadout;
        [[_medic] call ACM_core_fnc_equipmentKitChanged,"intentional replacement rejected"] call _check;
        [isNil {_medic getVariable "ACME_hang_weaponRestoreCargo"} && {isNil {_medic getVariable "ACME_hang_weaponRestoreCargoAnomaly"}},"old-kit cargo debt/anomaly survived intentional replacement"] call _check;
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"old restore entered replacement kit"] call _check;
        [_cargoWrites==0 && {_adds==0} && {(call _cargoState) isEqualTo _before} && {str _loadout==_gun},"old debt was repaid into replacement kit"] call _check;
        call _checkUnrelated;
    ''', extra)


@pytest.mark.parametrize("successor", ['["NewRifle","","","",["Mag_B",2],[],""]', '["Rifle","suppressor","laser","scope",["Mag_A",3],["Grenade",1],"bipod"]'])
def test_pending_cargo_can_repay_after_foreign_or_fired_slot_without_touching_it(successor):
    run(f'''
        (_containers select 2) setVariable ["testMagCargo",[["Mag_A",11]]];
        private _before=call _cargoState; _denyReturnContainers=[_containers select 2];
        [_medic] call ACME_fnc_hangBagRestoreWeapons;
        _loadout set [0,{successor}]; private _gun=str (_loadout select 0); _denyReturnContainers=[];
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"successor/fired slot was overwritten"] call _check;
        [str (_loadout select 0)==_gun && {{_adds==1}},"cargo retry recreated/refilled successor gun"] call _check;
        [(call _cargoState) isEqualTo _before,"safe cargo debt was not repaid exactly"] call _check;
    ''')


def test_second_slot_does_not_settle_or_drop_first_slot_pending_cargo():
    run(r'''
        (_containers select 0) setVariable ["testMagCargo",[["Mag_A",11]]];
        (_containers select 2) setVariable ["testMagCargo",[["Rocket",1]]];
        private _before=call _cargoState; _denyReturnContainers=[_containers select 0];
        _medic setVariable ["ACME_hang_savedWeaponSlots",[_rifle,_launcher]];
        [!([_medic] call ACME_fnc_hangBagRestoreWeapons),"first pending cargo falsely acknowledged"] call _check;
        private _saved=_medic getVariable ["ACME_hang_savedWeaponSlots",[]];
        [(_saved select 0) isEqualTo _rifle && {(_saved select 1) isEqualTo []},"per-slot debt/settlement mixed"] call _check;
        _denyReturnContainers=[];
        [[_medic] call ACME_fnc_hangBagRestoreWeapons,"first-slot debt could not settle"] call _check;
        [(call _cargoState) isEqualTo _before && {_adds==2},"two-slot retry duplicated gun/cargo"] call _check;
    ''')


def test_pending_cargo_alone_blocks_new_preparation_and_menu():
    run(r'''
        _medic setVariable ["ACME_hang_savedWeaponSlots",[]];
        _medic setVariable ["ACME_hang_weaponRestoreCargo",[[[_containers select 0,"Mag_A",11]],[]]];
        _loadout set [0,+_rifle]; private _before=str _loadout;
        [_medic] call ACME_fnc_hangBagPrep;
        [str _loadout==_before && {_removedWeapons isEqualTo []} && {count _messages==1},"new prep stripped weapon behind cargo debt"] call _check;
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["LeftArm",["bag"]]]];
        [!([_medic,_patient] call ACME_fnc_hangBagCanStart),"menu admitted cargo debt"] call _check;
    ''', code("hangBagPrep") + code("hangBagCanStart"))


@pytest.mark.parametrize("fence", ["kit", "episode", "active"])
def test_stale_or_active_restore_never_replays_pending_cargo(fence):
    change = {
        "kit": '_medic setVariable ["ACME_equipmentKitEpoch",2]; _medic setVariable ["ACME_hang_weaponKitEpoch",1];',
        "episode": '_medic setVariable ["ACME_hang_Start",20];',
        "active": '_medic setVariable ["ACME_hang_Active",true];',
    }[fence]
    args = "[_medic,10]" if fence == "episode" else "[_medic]"
    run(f'''
        _medic setVariable ["ACME_hang_weaponRestoreCargo",[[[_containers select 0,"Mag_A",11]],[]]];
        {change}
        private _before=call _cargoState;
        [!({args} call ACME_fnc_hangBagRestoreWeapons),"stale or active restore admitted"] call _check;
        [_adds==0 && {{_cargoWrites==0}} && {{(call _cargoState) isEqualTo _before}},"rejected restore repaid into unrelated kit/episode"] call _check;
    ''')


def test_production_uses_narrow_cargo_commands_and_never_rebuilds_unit_or_medical_state():
    s = source("hangBagRestoreWeapons")
    # Source guards supplement the executed cargo/medical conservation cases.
    assert "_medic setUnitLoadout" not in s
    assert "removeMagazines" not in re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", s)
    assert "clearMagazineCargo" not in s
    assert "addMagazineAmmoCargo [_class, -1, _ammo]" in s
    assert "ACME_hang_weaponRestoreCargo" in s
