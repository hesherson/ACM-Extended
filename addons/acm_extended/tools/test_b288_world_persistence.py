"""Production checkpoint/fridge/loose-blood persistence with explicit engine boundaries.

Native inventory, network transport, mission date and callbacks are stand-ins;
these do not certify an Arma save/restart or multiplayer transport.
"""
import re

import pytest

from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import F, adapt, execute


def production(name):
    s = (F / f'fn_{name}.sqf').read_text()
    s = s.replace('canSuspend', 'false').replace('isServer', '_server')
    s = s.replace('serverTime', '_serverTime').replace('diag_tickTime', '_nowTime')
    s = s.replace('(dateToNumber date)', '_gameDate')
    s = s.replace('_unit isEqualType objNull', '_unit isEqualType uiNamespace')
    s = s.replace('local _unit', '_local').replace('local _holder', '_local')
    s = s.replace('_unit isKindOf "CAManBase"', 'true').replace('_holder isKindOf "CAManBase"', 'false')
    s = s.replace('getUnitLoadout _unit', '(_unit getVariable ["nativeLoadout",[]])')
    s = s.replace('_fridge getVariable ["ACME_bf_restoreRestockDelayMins",_intervalMins]', '([_fridge,"ACME_bf_restoreRestockDelayMins",_intervalMins] call _nativeVariable)')
    s = s.replace('itemCargo _holder', '(_holder getVariable ["cargo",[]])')
    s = s.replace('netId _holder', '"holder"').replace('owner _holder', '7')
    s = s.replace('isClass (configFile >> "CfgWeapons" >> _class)', '(_class in ["ACM_BloodBag_ON_500","ACM_BloodBag_A_500"])')
    s = re.sub(r'\bfinite (\([^\n]*?\)|_\w+)', r'(\1 call _finite)', s)
    s = re.sub(r'values (\([^;\n]+? getVariable \[[^\n]+?\]\))', r'(\1 call _values)', s)
    s = re.sub(r'values (_\w+)', r'(\1 call _values)', s)
    return adapt(map_defaults(s))


def setup():
    return r'''
    private _server=true;private _local=true;private _serverTime=100;private _gameDate=0.5;
    private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    private _nativeVariable={params ["_o","_k","_default"];if (isNil {_o getVariable _k}) then {_default} else {_o getVariable _k}};
    private _values={private _m=_this;(keys _m) apply {_m get _x}};
    private _pfhs=[];private _removed=[];private _events=[];
    CBA_fnc_addPerFrameHandler={_pfhs pushBack _this;count _pfhs};
    CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
    CBA_fnc_serverEvent={_events pushBack _this;};
    CBA_fnc_targetEvent={_events pushBack _this;};
    private _hooks=createHashMap;
    CBA_fnc_addEventHandler={_hooks set [_this select 0,_this select 1];};
    ACME_fnc_persistenceJournalsReady={true};
    ACME_fnc_coolerBagVolume={params ["_c"];if (_c in ["ACM_BloodBag_ON_500","ACM_BloodBag_A_500"]) then {500} else {0}};
    ACME_fnc_coolerSnapshot={params ["_u"];_u getVariable ["coolers",[1,"holder",[]]]};
    ACME_fnc_inventorySnapshot={params ["_u"];_u getVariable ["inventory",[1,[]]]};
    ACME_fnc_equipmentSnapshot={params ["_u"];_u getVariable ["equipment",[1,[],[],[],[]]]};
    ACME_fnc_coolerSnapshotValid={params ["_s"];count _s==3};
    ACME_fnc_inventorySnapshotValid={params ["_s"];count _s==2};
    ACME_fnc_equipmentSnapshotValid={params ["_s"];count _s==5};
    private _restores=[];
    ACME_fnc_inventoryRestore={_restores pushBack "inventory";true};
    ACME_fnc_coolerRestore={_restores pushBack "cooler";true};
    ACME_fnc_equipmentRestore={_restores pushBack "equipment";true};
    ACME_fnc_setVarNet={(_this select 0) setVariable [_this select 1,_this select 2];};
    ACME_fnc_bloodFridgeSetup={params ["_f"];_f setVariable ["ACME_bf_setup",true];};
    _medic setVariable ["nativeLoadout",[[],[],[],[],[],[],[],[],[],[]]];
    _medic setVariable ["ACME_bloodFridge",true];
    _medic setVariable ["ACME_bf_setup",true];
    _medic setVariable ["ACME_bf_stock",[["ACM_BloodBag_ON_500",2]]];
    _medic setVariable ["ACME_bf_default",[["ACM_BloodBag_ON_500",6]]];
    _medic setVariable ["ACME_bf_restock",true];
    _medic setVariable ["ACME_bf_regenMins",120];
    _medic setVariable ["ACME_bf_lastRestockGH",4382];
    _medic setVariable ["cargo",[]];
    private _savedFridge=[1,[["ACM_BloodBag_ON_500",2]],[["ACM_BloodBag_ON_500",6]],true,120,60];
    ''' + '\n'.join('ACME_fnc_' + n + '={' + production(n) + '};' for n in [
        'bloodFridgeSnapshotValid', 'bloodFridgeSnapshot', 'bloodFridgeRestore', 'bloodFridgeTick',
        'bloodExposureSnapshotValid', 'bloodExposureSnapshot', 'bloodExposureRestore',
        'bloodPersistenceRequest', 'persistenceReady', 'persistenceSnapshot', 'persistenceFingerprint', 'persistenceCaptureValid', 'persistenceLocalCheckpoint', 'persistenceCheckpoint', 'persistenceRestoreExtended', 'persistenceBarrier',
        'coolerPersistenceInit'])


