"""Execute exact syringe ACK/refund proof before canonical escrow is discharged.

Production ACK, archive recovery, store writes and token settlement run. Native
inventory/CBA transport and an explicitly failed store writer are boundaries;
this does not claim provider migration or real multiplayer delivery acceptance.
"""
import pytest

from test_b282_retired_syringe_recovery import setup as retired_setup
from test_b209_narc_store_owner import function
from test_menu_death_lifecycle import execute


def active_setup():
    return retired_setup() + r'''
    _job set ["flowing",true];
    missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",[]];
    missionNamespace setVariable ["ACME_HCMedPushJob",_job];
    private _activeId=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
    missionNamespace setVariable ["ACME_HCMedPushPFH",_activeId];
    ACE_player=_medic;
    '''


def test_rejected_active_slice_and_unsent_tail_restore_atomically_once():
    execute(active_setup() + r'''
    [_medic,"receipt",false,"line removed"] call ACME_fnc_medicationAck;
    [_medic,"receipt",false,"duplicate"] call ACME_fnc_medicationAck; call _flush;
    private _left=(_medic getVariable "ACME_narcStore") select 0;
    [abs ((_left select 2)-2)<0.000001 && {abs ((_left select 5 select 0 select 1)-2)<0.000001},"combined refund lost or doubled drug/component"] call _check;
    [count (_medic getVariable "ACME_medicationEscrow")==0 && {count (_medic getVariable "ACME_inventoryEscrow")==0},"proven receipt remained unsettled"] call _check;
    [(_medic getVariable "native") isEqualTo [[_syrToken,"syringe"]],"combined refund duplicated or lost carrier"] call _check;
    [count _requests==0 && {!((_handlers select _activeId) select 2)},"rejected ACK submitted more medication or retained flow"] call _check;
    ''')


def test_accepted_active_receipt_is_consumed_once_without_refunding_or_stopping_flow():
    execute(active_setup() + r'''
    [_medic,"receipt",true,"accepted"] call ACME_fnc_medicationAck;
    [_medic,"receipt",true,"duplicate"] call ACME_fnc_medicationAck;
    [(_job get "pendingAcks")==0 && {_job get "flowing"},"accepted receipt changed live flow or was counted twice"] call _check;
    [count (_medic getVariable "ACME_medicationEscrow")==0 && {(_handlers select _activeId) select 2},"accepted receipt retained escrow or stopped current worker"] call _check;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.5 && {count (_medic getVariable "native")==0},"accepted receipt invented a refund"] call _check;
    [(_job get "unsentDelta") isEqualTo [0.25,0,[[0,"Ketamine",0.25]]],"accepted receipt discarded future unsent volume"] call _check;
    ''')


@pytest.mark.parametrize('active', [True, False])
def test_failed_exact_refund_preserves_receipt_count_and_both_deltas_then_retries(active):
    execute((active_setup() if active else retired_setup()) + r'''
    private _realRestore=ACME_fnc_hardcorePushRestoreDelta;
    ACME_fnc_hardcorePushRestoreDelta={false};
    [_medic,"receipt",false,"writer unavailable"] call ACME_fnc_medicationAck;
    private _archive=missionNamespace getVariable "ACME_HCMedPushRetiredJobs";
    private _entry=_archive select 0; private _saved=_entry select 2;
    [count _archive==1 && {(_saved get "pendingAcks")==1},"failed refund consumed pending count"] call _check;
    ["receipt" in (_medic getVariable "ACME_medicationEscrow") && {"receipt" in (_entry select 4)},"failed refund erased exact receipt"] call _check;
    [(_saved get "unsentDelta") isEqualTo [0.25,0,[[0,"Ketamine",0.25]]] && {(_saved get "pushedMl")==0.5},"failed refund erased dose evidence"] call _check;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.5 && {count (_medic getVariable "native")==0},"failed writer fabricated stock"] call _check;
    ACME_fnc_hardcorePushRestoreDelta=_realRestore;
    [_medic,"receipt",false,"same immutable rejection"] call ACME_fnc_medicationAck; call _flush;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==0 && {count (_medic getVariable "ACME_medicationEscrow")==0},"retry failed to consume proven exact receipt"] call _check;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==2 && {(_medic getVariable "native") isEqualTo [[_syrToken,"syringe"]]},"retry duplicated or lost remaining syringe"] call _check;
    ''')


