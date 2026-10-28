"""Execute source/recipient outcome proofs for generic medical returns."""
import re

import pytest

from test_b288_fresh_grants import fixture as fresh_fixture
from test_menu_death_lifecycle import F, ROOT, adapt, execute
from test_historical_vial_execution import map_defaults
from test_historical_medication_rows import iteration_scopes


def source(name):
    text=(F/f'fn_{name}.sqf').read_text()
    for old,new in {
        'canSuspend':'false','clientOwner':'_machineOwner','local _provider':'_medicLocal',
        'owner _provider':'_ownerNum',
        'owner _recipient':'_ownerNum',
        'uniformItems _provider':'(_provider getVariable ["nativeItems",[]])',
        'vestItems _provider':'[]','backpackItems _provider':'[]',
        'nearestObject [_provider,"WeaponHolder"]':'_ground',
        'itemCargo _near':'(_near getVariable ["nativeItems",[]])',
        'itemCargo _holder':'(_holder getVariable ["nativeItems",[]])',
        '(_placement select 1) isEqualType objNull':'true',
        'isClass (configFile >> "CfgWeapons" >> _value)':'true',
        '_provider isEqualType objNull':'(_provider isEqualType profileNamespace || {_provider isEqualTo objNull})',
        '_patient isEqualType objNull':'(_patient isEqualType profileNamespace || {_patient isEqualTo objNull})',
    }.items():text=text.replace(old,new)
    text=re.sub(r'\bfinite (\([^\n]*?\)|_\w+)',r'(\1 call _finite)',text)
    return adapt(map_defaults(iteration_scopes(text)))


def fixture():
    code=fresh_fixture()+r'''
        private _provider=_medic;
        private _products=[["used",["used-canonical","Saline",125,0,-1,250,"Saline",-1]]];
        private _certificate=[7,"nonce-A"];
        _args=[_provider,_patient,_request,_products,_certificate];
        private _fundReturn={_patient setVariable ["ACME_resourceReturnFunded",createHashMapFromArray [[_request,[_provider,_products]]]];};
        private _returnJournal={(missionNamespace getVariable "ACME_resourceReturns") get _request};
        _queries=[];_packets=[];_serverMessages=[];
        CBA_fnc_targetEvent={if ((_this select 0)=="ACME_resourceReturnDelivery") then {_packets pushBack (_this select 1)};};
        CBA_fnc_ownerEvent={_queries pushBack _this};
        private _flushReturns={while {count _serverMessages>0} do {private _m=_serverMessages deleteAt 0;if ((_m select 0)=="ACME_resourceReturn") then {(_m select 1) call ACME_fnc_resourceReturnBroker;};};};
    '''
    for name in ['resourceReturnProductsValid','resourceReturnBroker','resourceReturnReceive','resourceReturnQuery','resourceReturnSourceQuery']:
        code+='ACME_fnc_'+name+'={'+source(name)+'};'
    return code


def test_funded_used_product_does_not_depend_on_private_ui_context_and_replays_once():
    execute(fixture()+r'''
        call _fundReturn;["request",_args] call ACME_fnc_resourceReturnBroker;
        private _packet=+(_packets select 0);_packet call ACME_fnc_resourceReturnReceive;call _flushReturns;
        _packet call ACME_fnc_resourceReturnReceive;call _flushReturns;
        [count (_provider getVariable "ACME_usedBags")==1 && {((call _returnJournal) select 4)=="delivered"},"new-owner-compatible return was lost or duplicated"] call _check;
    ''')


def test_patient_deleted_before_public_proof_uses_only_committed_original_machine_certificate():
    execute(fixture()+r'''
        _patient=objNull;_args set [1,objNull];
        private _sources=createHashMapFromArray [[_request,[[_provider,objNull,_products,"nonce-A"],"funded",_certificate]]];
        missionNamespace setVariable ["ACME_resourceReturnSources",_sources];
        ["request",_args] call ACME_fnc_resourceReturnBroker;
        [count _packets==0 && {count (missionNamespace getVariable ["ACME_resourceReturns",createHashMap])==0},"unproven deleted source admitted products"] call _check;
        private _q=(_queries select {(_x select 0)=="ACME_resourceReturnSourceQuery"}) select 0;
        (_q select 1) call ACME_fnc_resourceReturnSourceQuery;call _flushReturns;
        [count _packets==1 && {((call _returnJournal) select 4)=="ready"},"committed private source proof could not recover deleted patient"] call _check;
        (_packets select 0) call ACME_fnc_resourceReturnReceive;call _flushReturns;
        [count (_provider getVariable "ACME_usedBags")==1 && {((call _returnJournal) select 4)=="delivered"},"deleted patient lost funded product"] call _check;
    ''')