def test_fridge_roundtrip_rebases_remaining_schedule_and_replay_never_refills():
    execute(setup() + r'''
    [([_medic] call ACME_fnc_bloodFridgeSnapshot) isEqualTo _savedFridge,"stock/restock remaining was not normalized"] call _check;
    _gameDate=0;
    [([_patient,_savedFridge] call ACME_fnc_bloodFridgeRestore),"fridge import failed"] call _check;
    [_patient getVariable "ACME_bf_lastRestockGH"==0 && {_patient getVariable "ACME_bf_restoreRestockDelayMins"==60},"fridge schedule reused old mission date"] call _check;
    _patient setVariable ["ACME_bf_stock",[["ACM_BloodBag_ON_500",1]]];
    [([_patient,_savedFridge] call ACME_fnc_bloodFridgeRestore),"fridge replay failed"] call _check;
    [(_patient getVariable "ACME_bf_stock") isEqualTo [["ACM_BloodBag_ON_500",1]],"fridge replay refilled consumed stock"] call _check;
    ''')


@pytest.mark.parametrize('block', [
    '_medic setVariable ["ACME_bf_takers",createHashMapFromArray [["player",[]]]];',
    '_medic setVariable ["ACME_bf_grants",createHashMapFromArray [["grant",[objNull,[],"bag","pending",0]]]];',
])
def test_fridge_refuses_unresolved_grants_even_after_theatre_lease(block):
    execute(setup() + block + r'''
    [([_medic] call ACME_fnc_bloodFridgeSnapshot) isEqualTo [],"unsettled fridge saved"] call _check;
    [!([_medic,_savedFridge] call ACME_fnc_bloodFridgeRestore),"unsettled fridge overwritten"] call _check;
    ''')


@pytest.mark.parametrize('bad', [
    '[]', '[2,[],[],true,120,60]', '[1,[],[],true,-2,60]',
    '[1,[],[],true,120,-1]', '[1,[["NotBlood",1]],[],true,120,60]',
    '[1,[["ACM_BloodBag_ON_500",-1]],[],true,120,60]',
    '[1,[["ACM_BloodBag_ON_500",1],["ACM_BloodBag_ON_500",2]],[],true,120,60]',
    '[1,[],[],"yes",120,60]',
])
def test_fridge_malformed_snapshot_cannot_change_live_state(bad):
    execute(setup() + f'private _bad={bad};' + r'''
    private _before=str (_medic getVariable "ACME_bf_stock");
    [!([_medic,_bad] call ACME_fnc_bloodFridgeRestore),"invalid fridge data accepted"] call _check;
    [str (_medic getVariable "ACME_bf_stock")==_before,"invalid data changed stock"] call _check;
    ''')


def test_fridge_explicit_offline_game_time_can_complete_one_refill():
    execute(setup() + r'''
    [([_patient,_savedFridge,90] call ACME_fnc_bloodFridgeRestore),"offline import failed"] call _check;
    [(_patient getVariable "ACME_bf_stock") isEqualTo [["ACM_BloodBag_ON_500",6]],"offline due refill not applied"] call _check;
    [_patient getVariable "ACME_bf_restoreRestockDelayMins"==120,"due refill retained stale delay"] call _check;
    ''')


