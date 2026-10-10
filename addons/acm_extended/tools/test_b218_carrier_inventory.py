"""Execute live removed-carrier custody and native supply selection in SQF-VM.

Only Arma cargo/locality/gear commands are adapted. The production recursive
snapshot/populate, identity checks, live restore and ACE useItem/hasItem code run.
This does not emulate replication, the in-game Gear display, or capacity physics.
"""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute, read, adapt, namespace_public_arguments


def cargo_source(name):
    native = name == "carrierLegacySnapshot"
    source = (ROOT / "addons/core/functions" / ("fnc_" + name + ".sqf")).read_text().split('#include "..\\script_component.hpp"', 1)[-1] if native else read(name)
    source = source.replace('local _patient', 'true')
    source = source.replace('vestContainer _patient', '_wornContainer').replace('vest _patient', '_wornVest')
    source = source.replace('getPosATL _patient', '[0,0,0]')
    source = source.replace('createVehicle ["ACME_RemovedCarrierCargo", [0,0,0], [], 0, "CAN_COLLIDE"]', '"GroundWeaponHolder" createVehicle [0,0,0]')
    source = source.replace('_cargo allowDamage false;', '')
    source = source.replace('removeVest _patient;', '_wornVest=""; deleteVehicle _wornContainer; _wornContainer=objNull;')
    source = source.replace('_patient addVest _class;', '_wornVest = _class; _wornContainer = "GroundWeaponHolder" createVehicle [0,0,0];')
    source = source.replace('getUnitLoadout _patient', '[[],[],[],[],[],[]]')
    source = source.replace('_patient setUnitLoadout [_loadout, false];', '_legacyWrites = _legacyWrites + 1; _wornVest = (_loadout select 4) select 0;')
    for command, key in [('itemCargo','items'),('magazinesAmmoCargo','mags'),('weaponsItemsCargo','weapons'),('everyContainer','children'),('backpackCargo','packs')]:
        source = re.sub(r'\b'+command+r' (_\w+)', rf'(\1 getVariable ["{key}", []])', source)
    source = re.sub(r'\bmagazineCargo (_\w+)', r'((\1 getVariable ["mags", []]) apply {_x select 0})', source)
    for command, key in [('clearItemCargoGlobal','items'),('clearMagazineCargoGlobal','mags'),('clearWeaponCargoGlobal','weapons'),('clearBackpackCargoGlobal','packs')]:
        extra = ' _container setVariable ["children", []];' if key == 'packs' else ''
        source = re.sub(r'\b'+command+r' (_\w+);', rf'\1 setVariable ["{key}", []];'+extra, source)
    source = re.sub(r'(_\w+) addItemCargoGlobal (\[[^;]*?\]);', r'[\1, \2] call _addItem;', source)
    source = re.sub(r'(_\w+) addBackpackCargoGlobal (\[[^;]*?\]);', r'[\1, \2, true] call _addItem;', source)
    source = re.sub(r'(_\w+) addMagazineAmmoCargo (\[[^;]*?\]);', r'[\1, \2] call _addMagazine;', source)
    source = re.sub(r'(_\w+) addWeaponWithAttachmentsCargoGlobal (\[[^;]*?\]);', r'[\1, \2] call _addWeapon;', source)
    return ('ACM_core_fnc_' if native else 'ACME_fnc_')+name+'={'+namespace_public_arguments(source)+'};\n'


