"""Execute delayed cooler commands across captured provider input periods.

The production broker/request/reply run; native cargo and transport use the
existing B287 boundaries. Historical accepted draws remain durable deliveries.
"""
import pytest

from test_b287_cooler_box_transactions import setup
from test_menu_death_lifecycle import execute
from test_b216_fridge import setup as fridge_setup, source as fridge_source
from test_b285_syringe_migration import setup as delivery_setup


@pytest.mark.parametrize("field,value", [
    ("ACME_equipmentKitEpoch", 1),
    ("ACME_providerLocalityEpoch", 1),
    ("ACME_providerLocalityEpoch", 2),
])
def test_delayed_first_draw_cannot_debit_source_for_replaced_input_period(field, value):
    execute(setup()+r'''
        private _sid=call _issueCooler;call _flush;
        ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
        private _called=[];
        ["draw",_medic,"ACM_BloodBag_ON_500",_boxFixture,[{_called pushBack (_this select 0)},[]]] call ACME_fnc_coolerBoxRequest;
    '''+f'_medic setVariable ["{field}",{value}];'+r'''
        call _flushBoxes;
        [(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"],"retired draw debited shared source"] call _check;
        [_given isEqualTo [] && {count (_medic getVariable "ACME_coolerBoxRequests")==0},"retired draw materialized blood or left retry"] call _check;
        [_called isEqualTo [],"retired input callback ran"] call _check;
    ''')


def test_accepted_draw_receipt_survives_later_owner_period_without_second_debit():
    execute(setup()+r'''
        private _sid=call _issueCooler;call _flush;
        ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
        ["draw",_medic,"ACM_BloodBag_ON_500",_boxFixture] call ACME_fnc_coolerBoxRequest;
        private _message=+(_boxQueue deleteAt 0);
        _message call ACME_fnc_coolerBoxBroker;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        call _flushBoxes;
        _message call ACME_fnc_coolerBoxBroker;call _flushBoxes;
        [_given isEqualTo [["ACM_BloodBag_ON_500",123]] && {(_boxFixture getVariable "cargo") isEqualTo []},"accepted draw lost custody or duplicate debit"] call _check;
    ''')


def test_delayed_first_deploy_cannot_execute_after_locality_period_retires():
    execute(setup()+r'''
        private _sid=call _issueCooler;call _flush;
        ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flush;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        call _flushBoxes;
        [!(_boxFixture getVariable ["ACME_boxCoolerClass",""] != ""),"retired deploy created world source"] call _check;
        [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_coolerBoxRequests")==0},"retired deploy failed to return original carrier"] call _check;
    ''')


def fridge_ack():
    init=fridge_source('initBloodStorageRuntime')
    body=init.split('["ACME_bfDeliveryAck", {',1)[1].split('}] call CBA_fnc_addEventHandler;',1)[0]
    return 'private _deliveryAck={'+body+'};'