def test_loose_blood_roundtrip_retains_age_and_has_no_raw_timestamp():
    execute(setup() + r'''
    _medic setVariable ["cargo",["ACM_BloodBag_ON_500","ACM_BloodBag_ON_500"]];
    _medic setVariable ["ACME_bloodExposure",[[["ACM_BloodBag_ON_500",500,700],["ACM_BloodBag_ON_500",500,30]],90]];
    private _s=[_medic] call ACME_fnc_bloodExposureSnapshot;
    [_s isEqualTo [1,[["ACM_BloodBag_ON_500",710],["ACM_BloodBag_ON_500",40]]],"loose age export lost elapsed time"] call _check;
    _serverTime=1;
    [([_medic,_s,20] call ACME_fnc_bloodExposureRestore),"loose age import failed"] call _check;
    private _row=(missionNamespace getVariable "ACME_ccByHolder") get "holder";
    private _ages=(_row select 0) apply {_x select 2};_ages sort true;
    [_ages isEqualTo [60,730] && {((_row select 0) findIf {(_x select 3)!=1})<0},"restart refreshed loose blood"] call _check;
    _serverTime=5;
    [([_medic,_s,20] call ACME_fnc_bloodExposureRestore),"loose replay failed"] call _check;
    [((_medic getVariable "ACME_bloodExposure") select 1)==1,"replay rebased age twice"] call _check;
    ''')


def test_loose_blood_import_preserves_older_existing_same_class_age():
    execute(setup() + r'''
    _medic setVariable ["cargo",["ACM_BloodBag_ON_500"]];
    missionNamespace setVariable ["ACME_ccByHolder",createHashMapFromArray [["holder",[[["ACM_BloodBag_ON_500",500,1000,90]],[]]]]];
    [([_medic,[1,[["ACM_BloodBag_ON_500",1]]]] call ACME_fnc_bloodExposureRestore),"valid loose import failed"] call _check;
    [((((_medic getVariable "ACME_bloodExposure") select 0) select 0) select 2)==1010,"same-class import made older blood fresh"] call _check;
    ''')


@pytest.mark.parametrize('case', ['untracked', 'count', 'seed'])
def test_loose_blood_snapshot_defers_unknown_or_inflight_inventory(case):
    body = {
        'untracked': '',
        'count': '_medic setVariable ["ACME_bloodExposure",[[],100]];',
        'seed': '_medic setVariable ["ACME_bloodSeedPending",createHashMapFromArray [["seed",true]]];',
    }[case]
    execute(setup() + '_medic setVariable ["cargo",["ACM_BloodBag_ON_500"]];' + body + r'''
    [([_medic] call ACME_fnc_bloodExposureSnapshot) isEqualTo [],"unknown loose bag saved as fresh"] call _check;
    ''')


def test_checkpoint_retries_and_returns_native_and_metadata_from_one_settled_read():
    execute(setup() + r'''
    _medic setVariable ["inventory",[]];
    private _done=[];
    private _request=[_medic,{_done=_this;},["adapter"],30] call ACME_fnc_persistenceCheckpoint;
    [_request==1 && {count _pfhs==1},"checkpoint not scheduled"] call _check;
    private _p=_pfhs select 0;
    [(_p select 2),1] call (_p select 0);
    [_done isEqualTo [] && {_removed isEqualTo []},"busy checkpoint wrote an empty save"] call _check;
    _medic setVariable ["inventory",[1,[]]];
    [(_p select 2),1] call (_p select 0);
    [(_done select 0) && {(_done select 2) isEqualTo ["adapter"]} && {_removed isEqualTo [1]},"settled callback failed"] call _check;
    private _pair=_done select 1;
    [(_pair select 0) isEqualTo (_medic getVariable "nativeLoadout"),"callback lost native inventory"] call _check;
    [((_pair select 1) get "ACME_checkpoint_v1") isEqualTo [1,true],"successful snapshot missing readiness marker"] call _check;
    ''')


@pytest.mark.parametrize('change', ['kit', 'locality', 'timeout'])
def test_checkpoint_failure_never_returns_empty_success(change):
    body = {'kit': '_medic setVariable ["ACME_equipmentKitEpoch",1];',
            'locality': '_local=false;', 'timeout': '_nowTime=_nowTime+31;'}[change]
    execute(setup() + r'''
    _medic setVariable ["inventory",[]];private _done=[];
    [_medic,{_done=_this;},[],30] call ACME_fnc_persistenceCheckpoint;
    private _p=_pfhs select 0;
    ''' + body + r'''
    [(_p select 2),1] call (_p select 0);
    [!(_done select 0) && {(_done select 1) isEqualTo []} && {(_done select 3)!=""},"failed checkpoint returned success"] call _check;
    ''')


def test_atomic_snapshot_refuses_native_change_during_export():
    execute(setup() + r'''
    ACME_fnc_inventorySnapshot={params ["_u"];_u setVariable ["nativeLoadout",["changed"]];[1,[]]};
    [([_medic] call ACME_fnc_persistenceSnapshot) isEqualTo [],"mixed revision checkpoint accepted"] call _check;
    ''')