def setup():
    native = ''.join('ACM_core_fnc_' + name + '={' +
        namespace_public_arguments((ROOT / 'addons/core/functions' / ('fnc_' + name + '.sqf')).read_text().split('#include "..\\script_component.hpp"', 1)[-1].replace(', _public]', ']')) + '};'
        for name in ('setDraggingCapability', 'setCargoLoadCapability'))
    return native + r'''
        _medic="GroundWeaponHolder" createVehicle [0,0,0];
        _patient="GroundWeaponHolder" createVehicle [0,0,0];
        private _wornVest="Vest_A";
        private _wornContainer="GroundWeaponHolder" createVehicle [0,0,0];
        private _legacyWrites=0;
        private _saved=["Vest_A",[["stale",9]]];
        private _savedVar="ACME_chestAccess_vestLoadout";
        private _addItem={
            params ["_container","_spec",["_backpack",false]];
            _spec params ["_class","_count"];
            private _key=["items","packs"] select _backpack;
            private _items=+(_container getVariable [_key,[]]);
            if (_count<0) then {
                private _idx=_items find _class;
                if (_idx>=0) then {_items deleteAt _idx;};
            } else {
                for "_i" from 1 to _count do {
                    _items pushBack _class;
                    if (_class in ["Pocket","Pack"]) then {
                        private _child="GroundWeaponHolder" createVehicle [0,0,0];
                        private _children=+(_container getVariable ["children",[]]);
                        _children pushBack [_class,_child]; _container setVariable ["children",_children];
                    };
                };
            };
            _container setVariable [_key,_items];
        };
        private _addMagazine={
            params ["_container","_spec"]; _spec params ["_class","_count","_ammo"];
            private _mags=+(_container getVariable ["mags",[]]);
            for "_i" from 1 to _count do {_mags pushBack [_class,_ammo];};
            _container setVariable ["mags",_mags];
        };
        private _addWeapon={
            params ["_container","_spec"]; _spec params ["_weapon","_count"];
            private _weapons=+(_container getVariable ["weapons",[]]);
            for "_i" from 1 to _count do {_weapons pushBack (+_weapon);};
            _container setVariable ["weapons",_weapons];
        };
        ace_common_fnc_adjustMagazineAmmo={
            params ["_container","_class"];
            private _mags=+(_container getVariable ["mags",[]]);
            private _i=_mags findIf {(_x select 0)==_class};
            if (_i>=0) then {
                private _remaining=(_mags select _i select 1)-1;
                if (_remaining>0) then {(_mags select _i) set [1,_remaining];} else {_mags deleteAt _i;};
            };
            _container setVariable ["mags",_mags];
        };
    '''+''.join(cargo_source(x) for x in ['carrierCargoSnapshot','carrierCargoEqual','carrierCargoPopulate','carrierInventoryGet','carrierInventoryCreate','carrierLegacySnapshot','carrierInventoryRestore','carrierSupplyTake'])


def remove():
    return r'''
        private _cargo=[_patient,_savedVar] call ACME_fnc_carrierInventoryCreate;
        [!isNull _cargo,"carrier staging failed"] call _check;
        _wornVest=""; deleteVehicle _wornContainer; _wornContainer=objNull;
    '''


@pytest.mark.parametrize('context',['ACME_chestAccess_vestLoadout','ACME_CS_vestLoadout','ACME_headElev_vestLoadout'])
@pytest.mark.parametrize('count',[0,1,7])
def test_live_contents_not_original_snapshot_restore_after_consumption_looting_and_additions(count,context):
    execute(setup()+f'_savedVar="{context}"; for "_i" from 1 to {count} do {{[_wornContainer,["seal",1]] call _addItem;}};'+remove()+r'''
        if ("seal" in (_cargo getVariable ["items",[]])) then {
            private _receipt=[_patient,["seal"]] call ACME_fnc_carrierSupplyTake;
            [(_receipt select 0) isEqualTo _patient && {(_receipt select 3) isEqualTo _cargo},"wrong debit provenance"] call _check;
        };
        // Gear can take/add contents while the visual carrier remains unpickable.
        [_cargo,["seal",-1]] call _addItem;
        [_cargo,["added",1]] call _addItem;
        private _now=[_cargo] call ACME_fnc_carrierCargoSnapshot;
        [[_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore,"restore rejected"] call _check;
        [([_wornContainer] call ACME_fnc_carrierCargoSnapshot) isEqualTo _now,"stale snapshot resurrected supplies"] call _check;
        [_legacyWrites==0 && {isNull _cargo},"live restore used loadout refill or retained duplicate cargo"] call _check;
        [!(("stale") in (_wornContainer getVariable ["items",[]])),"old saved supply returned"] call _check;
    ''')


@pytest.mark.parametrize('ammo',[0,1,7,29])
def test_partial_magazines_attached_weapon_and_recursive_containers_preserved(ammo):
    execute(setup()+f'''
        private _exact=[["seal"],[["Mag_A",{ammo}],["Mag_A",3]],[["Rifle","muzzle","pointer","optic",["Mag_A",{ammo}],[],"bipod"]],
            [["Pocket",false,[["syringe"],[["Mag_B",2]],[],[["Pack",true,[["needle"],[],[],[]]]]]]]];
        [_wornContainer,_exact] call ACME_fnc_carrierCargoPopulate;
        [([_wornContainer] call ACME_fnc_carrierCargoSnapshot) isEqualTo _exact,"recursive fixture failed"] call _check;
    '''+remove()+r'''
        [[_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore,"restore rejected"] call _check;
        [([_wornContainer] call ACME_fnc_carrierCargoSnapshot) isEqualTo _exact,"magazine ammo/attachments/nested cargo changed"] call _check;
    ''')


def test_deleted_live_container_does_not_resurrect_original_supplies():
    execute(setup()+remove()+r'''
        deleteVehicle _cargo;
        [[_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore,"lost cargo blocked empty carrier return"] call _check;
        [([_wornContainer] call ACME_fnc_carrierCargoSnapshot) isEqualTo [[],[],[],[]],"lost supplies recreated"] call _check;
        [_legacyWrites==0,"missing live holder fell back to stale loadout"] call _check;
    ''')


