"""Execute production cooler persistence, with native cargo/CBA/issue transport as boundaries.

These are serialization and funding regressions, not an Arma savegame or network test.
"""
import re

import pytest

from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import F, adapt, execute


def code(name):
    text = (F / f'fn_{name}.sqf').read_text()
    text = text.replace('canSuspend', 'false').replace('serverTime', '_serverTime')
    text = text.replace('local _holder', 'true')
    text = text.replace('typeOf _holder', '(_holder getVariable ["class", ""])')
    text = text.replace('_holder isKindOf "CAManBase"', 'false')
    text = text.replace('magazinesAmmoCargo _x', '(_x getVariable ["native",[]])')
    text = text.replace('itemCargo _holder', '(_holder getVariable ["cargo",[]])')
    text = text.replace('clearItemCargoGlobal _holder;', '_holder setVariable ["cargo",[]];')
    text = text.replace('_holder addItemCargoGlobal [_x,1];', '[_holder,_x] call _addItem;')
    text = text.replace('_holder addItemCargoGlobal [_x select 0,1];', '[_holder,_x select 0] call _addItem;')
    text = text.replace('getNumber (configFile >> "CfgWeapons" >> _base >> "ACME_coolerColdChainTime")', '([_base] call _chain)')
    text = text.replace('isClass (configFile >> "CfgWeapons" >> _bag)', '(_bag in _bags)')
    # VM does not implement finite. Retain scalar validation/ranges, adapt only that engine primitive.
    text = re.sub(r'\bfinite (\([^\n]*?\)|_\w+)', r'(\1 call _finite)', text)
    return adapt(map_defaults(text))


def setup():
    return r'''
    private _serverTime=10000;
    private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    private _bags=["ACM_BloodBag_ON_500","ACM_BloodBag_A_500","ACM_FreshBloodBag_250_7","ACM_BloodBag_ON_1000"];
    private _chain={params ["_base"];[7200,5400,10800] select (["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"] find _base)};
    private _addItem={params ["_o","_class"];private _a=+(_o getVariable ["cargo",[]]);_a pushBack _class;_o setVariable ["cargo",_a];};
    _medic setVariable ["native",[["ACME_CoolerCarrier_CSWB1U",37]]];
    _medic setVariable ["rows",[["save1",["ACME_BloodCooler_CSWB1U",2000,[["ACM_BloodBag_ON_500",31]],9990]]]];
    _medic setVariable ["ACME_inventoryPending",createHashMap];
    _medic setVariable ["ACME_inventoryEscrow",createHashMap];
    _medic setVariable ["ACME_coolerRestoreJournal",[]];
    missionNamespace setVariable ["ACME_inventoryLedgerIndex",createHashMapFromArray [["cooler:save1",37]]];
    missionNamespace setVariable ["ACME_coolerThawRateInside",0.2];
    private _issueCount=0;private _issued=[];private _issueAllowed=true;
    private _removeAllowed=true;private _lyingRemove=false;
    ACME_fnc_coolerRows={params ["_o"];_o getVariable ["rows",[]]};
    ACME_fnc_inventoryLedgerNative={params ["_o"];((_o getVariable ["native",[]]) select {(_x select 1)>0 && {(_x select 1)<65535}}) apply {[_x select 1,"cooler"]}};
    ACME_fnc_coolerIssue={params ["_o","_base","_state","_consume"];
        if (!_issueAllowed) exitWith {""};
        _issueCount=_issueCount+1;private _sid=format ["new%1",_issueCount];
        _issued pushBack [_sid,_base,_state,_consume];_sid
    };
    ace_common_fnc_removeSpecificMagazine={params ["_o","_class","_token"];
        if (!_removeAllowed) exitWith {false};
        if (_lyingRemove) exitWith {true};
        private _a=+(_o getVariable ["native",[]]);private _i=_a findIf {_x isEqualTo [_class,_token]};
        if (_i<0) exitWith {false};_a deleteAt _i;_o setVariable ["native",_a];true
    };
    ACME_fnc_coolerBoxReconcile={params ["_o","_now"];[_o getVariable ["ACME_boxCoolerState",[]],_now] call ACME_fnc_coolerAdvance};
    private _saved=[1,"holder",[["save1",37,"ACME_BloodCooler_CSWB1U",8000,[["ACM_BloodBag_ON_500",33]]]]];
    ''' + '\n'.join('ACME_fnc_' + n + '={' + code(n) + '};' for n in [
        'coolerBagVolume', 'coolerAdvance', 'coolerSnapshotValid', 'coolerSnapshot', 'coolerRestore', 'coolerPersistenceInit'])