@pytest.mark.parametrize('state', ['awaitBegin', 'ready', 'stopping'])
def test_server_readiness_refuses_nonterminal_delivery_to_this_patient(state):
    execute(setup() + f'private _state="{state}";' + r'''
    private _batch=[[_medic,"drug",0,"dose"],[],[],"pending"];
    private _j=createHashMapFromArray [["medic",_patient],["state",_state],["batches",createHashMapFromArray [["batch",_batch]]]];
    missionNamespace setVariable ["ACME_syringeDeliveries",createHashMapFromArray [["request",_j]]];
    [!([_medic] call ACME_fnc_persistenceReady),"unsettled patient decision considered saveable"] call _check;
    ''')


def test_terminal_client_and_settled_server_sessions_do_not_block_every_future_save():
    execute(setup() + r'''
    _medic setVariable ["ACME_syringeDeliverySessions",createHashMapFromArray [["s",[0,"","settled"]]]];
    missionNamespace setVariable ["ACME_syringeDeliveryClientSessions",createHashMapFromArray [["s",[_medic,"",0,0,"terminal"]]]];
    [([_medic] call ACME_fnc_persistenceReady),"terminal history blocked all later saves"] call _check;
    ''')


def test_cba_readiness_marker_refuses_failed_partial_metadata_before_any_restore():
    execute(setup() + r'''
    call ACME_fnc_coolerPersistenceInit;call ACME_fnc_coolerPersistenceInit;
    [count _hooks==4,"persistence hooks duplicated"] call _check;
    private _m=createHashMap;
    _medic setVariable ["equipment",[]];
    [_medic,_medic getVariable "nativeLoadout",_m] call (_hooks get "CBA_loadoutGet");
    [(_m get "ACME_checkpoint_v1") isEqualTo [1,false],"busy CBA save not marked invalid"] call _check;
    [_medic,[],_m] call (_hooks get "CBA_loadoutSet");
    [!(_medic getVariable "ACME_persistenceLastRestoreOK") && {_restores isEqualTo []},"invalid composite partially restored"] call _check;
    ''')


def test_legacy_b287_cooler_only_metadata_still_restores():
    execute(setup() + r'''
    call ACME_fnc_coolerPersistenceInit;
    private _m=createHashMapFromArray [["ACME_coolers_v1",[1,"holder",[]]]];
    [_medic,[],_m] call (_hooks get "CBA_loadoutSet");
    [_medic getVariable "ACME_persistenceLastRestoreOK" && {_restores isEqualTo ["cooler"]},"legacy cooler metadata rejected"] call _check;
    ''')


def test_restore_retries_staged_metadata_without_reapplying_native_kit():
    execute(setup() + r'''
    private _attempt=0;
    ACME_fnc_equipmentRestore={_attempt=_attempt+1;_attempt>1};
    private _m=createHashMapFromArray [["ACME_checkpoint_v1",[1,true]],["ACME_coolers_v1",[1,"holder",[]]],["ACME_inventory_v1",[1,[]]],["ACME_equipment_v1",[1,[],[],[],[]]],["ACME_blood_v1",[1,[]]]];
    private _native=str (_medic getVariable "nativeLoadout");
    [([_medic,_m] call ACME_fnc_persistenceRestoreExtended),"valid restore job refused"] call _check;
    [!(_medic getVariable "ACME_persistenceLastRestoreOK") && {count _pfhs==1},"pending nested restore falsely complete"] call _check;
    _m set ["ACME_equipment_v1",[]];
    private _p=_pfhs select 0;
    [(_p select 2),1] call (_p select 0);
    [_medic getVariable "ACME_persistenceLastRestoreOK" && {_attempt==2},"staged restore did not retry captured metadata"] call _check;
    [str (_medic getVariable "nativeLoadout")==_native,"retry reapplied or replaced native kit"] call _check;
    [(_medic getVariable "ACME_persistenceRestorePending") isEqualTo [],"complete job left unresolved state"] call _check;
    ''')


def test_restore_success_waits_for_native_custody_grant_not_just_enqueue():
    execute(setup() + r'''
    private _nativeReady=false;
    ACME_fnc_inventoryRestore={true};
    ACME_fnc_inventorySnapshot={if (_nativeReady) then {[1,[]]} else {[]}};
    private _m=createHashMapFromArray [["ACME_inventory_v1",[1,[]]]];
    [_medic,_m] call ACME_fnc_persistenceRestoreExtended;
    [!(_medic getVariable "ACME_persistenceLastRestoreOK"),"queued registration was reported settled"] call _check;
    private _p=_pfhs select 0;
    [(_p select 2),1] call (_p select 0);
    [!(_medic getVariable "ACME_persistenceLastRestoreOK"),"busy native proof ignored on retry"] call _check;
    _nativeReady=true;
    [(_p select 2),1] call (_p select 0);
    [_medic getVariable "ACME_persistenceLastRestoreOK","native grant never completed restore"] call _check;
    ''')


