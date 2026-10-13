"""Execute stopped syringe settlement after a controlled-unit switch.

Actual plunger retirement, patient ACK, exact token broker/settlement and Narc
Box writers run. Native magazine cargo and CBA transport are explicit fixtures;
this does not simulate Arma replication or transfer a live plunger to a new owner.
"""
import pytest

from test_b209_narc_store_owner import function, setup as push_setup
from test_b279_inventory_ledger import setup as ledger_setup
from test_menu_death_lifecycle import execute
from test_historical_medication_rows import iteration_scopes


def setup():
    return iteration_scopes(ledger_setup()) + push_setup() + ''.join(function(n) for n in (
        'skInventoryCommit', 'skInventorySettle', 'medicationAck',
        'medicationRefund', 'medicationEscrowCommit')) + r'''
    private _sid="owned-row";
    private _row=["Ketamine",3,2,"label",0,[["Ketamine",2]],"compoundB13","none","","","",_sid,"","inventoryB279"];
    _medic setVariable ["ACME_narcStore",[_row]];
    [_medic,"syringe",[[_sid,_row]]] call ACME_fnc_inventoryLedgerCommit; call _flush;
    private _syrToken=(missionNamespace getVariable "ACME_inventoryLedgerIndex") get "syringe:owned-row";
    private _inventoryRequest="syringe-reservation";
    [_medic,"syringe",_sid,_inventoryRequest] call ACME_fnc_inventoryLedgerReserve;
    [_medic,_inventoryRequest,{},[]] call ACME_fnc_inventoryLedgerClaim; call _flush;
    private _live=+_row; _live set [2,1.5]; _live set [5,[["Ketamine",1.5]]];
    [_medic,[_live],false] call ACME_fnc_narcStoreCommit;
    private _meta=["hcPush","owned-session",_sid,[0.25,0,[[0,"Ketamine",0.25]]]];
    _medic setVariable ["ACME_medicationEscrow",createHashMapFromArray [["receipt",[_patient,[],[],0,0,_meta]]]];
    private _job=createHashMapFromArray [
      ["medic",_medic],["patient",_patient],["flowing",true],["providerLocalityEpoch",0],["providerOwner",7],["kitEpoch",0],
      ["identity",[0,1,1]],["stableId",_sid],["session","owned-session"],
      ["pendingAcks",1],["unsentDelta",[0.25,0,[[0,"Ketamine",0.25]]]],["pushedMl",0.5],
      ["inventoryBacked",true],["inventoryRequest",_inventoryRequest],["virtual",true]];
    missionNamespace setVariable ["ACME_HCMedPushJob",_job];
    private _id=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
    missionNamespace setVariable ["ACME_HCMedPushPFH",_id];
    ACE_player=_patient;
    call ACME_fnc_hardcorePushTick;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==1,"push did not retire"] call _check;
    '''


@pytest.mark.parametrize('accepted', [False, True])
@pytest.mark.parametrize('duplicate', [False, True])
def test_actual_late_patient_ack_settles_exact_remaining_volume_and_one_token(accepted, duplicate):
    execute(setup() + f'[_medic,"receipt",{str(accepted).lower()},"late"] call ACME_fnc_medicationAck;' +
            (f'[_medic,"receipt",{str(accepted).lower()},"duplicate"] call ACME_fnc_medicationAck;' if duplicate else '') +
            'call _flush;' + f'private _expected={1.75 if accepted else 2.0};' + r'''
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==0,"settled archive retained blocker"] call _check;
    [count (_medic getVariable "ACME_medicationEscrow")==0 && {count (_medic getVariable "ACME_inventoryEscrow")==0},"settled receipt/token held"] call _check;
    [(_medic getVariable "native") isEqualTo [[_syrToken,"syringe"]],"exact token missing or duplicated"] call _check;
    private _final=(missionNamespace getVariable format ["ACME_inventoryToken_%1",_syrToken]) select 2 select 1;
    [abs ((_final select 2)-_expected)<0.000001 && {abs ((_final select 5 select 0 select 1)-_expected)<0.000001},"drug/component lost or duplicated"] call _check;
    [count _requests==0 && {count _returnedMagazines==0},"recovery submitted dose or created native syringe duplicate"] call _check;
    [!((_handlers select _id) select 2) && {(missionNamespace getVariable "ACME_HCMedPushPFH")==-1},"recovery resumed flow"] call _check;
    ''')