@pytest.mark.parametrize('boundary', [
    '_meta=+_meta; _meta set [2,"another-syringe"];',
    '_job set ["medic",_patient];',
    '_job set ["providerOwner",8];',
    '_job set ["kitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",2];',
])
def test_active_receipt_cannot_settle_another_provider_syringe_or_equipment_period(boundary):
    execute(active_setup() + boundary + r'''
    private _escrow=_medic getVariable "ACME_medicationEscrow";
    private _receipt=+(_escrow get "receipt"); _receipt set [5,_meta]; _escrow set ["receipt",_receipt];
    [_medic,"receipt",false,"foreign boundary"] call ACME_fnc_medicationAck;
    ["receipt" in (_medic getVariable "ACME_medicationEscrow"),"foreign ACK erased canonical evidence"] call _check;
    [(_job get "pendingAcks")==1 && {(_job get "pushedMl")==0.5},"foreign ACK changed dose accounting"] call _check;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.5 && {count (_medic getVariable "native")==0},"foreign ACK refunded another period"] call _check;
    ''')


@pytest.mark.parametrize('corruption', [
    '_meta set [3,[0.25,0,[[0,"Ketamine",0.20]]]]; _job set ["unsentDelta",[0.25,0,[[0,"Ketamine",0.30]]]];',
    '_meta set [3,[0.25,0,[[0,"Ketamine",0.125],[0,"Ketamine",0.125]]]];',
    '_meta set [3,[0.25,0,[[0,"Fentanyl",0.25]]]];',
    '_meta set [3,"not-a-delta"];',
    '_meta resize 3;',
])
def test_malformed_original_slices_cannot_become_valid_by_combining(corruption):
    execute(active_setup() + '_meta=+_meta;' + corruption + r'''
    private _escrow=_medic getVariable "ACME_medicationEscrow";
    private _receipt=+(_escrow get "receipt"); _receipt set [5,_meta]; _escrow set ["receipt",_receipt];
    [_medic,"receipt",false,"malformed"] call ACME_fnc_medicationAck;
    ["receipt" in (_medic getVariable "ACME_medicationEscrow") && {(_job get "pendingAcks")==1},"malformed rejection discharged debt"] call _check;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.5 && {count (_medic getVariable "native")==0},"malformed aggregation fabricated medication"] call _check;
    ''')


def test_synchronous_duplicate_ack_during_refund_cannot_reenter_settlement():
    execute(active_setup() + r'''
    private _realRestore=ACME_fnc_hardcorePushRestoreDelta; private _restoreCalls=0;
    ACME_fnc_hardcorePushRestoreDelta={
        _restoreCalls=_restoreCalls+1;
        [_medic,"receipt",false,"synchronous duplicate"] call ACME_fnc_medicationAck;
        _this call _realRestore
    };
    [_medic,"receipt",false,"original"] call ACME_fnc_medicationAck; call _flush;
    [_restoreCalls==1 && {((_medic getVariable "ACME_narcStore") select 0 select 2)==2},"synchronous duplicate replayed refund"] call _check;
    [count (_medic getVariable "ACME_medicationAckSettling")==0 && {count (_medic getVariable "ACME_medicationEscrow")==0},"completed ACK retained guard or receipt"] call _check;
    [(_medic getVariable "native") isEqualTo [[_syrToken,"syringe"]],"synchronous duplicate duplicated carrier"] call _check;
    ''')


def test_known_local_rejection_becomes_unsent_evidence_without_a_phantom_patient_receipt():
    execute(active_setup() + r'''
    _medic setVariable ["ACME_medicationEscrow",createHashMap];
    private _realRestore=ACME_fnc_hardcorePushRestoreDelta;
    ACME_fnc_hardcorePushRestoreDelta={false};
    [!([_medic,_meta,false,"local validation failed"] call ACME_fnc_hardcorePushAck),"unproved local refund reported success"] call _check;
    private _entry=(missionNamespace getVariable "ACME_HCMedPushRetiredJobs") select 0;
    private _saved=_entry select 2;
    [(_saved get "pendingAcks")==0 && {count (_entry select 4)==0},"local rejection waits for nonexistent patient receipt"] call _check;
    [(_saved get "unsentDelta") isEqualTo [0.5,0,[[0,"Ketamine",0.5]]],"local rejection lost known unsent volume"] call _check;
    ACME_fnc_hardcorePushRestoreDelta=_realRestore;
    [_medic] call ACME_fnc_hardcorePushRecover; call _flush;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==0 && {((_medic getVariable "ACME_narcStore") select 0 select 2)==2},"known local rejection could not settle exact unchanged row"] call _check;
    [count _requests==0 && {(_medic getVariable "native") isEqualTo [[_syrToken,"syringe"]]},"local recovery dispatched medication or duplicated carrier"] call _check;
    ''')