def test_restore_retired_kit_cannot_receive_delayed_staged_equipment():
    execute(setup() + r'''
    private _attempt=0;ACME_fnc_equipmentRestore={_attempt=_attempt+1;false};
    private _m=createHashMapFromArray [["ACME_equipment_v1",[1,[],[],[],[]]]];
    [_medic,_m] call ACME_fnc_persistenceRestoreExtended;
    _medic setVariable ["ACME_equipmentKitEpoch",1];
    private _p=_pfhs select 0;[(_p select 2),1] call (_p select 0);
    [_attempt==1 && {(_medic getVariable "ACME_persistenceRestorePending") isEqualTo []},"retired job wrote into new kit"] call _check;
    [count (_medic getVariable "ACME_persistenceRestoreRetired")>0,"retired evidence erased"] call _check;
    ''')


def test_server_barrier_requires_client_seen_lease_and_unchanged_native_state():
    execute(setup() + r'''
    private _lease=["begin",[_medic],[],30] call ACME_fnc_persistenceBarrier;
    [_lease!="" && {_medic getVariable "ACME_persistenceFrozen"},"settled barrier refused"] call _check;
    private _snapshot=[_medic] call ACME_fnc_persistenceSnapshot;
    [([_medic,_snapshot] call ACME_fnc_persistenceCaptureValid),"owner capture proof failed"] call _check;
    [("validate"!=_lease) && {(["validate",_lease,[[_medic,_snapshot]]] call ACME_fnc_persistenceBarrier)},"matching owner capture not validated"] call _check;
    (_snapshot select 1) set ["ACME_checkpointLease_v1",""];
    [!(["validate",_lease,[[_medic,_snapshot]]] call ACME_fnc_persistenceBarrier),"unacknowledged freeze validated"] call _check;
    (_snapshot select 1) set ["ACME_checkpointLease_v1",_lease];
    _medic setVariable ["nativeLoadout",["changed"]];
    [!(["validate",_lease,[[_medic,_snapshot]]] call ACME_fnc_persistenceBarrier),"changed native inventory validated"] call _check;
    [(["end",_lease] call ACME_fnc_persistenceBarrier) && {!(_medic getVariable "ACME_persistenceFrozen")},"barrier did not release"] call _check;
    ''')


@pytest.mark.parametrize('fault', ['epoch', 'unfreeze', 'pending', 'timeout'])
def test_barrier_cannot_validate_expired_or_invalidated_save(fault):
    mutation = {
        'epoch': '_medic setVariable ["ACME_clinicalEpoch",1];',
        'unfreeze': '_medic setVariable ["ACME_persistenceFrozen",false];',
        'pending': '_medic setVariable ["ACME_inventoryPending",createHashMapFromArray [["new",true]]];',
        'timeout': '_nowTime=_nowTime+31;',
    }[fault]
    execute(setup() + r'''
    private _lease=["begin",[_medic],[],30] call ACME_fnc_persistenceBarrier;
    private _snapshot=[_medic] call ACME_fnc_persistenceSnapshot;
    [([_medic,_snapshot] call ACME_fnc_persistenceCaptureValid),"initial proof failed"] call _check;
    ''' + mutation + r'''
    [!(["validate",_lease,[[_medic,_snapshot]]] call ACME_fnc_persistenceBarrier),"invalidated save lease validated"] call _check;
    ''')


def test_checkpoint_refuses_native_fresh_blood_without_mission_registry_adapter():
    execute(setup() + r'''
    _medic setVariable ["nativeLoadout",["ACM_FreshBloodBag_500_1"]];
    [([_medic] call ACME_fnc_persistenceSnapshot) isEqualTo [],"native donorID silently persisted without global metadata"] call _check;
    [_medic getVariable ["ACME_persistenceBlockReason",""]!="","missing donor adapter has no reason"] call _check;
    ''')


def test_server_ready_blocks_pending_fridge_after_source_object_deletion():
    execute(setup() + r'''
    missionNamespace setVariable ["ACME_bf_serverGrants",createHashMapFromArray [["g",[_medic,[7,1],"ACM_BloodBag_ON_500","pending",0,objNull]]]];
    [!([_medic] call ACME_fnc_persistenceReady),"deleted fridge erased unresolved delivery"] call _check;
    ''')