def test_snapshot_advances_exposure_without_mutating_live_rows_and_has_no_absolute_clock():
    execute(setup() + r'''
    private _before=str (_medic getVariable "rows");
    private _result=[_medic,"holder"] call ACME_fnc_coolerSnapshot;
    [_result isEqualTo _saved,"snapshot lost elapsed warming or normalized age"] call _check;
    [str (_medic getVariable "rows")==_before,"snapshot mutated source state"] call _check;
    ''')


@pytest.mark.parametrize('pending', ['allocation', 'escrow', 'unadopted', 'duplicate', 'box_request', 'mutation_intent', 'restore_funding', 'pickup_actor', 'pickup_source'])
def test_snapshot_refuses_unsettled_or_unidentified_custody(pending):
    action = {
        'allocation': '_medic setVariable ["ACME_inventoryPending",createHashMapFromArray [["cooler:new",["cooler"]]]];',
        'escrow': '_medic setVariable ["ACME_inventoryEscrow",createHashMapFromArray [["use",[37,[],"cooler"]]]];',
        'unadopted': '_medic setVariable ["rows",[]];',
        'duplicate': '_medic setVariable ["native",[["ACME_CoolerCarrier_CSWB1U",37],["ACME_CoolerCarrier_CSWB1U",37]]];',
        'box_request': '_medic setVariable ["ACME_coolerBoxRequests",createHashMapFromArray [["pack",["pack"]]]];',
        'mutation_intent': '_medic setVariable ["ACME_coolerIntents",createHashMapFromArray [["edit",["mutationResult"]]]];',
        'restore_funding': '_medic setVariable ["ACME_coolerRestoreJournal",["snapshot",0,[],false,0,0]];_medic setVariable ["native",[]];_medic setVariable ["rows",[]];',
        'pickup_actor': '_medic setVariable ["ACME_coolerTake4UPending",["pending"]];',
        'pickup_source': '_medic setVariable ["ACME_coolerTake4UClaims",createHashMapFromArray [["request",true]]];',
    }[pending]
    execute(setup() + action + r'''
    [([_medic,"holder"] call ACME_fnc_coolerSnapshot) isEqualTo [],"unsafe snapshot silently omitted a cooler"] call _check;
    ''')


def test_empty_settled_holder_has_valid_empty_snapshot():
    execute(setup() + r'''
    _medic setVariable ["native",[]];_medic setVariable ["rows",[]];
    [([_medic,"holder"] call ACME_fnc_coolerSnapshot) isEqualTo [1,"holder",[]],"empty holder confused with failure"] call _check;
    ''')


@pytest.mark.parametrize('bad', [
    '[]', '[2,"holder",[]]', '[1,"wrong",[]]', '[1,"holder",[nil]]',
    '[1,"holder",[["save1",37,"ACME_BloodCooler_CSWB1U",-1,[]]]]',
    '[1,"holder",[["save1",0,"ACME_BloodCooler_CSWB1U",0,[]]]]',
    '[1,"holder",[["save1",37.5,"ACME_BloodCooler_CSWB1U",0,[]]]]',
    '[1,"holder",[["save1",37,"ACME_BloodCooler_CSWB1U",0,[["ACM_BloodBag_ON_1000",0]]]]]',
    '[1,"holder",[["save1",37,"ACME_BloodCooler_CSWB1U",0,[["ACM_BloodBag_ON_500",-1]]]]]',
    '[1,"holder",[["save1",37,"ACME_BloodCooler_CSWB1U",0,[["not_blood",0]]]]]',
    '[1,"box",[]]', '[1,"box",[["box",37,"ACME_BloodCooler_CSWB1U",0,[]]]]',
])
def test_malformed_snapshot_rejected_before_any_native_mutation(bad):
    execute(setup() + f'private _bad={bad};' + r'''
    private _before=str (_medic getVariable "native");
    [!([_bad] call ACME_fnc_coolerSnapshotValid),"malformed metadata validated"] call _check;
    [!([_medic,_bad] call ACME_fnc_coolerRestore),"malformed metadata restored"] call _check;
    [str (_medic getVariable "native")==_before && {_issueCount==0},"invalid restore mutated inventory"] call _check;
    ''')


