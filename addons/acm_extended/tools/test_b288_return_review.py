"""Independent execution review of generic return recipient outcomes.

Native objects, locality, machine IDs and CBA delivery are explicit stand-ins;
these cases do not certify Arma transport or inventory replication.
"""
import pytest

from test_b288_resource_returns import fixture as return_fixture
from test_menu_death_lifecycle import execute
from test_historical_medication_rows import iteration_scopes


def fixture():
    # The pinned VM lacks continue; preserve each exact production iteration's
    # scope without replacing any outcome, filtering or mutation decision.
    return iteration_scopes(return_fixture())


def delivery_setup():
    return fixture()+r'''
        call _fundReturn;["request",_args] call ACME_fnc_resourceReturnBroker;
        private _packet=[_packets select 0] call ACME_fnc_syringeDeliveryCopy;
        private _key=format ["%1:%2",_request,1];
    '''


@pytest.mark.parametrize('phase',['applying','uncertain'])
def test_interrupted_or_unknown_recipient_write_is_held_on_reentry_and_query(phase):
    execute(delivery_setup()+f'private _phase="{phase}";'+r'''
        private _fingerprint=[_provider,_patient,_products,"nonce-A"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",createHashMapFromArray [[_key,[_fingerprint,_phase]]]];
        missionNamespace setVariable ["ACME_resourceReturnProgress",createHashMapFromArray [[_key,[[_phase,[]]]]]];
        _packet call ACME_fnc_resourceReturnReceive;
        _packet call ACME_fnc_resourceReturnReceive;
        [count (_provider getVariable ["ACME_usedBags",[]])==0 && {count _serverMessages==0},"unknown prior write was repeated or acknowledged"] call _check;
        _packet call ACME_fnc_resourceReturnQuery;call _flushReturns;
        [((call _returnJournal) select 4)=="ready" && {((call _returnJournal) select 9)==1},"unknown old outcome released funding to another attempt"] call _check;
    ''')


@pytest.mark.parametrize('invalid',['nonce','locality','owner'])
def test_receiver_rejects_stale_machine_or_locality_before_virtual_inventory_mutation(invalid):
    change={'nonce':'missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","replacement-nonce"];',
            'locality':'_medicLocal=false;','owner':'_machineOwner=8;'}[invalid]
    execute(delivery_setup()+change+r'''
        _packet call ACME_fnc_resourceReturnReceive;
        [count (_provider getVariable ["ACME_usedBags",[]])==0 && {count _serverMessages==0},"stale machine/locality wrote returned inventory"] call _check;
    ''')


def test_controlled_actor_switch_keeps_return_on_captured_provider_without_private_ui_context():
    execute(delivery_setup()+r'''
        ACE_player=_patient;
        _packet call ACME_fnc_resourceReturnReceive;call _flushReturns;
        [count (_provider getVariable ["ACME_usedBags",[]])==1 && {count (_patient getVariable ["ACME_usedBags",[]])==0},"return followed replacement controlled actor"] call _check;
        [((call _returnJournal) select 4)=="delivered","captured provider lost owed resource after UI switch"] call _check;
    ''')


def test_receiver_private_decision_and_live_used_row_are_not_aliases_of_mutable_wire_arrays():
    execute(delivery_setup()+r'''
        _packet call ACME_fnc_resourceReturnReceive;call _flushReturns;
        ((_packet select 3 select 0) select 1) set [2,1];
        private _decision=(missionNamespace getVariable "ACME_resourceReturnDecisions") get _key;
        [((_decision select 0 select 2 select 0) select 1 select 2)==125,"caller mutated private terminal outcome"] call _check;
        [(_provider getVariable "ACME_usedBags" select 0 select 2)==125,"caller mutated placed resource through shared nested array"] call _check;
    ''')


def test_changed_same_attempt_cannot_replace_original_delivered_product():
    execute(delivery_setup()+r'''
        _packet call ACME_fnc_resourceReturnReceive;call _flushReturns;
        private _changed=[_packet] call ACME_fnc_syringeDeliveryCopy;
        ((_changed select 3 select 0) select 1) set [2,100];
        _changed call ACME_fnc_resourceReturnReceive;
        [count (_provider getVariable "ACME_usedBags")==1 && {(_provider getVariable "ACME_usedBags" select 0 select 2)==125},"changed duplicate rewrote or duplicated original resource"] call _check;
        [count _serverMessages==0,"changed replay emitted an authorization for mismatched contents"] call _check;
    ''')


def test_cancelled_old_attempt_blocks_delayed_aba_delivery_after_new_owner_receives_once():
    execute(delivery_setup()+r'''
        _ownerNum=8;_medicLocal=false;CBA_missionTime=103;
        ["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _query=(_queries select {(_x select 0)=="ACME_resourceReturnQuery"}) select 0;
        (_query select 1) call ACME_fnc_resourceReturnQuery;call _flushReturns;
        [((call _returnJournal) select 9)==2 && {!((call _returnJournal) select 8)},"unseen old attempt was not cancelled before handoff"] call _check;
        private _oldDecisions=missionNamespace getVariable "ACME_resourceReturnDecisions";
        _machineOwner=8;_medicLocal=true;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","nonce-B"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",createHashMap];
        missionNamespace setVariable ["ACME_resourceReturnProgress",createHashMap];
        CBA_missionTime=104;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _newPacket=_packets select ((count _packets)-1);
        _newPacket call ACME_fnc_resourceReturnReceive;call _flushReturns;
        _ownerNum=7;_machineOwner=7;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","nonce-A"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",_oldDecisions];
        _packet call ACME_fnc_resourceReturnReceive;call _flushReturns;
        [count (_provider getVariable "ACME_usedBags")==1 && {((call _returnJournal) select 4)=="delivered"},"late old packet duplicated return after away/back ownership"] call _check;
    ''')


def test_reused_numeric_machine_id_cannot_cancel_or_receive_previous_incarnation_attempt():
    execute(delivery_setup()+r'''
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","replacement-nonce"];
        missionNamespace setVariable ["ACME_syringeDeliveryMachines",createHashMapFromArray [["7","replacement-nonce"]]];
        _packet call ACME_fnc_resourceReturnReceive;
        CBA_missionTime=103;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _query=(_queries select {(_x select 0)=="ACME_resourceReturnQuery"}) select 0;
        (_query select 1) call ACME_fnc_resourceReturnQuery;call _flushReturns;
        [count (_provider getVariable ["ACME_usedBags",[]])==0 && {((call _returnJournal) select 9)==1}
            && {((call _returnJournal) select 7)=="nonce-A"},"replacement process reused uncertain old funding"] call _check;
    ''')


def test_partial_product_application_cannot_cancel_whole_funding_or_repeat_completed_row():
    execute(fixture()+r'''
        private _second=["used-other","Saline",80,0,-1,250,"Saline",-1];
        _products pushBack ["used",_second];
        _provider setVariable ["ACME_usedBags",[["used-other","Saline",1,0,-1,250,"Saline",-1]]];
        call _fundReturn;["request",_args] call ACME_fnc_resourceReturnBroker;
        private _packet=_packets select 0;
        _packet call ACME_fnc_resourceReturnReceive;
        _packet call ACME_fnc_resourceReturnReceive;
        [count (_provider getVariable "ACME_usedBags")==2 && {count _serverMessages==0},"partial retry repeated delivered row or acknowledged conflicted product"] call _check;
        _packet call ACME_fnc_resourceReturnQuery;call _flushReturns;
        [((call _returnJournal) select 4)=="ready" && {((call _returnJournal) select 9)==1},"partial application released complete funding to another owner"] call _check;
    ''')