def test_server_ready_blocks_temporary_mixing_pause():
    execute(setup() + r'''
    _medic setVariable ["ACME_infusionMixFlowLeases",createHashMapFromArray [["mix",["active",_patient,0,true,1,0,"bag",1,[],0,0,7]]]];
    [!([_medic] call ACME_fnc_persistenceReady),"temporary UI flow pause treated as persistent intent"] call _check;
    ''')


def test_loose_import_retries_until_native_replication_and_owner_ack():
    execute(setup() + r'''
    call ACME_fnc_coolerPersistenceInit;
    _server=false;
    private _saved=[1,[["ACM_BloodBag_ON_500",900]]];
    [([_medic,_saved] call ACME_fnc_bloodPersistenceRequest),"client import refused"] call _check;
    private _p=_pfhs select 0;[(_p select 2),1] call (_p select 0);
    [count _events==1 && {!([_medic] call ACME_fnc_persistenceReady)},"unacknowledged import failed to block save"] call _check;
    private _message=(_events select 0) select 1;
    _server=true;
    _message call (_hooks get "ACME_bloodPersistenceImport");
    [count _events==1,"missing native blood falsely acknowledged"] call _check;
    _medic setVariable ["cargo",["ACM_BloodBag_ON_500"]];
    _message call (_hooks get "ACME_bloodPersistenceImport");
    [count _events==2,"visible native blood was not acknowledged"] call _check;
    _server=false;
    ((_events select 1) select 1) call (_hooks get "ACME_bloodPersistenceImported");
    [_medic getVariable "ACME_bloodLastRestoreOK" && {(_medic getVariable "ACME_bloodRestoreOutbox") isEqualTo []},"ack did not retire exact import"] call _check;
    ''')


def test_expired_loose_import_retains_unresolved_metadata_and_no_fresh_fallback():
    execute(setup() + r'''
    _server=false;
    [_medic,[1,[["ACM_BloodBag_ON_500",900]]]] call ACME_fnc_bloodPersistenceRequest;
    private _p=_pfhs select 0;_nowTime=_nowTime+31;
    [(_p select 2),1] call (_p select 0);
    private _state=_medic getVariable "ACME_bloodRestoreOutbox";
    [_state isNotEqualTo [] && {(_state select 7)==-1} && {!([_medic] call ACME_fnc_persistenceReady)},"timed-out import disappeared as a fresh bag"] call _check;
    ''')


def test_loose_import_old_ack_cannot_clear_successor_kit_job():
    execute(setup() + r'''
    call ACME_fnc_coolerPersistenceInit;_server=false;
    [_medic,[1,[["ACM_BloodBag_ON_500",900]]]] call ACME_fnc_bloodPersistenceRequest;
    private _old=(_medic getVariable "ACME_bloodRestoreOutbox") select 4;
    _medic setVariable ["ACME_equipmentKitEpoch",1];
    [_medic,[1,[["ACM_BloodBag_ON_500",10]]]] call ACME_fnc_bloodPersistenceRequest;
    private _before=str (_medic getVariable "ACME_bloodRestoreOutbox");
    [_medic,_old] call (_hooks get "ACME_bloodPersistenceImported");
    [str (_medic getVariable "ACME_bloodRestoreOutbox")==_before,"old ack erased new import"] call _check;
    ''')


def test_cba_get_preserves_client_observed_barrier_lease():
    execute(setup() + r'''
    call ACME_fnc_coolerPersistenceInit;
    private _lease=["begin",[_medic],[],30] call ACME_fnc_persistenceBarrier;
    [_lease!="","fixture did not acquire barrier"] call _check;
    private _native=_medic getVariable "nativeLoadout";private _m=createHashMap;
    [_medic,_native,_m] call (_hooks get "CBA_loadoutGet");
    [(_m get "ACME_checkpointLease_v1")==_lease,"CBA getter dropped observed save lease"] call _check;
    [([_medic,[_native,_m]] call ACME_fnc_persistenceCaptureValid),"CBA owner proof failed"] call _check;
    [(["validate",_lease,[[_medic,[_native,_m]]]] call ACME_fnc_persistenceBarrier),"CBA captured pair failed barrier"] call _check;
    ''')


def test_owner_revalidation_rejects_virtual_only_drift_and_retires_old_proof():
    execute(setup() + r'''
    private _lease=["begin",[_medic],[],30] call ACME_fnc_persistenceBarrier;
    private _s=[_medic] call ACME_fnc_persistenceSnapshot;
    [([_medic,_s] call ACME_fnc_persistenceCaptureValid),"initial capture proof failed"] call _check;
    _medic setVariable ["equipment",[1,[["Drug",2]],[],[],[]]];
    [!([_medic,_s] call ACME_fnc_persistenceCaptureValid),"virtual vial amount drift was accepted"] call _check;
    [!(["validate",_lease,[[_medic,_s]]] call ACME_fnc_persistenceBarrier),"failed revalidation left stale proof valid"] call _check;
    ''')


