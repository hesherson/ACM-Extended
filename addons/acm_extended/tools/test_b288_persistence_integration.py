"""Production persistence admission boundaries with engine stand-ins.

These checks do not certify a mission save adapter or native multiplayer timing.
"""
import pytest
import re

from test_historical_vial_execution import setup as vial_setup
from test_menu_death_lifecycle import execute, F, adapt
from test_historical_vial_execution import map_defaults


@pytest.mark.parametrize('source', ['partial', 'sealed'])
@pytest.mark.parametrize('frozen', ['holder', 'explicit-provider', 'resolved-provider'])
def test_checkpoint_fences_vial_debit_before_any_inventory_or_virtual_store_write(source, frozen):
    holder = '_medic' if frozen == 'holder' else '_patient'
    provider = '_medic'
    captured = ',_medic' if frozen != 'resolved-provider' else ''
    execute(vial_setup() + f'''
        {holder} setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",{5 if source == 'partial' else 0}]]];
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[_patient,"lease",14]];
        {holder if frozen == 'holder' else provider} setVariable ["ACME_persistenceFrozen",true];
        private _before=str ({holder} getVariable "ACME_infusion_openVials");
        [!([{holder},"Ketamine",1{captured}] call ACME_fnc_vialTake),"checkpoint admitted a new vial debit"] call _check;
        [_inventoryDebits==0 && {{_stockWrites==0}},"frozen admission changed physical or virtual stock"] call _check;
        [str ({holder} getVariable "ACME_infusion_openVials")==_before,"frozen draw lost partial vial remainder"] call _check;
    ''')


def test_checkpoint_does_not_block_returning_previously_reserved_vial_solution():
    execute(vial_setup() + r'''
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",5]]];
        [[_medic,"Ketamine",1,_medic] call ACME_fnc_vialTake,"settled pre-checkpoint draw failed"] call _check;
        _medic setVariable ["ACME_persistenceFrozen",true];
        [[_medic,"Ketamine",1,_medic] call ACME_fnc_vialRefund,"checkpoint stranded existing refund"] call _check;
        [((_medic getVariable "ACME_infusion_openVials") get "Ketamine")==5,"refund did not restore exact reserved solution"] call _check;
        [_inventoryDebits==0,"refund fabricated a sealed vial"] call _check;
    ''')


def fingerprint_function(name):
    text=(F/f'fn_{name}.sqf').read_text()
    text=text.replace('isClass (configFile >> "CfgMagazines" >> _class)',
                      '(_class in ["ACME_PreparedIVSet","ACME_PreparedSyringe10"])')
    text=text.replace('getText (configFile >> "CfgMagazines" >> _class >> "ACME_inventoryKind")',
                      '(["prepared","syringe"] select (_class=="ACME_PreparedSyringe10"))')
    text=text.replace('isClass (configFile >> "CfgWeapons" >> _bag)', '(_bag=="ACM_BloodBag_ON_500")')
    text=text.replace('isClass (configFile >> "CfgWeapons" >> _vest)', '(_vest=="Vest_A")')
    text=re.sub(r'\bfinite (\([^()\n]*\)|_\w+)',r'(\1 call _finite)',text)
    return 'ACME_fnc_'+name+'={'+adapt(map_defaults(text))+'};\n'


def fingerprint_setup():
    return r'''
        private _finite={_this isEqualType 0};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        ACME_fnc_coolerBagVolume={params ["_class"];if (_class=="ACM_BloodBag_ON_500") then {500} else {0}};
        ACME_fnc_vialCapacity={10};
    '''+''.join(fingerprint_function(n) for n in (
        'ventDeviceFields','inventorySnapshotValid','coolerSnapshotValid','equipmentCargoValid',
        'equipmentSnapshotValid','bloodExposureSnapshotValid','persistenceFingerprint'))+r'''
        private _syringe=["Lidocaine",10,3.25,"Custom",2.125,[["Lidocaine",3.25]],"dilutionB13","red","line1","line2","line3","dose","flush","inventoryB279"];
        private _set=["fresh","ACM_FreshBloodBag_500_12","FreshBloodBag_500_12","FreshBlood","label","","pic",false,"Blood",370,500,["freshAgeV1",true,100,3]];
        private _inventory=[1,[["syringe",26,"ACME_PreparedSyringe10",["dose",_syringe],[]],
            ["prepared",27,"ACME_PreparedIVSet",["fresh",_set,[]],[]]]];
        private _cooler=[1,"holder",[["cooler-1",23,"ACME_BloodCooler_CSWB1U",7000,[["ACM_BloodBag_ON_500",300]]]]];
        private _used=["used-1","FreshBlood",240,1,3,500,"Blood",-1,["freshAgeV1",true,100,3]];
        private _tree=[[["bandage"],[],[],[]],[1,[]],[1,"holder",[]],[]];
        private _equipment=[1,[["Morphine",2],["Ketamine",3]],[_used],[["ACME_vent_battery",20],["ACME_vent_mode","SIMV VC PS"]],
            ["ACME_CS_vestLoadout","Vest_A",_tree]];
        private _blood=[1,[["ACM_BloodBag_ON_500",200]]];
        private _metadata=createHashMapFromArray [["ACME_inventory_v1",_inventory],["ACME_coolers_v1",_cooler],
            ["ACME_equipment_v1",_equipment],["ACME_blood_v1",_blood]];
        private _before=[_metadata] call ACME_fnc_persistenceFingerprint;
        [_before!="","valid fingerprint fixture rejected"] call _check;
    '''


