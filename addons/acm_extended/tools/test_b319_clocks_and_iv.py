"""Exercise the server clock, shared blood Y warmer and physical IV kit."""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b156_procedure_supplies import supply_setup


def test_server_clinical_clock_preserves_age_across_rate_changes():
    tick = adapt(read("clinicalClockTick"))
    tick = tick.replace("serverTime", "_nowTime").replace("timeMultiplier", "_multiplier")
    tick = tick.replace("accTime", "1").replace("isMultiplayer", "true")
    tick = tick.replace('_next remoteExecCall ["ACME_fnc_clinicalTimingSync",-2,"ACME_clinicalClockAnchor"]', "_publications pushBack +_next")
    execute("private _tick={" + tick + "};" + '''
        private _publications=[];private _multiplier=4;
        CBA_missionTime=10;_nowTime=100;
        missionNamespace setVariable ["ACME_clinicalTiming",[1,true,true,true,24,24,48,4,24,4,21,1]];
        call _tick;
        private _blood=[] call ACME_fnc_clinicalClock;
        private _med=[true] call ACME_fnc_clinicalClock;
        _nowTime=130;CBA_missionTime=40;
        [([] call ACME_fnc_clinicalClock)-_blood==120 && {([true] call ACME_fnc_clinicalClock)-_med==120},"4x did not apply to both domains"] call _check;
        _multiplier=2;call _tick;call _tick;
        [([] call ACME_fnc_clinicalClock)-_blood==120 && {count _publications==2},"rate transition jumped time or republished"] call _check;
        _nowTime=160;
        [([] call ACME_fnc_clinicalClock)-_blood==180 && {([true] call ACME_fnc_clinicalClock)-_med==180},"new rate did not carry prior age"] call _check;
        missionNamespace setVariable ["ACME_clinicalTiming",[]];
        call _tick;_nowTime=170;
        [([] call ACME_fnc_clinicalClock)-_blood==190,"wall time did not advance one second per second"] call _check;
    ''')


def test_automatic_y_warmer_requires_blood_and_stays_for_the_saline_flush():
    execute('''
        ACME_fnc_isYLineAccess={(_this select 3)==0};
        ACME_fnc_setVarNet={params ["_unit","_name","_value"];_unit setVariable [_name,_value];};
        private _saline=["ACME_SalineY",100,1,0,true,-1,500,-1,"saline"];
        private _blood=["Blood",300,1,0,true,0,500,-1,"blood"];
        private _rows=createHashMapFromArray [["leftarm",[_saline]]];
        _patient setVariable ["ACM_circulation_IV_Bags",_rows];
        [!([_patient,"leftarm",true,0,true] call ACME_fnc_yAutoWarmer),"saline-only set installed automatic warmer"] call _check;
        _rows set ["leftarm",[_saline,_blood]];
        [!([_patient,"leftarm",true,1,true] call ACME_fnc_yAutoWarmer),"warmer appeared on a neighboring access"] call _check;
        [[_patient,"leftarm",true,0,true] call ACME_fnc_yAutoWarmer,"blood Y did not install a warmer"] call _check;
        _rows set ["leftarm",[_saline]];
        [[_patient,"leftarm",true,0] call ACME_fnc_yAutoWarmer,"saline lost its shared warmer after the blood bag came out"] call _check;
        ACME_fnc_isYLineAccess={false};
        [!([_patient,"leftarm",true,0] call ACME_fnc_yAutoWarmer),"disconnected Y still warmed"] call _check;
    ''')


KIT = '"ACME_IVStartKit_18g"'
NEEDLE = '"ACM_IV_18g"'
CONTENTS = '["ACM_IV_18g","ACM_IV_18g","ACME_NARBOA","ACME_Tegaderm","ACME_SalineLock","ACM_SalineFlush_10"]'


