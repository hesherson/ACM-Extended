"""Execute admitted transfer epochs, funded receipts and delayed owner/server messages.

Native inventory, locality, cargo and transport are explicit boundaries; production
admission, receipt, retirement and commit branches execute in SQF-VM.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_b308_patient_equipment import converted
from test_b313_equipment_pickup import setup

E=ROOT/'addons/acme_equipment/functions'
EPOCHS=['ACME_equipmentKitEpoch','ACME_providerLocalityEpoch']


@pytest.mark.parametrize('epoch',EPOCHS)
@pytest.mark.parametrize('kind',['pro','ls','accu'])
def test_delayed_setup_cannot_debit_a_replacement_inventory(epoch,kind):
    execute(setup()+f'''
      [_medic,_patient,"{kind}"] call ACME_fnc_equipmentRequest;
      _medic setVariable ["{epoch}",1];
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1 && {{(_acks select 0) select 4}},"retired request debited replacement inventory"] call _check;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;(_acks select 1) call ACME_fnc_equipmentAck;
      [_spawnCount==0 && {{(_medic getVariable ["ACME_equipmentWorldPending","busy"])==""}},"cancelled request spawned or stranded reservation"] call _check;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1,"retired replay debited new kit after cancellation"] call _check;
    ''')


@pytest.mark.parametrize('epoch',EPOCHS)
@pytest.mark.parametrize('kind',['pro','ls','accu'])
def test_uncredited_pickup_cancels_on_epoch_change_and_unlocks_the_source(epoch,kind):
    execute(setup()+f'''
      [_medic,_patient,"{kind}","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      _medic setVariable ["{epoch}",1];
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_stock==1 && {{_deleted==0}},"retired pickup credited or deleted source"] call _check;
      [!(_deviceFixture getVariable ["ACME_eq_busy",true]),"retired pickup left source locked"] call _check;
      [count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0,"retired pickup blocked checkpoints"] call _check;
    ''')


@pytest.mark.parametrize('epoch',EPOCHS)
@pytest.mark.parametrize('kind,prefix',[('pro','acme_tempus'),('ls','acme_tempusls')])
def test_funded_setup_finishes_once_without_clearing_replacement_monitor_state(epoch,kind,prefix):
    execute(setup()+f'''
      _medic setVariable ["{prefix}_pw",[true,0,false]];
      _medic setVariable ["{prefix}_st","old monitor"];
      [_medic,_patient,"{kind}"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==0,"setup source was not debited"] call _check;
      _medic setVariable ["{epoch}",1];_stock=5;
      _medic setVariable ["{prefix}_pat",_mount];
      _medic setVariable ["{prefix}_pw",[false,123,true]];
      _medic setVariable ["{prefix}_st","replacement"];
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [!((_acks select 1) select 5),"owner replay did not report changed context"] call _check;
      // Model a server whose public epoch update still lags the owner ACK.
      _medic setVariable ["{epoch}",0];
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;(_acks select 0) call ACME_fnc_equipmentAck;
      [_stock==5 && {{_spawnCount==1}},"paid setup duplicated debit or lost funded device"] call _check;
      [(_medic getVariable ["{prefix}_pat",objNull]) isEqualTo _mount && {{(_medic getVariable "{prefix}_pw") isEqualTo [false,123,true]}} && {{(_medic getVariable "{prefix}_st")=="replacement"}},"late commit overwrote replacement monitor state"] call _check;
    ''')


@pytest.mark.parametrize('epoch',EPOCHS)
@pytest.mark.parametrize('kind,prefix',[('pro','acme_tempus'),('ls','acme_tempusls')])
def test_credited_pickup_replays_receipt_without_overwriting_new_actor_state(epoch,kind,prefix):
    execute(setup()+f'''
      _deviceFixture setVariable ["{prefix}_pat",_patient];
      _deviceFixture setVariable ["{prefix}_pw",[true,0,false]];
      [_medic,_patient,"{kind}","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==2,"pickup was not physically credited"] call _check;
      _medic setVariable ["{epoch}",1];_stock=5;
      _medic setVariable ["{prefix}_pat",_mount];
      _medic setVariable ["{prefix}_pw",[false,123,true]];
      _medic setVariable ["{prefix}_st","replacement"];
      _medic setVariable ["acme_tempusls_pace",[true,90,100,true]];
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _medic setVariable ["{epoch}",0];
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;(_acks select 0) call ACME_fnc_equipmentAck;
      [_stock==5 && {{_deleted==1}} && {{_feeds==0}},"credited pickup duplicated grant or started a replacement feed"] call _check;
      [(_medic getVariable ["{prefix}_pat",objNull]) isEqualTo _mount && {{(_medic getVariable "{prefix}_pw") isEqualTo [false,123,true]}} && {{(_medic getVariable "{prefix}_st")=="replacement"}},"pickup rewrote replacement monitor"] call _check;
      [(_medic getVariable "acme_tempusls_pace") isEqualTo [true,90,100,true],"old pickup stopped new-kit pacing"] call _check;
    ''')


@pytest.mark.parametrize('epoch',EPOCHS)
def test_paid_failed_placement_refunds_once_across_epoch_change(epoch):
    execute(setup()+f'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _medic setVariable ["{epoch}",1];_stock=5;
      ACME_fnc_equipmentPose={{[]}};
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [count _refundMessages==1 && {{_spawnCount==0}},"failed paid placement lost refund"] call _check;
      _caller=2;(_refundMessages select 0) call ACME_fnc_equipmentInventory;
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==6,"funded refund was lost or duplicated after epoch change"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [(_medic getVariable ["ACME_equipmentWorldPending","busy"])=="","refund did not settle"] call _check;
    ''')


@pytest.mark.parametrize('admission',['[]','["other",[0,[7,0]]]','["wrong"]','["REPLACE",[]]','["REPLACE",[0,[]]]'])
def test_rpc_waits_for_its_own_complete_admission_publication(admission):
    execute(setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      private _saved=_medic getVariable "ACME_eqAdmission";
      private _id=(_inventoryMessages select 0) select 1;
    '''+f'_medic setVariable ["ACME_eqAdmission",{admission.replace(chr(34)+"REPLACE"+chr(34),"_id")}];'+'''
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==0},"partial admission made an inventory decision"] call _check;
      _medic setVariable ["ACME_eqAdmission",_saved];
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==0 && {count _acks==1},"complete admission could not retry"] call _check;
    ''')


def test_false_or_retired_ack_cannot_cancel_a_proved_physical_credit():
    execute(setup()+'''
      [_medic,_patient,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      private _bad=+(_acks select 0);_bad set [3,false];_bad set [4,true];_bad set [5,false];
      _caller=7;_bad call ACME_fnc_equipmentAck;
      [_deviceFixture getVariable ["ACME_eq_busy",false],"negative ACK discarded proved credit"] call _check;
      (_acks select 0) call ACME_fnc_equipmentAck;
      [_deleted==1 && {_stock==2},"positive receipt could not settle after old false ACK"] call _check;
    ''')


def test_a_current_request_cannot_be_cancelled_by_a_contradictory_retired_ack():
    execute(setup()+'''
      [_medic,_patient,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      [_medic,(_inventoryMessages select 0) select 1,"give",false,true,true] call ACME_fnc_equipmentAck;
      [_deviceFixture getVariable ["ACME_eq_busy",false],"contradictory retirement unlocked a live request"] call _check;
    ''')


def test_refund_without_its_physical_source_debit_cannot_mint_an_item():
    execute(setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      private _id=(_inventoryMessages select 0) select 1;
      _caller=2;[_medic,_id,"refund","ACM_ACCUVAC"] call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==0},"unpaid refund manufactured equipment or guessed funding"] call _check;
    ''')


def test_failed_take_is_terminal_even_if_new_stock_arrives_before_its_ack():
    execute(setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _stock=0;_caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _stock=1;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1 && {!((_acks select 0) select 3)} && {!((_acks select 1) select 3)},"negative receipt later debited a fresh item"] call _check;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;(_acks select 1) call ACME_fnc_equipmentAck;
      [_spawnCount==0 && {(_medic getVariable ["ACME_equipmentWorldPending","busy"])==""},"failed take left a paid source or reservation"] call _check;
    ''')


def test_private_receipt_survives_lagging_public_proof_without_duplicate_credit():
    execute(setup()+'''
      [_medic,_patient,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _medic setVariable ["ACME_eqReceipts",createHashMap];
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==2 && {(_acks select 1) select 3},"public proof lag duplicated or lost a local receipt"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [_deleted==1,"republished local proof could not settle"] call _check;
    ''')


@pytest.mark.parametrize('operation',['setup','pickup'])
def test_native_inventory_callback_changing_the_kit_is_reflected_in_the_ack(operation):
    inv=converted('equipmentInventory').replace('_stock=_stock+1','_stock=_stock+1;_actor setVariable ["ACME_equipmentKitEpoch",1]')
    args='[_medic,_patient,"pro"]' if operation=='setup' else '[_medic,_patient,"pro","pickup",false,[],_deviceFixture]'
    execute(setup()+'ACME_fnc_equipmentInventory={'+inv+'''};
      ACME_fnc_itemTake={_stock=_stock-1;_medic setVariable ["ACME_equipmentKitEpoch",1];true};
    '''+args+''' call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [(_acks select 0) select 3 && {!((_acks select 0) select 5)},"ACK used context captured before native callback"] call _check;
    ''')


def test_failed_give_readback_can_retry_without_an_early_negative_ack_cancelling_later_credit():
    inv=converted('equipmentInventory').replace('_stock=_stock+1','if (_allowGive) then {_stock=_stock+1}')
    execute(setup()+'ACME_fnc_equipmentInventory={'+inv+'''};
      private _allowGive=false;
      [_medic,_patient,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1 && {!((_acks select 0) select 3)},"failed readback granted item"] call _check;
      _allowGive=true;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_deviceFixture getVariable ["ACME_eq_busy",false],"early failure cancelled a later proved credit"] call _check;
      (_acks select 1) call ACME_fnc_equipmentAck;
      [_deleted==1 && {_stock==2},"retryable give did not settle exactly once"] call _check;
    ''')


def contextual(name):
    source=(E/f'fn_{name}.sqf').read_text()
    source=source.replace('clientOwner','_fixtureMachine').replace('owner _actor','_fixtureOwner').replace('local _actor','_fixtureLocal')
    return converted(name,source)


def handoff_setup():
    return setup()+'''
      private _fixtureMachine=7;private _fixtureOwner=7;private _fixtureLocal=true;
    '''+''.join('ACME_fnc_'+name+'={'+contextual(name)+'};' for name in ['equipmentTransferStamp','equipmentInventory','equipmentAck'])


@pytest.mark.parametrize('operation',['setup','pickup'])
def test_new_machine_waits_and_original_owner_seals_unexecuted_transfer_without_inventory_access(operation):
    args='[_medic,_patient,"pro"]' if operation=='setup' else '[_medic,_patient,"pro","pickup",false,[],_deviceFixture]'
    execute(handoff_setup()+args+''' call ACME_fnc_equipmentRequest;
      private _message=+(_inventoryMessages select 0);
      _fixtureMachine=8;_fixtureOwner=8;_fixtureLocal=true;
      _caller=2;_message call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==0},"new owner guessed an unpublished previous outcome"] call _check;
      _fixtureMachine=7;_fixtureLocal=false;
      _message append [-1,-1,true];_message call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==1} && {!((_acks select 0) select 3)},"origin query touched nonlocal inventory"] call _check;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_deleted==0 && {_spawnCount==0} && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"proved unexecuted transfer did not cancel"] call _check;
      [!(_deviceFixture getVariable ["ACME_eq_busy",false]),"origin cancellation left source locked"] call _check;
    ''')


@pytest.mark.parametrize('operation',['setup','pickup'])
def test_origin_receipt_recovers_paid_transfer_when_new_owner_has_not_received_public_proof(operation):
    args='[_medic,_patient,"pro"]' if operation=='setup' else '[_medic,_patient,"pro","pickup",false,[],_deviceFixture]'
    execute(handoff_setup()+args+''' call ACME_fnc_equipmentRequest;
      private _message=+(_inventoryMessages select 0);
      _caller=2;_message call ACME_fnc_equipmentInventory;
      private _paidStock=_stock;
      private _originLocal=_medic getVariable "ACME_eqLocalReceipts";
      // A second replica has no private journal and has not received public proof yet.
      _medic setVariable ["ACME_eqLocalReceipts",createHashMap];
      _medic setVariable ["ACME_eqReceipts",createHashMap];
      _fixtureMachine=8;_fixtureOwner=8;_fixtureLocal=true;
      _message call ACME_fnc_equipmentInventory;
      [_stock==_paidStock && {count _acks==1},"new owner duplicated or guessed previous payment"] call _check;
      _fixtureMachine=7;_fixtureLocal=false;
      _medic setVariable ["ACME_eqLocalReceipts",_originLocal];
      _message append [-1,-1,true];_message call ACME_fnc_equipmentInventory;
      [_stock==_paidStock && {(_acks select 1) select 3},"origin query forgot its paid local receipt"] call _check;
      _caller=9;(_acks select 1) call ACME_fnc_equipmentAck;
      [_spawnCount==0 && {_deleted==0},"unrelated machine settled another owner's receipt"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;(_acks select 0) call ACME_fnc_equipmentAck;
      [_spawnCount+_deleted==1 && {_stock==_paidStock},"origin proof did not settle exactly once"] call _check;
    ''')


def test_foreign_machine_or_nonserver_query_cannot_seal_a_transfer():
    execute(handoff_setup()+'''
      [_medic,_patient,"pro"] call ACME_fnc_equipmentRequest;
      private _query=+(_inventoryMessages select 0);_query append [-1,-1,true];
      _fixtureMachine=9;_fixtureOwner=8;_fixtureLocal=false;_caller=2;
      _query call ACME_fnc_equipmentInventory;
      _fixtureMachine=7;_caller=9;_query call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==0} && {count (_medic getVariable ["ACME_eqLocalReceipts",createHashMap])==0},"foreign query altered terminal receipts"] call _check;
    ''')


def test_tick_queries_origin_after_handoff_but_does_not_guess_an_offline_owner_outcome():
    tick=contextual('equipmentTick')
    tick=tick.replace('remoteExecCall ["ACME_fnc_equipmentInventory",_actor]','call {_queries pushBack [_this,_fixtureOwner]}')
    tick=tick.replace('remoteExecCall ["ACME_fnc_equipmentInventory",_origin]','call {_queries pushBack [_this,_origin]}')
    execute(handoff_setup()+'ACME_fnc_equipmentTick={'+tick+'''};
      private _queries=[];
      [_medic,_patient,"pro","pickup",false,[],_deviceFixture] call ACME_fnc_equipmentRequest;
      _fixtureOwner=8;_clock=13;call ACME_fnc_equipmentTick;
      [count _queries==2 && {(_queries select 0) select 1==8} && {(_queries select 1) select 1==7} && {((_queries select 1) select 0) select 6},"handoff retry omitted origin receipt query"] call _check;
      // No reply is not a negative proof, even after a long wait.
      _clock=1000;call ACME_fnc_equipmentTick;
      [_deviceFixture getVariable ["ACME_eq_busy",false],"timeout guessed an undelivered pickup"] call _check;
      [count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==1 && {_stock==1},"offline origin timeout invented settlement"] call _check;
    ''')


def test_funded_refund_can_use_private_debit_proof_while_public_metadata_lags():
    execute(setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      ACME_fnc_equipmentPose={[]};_caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      _medic setVariable ["ACME_eqReceipts",createHashMap];
      _caller=2;(_refundMessages select 0) call ACME_fnc_equipmentInventory;
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1 && {(_acks select 1) select 3},"private funding proof was lost or refund duplicated"] call _check;
    ''')


def test_delivered_refund_receipt_recovers_from_original_machine_after_handoff():
    execute(handoff_setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      ACME_fnc_equipmentPose={[]};_caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      _caller=2;(_refundMessages select 0) call ACME_fnc_equipmentInventory;
      private _originLocal=_medic getVariable "ACME_eqLocalReceipts";
      _medic setVariable ["ACME_eqReceipts",createHashMap];_medic setVariable ["ACME_eqLocalReceipts",createHashMap];
      _fixtureMachine=8;_fixtureOwner=8;_fixtureLocal=true;
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==2},"new owner issued a duplicate refund without proof"] call _check;
      _fixtureMachine=7;_fixtureLocal=false;_medic setVariable ["ACME_eqLocalReceipts",_originLocal];
      private _query=+(_refundMessages select 0);_query append [-1,-1,true];
      _query call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 2) call ACME_fnc_equipmentAck;
      [_stock==1 && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"original refund proof could not settle"] call _check;
    ''')


def test_unexecuted_refund_waits_for_original_machine_to_regain_inventory_locality():
    execute(handoff_setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      ACME_fnc_equipmentPose={[]};_caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      private _originLocal=_medic getVariable "ACME_eqLocalReceipts";
      _medic setVariable ["ACME_eqLocalReceipts",createHashMap];
      _fixtureMachine=8;_fixtureOwner=8;_fixtureLocal=true;_caller=2;
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      _fixtureMachine=7;_fixtureLocal=false;_medic setVariable ["ACME_eqLocalReceipts",_originLocal];
      private _query=+(_refundMessages select 0);_query append [-1,-1,true];_query call ACME_fnc_equipmentInventory;
      [_stock==0 && {count _acks==1} && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==1},"unexecuted refund guessed delivery or cancellation"] call _check;
      _fixtureOwner=7;_fixtureLocal=true;_medic setVariable ["ACME_providerLocalityEpoch",2];
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [_stock==1 && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"original owner could not place its still-owed refund"] call _check;
    ''')


def test_transfer_stamp_reads_remote_published_period_instead_of_private_server_epoch():
    source=(E/'fn_equipmentTransferStamp.sqf').read_text()
    source=source.replace('local _actor','_fixtureLocal').replace('clientOwner','7').replace('owner _actor','7')
    execute('ACME_fnc_equipmentTransferStamp={'+adapt(source)+'''};
      private _fixtureLocal=false;
      _medic setVariable ["ACME_equipmentKitEpoch",3];
      _medic setVariable ["ACME_providerLocalityEpoch",0];
      _medic setVariable ["ACME_vent_batterySwapOwnerPeriod",[7,9]];
      [([_medic] call ACME_fnc_equipmentTransferStamp) isEqualTo [3,[7,9]],"server used private locality epoch"] call _check;
      _fixtureLocal=true;_medic setVariable ["ACME_providerLocalityEpoch",9];
      [([_medic] call ACME_fnc_equipmentTransferStamp) isEqualTo [3,[7,9]],"owner and server stamps disagree"] call _check;
      _fixtureLocal=false;_medic setVariable ["ACME_vent_batterySwapOwnerPeriod",[8,9]];
      [([_medic] call ACME_fnc_equipmentTransferStamp) isEqualTo [],"stale machine period admitted transfer"] call _check;
    ''')


def test_client_uses_clientowner_when_native_owner_returns_zero():
    source=(E/'fn_equipmentTransferStamp.sqf').read_text()
    source=source.replace('local _actor','_fixtureLocal').replace('isServer','false').replace('clientOwner','7').replace('owner _actor','0')
    execute('ACME_fnc_equipmentTransferStamp={'+adapt(source)+'''};
      private _fixtureLocal=true;
      _medic setVariable ["ACME_equipmentKitEpoch",3];_medic setVariable ["ACME_providerLocalityEpoch",9];
      [([_medic] call ACME_fnc_equipmentTransferStamp) isEqualTo [3,[7,9]],"client owner-zero result rejected its own inventory context"] call _check;
      _fixtureLocal=false;_medic setVariable ["ACME_vent_batterySwapOwnerPeriod",[7,9]];
      [([_medic] call ACME_fnc_equipmentTransferStamp) isEqualTo [],"non-owning client invented server authority"] call _check;
    ''')


def blood_setup():
    load=converted('equipmentCoolerLoad').replace('typeOf _box','"ACME_BloodCoolerBox_CSWB1U"')
    capacity='getNumber(configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl")'
    load=load.replace(capacity,'500')
    load=load.replace('[_actor,_id,"take",_bag] remoteExecCall ["ACME_fnc_equipmentInventory",_actor]',
                      '_inventoryMessages pushBack [_actor,_id,"take",_bag]')
    ack=converted('equipmentAck').replace(capacity,'500').replace('itemCargo _box','_boxCargo')
    ack=ack.replace('_box addItemCargoGlobal [_bag,1]','_boxCargo pushBack _bag')
    refund='[_actor,_id,"refund",_r get "item",(_r get "warm")+((_clock-(_r get "sample")) max 0),_clock] remoteExecCall ["ACME_fnc_equipmentInventory",_actor]'
    ack=ack.replace(refund,'_refundMessages pushBack [_actor,_id,"refund",_r get "item",(_r get "warm")+((_clock-(_r get "sample")) max 0),_clock]')
    return setup()+'''
      private _box=parsingNamespace;private _boxCargo=[];private _refundAges=[];
      private _bag="ACM_BloodBag_ON_500";
      private _boxState=["ACME_BloodCooler_CSWB1U",_clock,[],_clock];
      _medic setVariable ["ACME_bloodExposure",[[[_bag,500,20]],_clock]];
      ACME_bloodLooseSpoilTime=1800;
      ACME_fnc_coolerBagVolume={500};ACME_fnc_bloodColdChainTick={};
      ACME_fnc_coolerBoxReconcile={+_boxState};
      // Placement is a native boundary; record exact thermal values delivered to it.
      ACME_fnc_coolerGiveBag={_refundAges pushBack +(_this select 1);_stock=_stock+1;true};
    '''+'ACME_fnc_equipmentCoolerLoad={'+load+'};ACME_fnc_equipmentAck={'+ack+'};'


@pytest.mark.parametrize('epoch',EPOCHS)
def test_old_cooler_load_cannot_take_blood_from_replacement_inventory(epoch):
    execute(blood_setup()+f'''
      [_medic,_box,_bag] call ACME_fnc_equipmentCoolerLoad;
      [count _inventoryMessages==1,"blood load did not reserve"] call _check;
      _medic setVariable ["{epoch}",1];
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_stock==1 && {{count _boxCargo==0}},"retired cooler load stole a replacement blood bag"] call _check;
      [count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0,"cancelled load blocked checkpoint"] call _check;
    ''')


@pytest.mark.parametrize('epoch',EPOCHS)
def test_already_debited_blood_reaches_box_once_with_its_exposure_intact(epoch):
    execute(blood_setup()+f'''
      [_medic,_box,_bag] call ACME_fnc_equipmentCoolerLoad;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _medic setVariable ["{epoch}",1];_stock=5;_clock=50;
      (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;(_acks select 0) call ACME_fnc_equipmentAck;
      [_stock==5 && {{_boxCargo isEqualTo [_bag]}},"paid blood load duplicated debit or cargo"] call _check;
      [((_box getVariable "ACME_boxCoolerState") select 2) isEqualTo [[_bag,60]],"paid load renewed warm exposure"] call _check;
    ''')


@pytest.mark.parametrize('epoch',EPOCHS)
def test_failed_funded_cooler_load_refunds_one_aged_bag_after_epoch_change(epoch):
    execute(blood_setup()+f'''
      [_medic,_box,_bag] call ACME_fnc_equipmentCoolerLoad;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _medic setVariable ["{epoch}",1];_stock=5;_clock=50;
      ACME_fnc_coolerBoxReconcile={{[]}};
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      _caller=2;(_refundMessages select 0) call ACME_fnc_equipmentInventory;
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      [_stock==6 && {{_refundAges isEqualTo [[_bag,60]]}},"failed blood load lost, duplicated or renewed refund"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0,"blood refund retained pending transfer"] call _check;
    ''')


def test_delayed_blood_refund_includes_time_spent_in_the_network_queue():
    execute(blood_setup()+'''
      [_medic,_box,_bag] call ACME_fnc_equipmentCoolerLoad;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _clock=50;ACME_fnc_coolerBoxReconcile={[]};
      _caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      _clock=70;_caller=2;(_refundMessages select 0) call ACME_fnc_equipmentInventory;
      (_refundMessages select 0) call ACME_fnc_equipmentInventory;
      [_refundAges isEqualTo [[_bag,80]],"refund renewed exposure during network delay"] call _check;
    ''')


def test_new_stamp_is_local_only_and_owner_inventory_decisions_are_unscheduled():
    cfg=(E.parent/'config.cpp').read_text()
    assert 'class equipmentTransferStamp {};' in cfg
    assert 'ACME_fnc_equipmentTransferStamp' not in cfg.split('class CfgRemoteExec',1)[1]
    for name in ['equipmentInventory','equipmentCoolerLoad']:
        s=(E/f'fn_{name}.sqf').read_text()
        assert re.search(r'if \(canSuspend\) exitWith \{isNil \{[^\n]+ call ACME_fnc_'+name+r';\};\};',s)