def test_complete_payload_binding_preflight_prevents_partial_removal():
    execute(setup() + r'''
    private _second=["save2",99,"ACME_BloodCooler_CSWB2U",200,[]];
    (_saved select 2) pushBack _second;
    private _before=str (_medic getVariable "native");
    [!([_medic,_saved] call ACME_fnc_coolerRestore),"missing second native tuple accepted"] call _check;
    [str (_medic getVariable "native")==_before && {_issueCount==0},"partial inventory removal before binding preflight"] call _check;
    ''')


def test_restore_rebases_clock_preserves_exposure_and_remints_only_after_exact_funding():
    execute(setup() + r'''
    _serverTime=100;
    [([_medic,_saved] call ACME_fnc_coolerRestore),"valid restore failed"] call _check;
    [(_medic getVariable "native") isEqualTo [] && {_issueCount==1},"source carrier not exchanged exactly once"] call _check;
    private _i=_issued select 0;
    [(_i select 0)!="save1" && {!(_i select 3)},"saved identity reused or base item consumed"] call _check;
    [(_i select 2) isEqualTo ["ACME_BloodCooler_CSWB1U",-7900,[["ACM_BloodBag_ON_500",33]],100],"restart rebase refreshed state"] call _check;
    [([_medic,_saved] call ACME_fnc_coolerRestore) && {_issueCount==1},"same application replay reminted cooler"] call _check;
    ''')


def test_intentional_full_saved_loadout_reapplication_is_a_new_funded_application():
    execute(setup() + r'''
    [_medic,_saved] call ACME_fnc_coolerRestore;
    _medic setVariable ["native",[["ACME_CoolerCarrier_CSWB1U",37]]];
    [([_medic,_saved] call ACME_fnc_coolerRestore) && {_issueCount==2},"new native loadout application rejected"] call _check;
    [(_medic getVariable "native") isEqualTo [],"new source copy remained alongside replacement"] call _check;
    ''')


def test_failed_issue_retains_funding_and_retry_applies_offline_age_once():
    execute(setup() + r'''
    _issueAllowed=false;
    [!([_medic,_saved,600] call ACME_fnc_coolerRestore),"failed enqueue reported success"] call _check;
    [(_medic getVariable "native") isEqualTo [] && {_issueCount==0},"failed funding exchange wrong"] call _check;
    _serverTime=10100;_issueAllowed=true;
    [([_medic,_saved,600] call ACME_fnc_coolerRestore) && {_issueCount==1},"funded retry failed"] call _check;
    private _s=(_issued select 0) select 2;
    [((_s select 2) select 0) select 1==153,"offline time double-counted or lost"] call _check;
    [(_s select 1)==1400 && {(_s select 3)==10000},"funded receipt was rebased/rejuvenated during retry"] call _check;
    ''')


@pytest.mark.parametrize('epoch', ['ACME_equipmentKitEpoch', 'ACME_providerLocalityEpoch'])
def test_removed_funding_cannot_resume_into_a_later_kit_or_locality_period(epoch):
    execute(setup() + r'''
    _issueAllowed=false;
    [!([_medic,_saved] call ACME_fnc_coolerRestore),"failed issue did not retain funding"] call _check;
    private _evidence=str (_medic getVariable "ACME_coolerRestoreJournal");
    _issueAllowed=true;
    ''' + f'_medic setVariable ["{epoch}",1];' + r'''
    [!([_medic,_saved] call ACME_fnc_coolerRestore),"retired funding entered a successor period"] call _check;
    [_issueCount==0 && {str (_medic getVariable "ACME_coolerRestoreJournal")==_evidence},"retired funding was reminted or erased"] call _check;
    ''')


