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
    # The old ACK can no longer settle stock; only a generic delivered journal may.
    return 'private _legacyDeliveryAck={'+body+'};private _deliveryAck={_this call _legacyDeliveryAck;call ACME_fnc_bloodFridgeTick;};'


def test_fridge_unacknowledged_grant_survives_door_timeout_and_retries_without_new_debit():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _grants=_anchor getVariable "ACME_bf_grants";
        [count _grants==1 && {((_grants get "one:7:1") select 3)=="pending"},"fridge did not journal funding before send"] call _check;
        _nowTime=19;call ACME_fnc_bloodFridgeTick;
        [!(_anchor getVariable "ACME_bf_open") && {((_grants get "one:7:1") select 3)=="pending"},"door timeout settled undelivered stock"] call _check;
        CBA_missionTime=103;call _resourceTick;
        private _messages=_events select {(_x select 0)=="ACME_resourceReturnDelivery"};
        [count _messages>=2 && {((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0},"unacknowledged grant was not retried or debited twice"] call _check;
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        [((_grants get "one:7:1") select 3)=="delivered" && {count _given==1},"native grant did not settle journal"] call _check;
        private _before=count (_events select {(_x select 0)=="ACME_resourceReturnDelivery"});
        _nowTime=30;CBA_missionTime=130;call ACME_fnc_bloodFridgeTick;call _resourceTick;
        [count (_events select {(_x select 0)=="ACME_resourceReturnDelivery"})==_before,"settled grant retained transport work"] call _check;
    ''')


def test_fridge_lost_ack_replays_receipt_without_a_second_item_even_after_legacy_window_eviction():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _packet=[_resourcePackets deleteAt 0] call ACME_fnc_syringeDeliveryCopy;
        _packet call ACME_fnc_resourceReturnReceive;
        // Drop the generic ACK and public projection; the captured-machine
        // private decision remains the only proof of the completed native grant.
        _resourceServerMessages=[];
        _player setVariable ["ACME_bf_receivedTokens",[]];
        _player setVariable ["ACME_resourceReturnReceived",createHashMap];
        private _before=count (_events select {(_x select 0)=="ACME_resourceReturn" && {((_x select 1) select 0)=="ack"}});
        _packet call ACME_fnc_resourceReturnReceive;
        [count _given==1 && {count (_events select {(_x select 0)=="ACME_resourceReturn" && {((_x select 1) select 0)=="ack"}})==_before+1},"lost ACK rematerialized a grant or failed private proof retry"] call _check;
        call _flushResources;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        private _grants=_anchor getVariable "ACME_bf_grants";
        [((_grants get "one:7:1") select 3)=="delivered","private replay acknowledgement failed terminal stock journal"] call _check;
    ''')


@pytest.mark.parametrize('ground', [False, True])
def test_fridge_failed_native_placement_retains_funding_until_readback_succeeds(ground):
    execute(fridge_setup()+fridge_ack()+f'_giveGround={str(ground).lower()};'+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        _giveWorks=false;
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        private _grants=_anchor getVariable "ACME_bf_grants";
        [((_grants get "one:7:1") select 3)=="pending" && {count (_events select {(_x select 0)=="ACME_bfDeliveryAck"})==0},"failed native placement was acknowledged"] call _check;
        _giveWorks=true;CBA_missionTime=103;call _resourceTick;
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
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
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        _requestOwnerSim=8;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        [((_grants get "one:7:1") select 3)=="delivered","exact replicated receipt failed after ownership migration"] call _check;
    ''')


def test_fridge_funded_grant_survives_source_removal_and_can_finish_without_door_object():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _global=missionNamespace getVariable "ACME_bf_serverGrants";
        private _grant=_global get "one:7:1";_grant set [5,objNull];
        private _returns=missionNamespace getVariable ["ACME_resourceReturns",createHashMap];
        private _return=_returns get "fridge:one:7:1";_return set [1,objNull];
        // Arma object handles in queued packets also become objNull after deletion.
        {_x set [1,objNull];} forEach _resourcePackets;
        _anchor=objNull;missionNamespace setVariable ["ACME_bloodFridges",[]];
        _nowTime=19;call ACME_fnc_bloodFridgeTick;
        CBA_missionTime=103;call _resourceTick;
        private _messages=_events select {(_x select 0)=="ACME_resourceReturnDelivery"};
        [count _messages>=2 && {(_messages select (count _messages-1) select 1 select 1) isEqualTo objNull},"removed source lost funded retry"] call _check;
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        [((_global get "one:7:1") select 3)=="delivered" && {count _given==1},"removed source could not settle granted bag"] call _check;
        [count (_player getVariable "ACME_bf_pendingGrants")==0,"removed source left provider save fence"] call _check;
    ''')


def test_fridge_unverifiable_custom_inventory_result_holds_custody_without_repeat_materialization():
    execute(fridge_setup()+fridge_ack()+r'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        ace_common_fnc_addToInventory={_given pushBack _this;nil};
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        [count _given==1 && {count (_events select {(_x select 0)=="ACME_bfDeliveryAck"})==0},"unverifiable custom grant was retried or settled"] call _check;
        private _receipts=_player getVariable "ACME_bf_deliveryReceipts";
        [((_receipts get "7:1") select 3)=="uncertain","unknown placement lost explicit recovery state"] call _check;
    ''')


def assert_fridge_failure_diagnostics_bounded():
    # Capture the actual production log command while retaining receipt guards,
    # native readback and both ordinary ACE placement paths from the fixture.
    from test_b279_inventory_diagnostics import capture_logs
    execute('private _diagnostics=[];'+capture_logs(fridge_setup()+fridge_ack())+r'''
        _anchor setVariable ["ACME_bf_stock",[["ON",1],["A",3]]];
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        [_anchor,_player,[7,1],"ON",7] call _deliveryAck;
        call _flushResources;
        [_anchor,"ON",_player,[7,1],"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        _giveGround=true;
        [_anchor,"A",_player,[7,2]] call ACME_fnc_bloodFridgeTakeOwner;
        call _flushResources;
        [_anchor,"A",_player,[7,2],"delivered","fridge:one:7:2"] call ACME_fnc_bloodFridgeReceive;
        [_anchor,_player,[7,2],"A",7] call _deliveryAck;
        call _flushResources;
        [_anchor,"A",_player,[7,2],"delivered","fridge:one:7:2"] call ACME_fnc_bloodFridgeReceive;
        [count _diagnostics==0 && {count _given==2},"normal inventory/ground delivery or successful replay logged"] call _check;
        private _acksBefore=count (_events select {(_x select 0)=="ACME_bfDeliveryAck"});
        ace_common_fnc_addToInventory={_given pushBack _this;nil};
        [_anchor,"A",_player,[7,3]] call ACME_fnc_bloodFridgeTakeOwner;
        call _flushResources;
        [_anchor,"A",_player,[7,3],"uncertain","fridge:one:7:3"] call ACME_fnc_bloodFridgeReceive;
        [count _diagnostics==1 && {count _given==3}
            && {((_diagnostics select 0) find "stock remains reserved for recovery")>=0},"unknown placement did not report one retained recovery hold"] call _check;
        for "_replay" from 1 to 20 do {
            [_anchor,"A",_player,[7,3]] call ACME_fnc_bloodFridgeTakeOwner;
            call _flushResources;
        [_anchor,"A",_player,[7,3],"uncertain","fridge:one:7:3"] call ACME_fnc_bloodFridgeReceive;
        };
        [count _diagnostics==1 && {count _given==3},"unknown receipt replay repeated diagnostic or native placement"] call _check;
        [_anchor,"A",_player,[7,4]] call ACME_fnc_bloodFridgeTakeOwner;
        call _flushResources;
        [_anchor,"A",_player,[7,4],"uncertain","fridge:one:7:4"] call ACME_fnc_bloodFridgeReceive;
        call _flushResources;
        [_anchor,"A",_player,[7,4],"uncertain","fridge:one:7:4"] call ACME_fnc_bloodFridgeReceive;
        [count _diagnostics==2 && {count _given==4},"a distinct uncertain delivery failed its own once-only diagnostic"] call _check;
        [count (_events select {(_x select 0)=="ACME_bfDeliveryAck"})==_acksBefore,"uncertain placement was acknowledged as delivered"] call _check;
        private _receipts=_player getVariable "ACME_bf_deliveryReceipts";
        [((_receipts get "7:3") select 3)=="uncertain" && {((_receipts get "7:4") select 3)=="uncertain"}
            && {count (_player getVariable "ACME_bf_pendingGrants")==2},"bounded diagnostics discarded unresolved custody"] call _check;
    ''')


def test_fridge_failure_diagnostic_is_once_per_delivery_and_normal_or_replayed_delivery_is_quiet():
    assert_fridge_failure_diagnostics_bounded()


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