def test_fridge_unacknowledged_grant_survives_door_timeout_and_retries_without_new_debit():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _grants=_anchor getVariable "ACME_bf_grants";
        [count _grants==1 && {((_grants get "one:7:1") select 3)=="pending"},"fridge did not journal funding before send"] call _check;
        _nowTime=19;call ACME_fnc_bloodFridgeTick;
        [!(_anchor getVariable "ACME_bf_open") && {((_grants get "one:7:1") select 3)=="pending"},"door timeout settled undelivered stock"] call _check;
        private _messages=_events select {(_x select 0)=="ACME_bfGive"};
        [count _messages>=2 && {((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0},"unacknowledged grant was not retried or debited twice"] call _check;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        [((_grants get "one:7:1") select 3)=="delivered" && {count _given==1},"native grant did not settle journal"] call _check;
        private _before=count (_events select {(_x select 0)=="ACME_bfGive"});
        _nowTime=30;call ACME_fnc_bloodFridgeTick;
        [count (_events select {(_x select 0)=="ACME_bfGive"})==_before,"settled grant retained transport work"] call _check;
    ''')


def test_fridge_lost_ack_replays_receipt_without_a_second_item_even_after_legacy_window_eviction():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        _player setVariable ["ACME_bf_receivedTokens",[]];
        private _before=count (_events select {(_x select 0)=="ACME_bfDeliveryAck"});
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        [count _given==1 && {count (_events select {(_x select 0)=="ACME_bfDeliveryAck"})==_before+1},"lost ack rematerialized a grant or failed to retry proof"] call _check;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        private _grants=_anchor getVariable "ACME_bf_grants";
        [((_grants get "one:7:1") select 3)=="delivered","duplicate acknowledgement failed terminal journal"] call _check;
    ''')


@pytest.mark.parametrize('ground', [False, True])
def test_fridge_failed_native_placement_retains_funding_until_readback_succeeds(ground):
    execute(fridge_setup()+fridge_ack()+f'_giveGround={str(ground).lower()};'+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        _giveWorks=false;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        private _grants=_anchor getVariable "ACME_bf_grants";
        [((_grants get "one:7:1") select 3)=="pending" && {count (_events select {(_x select 0)=="ACME_bfDeliveryAck"})==0},"failed native placement was acknowledged"] call _check;
        _giveWorks=true;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        [((_grants get "one:7:1") select 3)=="delivered" && {((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0},"funded retry lost stock or failed settlement"] call _check;
        [count (_player getVariable "fixtureItems")+count (_groundHolder getVariable "fixtureItems")==1,"native retry duplicated or lost blood"] call _check;
    ''')


def test_fridge_duplicate_changed_request_cannot_choose_new_class_or_forge_migration_ack():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _before=count (_events select {(_x select 0)=="ACME_bfGive"});
        [_anchor,"A",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        [count (_events select {(_x select 0)=="ACME_bfGive"})==_before && {((_anchor getVariable "ACME_bf_stock") select 1 select 1)==2},"repeated token changed its immutable class"] call _check;
        [_anchor,_player,[7,1],"A",7] call _deliveryAck;
        [_anchor,_player,[7,1],"ON",8] call _deliveryAck;
        private _grants=_anchor getVariable "ACME_bf_grants";
        [((_grants get "one:7:1") select 3)=="pending","mismatched decision retired a grant"] call _check;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        _requestOwnerSim=8;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        [((_grants get "one:7:1") select 3)=="delivered","exact replicated receipt failed after ownership migration"] call _check;
    ''')


def test_fridge_funded_grant_survives_source_removal_and_can_finish_without_door_object():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _global=missionNamespace getVariable "ACME_bf_serverGrants";
        private _grant=_global get "one:7:1";_grant set [5,objNull];
        _anchor=objNull;missionNamespace setVariable ["ACME_bloodFridges",[]];
        _nowTime=19;call ACME_fnc_bloodFridgeTick;
        private _messages=_events select {(_x select 0)=="ACME_bfGive"};
        [count _messages>=2 && {(_messages select (count _messages-1) select 1 select 0) isEqualTo objNull},"removed source lost funded retry"] call _check;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        [((_global get "one:7:1") select 3)=="delivered" && {count _given==1},"removed source could not settle granted bag"] call _check;
        [count (_player getVariable "ACME_bf_pendingGrants")==0,"removed source left provider save fence"] call _check;
    ''')


def test_fridge_unverifiable_custom_inventory_result_holds_custody_without_repeat_materialization():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        ace_common_fnc_addToInventory={_given pushBack _this;nil};
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeReceive;
        [count _given==1 && {count (_events select {(_x select 0)=="ACME_bfDeliveryAck"})==0},"unverifiable custom grant was retried or settled"] call _check;
        private _receipts=_player getVariable "ACME_bf_deliveryReceipts";
        [((_receipts get "7:1") select 3)=="uncertain","unknown placement lost explicit recovery state"] call _check;
    ''')


def test_checkpoint_freeze_blocks_new_fridge_take_before_any_stock_or_history_mutation():
    execute(fridge_setup()+r'''
        _player setVariable ["ACME_persistenceFrozen",true];
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        [((_anchor getVariable "ACME_bf_stock") select 0 select 1)==1 && {count _events==0},"frozen inventory admitted new fridge grant"] call _check;
        _player setVariable ["ACME_persistenceFrozen",false];
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        [((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0,"freeze consumed the unadmitted request identity"] call _check;
    ''')


def test_checkpoint_freeze_blocks_new_cooler_draw_without_debit():
    execute(setup()+r'''
        private _sid=call _issueCooler;call _flush;
        ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
        ["draw",_medic,"ACM_BloodBag_ON_500",_boxFixture] call ACME_fnc_coolerBoxRequest;
        _medic setVariable ["ACME_persistenceFrozen",true];call _flushBoxes;
        [_given isEqualTo [] && {(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"]},"frozen inventory admitted new cooler source debit"] call _check;
    ''')


def test_checkpoint_frozen_patient_rejects_new_syringe_batch_without_source_or_patient_dose():
    execute(delivery_setup()+r'''
        call _claim;call _begin;
        _patient setVariable ["ACME_persistenceFrozen",true];
        ["slice-a"] call _batch;
        [count _patientEvents==0 && {call _remaining==2},"frozen patient received or reserved a new dose"] call _check;
        [(((call _journal) get "batches") get "slice-a" select 3)=="rejected","checkpoint rejection did not settle exact submitted batch"] call _check;
    ''')