@pytest.mark.parametrize('state',['applying','uncertain','missing'])
def test_failed_or_unconfirmed_source_debit_never_becomes_positive_funding(state):
    execute(fixture()+f'private _sourceState="{state}";'+r'''
        private _sources=createHashMap;
        if (_sourceState!="missing") then {_sources set [_request,[[_provider,_patient,_products,"nonce-A"],_sourceState,_certificate]];};
        missionNamespace setVariable ["ACME_resourceReturnSources",_sources];
        ["request",_args] call ACME_fnc_resourceReturnBroker;
        private _q=(_queries select {(_x select 0)=="ACME_resourceReturnSourceQuery"}) select 0;
        (_q select 1) call ACME_fnc_resourceReturnSourceQuery;call _flushReturns;
        [count _packets==0 && {count _serverMessages==0} && {count (missionNamespace getVariable ["ACME_resourceReturns",createHashMap])==0},"unconfirmed debit minted returned inventory"] call _check;
    ''')


def test_recipient_private_decision_proves_delivery_after_missing_receipt_replication():
    execute(fixture()+r'''
        call _fundReturn;["request",_args] call ACME_fnc_resourceReturnBroker;
        (_packets select 0) call ACME_fnc_resourceReturnReceive;
        _serverMessages=[];_provider setVariable ["ACME_resourceReturnReceived",createHashMap];
        _ownerNum=8;_medicLocal=false;CBA_missionTime=103;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _q=(_queries select {(_x select 0)=="ACME_resourceReturnQuery"}) select 0;
        (_q select 1) call ACME_fnc_resourceReturnQuery;call _flushReturns;
        [((call _returnJournal) select 4)=="delivered" && {count (_provider getVariable "ACME_usedBags")==1},"migration lost original machine delivery decision"] call _check;
    ''')


def test_deleted_recipient_keeps_verified_funding_in_quiet_server_escrow_without_redirect():
    execute(fixture()+r'''
        _provider=objNull;_args set [0,objNull];call _fundReturn;
        ["request",_args] call ACME_fnc_resourceReturnBroker;
        [((call _returnJournal) select 4)=="orphaned" && {((call _returnJournal) select 3) isEqualTo _products},"deleted recipient lost canonical funded products"] call _check;
        [count _packets==0 && {(missionNamespace getVariable "ACME_resourceReturnActive") isEqualTo []}
            && {(missionNamespace getVariable "ACME_resourceReturnPFH")==-1},"orphaned funding redirected or retained active transport work"] call _check;
    ''')


def test_deleted_dispatched_recipient_waits_for_original_machine_decision_before_orphaning():
    execute(fixture()+r'''
        call _fundReturn;["request",_args] call ACME_fnc_resourceReturnBroker;
        private _j=call _returnJournal;_j set [0,objNull];_provider=objNull;
        CBA_missionTime=103;["tick",[]] call ACME_fnc_resourceReturnBroker;
        private _q=(_queries select {(_x select 0)=="ACME_resourceReturnQuery"}) select 0;
        [((_q select 1) select 0) isEqualTo objNull && {((call _returnJournal) select 4)=="ready"},"recipient deletion guessed delivery outcome"] call _check;
        (_q select 1) call ACME_fnc_resourceReturnQuery;call _flushReturns;
        [((call _returnJournal) select 4)=="orphaned" && {count _packets==1},"proven unseen grant did not enter held escrow or created replacement actor"] call _check;
    ''')


def test_public_event_cannot_supply_internal_source_certification_flags():
    init=(ROOT/'addons/circulation/XEH_postInit.sqf').read_text()
    handler=init.split('["ACME_resourceReturn", {',1)[1].split('}] call CBA_fnc_addEventHandler;',1)[0]
    execute(fixture()+'private _wireHandler={'+adapt(handler,'circulation')+'};'+r'''
        ["request",_args,false,true] call _wireHandler;
        [count _packets==0 && {count (missionNamespace getVariable ["ACME_resourceReturns",createHashMap])==0},"wire-supplied internal flag bypassed source proof"] call _check;
        ["request",_args] call _wireHandler;
        [count _packets==0 && {count (missionNamespace getVariable ["ACME_resourceReturns",createHashMap])==0},"ordinary unfunded wire bypassed admission"] call _check;
    ''')


def test_positive_public_receipt_settles_after_ack_loss_and_original_process_disappears():
    execute(fixture()+r'''
        call _fundReturn;["request",_args] call ACME_fnc_resourceReturnBroker;
        (_packets select 0) call ACME_fnc_resourceReturnReceive;
        _serverMessages=[];
        _ownerNum=8;_machineOwner=8;
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","nonce-B"];
        missionNamespace setVariable ["ACME_resourceReturnDecisions",createHashMap];
        CBA_missionTime=103;["tick",[]] call ACME_fnc_resourceReturnBroker;
        [((call _returnJournal) select 4)=="delivered" && {count (_provider getVariable "ACME_usedBags")==1},"known positive public delivery waited forever for missing original process"] call _check;
    ''')