def test_complete_journal_does_not_block_intentional_source_funded_new_kit_restore():
    execute(setup() + r'''
    [_medic,_saved] call ACME_fnc_coolerRestore;
    _medic setVariable ["ACME_equipmentKitEpoch",1];
    _medic setVariable ["ACME_providerLocalityEpoch",1];
    _medic setVariable ["native",[["ACME_CoolerCarrier_CSWB1U",37]]];
    [([_medic,_saved] call ACME_fnc_coolerRestore) && {_issueCount==2},"new funded kit restore borrowed old admission"] call _check;
    private _j=_medic getVariable "ACME_coolerRestoreJournal";
    [(_j select 4)==1 && {(_j select 5)==1},"new application did not bind current admission"] call _check;
    ''')


@pytest.mark.parametrize('mode', ['false', 'lying'])
def test_failed_native_removal_cannot_fund_issue(mode):
    switch = '_removeAllowed=false;' if mode == 'false' else '_lyingRemove=true;'
    execute(setup() + switch + r'''
    [!([_medic,_saved] call ACME_fnc_coolerRestore),"unproven removal succeeded"] call _check;
    [_issueCount==0 && {count (_medic getVariable "native")==1},"unproven removal minted cooler"] call _check;
    ''')


@pytest.mark.parametrize('offline', ['-1', '"bad"', '1e10'])
def test_invalid_offline_duration_does_not_touch_inventory(offline):
    execute(setup() + f'[!([_medic,_saved,{offline}] call ACME_fnc_coolerRestore),"invalid offline duration accepted"] call _check;' + r'''
    [_issueCount==0 && {count (_medic getVariable "native")==1},"invalid offline duration removed funding"] call _check;
    ''')


def test_offline_age_crosses_coolant_expiry_only_for_elapsed_warm_tail():
    execute(setup() + r'''
    ((_saved select 2) select 0) set [3,7000];
    [_medic,_saved,600] call ACME_fnc_coolerRestore;
    private _s=(_issued select 0) select 2;
    [abs ((((_s select 2) select 0) select 1)-113)<0.001,"offline tail charged the cold portion"] call _check;
    ''')


def test_box_import_is_idempotent_preserves_nonblood_and_rejects_live_ledger_box():
    execute(setup() + r'''
    private _box=_patient;
    _box setVariable ["class","ACME_BloodCoolerBox_CSWB1U"];
    _box setVariable ["cargo",["OtherItem","ACM_BloodBag_A_500"]];
    private _save=[1,"box",[["boxsave",0,"ACME_BloodCooler_CSWB1U",8000,[["ACM_BloodBag_ON_500",33]]]]];
    [([_box,_save,600] call ACME_fnc_coolerRestore),"box import failed"] call _check;
    [(_box getVariable "cargo") isEqualTo ["OtherItem","ACM_BloodBag_ON_500"],"box cargo lost nonblood or duplicated blood"] call _check;
    private _before=str (_box getVariable "ACME_boxCoolerState");_serverTime=10200;
    [([_box,_save,600] call ACME_fnc_coolerRestore),"box replay failed"] call _check;
    [str (_box getVariable "ACME_boxCoolerState")==_before,"box replay reset clocks"] call _check;
    _box setVariable ["ACME_boxCoolerToken",77];
    [!([_box,_save] call ACME_fnc_coolerRestore),"live ledger box overwritten"] call _check;
    ''')