def kit_runtime(stock):
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    recipe = re.search(r'ACME_ivStartKitContents\[\] = \{(.*?)\};', config)[1]
    unpack = adapt(read('ivStartKitUnpack'))
    for native, fixture in (
        ('uniformContainer _unit', '_unit'), ('vestContainer _unit', 'objNull'),
        ('backpackContainer _unit', 'objNull'), ('itemCargo _container', '(_container call _cargoFor)'),
        ('_container canAdd _class', '(_class != _cannotFit)'),
        ('_container addItemCargoGlobal [_kit, -1]', '[_container, _kit, -1] call _adjust'),
        ('_container addItemCargoGlobal [_class, 1]', '[_container, _class, 1] call _adjust'),
        ('_container addItemCargoGlobal [_x, -1]', '[_container, _x, -1] call _adjust'),
        ('_container addItemCargoGlobal [_kit, 1]', '[_container, _kit, 1] call _adjust'),
    ):
        assert native in unpack
        unpack = unpack.replace(native, fixture)
    stock_check = adapt(read('ivStartKitStock')).replace('local _unit', '(!(_unit isEqualTo _remote))')
    stock_check = stock_check.replace('alive _unit', 'true').replace('items _unit', '(_unit call _cargoFor)')
    stock_check = stock_check.replace('getArray (configFile >> "CfgWeapons" >> "ACME_IVStartKit_18g" >> "ACME_ivStartKitContents")', f'[{recipe}]')
    return supply_setup() + f'''
        private _cannotFit="";
        private _remote=objNull;
        private _failSecond=false;
        _medic setVariable ["fixtureCargo",{stock}];
        private _adjust = {{
            params ["_container","_class","_amount"];
            private _cargo=+(_container call _cargoFor);
            private _i=_cargo find _class;
            if (_amount < 0) exitWith {{_cargo deleteAt _i;_container setVariable ["fixtureCargo",_cargo];}};
            if (!(_failSecond && {{_class=={NEEDLE}}} && {{_i>=0}})) then {{
                _cargo pushBack _class;
                _container setVariable ["fixtureCargo",_cargo];
            }};
        }};
        ACME_fnc_ivStartKitStock={{{stock_check}}};
        ACME_fnc_ivStartKitUnpack={{{unpack}}};
    '''


@pytest.mark.parametrize("gauge", [14, 16, 18, 20])
def test_sealed_kit_counts_without_materializing_and_opens_once(gauge):
    selected = f'"ACME_IVStartKit_{gauge}g"'
    execute(kit_runtime(f'[{selected},{selected}]') + f'''
        private _count=[_medic,_patient,{NEEDLE}] call ACME_fnc_treatmentSupplyCount;
        [_count==4 && {{(_medic call _cargoFor) isEqualTo [{selected},{selected}]}}, "counting unsealed a kit or missed a needle"] call _check;
        [[_medic,_patient,"ACM_IV_16g"] call ACME_fnc_treatmentSupplyCount==0, "legacy class issued wrong gauge"] call _check;
        [([_medic,_patient,["ACM_IV_16g"]] call ACME_fnc_treatmentSupplyTake) isEqualTo [], "unrelated debit opened kit"] call _check;
        private _receipt=[_medic,_patient,[{NEEDLE}]] call ACME_fnc_treatmentSupplyTake;
        [count _receipt==4 && {{(_receipt select 2) isEqualTo objNull}}, "worn cargo leaked into network receipt"] call _check;
        private _left={CONTENTS}; _left deleteAt 0;
        [(_medic call _cargoFor) isEqualTo ([{selected}]+_left), "first use changed sealed quantity or lost leftovers"] call _check;
        [([_receipt,false] call ACME_fnc_treatmentSupplyRefund), "commit failed"] call _check;
        [!([_receipt] call ACME_fnc_treatmentSupplyRefund), "replay minted another catheter"] call _check;
    ''')