def test_replaced_worn_vest_preserves_custody_without_overwrite():
    execute(setup()+remove()+r'''
        _wornVest="Replacement";
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"replacement overwritten"] call _check;
        [_wornVest=="Replacement" && {!isNull _cargo} && {!(_cargo getVariable ["ACME_carrierClosing",false])},"custody lost"] call _check;
    ''')


@pytest.mark.parametrize('fault',['closing','patient','custody'])
def test_wrong_container_identity_and_closing_container_are_not_spendable_or_restorable(fault):
    mutation={
        'closing':'_cargo setVariable ["ACME_carrierClosing",true];',
        'patient':'_cargo setVariable ["ACME_carrierPatient",_medic];',
        'custody':'_cargo setVariable ["ACME_carrierSavedVar","another-workspace"];',
    }[fault]
    assertion = '[isNull ([_patient] call ACME_fnc_carrierInventoryGet),"invalid cargo was available"] call _check;' if fault!='custody' else '[!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"another custody restored"] call _check;'
    execute(setup()+remove()+mutation+assertion)


def test_settlement_is_idempotent_even_after_external_removal_of_returned_vest():
    execute(setup()+remove()+r'''
        [[_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore,"first restore failed"] call _check;
        _wornVest=""; deleteVehicle _wornContainer; _wornContainer=objNull;
        [[_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore,"repeat settlement not acknowledged"] call _check;
        [_wornVest=="" && {_legacyWrites==0},"late repeat recreated a second vest"] call _check;
    ''')


def test_one_patient_cannot_create_two_live_carriers():
    execute(setup()+remove()+r'''
        _wornVest="Vest_B"; _wornContainer="GroundWeaponHolder" createVehicle [0,0,0];
        [isNull ([_patient,"ACME_CS_vestLoadout"] call ACME_fnc_carrierInventoryCreate),"two live carrier copies allowed"] call _check;
        [(_patient getVariable ["ACME_carrierCargo",objNull]) isEqualTo _cargo,"original identity replaced"] call _check;
    ''')


def native_setup():
    sources=''
    for name in ['useItem','hasItem']:
        s=(ROOT/'addons/core/overrides'/('fnc_'+name+'.sqf')).read_text()
        s=s.replace('_medic isEqualTo player && {!isNull findDisplay 312}', 'false')
        s=s.replace('objectParent _unit','objNull')
        s=s.replace('itemCargo _unitVehicle','[]').replace('magazineCargo _unitVehicle','[]')
        s=s.replace('itemCargo _carrier','(_carrier getVariable ["items",[]])').replace('magazineCargo _carrier','((_carrier getVariable ["mags",[]]) apply {_x select 0})')
        s=s.replace('_unit removeItem _x;','[_unit,[_x,-1]] call _addItem;')
        s=s.replace('_items findAny _unitItems', '(_items findIf {_x in _unitItems})')
        # No object substitution: real VM objects are retained; preprocess only CBA macros.
        s=re.sub(r'^#include.*$','',s,flags=re.M)
        s=re.sub(r'ACEFUNC\((\w+),(\w+)\)',lambda m:'ace_'+m[1]+'_fnc_'+m[2],s)
        sources+='ace_medical_treatment_fnc_'+name+'={'+s+'};'
    return setup()+sources+r'''
        ace_common_fnc_uniqueItems={params ["_u","_kind"]; +(_u getVariable ["items",[]])};
        ace_medical_treatment_fnc_isMedic={_trained};
        private _trained=false;
        _medic setVariable ["items",["seal"]];
        _patient setVariable ["items",["seal"]];
        _wornContainer setVariable ["items",["seal"]];
    '''+remove()


@pytest.mark.parametrize('mode,trained,donor,from_carrier',[(0,False,'_patient',True),(1,False,'_medic',False),(2,False,'_medic',False),(3,False,'_patient',True),(3,True,'_medic',False)])
def test_actual_native_useItem_obeys_shared_policy_and_spends_carrier_before_worn_patient_items(mode,trained,donor,from_carrier):
    execute(native_setup()+f'''
        ace_medical_treatment_allowSharedEquipment={mode}; _trained={str(trained).lower()};
        [[_medic,_patient,["seal"]] call ace_medical_treatment_fnc_hasItem,"native gate missed available supply"] call _check;
        private _receipt=[_medic,_patient,["seal"]] call ace_medical_treatment_fnc_useItem;
        [(_receipt select 0) isEqualTo {donor},"shared policy chose wrong donor"] call _check;
        [((_receipt param [3,objNull]) isEqualTo _cargo)=={str(from_carrier).lower()},"wrong source selected"] call _check;
        [(_patient getVariable ["items",[]]) isEqualTo ["seal"],"patient worn items debited before removed carrier"] call _check;
    ''')