@pytest.mark.parametrize('flag', ['ACME_coolerPacking', 'ACME_coolerRetired'])
def test_box_snapshot_refuses_packing_source_and_retired_shell(flag):
    execute(setup() + f'_patient setVariable ["{flag}",true];' + r'''
    _patient setVariable ["class","ACME_BloodCoolerBox_CSWB1U"];
    _patient setVariable ["ACME_boxCoolerState",["ACME_BloodCooler_CSWB1U",2000,[["ACM_BloodBag_ON_500",31]],9990]];
    private _before=str (_patient getVariable "ACME_boxCoolerState");
    [([_patient,"box"] call ACME_fnc_coolerSnapshot) isEqualTo [],"transaction source or retired shell exported"] call _check;
    [str (_patient getVariable "ACME_boxCoolerState")==_before,"blocked export advanced transaction state"] call _check;
    ''')


def test_failed_box_cargo_readback_restores_old_cargo_and_does_not_publish_success():
    execute(setup() + r'''
    private _box=_patient;
    _box setVariable ["class","ACME_BloodCoolerBox_CSWB1U"];
    _box setVariable ["cargo",["OtherItem","ACM_BloodBag_A_500"]];
    private _nativeAdd=_addItem;
    _addItem={params ["_o","_class"];if (_class!="ACM_BloodBag_ON_500") then {_this call _nativeAdd;};};
    private _save=[1,"box",[["boxsave",0,"ACME_BloodCooler_CSWB1U",8000,[["ACM_BloodBag_ON_500",33]]]]];
    [!([_box,_save] call ACME_fnc_coolerRestore),"failed box placement reported success"] call _check;
    [(_box getVariable "cargo") isEqualTo ["OtherItem","ACM_BloodBag_A_500"],"old box cargo was not recovered"] call _check;
    [isNil {_box getVariable "ACME_boxCoolerState"},"failed placement published restored state"] call _check;
    ''')


def test_cba_hooks_register_once_and_roundtrip_the_versioned_metadata():
    execute(setup() + r'''
    private _hooks=createHashMap;
    CBA_fnc_addEventHandler={_hooks set [_this select 0,_this select 1];};
    call ACME_fnc_coolerPersistenceInit;call ACME_fnc_coolerPersistenceInit;
    [count _hooks==4,"persistence hooks duplicated"] call _check;
    ACME_fnc_persistenceSnapshot={params ["_o"];[[],createHashMapFromArray [["ACME_checkpointLease_v1",""],["ACME_coolers_v1",[_o,"holder"] call ACME_fnc_coolerSnapshot],["ACME_inventory_v1",[1,[]]],["ACME_equipment_v1",[1,[],[],[],[]]],["ACME_blood_v1",[1,[]]]]]};
    ACME_fnc_inventorySnapshotValid={true};ACME_fnc_equipmentSnapshotValid={true};ACME_fnc_bloodExposureSnapshotValid={true};
    ACME_fnc_persistenceRestoreExtended={params ["_o","_m"];private _ok=[_o,_m get "ACME_coolers_v1"] call ACME_fnc_coolerRestore;_o setVariable ["ACME_coolerLastRestoreOK",_ok];_ok};
    private _metadata=createHashMap;
    [_medic,[],_metadata] call (_hooks get "CBA_loadoutGet");
    [(_metadata get "ACME_coolers_v1") isEqualTo _saved,"CBA get did not preserve metadata"] call _check;
    [_medic,[],_metadata] call (_hooks get "CBA_loadoutSet");
    [_medic getVariable ["ACME_coolerLastRestoreOK",false],"CBA set did not restore"] call _check;
    [_issueCount==1,"CBA set did not fund one replacement"] call _check;
    ''')


@pytest.mark.parametrize('invalid_token', [0, 65535])
def test_default_or_zero_ammo_cooler_is_not_saved_as_empty_inventory(invalid_token):
    execute(setup() + f'''
    _medic setVariable ["native",[["ACME_CoolerCarrier_CSWB1U",{invalid_token}]]];
    _medic setVariable ["rows",[]];
    [([_medic] call ACME_fnc_coolerSnapshot) isEqualTo [],"unbound native cooler disappeared from save metadata"] call _check;
    ''')
