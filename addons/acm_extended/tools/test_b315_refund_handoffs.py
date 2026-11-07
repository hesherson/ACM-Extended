"""Execute funded refund grants, handoff closure, stale packets and native-attempt uncertainty."""
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute
from test_b308_patient_equipment import converted
from test_b314_equipment_epochs import handoff_setup, contextual, blood_setup

E=ROOT/'addons/acme_equipment/functions'


def setup():
    return handoff_setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      ACME_fnc_equipmentPose={[]};_caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      private _first=+(_refundMessages select 0);private _id=_first select 1;
      private _query=+_first;_query set [4,-1];_query set [5,-1];_query set [6,true];
    '''


def close_first():
    return '''
      _fixtureOwner=8;_fixtureMachine=7;_fixtureLocal=false;_caller=2;
      _query call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      private _second=+(_refundMessages select 1);
    '''


def test_normal_funded_refund_uses_one_correlated_grant_and_settles_once():
    execute(setup()+'''
      [(_first select 7) isEqualTo [0,7],"initial refund did not name its executor"] call _check;
      [(_medic getVariable "ACME_eqRefundLease") isEqualTo [_id,0,7],"grant metadata missing"] call _check;
      _caller=2;_first call ACME_fnc_equipmentInventory;_first call ACME_fnc_equipmentInventory;
      [_stock==1 && {(_acks select 1) select 6 isEqualTo [0,7]},"refund duplicated or lost grant correlation"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;(_acks select 2) call ACME_fnc_equipmentAck;
      [count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0 && {(_medic getVariable "ACME_eqRefundLease") isEqualTo []},"refund did not retire pending state"] call _check;
    ''')


def test_first_refund_grant_can_start_on_new_owner_without_waiting_for_admission_owner():
    execute(handoff_setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _fixtureOwner=8;_fixtureMachine=8;_fixtureLocal=true;
      _medic setVariable ["ACME_equipmentKitEpoch",1];_stock=4;
      ACME_fnc_equipmentPose={[]};_caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [((_refundMessages select 0) select 7) isEqualTo [0,8],"first refund was pinned to old source machine"] call _check;
      _medic setVariable ["ACME_eqReceipts",createHashMap];_medic setVariable ["ACME_eqLocalReceipts",createHashMap];
      _caller=2;(_refundMessages select 0) call ACME_fnc_equipmentInventory;
      _caller=8;(_acks select 1) call ACME_fnc_equipmentAck;
      [_stock==5 && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"funded new-owner refund lost or duplicated an item"] call _check;
    ''')


def test_unissued_refund_hands_off_after_negative_proof_and_ignores_duplicate_closure():
    execute(setup()+close_first()+'''
      [(_second select 7) isEqualTo [1,8] && {_stock==0},"handoff issued before proof or chose wrong owner"] call _check;
      (_acks select 1) call ACME_fnc_equipmentAck;
      [count _refundMessages==2,"duplicate closure created another generation"] call _check;
      _fixtureMachine=8;_fixtureLocal=true;_caller=2;
      _second call ACME_fnc_equipmentInventory;_second call ACME_fnc_equipmentInventory;
      _caller=8;(_acks select 2) call ACME_fnc_equipmentAck;(_acks select 3) call ACME_fnc_equipmentAck;
      [_stock==1 && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"handoff refund did not settle exactly once"] call _check;
    ''')