def test_barrier_rejects_marker_only_metadata_that_restore_would_reject():
    execute(setup() + r'''
    private _lease=["begin",[_medic],[],30] call ACME_fnc_persistenceBarrier;
    private _s=[_medic] call ACME_fnc_persistenceSnapshot;
    [_medic,_s] call ACME_fnc_persistenceCaptureValid;
    private _bad=[_s select 0,createHashMapFromArray [["ACME_checkpoint_v1",[1,true]],["ACME_checkpointLease_v1",_lease]]];
    [!(["validate",_lease,[[_medic,_bad]]] call ACME_fnc_persistenceBarrier),"incomplete marked checkpoint validated"] call _check;
    ''')


def test_unresolved_blood_import_fence_survives_owner_private_outbox_loss():
    execute(setup() + r'''
    _medic setVariable ["ACME_bloodRestoreUnresolved",[0,0,[7,1]]];
    _medic setVariable ["ACME_bloodRestoreOutbox",[]];
    [!([_medic] call ACME_fnc_persistenceReady),"migration lost unresolved blood import evidence"] call _check;
    _medic setVariable ["ACME_equipmentKitEpoch",1];
    [([_medic] call ACME_fnc_persistenceReady),"retired kit fence blocked a fresh kit forever"] call _check;
    ''')


def test_restored_fridge_tick_uses_remaining_delay_once_then_normal_interval():
    execute(setup() + r'''
    _gameDate=0;
    [_patient,_savedFridge] call ACME_fnc_bloodFridgeRestore;
    _patient setVariable ["ACME_bloodFridge",true];
    missionNamespace setVariable ["ACME_bloodFridges",[_patient]];
    _gameDate=(59/60)/(365.25*24);call ACME_fnc_bloodFridgeTick;
    [(_patient getVariable "ACME_bf_stock") isEqualTo [["ACM_BloodBag_ON_500",2]],"restore restocked before remaining delay"] call _check;
    _gameDate=(61/60)/(365.25*24);call ACME_fnc_bloodFridgeTick;
    [(_patient getVariable "ACME_bf_stock") isEqualTo [["ACM_BloodBag_ON_500",6]],"restored remaining delay never elapsed"] call _check;
    [isNil {_patient getVariable "ACME_bf_restoreRestockDelayMins"},"restored short delay reused for future cycles"] call _check;
    _patient setVariable ["ACME_bf_stock",[["ACM_BloodBag_ON_500",1]]];
    _gameDate=(161/60)/(365.25*24);call ACME_fnc_bloodFridgeTick;
    [(_patient getVariable "ACME_bf_stock") isEqualTo [["ACM_BloodBag_ON_500",1]],"next cycle did not resume configured interval"] call _check;
    ''')


@pytest.mark.parametrize('state', ['pending', 'uncertain', 'dispatched'])
def test_fresh_grant_to_provider_or_from_donor_blocks_checkpoint(state):
    execute(setup() + f'private _state="{state}";' + r'''
    private _grant=[_patient,_medic,500,"req",[],_state,1,[],0,"",7,"nonce",true,1];
    missionNamespace setVariable ["ACM_circulation_FreshBloodGrants",createHashMapFromArray [["req",_grant]]];
    [!([_medic] call ACME_fnc_persistenceReady),"funded donor transfer falsely settled"] call _check;
    ''')


def test_funded_fresh_removal_without_grant_is_not_saveable():
    execute(setup() + r'''
    _medic setVariable ["ACME_txRemoveFunded",createHashMapFromArray [["req",[_patient,500,[]]]]];
    [!([_medic] call ACME_fnc_persistenceReady),"removed blood fell between patient and supplier snapshots"] call _check;
    ''')


def test_unscoped_native_supply_receipt_blocks_owner_checkpoint_without_discarding_funding():
    execute(setup() + r'''
    private _receipt=[_medic,"ACME_IVLine",objNull,"supply1"];
    missionNamespace setVariable ["ACME_supplyReceipts",createHashMapFromArray [["supply1",_receipt]]];
    [!([_medic] call ACME_fnc_persistenceReady),"native supply escrow omitted from checkpoint"] call _check;
    [count (missionNamespace getVariable "ACME_supplyReceipts")==1,"readiness discarded live funding"] call _check;
    ''')