@pytest.mark.parametrize("class_name", ["ACME_Tegaderm", "ACME_SalineLock", "ACM_SalineFlush_10"])
def test_loose_supply_goes_first_and_rejected_attempt_returns_to_inventory(class_name):
    execute(kit_runtime(f'[{KIT}]') + f'''
        private _item="{class_name}";
        _patient setVariable ["fixtureStock",[_item]];
        [([_medic,_patient,_item] call ACME_fnc_treatmentSupplyCount)==2, "sealed and loose counts did not combine"] call _check;
        private _loose=[_medic,_patient,[_item]] call ACME_fnc_treatmentSupplyTake;
        [(_loose select 0) isEqualTo _patient && {{(_medic call _cargoFor) isEqualTo [{KIT}]}}, "kit opened ahead of loose supply"] call _check;
        [_loose,false] call ACME_fnc_treatmentSupplyRefund;
        private _packed=[_medic,_patient,[_item]] call ACME_fnc_treatmentSupplyTake;
        private _left={CONTENTS};_left deleteAt (_left find _item);
        [(_medic call _cargoFor) isEqualTo _left, "disposable did not take exactly one item"] call _check;
        [_packed] call ACME_fnc_treatmentSupplyRefund;
        [_packed] call ACME_fnc_treatmentSupplyRefund;
        [(_medic call _cargoFor) isEqualTo (_left+[_item]), "refund failed to return exactly one loose supply"] call _check;
    ''')


@pytest.mark.parametrize("failure", ['_cannotFit="ACM_SalineFlush_10";', '_failSecond=true;'])
def test_failed_materialization_keeps_kit_and_existing_stock(failure):
    execute(kit_runtime(f'[{KIT},"ACME_Tegaderm"]') + failure + f'''
        [([_medic,"ACME_NARBOA",false] call ACME_fnc_ivStartKitUnpack) isEqualTo objNull, "failed unpack reported success"] call _check;
        [(_medic call _cargoFor) isEqualTo ["ACME_Tegaderm",{KIT}], "rollback lost the kit or changed loose stock"] call _check;
        _cannotFit="";_failSecond=false;
        [([_medic,"ACME_NARBOA",false] call ACME_fnc_ivStartKitUnpack) isEqualTo _medic, "BOA could not open the kit"] call _check;
        [(_medic call _cargoFor) isEqualTo (["ACME_Tegaderm"]+{CONTENTS}), "BOA use should keep all supplies, including the reusable band"] call _check;
    ''')


def test_frozen_or_remote_inventory_does_not_fund_treatment():
    execute(kit_runtime(f'[{KIT}]') + f'''
        _medic setVariable ["ACME_persistenceFrozen",true];
        [([_medic,_patient,[{NEEDLE}]] call ACME_fnc_treatmentSupplyTake) isEqualTo [], "frozen inventory was mutated"] call _check;
        _medic setVariable ["ACME_persistenceFrozen",false];
        _remote=_medic;
        [([_medic,_patient,{NEEDLE}] call ACME_fnc_treatmentSupplyCount)==0, "remote kit supplied unavailable materials"] call _check;
        [([_medic,_patient,[{NEEDLE}]] call ACME_fnc_treatmentSupplyTake) isEqualTo [] && {{(_medic call _cargoFor) isEqualTo [{KIT}]}}, "remote kit was opened"] call _check;
    ''')


def test_inventory_and_tray_selection_have_no_unpack_hook():
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    assert 'registerIVStartKitRuntime' not in config
    assert 'registerIVStartKitRuntime' not in read('postInit')
    for name in ('ivMinigameGrabBand', 'ivMinigameGrabNeedle', 'ivFinishGrab'):
        source = read(name)
        assert 'ivStartKitUnpack' not in source
        assert 'treatmentSupplyTake' not in source
    assert read('ivMinigameClick').index('ivStartKitUnpack') > read('ivMinigameClick').index('case "band"')
    assert read('ivMinigameInsertStart').index('treatmentSupplyTake') < read('ivMinigameInsertStart').index('ctrlCreate')
    assert 'ACME_IV_InsFunded' in read('ivMinigameSaveState')
    assert 'ACME_IV_InsFunded' in read('ivMinigameRestoreState')