def test_missing_ack_restores_only_known_unsent_tail_and_keeps_submitted_dose_reserved():
    execute(setup() + r'''
    [_medic] call ACME_fnc_hardcorePushRecover;
    [_medic] call ACME_fnc_hardcorePushRecover;
    private _remaining=(_medic getVariable "ACME_narcStore") select 0;
    [abs ((_remaining select 2)-1.75)<0.000001,"unsent tail lost or restored twice"] call _check;
    [count (_medic getVariable "native")==0 && {count (_medic getVariable "ACME_inventoryEscrow")==1},"missing ACK manufactured usable stock"] call _check;
    private _archive=missionNamespace getVariable "ACME_HCMedPushRetiredJobs";
    [count _archive==1 && {((_archive select 0 select 2) get "pendingAcks")==1},"missing ACK was forgiven"] call _check;
    [count _requests==0,"recovery sent undispatched tail to patient"] call _check;
    ''')


@pytest.mark.parametrize('boundary', [
    '_medicLocal=false;',
    '_medic setVariable ["ACME_providerLocalityEpoch",2];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_job set ["providerOwner",8];',
    '_medic setVariable ["ACME_narcStore",[]];',
    'private _new=+_live; _new set [2,2.5]; _medic setVariable ["ACME_narcStore",[_new]];',
])
def test_foreign_epoch_kit_missing_or_edited_row_remains_unresolved_without_refund(boundary):
    execute(setup()+boundary+r'''
    private _before=+(_medic getVariable "ACME_narcStore");
    [!([_medic,"owned-session","receipt",_meta,false] call ACME_fnc_hardcorePushRecover),"foreign archive recovered"] call _check;
    [(_medic getVariable "ACME_narcStore") isEqualTo _before,"foreign archive rewrote row"] call _check;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==1 && {count (_medic getVariable "native")==0},"foreign archive refunded/discarded evidence"] call _check;
    ''')


@pytest.mark.parametrize('receipt', ['missing', 'wrong-meta'])
def test_unknown_or_changed_ack_cannot_discharge_archive(receipt):
    execute(setup() + ('_meta=+_meta; _meta set [2,"other-syringe"];' if receipt=='wrong-meta' else '') +
            f'private _requestId="{("receipt" if receipt=="wrong-meta" else "missing")}";' + r'''
    [!([_medic,"owned-session",_requestId,_meta,false] call ACME_fnc_hardcorePushRecover),"unknown ACK settled archive"] call _check;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.5,"unknown ACK refunded volume"] call _check;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==1,"unknown ACK removed archive"] call _check;
    ''')


def test_archive_settlement_preserves_another_providers_active_job_ui_and_handler():
    execute(setup()+r'''
    private _other=createHashMapFromArray [["medic",_patient],["session","other-session"],["flowing",true],["pendingAcks",2]];
    missionNamespace setVariable ["ACME_HCMedPushJob",_other];
    private _otherId=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
    missionNamespace setVariable ["ACME_HCMedPushPFH",_otherId];
    uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
    uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
    [_medic,"receipt",false,"late"] call ACME_fnc_medicationAck; call _flush;
    [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _other && {_other get "flowing"},"archive altered active job"] call _check;
    [(_handlers select _otherId) select 2 && {(missionNamespace getVariable "ACME_HCMedPushPFH")==_otherId},"archive removed active worker"] call _check;
    [uiNamespace getVariable "ACME_SK_InjectionBusy" && {uiNamespace getVariable "ACME_SK_CarouselBusy"},"archive cleared active UI"] call _check;
    ''')