@pytest.mark.parametrize('mode,allowed',[(0,True),(1,True),(2,False),(3,True)])
def test_actual_native_availability_finds_carrier_only_supplies_except_medic_only(mode,allowed):
    execute(native_setup()+f'''
        _medic setVariable ["items",[]]; _patient setVariable ["items",[]];
        ace_medical_treatment_allowSharedEquipment={mode};
        [([_medic,_patient,["seal"]] call ace_medical_treatment_fnc_hasItem)=={str(allowed).lower()},"carrier-only gate ignored sharing policy"] call _check;
    ''')


def test_magazine_supply_uses_existing_ace_dose_semantics():
    execute(setup()+remove()+r'''
        _cargo setVariable ["mags",[["dose",4]]];
        private _receipt=[_patient,["dose"]] call ACME_fnc_carrierSupplyTake;
        [(_receipt select 0) isEqualTo _patient && {(_cargo getVariable ["mags",[]]) isEqualTo [["dose",3]]},"carrier magazine was discarded/refilled instead of dosed"] call _check;
    ''')


def test_nonpickup_and_shared_custody_are_wired_through_all_three_removal_contexts():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    assert 'class ACME_RemovedCarrierCargo: GroundWeaponHolder_Scripted' in config
    assert 'class ACME_OpenPlateCarrierInventory:' in config
    assert 'ace_dragging_canCarry = 0;' in config
    for name in ['chestAccessVestAcquire','headElevateStart']:
        s=read(name)
        assert s.index('call ACME_fnc_carrierInventoryCreate') < s.index('removeVest')
    for name in ['headElevVestRestore','chestAccessVestRestore']:
        s=read(name)
        assert 'call ACME_fnc_carrierInventoryRestore' in s
        assert 'setUnitLoadout' not in s
    assert 'ACME_chestAccess_vestLoadoutLive' in read('headElevateStop')
    assert 'ACME_headElev_vestLoadout' in read('carrierInventoryCapacity')
    assert 'addItemCargoGlobal [_vest' not in read('chestAccessVestAcquire')
    assert 'carrierInventoryGet' not in read('itemCount'), 'personal-only count must stay personal'


def test_failed_staging_cannot_remove_worn_inventory():
    execute(setup()+r'''
        _wornContainer setVariable ["items",["seal"]];
        _addItem={}; // engine rejects a cargo write
        private _cargo=[_patient,_savedVar] call ACME_fnc_carrierInventoryCreate;
        [isNull _cargo && {_wornVest=="Vest_A"} && {(_wornContainer getVariable ["items",[]]) isEqualTo ["seal"]},"failed staging lost original inventory"] call _check;
        [isNull (_patient getVariable ["ACME_carrierCargo",objNull]),"failed staging published custody"] call _check;
    ''')


def test_failed_restoration_keeps_current_live_contents_and_releases_closing_gate():
    execute(setup()+remove()+r'''
        _cargo setVariable ["items",["seal"]];
        _addItem={}; // returned vest rejects contents
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"failed restore declared success"] call _check;
        [_wornVest=="" && {!isNull _cargo} && {(_cargo getVariable ["items",[]]) isEqualTo ["seal"]},"failed restore lost live supplies"] call _check;
        [!(_cargo getVariable ["ACME_carrierClosing",true]),"failure retained inventory lock"] call _check;
    ''')


def test_cargo_comparison_allows_reordering_but_rejects_lost_duplicate_or_ammo():
    execute(setup()+r'''
        [[["a","b","a"],[["M",3],["M",7]],[],[]],[["b","a","a"],[["M",7],["M",3]],[],[]]] call ACME_fnc_carrierCargoEqual call {[_this,"engine reordering was treated as loss"] call _check;};
        [!([[["a","a"],[],[],[]],[["a"],[],[],[]]] call ACME_fnc_carrierCargoEqual),"lost duplicate accepted"] call _check;
        [!([[[],[["M",3]],[],[]],[[],[["M",30]],[],[]]] call ACME_fnc_carrierCargoEqual),"refilled magazine accepted"] call _check;
    ''')


def test_inventory_launcher_bypasses_clinical_progress_and_pending_reopen():
    treatment=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    assert 'if (_classname in ["ACME_OpenPlateCarrierInventory", "ACME_FlushLine"]) exitWith {false};' in treatment
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    from medication_inventory import subtree
    action=subtree(config,'ace_medical_treatment_actions')['classes']['ACME_OpenPlateCarrierInventory']
    assert action['props']['condition']=='false'
    assert action['props']['allowedSelections']==[]
    assert 'addAction' not in read('carrierInventoryWorld')