@pytest.mark.parametrize('accepted', [False, True])
def test_explicit_kit_reset_preserves_wire_retry_then_discards_only_old_syringe_accounting(accepted):
    # Unit objects are namespaces in this VM boundary; preserve the real null test.
    retry = function('medicationRetry').replace('isNull (_row select 0)', '((_row select 0) isEqualTo objNull)')
    execute(active_setup() + function('resetPersonalMedicationKit') + retry + r'''
    ACME_fnc_openVialStoreCommit={}; ACME_fnc_vialLeaseRelease={};
    private _wire=[_patient,_medic,0,"receipt","administer","leftarm",[["Ketamine_IV",12.5,true,"label"]],0,[0,1,1],_meta];
    private _escrow=_medic getVariable "ACME_medicationEscrow";
    private _receipt=+(_escrow get "receipt"); _receipt set [1,_wire]; _escrow set ["receipt",_receipt];
    private _ordinary=[_patient,["ordinary-wire"],[],0,0,["ordinary-meta"]];
    _escrow set ["ordinary",_ordinary];
    [_medic] call ACME_fnc_resetPersonalMedicationKit;
    private _retained=(_medic getVariable "ACME_medicationEscrow") get "receipt";
    [(_retained select 5 select 0)=="hcPushKitReset","fresh kit left old HC accounting active"] call _check;
    [(_retained select 1) isEqualTo _wire && {(_wire select 9 select 0)=="hcPush"} && {(_meta select 0)=="hcPush"},"reset mutated immutable patient retry metadata"] call _check;
    [((_medic getVariable "ACME_medicationEscrow") get "ordinary") isEqualTo _ordinary,"reset invalidated unrelated medication request"] call _check;
    _escrow=_medic getVariable "ACME_medicationEscrow"; _escrow deleteAt "ordinary";
    private _newRow=+_row; _newRow set [2,3]; _newRow set [5,[["Ketamine",3]]];
    _medic setVariable ["ACME_narcStore",[_newRow]];
    private _newJob=createHashMapFromArray [["medic",_medic],["session","new-session"],["stableId",_sid],["pendingAcks",1],["flowing",true]];
    missionNamespace setVariable ["ACME_HCMedPushJob",_newJob];
    private _newId=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
    missionNamespace setVariable ["ACME_HCMedPushPFH",_newId];
    uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
    private _refundCalls=0; private _hcCalls=0; private _tokenCalls=0;
    ACME_fnc_medicationRefund={_refundCalls=_refundCalls+1;};
    ACME_fnc_hardcorePushAck={_hcCalls=_hcCalls+1; false};
    ACME_fnc_skInventorySettle={_tokenCalls=_tokenCalls+1; false};
    private _wireRequests=[];
    ACME_fnc_clinicalTickDelta={2};
    missionNamespace setVariable ["ACME_clinical_ownedUnits",[_medic]];
    ACME_fnc_ownerDispatch={
        _wireRequests pushBack _this;
    ''' + f'[_medic,"receipt",{str(accepted).lower()},"patient terminal decision"] call ACME_fnc_medicationAck;' + r'''
    };
    call ACME_fnc_medicationRetry;
    call ACME_fnc_medicationRetry;
    ''' + f'[_medic,"receipt",{str(accepted).lower()},"duplicate terminal decision"] call ACME_fnc_medicationAck;' + r'''
    [count _wireRequests==1 && {((_wireRequests select 0) select 2) isEqualTo _wire},"reset changed or repeated terminal patient retry"] call _check;
    [count (_medic getVariable "ACME_medicationEscrow")==0,"terminal invalidated receipt retried forever"] call _check;
    [_refundCalls==0 && {_hcCalls==0} && {_tokenCalls==0},"old kit terminal ACK invoked accounting or token settlement"] call _check;
    [(_medic getVariable "ACME_narcStore") isEqualTo [_newRow] && {(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _newJob},"old kit ACK altered replacement syringe/controller"] call _check;
    [(_newJob get "pendingAcks")==1 && {_newJob get "flowing"} && {(_handlers select _newId) select 2} && {uiNamespace getVariable "ACME_SK_InjectionBusy"},"old kit ACK cleared replacement flow or UI"] call _check;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==0 && {count (_medic getVariable "native")==0},"old kit ACK recreated blocker or usable old carrier"] call _check;
    ''')


def test_other_provider_kit_reset_keeps_original_active_request_metadata():
    execute(active_setup() + function('resetPersonalMedicationKit') + r'''
    ACME_fnc_openVialStoreCommit={}; ACME_fnc_vialLeaseRelease={};
    [_patient] call ACME_fnc_resetPersonalMedicationKit;
    private _retained=(_medic getVariable "ACME_medicationEscrow") get "receipt";
    [(_retained select 5) isEqualTo _meta && {(_retained select 5 select 0)=="hcPush"},"another provider reset invalidated original receipt"] call _check;
    [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _job && {_job get "flowing"},"another provider reset retired original flow"] call _check;
    ''')