def test_tail_only_archive_settles_without_waiting_for_an_ack_that_was_never_sent():
    execute(setup()+r'''
    private _archive=missionNamespace getVariable "ACME_HCMedPushRetiredJobs";
    private _entry=_archive select 0;
    private _saved=_entry select 2; _saved set ["pendingAcks",0]; _saved set ["pushedMl",0.25];
    _entry set [4,createHashMap];
    [_medic] call ACME_fnc_hardcorePushRecover; call _flush;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==0 && {count (_medic getVariable "native")==1},"tail-only archive stayed blocked"] call _check;
    [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.75,"tail-only archive duplicated submitted dose"] call _check;
    ''')


def start_fixture():
    # Full Start executes; display controls, sound and redraw calls are native boundaries.
    start = function('hardcorePushStart')
    start = start.replace('playSound "ACME_SyringePush";', '_sounds pushBack "ACME_SyringePush";')
    start = start.replace('_d displayCtrl _x', 'objNull')
    start = start.replace('objectParent ACE_player', '_medicVehicle')
    start = start.replace('localize _key', '_key')
    start = start.replace('safeZoneW', '1').replace('safeZoneH', '1')
    start = start.replace('["_inventoryRequest","",[""]]', '["_inventoryRequest",""]')
    return r'''
    private _sounds=[];
    private _selected=1;
    _drawDisplay=missionNamespace;
    ACE_player=_medic;
    uiNamespace setVariable ["ACME_SK_View","body"];
    uiNamespace setVariable ["ACME_SK_Patient",_patient];
    uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",0,"vascular"]];
    ACME_fnc_skStoreEnsureIds={(_this select 0) getVariable ["ACME_narcStore",[]]};
    ACME_fnc_skSelectedIndex={_selected};
    ACME_fnc_skCarouselRender={}; ACME_fnc_skBodyActionRender={};
    ''' + function('skInventoryReserve') + start


def test_full_start_allows_another_exact_funded_syringe_while_old_receipt_is_pending():
    execute(setup()+start_fixture()+r'''
    private _otherRow=+_row; _otherRow set [11,"other-syringe"];
    [_medic,"syringe",[["other-syringe",_otherRow]]] call ACME_fnc_inventoryLedgerCommit; call _flush;
    private _before=(_medic getVariable "ACME_narcStore") select 0;
    [_medic,[_before,_otherRow],false] call ACME_fnc_narcStoreCommit;
    [([] call ACME_fnc_hardcorePushStart),"old exact syringe blocked another funded syringe"] call _check;
    call _flush;
    private _new=missionNamespace getVariable "ACME_HCMedPushJob";
    [(_new get "stableId")=="other-syringe" && {_new get "flowing"},"different funded syringe did not start"] call _check;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==1,"new syringe discarded prior debt"] call _check;
    [count (_medic getVariable "ACME_inventoryEscrow")==2,"new syringe reused or released old token"] call _check;
    [count _requests==0 && {count _sounds==1},"starting another syringe delivered old tail or replayed presentation"] call _check;
    ''')


def test_full_start_keeps_exact_unsettled_syringe_blocked_before_reservation_or_flow():
    execute(setup()+start_fixture()+r'''
    _selected=0;
    [!([] call ACME_fnc_hardcorePushStart),"exact unsettled syringe restarted"] call _check;
    [count (missionNamespace getVariable "ACME_HCMedPushJob")==0 && {count _sounds==0},"unsettled syringe resumed worker"] call _check;
    [count (_medic getVariable "ACME_inventoryEscrow")==1 && {count _requests==0},"blocked restart reserved another token or submitted tail"] call _check;
    private _left=(_medic getVariable "ACME_narcStore") select 0 select 2;
    [abs (_left-1.75)<0.000001,"Start did not restore only its known unsent tail"] call _check;
    ''')