def test_known_expired_iv_scope_retires_by_existing_commit_unknown_policy_without_refund():
    execute(setup() + r'''
    private _receipt=[_medic,"ACM_SalineFlush_10",objNull,"supply1"];
    private _scope=[_receipt,_patient,"site","flush","token",0,69,_medic];
    missionNamespace setVariable ["ACME_supplyReceipts",createHashMapFromArray [["supply1",_receipt]]];
    missionNamespace setVariable ["ACME_IV_SupplyScopes",createHashMapFromArray [["supply1",_scope]]];
    _medic setVariable ["ACME_IV_SupplyBindings",[_scope]];
    private _native=str (_medic getVariable "nativeLoadout");
    [([_medic] call ACME_fnc_persistenceReady),"expired committed IV scope blocked saves forever"] call _check;
    [count (missionNamespace getVariable "ACME_supplyReceipts")==0 && {(_medic getVariable "ACME_IV_SupplyBindings") isEqualTo []},"known expired reservation not retired"] call _check;
    [str (_medic getVariable "nativeLoadout")==_native,"expired uncertain outcome manufactured a refund"] call _check;
    ''')


@pytest.mark.parametrize('state', ['applying', 'funded', 'uncertain'])
def test_private_source_decision_prevents_owner_checkpoint_before_public_admission(state):
    execute(setup() + f'private _state="{state}";' + r'''
    _server=false;
    missionNamespace setVariable ["ACME_resourceReturnSources",createHashMapFromArray [["return1",[[_patient,_medic,[],"nonce"],_state,[7,"nonce"]]]]];
    [!([_medic] call ACME_fnc_persistenceReady),"source private decision was lost before public grant admission"] call _check;
    ''')


def test_admitted_return_source_is_busy_until_delivery_terminal_proof():
    execute(setup() + r'''
    _server=false;
    _medic setVariable ["ACME_resourceReturnFunded",createHashMapFromArray [["return1",[_patient,[]]]]];
    missionNamespace setVariable ["ACME_resourceReturnSources",createHashMapFromArray [["return1",[[_patient,_medic,[],"nonce"],"admitted",[7,"nonce"]]]]];
    [!([_medic] call ACME_fnc_persistenceReady),"admission was mistaken for terminal native placement"] call _check;
    _medic setVariable ["ACME_resourceReturnResolved",createHashMapFromArray [["return1",true]]];
    missionNamespace setVariable ["ACME_resourceReturnSources",createHashMapFromArray [["return1",[[_patient,_medic,[],"nonce"],"delivered",[7,"nonce"]]]]];
    [([_medic] call ACME_fnc_persistenceReady),"proven delivered source remained permanently busy"] call _check;
    ''')


def test_fresh_funded_source_requires_terminal_delivery_proof_on_client():
    execute(setup() + r'''
    _server=false;
    _medic setVariable ["ACME_txRemoveFunded",createHashMapFromArray [["fresh1",[_patient,500,[]]]]];
    [!([_medic] call ACME_fnc_persistenceReady),"funded fresh source omitted before server journal existed"] call _check;
    _medic setVariable ["ACME_txRemoveResolved",createHashMapFromArray [["fresh1",true]]];
    [([_medic] call ACME_fnc_persistenceReady),"delivered fresh source remained busy"] call _check;
    ''')


def test_global_orphan_journal_preflight_blocks_begin_and_validation_but_never_release():
    execute(setup() + r'''
    ACME_fnc_persistenceJournalsReady={false};
    [(["begin",[_medic],[],30] call ACME_fnc_persistenceBarrier)=="","orphaned funding did not block save admission"] call _check;
    ACME_fnc_persistenceJournalsReady={true};
    private _lease=["begin",[_medic],[],30] call ACME_fnc_persistenceBarrier;
    private _s=[_medic] call ACME_fnc_persistenceSnapshot;[_medic,_s] call ACME_fnc_persistenceCaptureValid;
    ACME_fnc_persistenceJournalsReady={false};
    [!(["validate",_lease,[[_medic,_s]]] call ACME_fnc_persistenceBarrier),"new orphaned funding validated"] call _check;
    [(["end",_lease] call ACME_fnc_persistenceBarrier),"busy journal prevented lease release"] call _check;
    ''')


def test_machine_private_return_outbox_remains_busy_after_both_actor_objects_deleted():
    execute(setup() + r'''
    _server=false;
    missionNamespace setVariable ["ACME_resourceReturnSources",createHashMapFromArray [["orphan",[[objNull,objNull,[],"nonce"],"admitted",[7,"nonce"]]]]];
    [!([_medic] call ACME_fnc_persistenceReady),"deleted actor references hid a nonterminal machine return"] call _check;
    ''')