@pytest.mark.parametrize('lease',['[]','[0]','[0,"seven"]','[-1,7]','[0.5,7]','[0,0]','[0,9]','"bad"'])
def test_bad_or_uncorrelated_refund_packets_do_not_touch_inventory(lease):
    execute(setup()+f'''
      private _bad=+_first;_bad set [7,{lease}];_caller=2;
      _bad call ACME_fnc_equipmentInventory;
      [_stock==0 && {{count _acks==1}},"bad refund grant touched inventory or acknowledged"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_caller=9;',
    '_medic setVariable ["ACME_eqRefundLease",[]];',
    '_medic setVariable ["ACME_eqRefundLease",["other",0,7]];',
    '_medic setVariable ["ACME_eqAdmission",[]];',
])
def test_sender_or_publication_delay_cannot_authorize_refund(change):
    execute(setup()+'_caller=2;'+change+'''
      _first call ACME_fnc_equipmentInventory;
      [_stock==0 && {count _acks==1},"unauthorized or unpublished refund executed"] call _check;
    ''')


def test_missing_grant_publication_can_retry_when_exact_metadata_arrives():
    execute(setup()+'''
      private _published=_medic getVariable "ACME_eqRefundLease";
      _medic setVariable ["ACME_eqRefundLease",[]];_caller=2;
      _first call ACME_fnc_equipmentInventory;
      _medic setVariable ["ACME_eqRefundLease",_published];_first call ACME_fnc_equipmentInventory;
      [_stock==1 && {count _acks==2},"metadata retry lost or duplicated funded refund"] call _check;
    ''')


def test_new_owner_can_witness_a_delivered_receipt_without_issuing_another_item():
    execute(setup()+'''
      _caller=2;_first call ACME_fnc_equipmentInventory;
      _medic setVariable ["ACME_eqLocalReceipts",createHashMap];
      _fixtureOwner=8;_fixtureMachine=8;_fixtureLocal=true;
      _first call ACME_fnc_equipmentInventory;
      _caller=8;(_acks select 2) call ACME_fnc_equipmentAck;
      [_stock==1 && {count _refundMessages==1} && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"witness duplicated a delivered refund"] call _check;
    ''')


def test_new_owner_can_witness_sealed_negative_proof_when_original_ack_was_delayed():
    execute(setup()+'''
      _fixtureOwner=8;_fixtureMachine=7;_fixtureLocal=false;_caller=2;
      _query call ACME_fnc_equipmentInventory;
      _fixtureMachine=8;_fixtureLocal=true;_medic setVariable ["ACME_eqLocalReceipts",createHashMap];
      _first call ACME_fnc_equipmentInventory;
      _caller=8;(_acks select 2) call ACME_fnc_equipmentAck;
      [((_refundMessages select 1) select 7) isEqualTo [1,8] && {_stock==0},"negative witness could not hand off sealed attempt"] call _check;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [count _refundMessages==2,"old executor ACK reopened retired grant"] call _check;
    ''')


@pytest.mark.parametrize('change',['_caller=9;','_packet set [6,[9,7]];','_packet set [3,false];_packet set [4,true];'])
def test_unproved_or_wrong_sender_ack_cannot_complete_or_reassign_refund(change):
    execute(setup()+'''
      _caller=2;_first call ACME_fnc_equipmentInventory;
      private _packet=+(_acks select 1);_caller=7;
    '''+change+'''
      _packet call ACME_fnc_equipmentAck;
      [_stock==1 && {count _refundMessages==1} && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==1},"bad ACK settled or reassigned a paid refund"] call _check;
    ''')


def test_public_proof_lag_republishes_private_receipt_without_second_credit():
    execute(setup()+'''
      _caller=2;_first call ACME_fnc_equipmentInventory;
      _medic setVariable ["ACME_eqReceipts",createHashMap];
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==1,"missing proof guessed settlement"] call _check;
      _caller=2;_first call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 2) call ACME_fnc_equipmentAck;
      [_stock==1 && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"local proof retry duplicated refund"] call _check;
    ''')


def test_old_packet_cannot_execute_after_public_metadata_regresses_on_owner_return():
    execute(setup()+close_first()+'''
      // Return to machine 7 while generation 1 is still assigned to machine 8.
      _fixtureOwner=7;_fixtureMachine=7;_fixtureLocal=true;_caller=2;
      _second call ACME_fnc_equipmentInventory;
      [(_medic getVariable "ACME_eqLocalRefundWatermark") isEqualTo [_id,1,8],"new generation was not observed"] call _check;
      _medic setVariable ["ACME_eqRefundLease",[_id,0,7]];
      _first call ACME_fnc_equipmentInventory;
      [_stock==0 && {count _acks==2},"regressed public metadata reissued an old refund"] call _check;
    ''')


def test_away_and_back_closure_gets_fresh_generation_even_for_same_executor():
    execute(setup()+'''
      _caller=2;_query call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [((_refundMessages select 1) select 7) isEqualTo [1,7],"same-owner closure reused old generation"] call _check;
      _caller=2;_first call ACME_fnc_equipmentInventory;
      [_stock==0,"old generation executed after closure"] call _check;
      (_refundMessages select 1) call ACME_fnc_equipmentInventory;
      [_stock==1,"fresh same-owner generation could not place refund"] call _check;
    ''')


def test_temporary_owner_zero_waits_without_reusing_or_incrementing_closed_attempt():
    execute(setup()+'''
      _fixtureOwner=0;_fixtureLocal=false;_caller=2;_query call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;(_acks select 1) call ACME_fnc_equipmentAck;
      [count _refundMessages==1 && {_stock==0},"owner-zero interval issued or repeated a grant"] call _check;
      _fixtureOwner=8;[_medic,_id] call ACME_fnc_equipmentRefundRequest;
      [((_refundMessages select 1) select 7) isEqualTo [1,8],"valid owner did not receive next generation"] call _check;
    ''')


def test_capacity_readback_failure_retries_same_generation_until_one_credit_succeeds():
    helper=contextual('equipmentRefundInventory').replace('_stock=_stock+1','if (_allowGive) then {_stock=_stock+1}')
    execute(setup()+'ACME_fnc_equipmentRefundInventory={'+helper+'''};
      private _allowGive=false;_caller=2;_first call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      [_stock==0 && {count _refundMessages==1},"capacity failure settled or changed generation"] call _check;
      _allowGive=true;_caller=2;_first call ACME_fnc_equipmentInventory;
      _caller=7;(_acks select 2) call ACME_fnc_equipmentAck;
      [_stock==1 && {count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==0},"capacity retry lost or duplicated refund"] call _check;
    ''')


def test_context_change_during_failed_native_readback_stays_uncertain_instead_of_reassigning():
    helper=contextual('equipmentRefundInventory').replace('_stock=_stock+1','_actor setVariable ["ACME_equipmentKitEpoch",1]')
    execute(setup()+'ACME_fnc_equipmentRefundInventory={'+helper+'''};
      _caller=2;_first call ACME_fnc_equipmentInventory;
      _fixtureOwner=8;_fixtureLocal=false;_query call ACME_fnc_equipmentInventory;
      [_stock==0 && {count _acks==1} && {count _refundMessages==1},"uncertain native attempt was guessed unissued"] call _check;
      [count (missionNamespace getVariable ["ACME_eqPending",createHashMap])==1,"uncertain attempt allowed checkpoint settlement"] call _check;
    ''')


def test_interrupted_attempt_marker_cannot_be_sealed_as_unissued():
    execute(setup()+'''
      private _key=_id+":refund:0";
      private _journal=_medic getVariable ["ACME_eqLocalReceipts",createHashMap];
      _journal set [_key,[false,false,"attempting"]];_medic setVariable ["ACME_eqLocalReceipts",_journal];
      _fixtureOwner=8;_fixtureLocal=false;_caller=2;_query call ACME_fnc_equipmentInventory;
      [_stock==0 && {count _acks==1} && {count _refundMessages==1},"interrupted attempt was retried or cancelled"] call _check;
    ''')


def test_missing_current_context_defers_native_refund_without_guessing_outcome():
    execute(setup()+'''
      _medic setVariable ["ACME_equipmentKitEpoch","unknown"];
      _caller=2;_first call ACME_fnc_equipmentInventory;
      [_stock==0 && {count _acks==1},"unverifiable context allowed a native refund"] call _check;
    ''')


def test_server_never_grants_an_unfunded_or_unmatched_refund():
    execute(setup()+'''
      private _pending=missionNamespace getVariable "ACME_eqPending";private _r=_pending get _id;
      _r set ["debited",false];_r set ["refundLease",[]];
      [_medic,_id] call ACME_fnc_equipmentRefundRequest;
      [_patient,_id] call ACME_fnc_equipmentRefundRequest;
      [_medic,"other"] call ACME_fnc_equipmentRefundRequest;
      [_stock==0 && {count _refundMessages==1},"unfunded or mismatched request acquired a refund grant"] call _check;
    ''')


def test_retry_queries_current_refund_executor_without_reassigning_on_timeout():
    tick=contextual('equipmentTick')
    execute(setup()+'ACME_fnc_equipmentTick={'+tick+'''};
      _fixtureOwner=8;_clock=13;call ACME_fnc_equipmentTick;
      [count _refundMessages==2 && {count _refundQueries==1} && {(_refundQueries select 0) select 1==7},"retry omitted old-executor query"] call _check;
      _clock=1000;call ACME_fnc_equipmentTick;
      private _r=(missionNamespace getVariable "ACME_eqPending") get _id;
      [(_r get "refundLease") isEqualTo [0,7] && {_stock==0},"timeout guessed non-delivery and reassigned refund"] call _check;
    ''')


def test_blood_warm_exposure_survives_handoff_and_transport_delay():
    defs=''.join('ACME_fnc_'+n+'={'+contextual(n)+'};' for n in ['equipmentTransferStamp','equipmentRefundRequest','equipmentRefundInventory','equipmentInventory','equipmentAck'])
    execute(blood_setup()+'''
      private _fixtureMachine=7;private _fixtureOwner=7;private _fixtureLocal=true;
    '''+defs+'''
      [_medic,_box,_bag] call ACME_fnc_equipmentCoolerLoad;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _clock=50;ACME_fnc_coolerBoxReconcile={[]};_caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      private _query=+(_refundMessages select 0);_query set [4,-1];_query set [5,-1];_query set [6,true];
      _fixtureOwner=8;_fixtureLocal=false;_clock=70;_caller=2;_query call ACME_fnc_equipmentInventory;
      _clock=90;_caller=7;(_acks select 1) call ACME_fnc_equipmentAck;
      _fixtureMachine=8;_fixtureLocal=true;_clock=110;_caller=2;
      (_refundMessages select 1) call ACME_fnc_equipmentInventory;(_refundMessages select 1) call ACME_fnc_equipmentInventory;
      _caller=8;(_acks select 2) call ACME_fnc_equipmentAck;
      [_stock==1 && {_refundAges isEqualTo [[_bag,120]]},"blood handoff renewed age, lost bag or duplicated refund"] call _check;
    ''')


def test_refund_helpers_are_registered_locally_and_queries_have_no_new_remote_endpoint():
    cfg=(E.parent/'config.cpp').read_text();remote=cfg.split('class CfgRemoteExec',1)[1]
    for name in ['equipmentRefundRequest','equipmentRefundInventory']:
        assert 'class '+name+' {};' in cfg and 'ACME_fnc_'+name not in remote
        s=(E/f'fn_{name}.sqf').read_text()
        assert re.search(r'if \(canSuspend\) exitWith \{isNil \{[^\n]+ call ACME_fnc_'+name+r';\};\};',s)