@pytest.mark.parametrize('first_accepted,second_accepted', [(True, False), (False, True), (False, False), (True, True)])
def test_multiple_out_of_order_aliquots_wait_for_each_exact_receipt(first_accepted, second_accepted):
    execute(setup()+r'''
    private _archive=missionNamespace getVariable "ACME_HCMedPushRetiredJobs";
    private _entry=_archive select 0;
    private _saved=_entry select 2;
    private _moreLive=+_live; _moreLive set [2,1.25]; _moreLive set [5,[["Ketamine",1.25]]];
    [_medic,[_moreLive],false] call ACME_fnc_narcStoreCommit;
    _entry set [3,+_moreLive];
    _saved set ["pendingAcks",2]; _saved set ["pushedMl",0.75];
    private _meta2=+_meta;
    private _escrow=createHashMapFromArray [
        ["receipt",[_patient,[],[],0,0,_meta]], ["receipt2",[_patient,[],[],0,0,_meta2]]];
    private _captured=createHashMap;
    {_captured set [_x,+(_escrow get _x)];} forEach (keys _escrow);
    _entry set [4,_captured]; _medic setVariable ["ACME_medicationEscrow",_escrow];
    '''+f'[_medic,"receipt2",{str(second_accepted).lower()},"second arrived first"] call ACME_fnc_medicationAck;'+r'''
    [count (_medic getVariable "native")==0 && {count (_medic getVariable "ACME_inventoryEscrow")==1},"first of two ACKs released token"] call _check;
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==1,"one ACK forgave other debt"] call _check;
    '''+f'[_medic,"receipt",{str(first_accepted).lower()},"first arrived second"] call ACME_fnc_medicationAck; call _flush;'+
      f'private _expected={1.5+0.25*(not first_accepted)+0.25*(not second_accepted)};'+r'''
    [count (missionNamespace getVariable "ACME_HCMedPushRetiredJobs")==0 && {count (_medic getVariable "native")==1},"all exact receipts failed to settle"] call _check;
    private _remaining=(_medic getVariable "ACME_narcStore") select 0;
    [abs ((_remaining select 2)-_expected)<0.000001 && {abs ((_remaining select 5 select 0 select 1)-_expected)<0.000001},"out-of-order delivery/refund changed exact remaining volume"] call _check;
    ''')


@pytest.mark.parametrize('mutation', ['epoch', 'tail_once', 'rejected_delta', 'detached_job'])
def test_semantic_mutations_are_rejected_by_execution(monkeypatch, mutation):
    import test_b209_narc_store_owner as adapter
    original=adapter.source
    replacements={
        'epoch': ('hardcorePushRecover', '_epoch != (_medic getVariable ["ACME_providerLocalityEpoch",0])', 'false'),
        'tail_once': ('hardcorePushRecover', '_job set ["unsentDelta",[0,0,[]]];', ''),
        'rejected_delta': ('hardcorePushRecover', 'if (!_accepted) then {', 'if (false) then {'),
        'detached_job': ('hardcorePushFinalize', 'if (_detached) exitWith {true};', 'if (false) exitWith {true};'),
    }
    name,old,new=replacements[mutation]
    assert old in original(name)
    def changed(function_name):
        text=original(function_name)
        return text.replace(old,new,1) if function_name==name else text
    monkeypatch.setattr(adapter,'source',changed)
    calls={
        'epoch': (lambda: test_foreign_epoch_kit_missing_or_edited_row_remains_unresolved_without_refund('_medic setVariable ["ACME_providerLocalityEpoch",2];'), 'foreign archive recovered'),
        'tail_once': (test_missing_ack_restores_only_known_unsent_tail_and_keeps_submitted_dose_reserved, 'unsent tail lost or restored twice'),
        'rejected_delta': (lambda: test_actual_late_patient_ack_settles_exact_remaining_volume_and_one_token(False,False), 'drug/component lost or duplicated'),
        'detached_job': (test_archive_settlement_preserves_another_providers_active_job_ui_and_handler, 'archive altered active job'),
    }
    case,reason=calls[mutation]
    with pytest.raises(AssertionError,match=reason):
        case()