@pytest.mark.parametrize('key', ['ACME_inventory_v1','ACME_coolers_v1','ACME_equipment_v1','ACME_blood_v1'])
@pytest.mark.parametrize('fault', ['missing','invalid'])
def test_fingerprint_requires_every_complete_valid_component(key,fault):
    change=f'_metadata deleteAt "{key}";' if fault=='missing' else f'_metadata set ["{key}",[]];'
    execute(fingerprint_setup()+change+r'''
        [([_metadata] call ACME_fnc_persistenceFingerprint)=="","incomplete/invalid composite produced valid save proof"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_syringe set [2,2.25];', '_syringe set [8,"changed label"];',
    '_syringe set [2,3.250001];',
    '_set set [9,300];', '(_inventory select 1) deleteAt 0;',
    '(((_cooler select 2) select 0) select 4) deleteAt 0;',
    '((_cooler select 2) select 0) set [1,99];',
    '(_equipment select 1 select 0) set [1,1];',
    '_used set [2,230];', '(_used select 8) set [1,false];',
    '(_equipment select 3 select 0) set [1,19];',
    '(_equipment select 3 select 1) set [1,"PCV"];',
    '(_tree select 0 select 0) pushBack "morphine";',
    '(_blood select 1) pushBack ["ACM_BloodBag_ON_500",200];',
])
def test_fingerprint_detects_virtual_contents_identity_and_device_changes(change):
    execute(fingerprint_setup()+change+r'''
        private _after=[_metadata] call ACME_fnc_persistenceFingerprint;
        [_after!="" && {_after!=_before},"changed stable equipment facts retained old save proof"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '((_cooler select 2) select 0) set [3,7100];',
    '(((_cooler select 2) select 0) select 4 select 0) set [1,320];',
    '(_set select 11) set [2,120];', '(_used select 8) set [2,120];',
    '(_blood select 1 select 0) set [1,220];',
    'reverse (_equipment select 1);reverse (_equipment select 3);reverse (_inventory select 1);',
])
def test_fingerprint_ignores_elapsed_ages_and_unordered_row_order(change):
    execute(fingerprint_setup()+change+r'''
        [([_metadata] call ACME_fnc_persistenceFingerprint)==_before,"time passage or row ordering invalidated stable proof"] call _check;
    ''')


def test_fingerprint_never_mutates_live_metadata_while_removing_age_from_comparison():
    execute(fingerprint_setup()+r'''
        private _saved=str _metadata;
        [_metadata] call ACME_fnc_persistenceFingerprint;
        [str _metadata==_saved && {(_set select 11 select 2)==100} && {(_used select 8 select 2)==100},"fingerprint rewrote saved/live collection age"] call _check;
    ''')


def test_recursive_cargo_fingerprint_ignores_child_clock_age_and_tracks_child_custody():
    execute(fingerprint_setup()+r'''
        private _nativeChild=[["bandage"],[["ACME_CoolerCarrier_CSWB1U",31]],[],[]];
        private _childCooler=[1,"holder",[["child-cold",31,"ACME_BloodCooler_CSWB1U",70,[["ACM_BloodBag_ON_500",30]]]]];
        private _child=[_nativeChild,[1,[]],_childCooler,[]];
        (_tree select 0 select 3) pushBack ["Pouch",false,_nativeChild];
        (_tree select 3) pushBack _child;
        private _nestedBefore=[_metadata] call ACME_fnc_persistenceFingerprint;
        [_nestedBefore!="","valid recursive cargo rejected"] call _check;
        (_childCooler select 2 select 0) set [3,90];
        (_childCooler select 2 select 0 select 4 select 0) set [1,50];
        [([_metadata] call ACME_fnc_persistenceFingerprint)==_nestedBefore,"nested aging invalidated stable cargo proof"] call _check;
        (_childCooler select 2 select 0) set [1,32];
        private _changed=[_metadata] call ACME_fnc_persistenceFingerprint;
        [_changed!="" && {_changed!=_nestedBefore},"nested opaque identity changed without invalidating save proof"] call _check;
    ''')


@pytest.mark.parametrize('first,second', [('3.250001','3.250002'),('1e-30','1.01e-30'),('1e-44','2e-44')])
def test_scalar_fingerprint_does_not_use_rounded_display_numbers(first,second):
    execute(fingerprint_setup()+f'''
        _syringe set [2,{first}];
        private _precise=[_metadata] call ACME_fnc_persistenceFingerprint;
        _syringe set [2,{second}];
        private _changed=[_metadata] call ACME_fnc_persistenceFingerprint;
        [_precise!="" && {{_changed!=""}} && {{_precise!=_changed}},"distinct native scalar contents shared a rounded display fingerprint"] call _check;
    ''')


def test_worn_root_nested_container_extension_is_part_of_the_owner_save_proof():
    execute(fingerprint_setup()+r'''
        private _nestedTree=[[["bandage"],[],[],[]],[1,[]],[1,"holder",[]],[]];
        _equipment pushBack [[2,"Pouch",_nestedTree]];
        private _extended=[_metadata] call ACME_fnc_persistenceFingerprint;
        [_extended!="" && {_extended!=_before},"nested worn-root extension omitted from save proof"] call _check;
        (_nestedTree select 0 select 0) pushBack "Morphine";
        private _changed=[_metadata] call ACME_fnc_persistenceFingerprint;
        [_changed!="" && {_changed!=_extended},"nested worn-root content change retained old proof"] call _check;
    ''')
