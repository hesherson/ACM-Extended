"""Execute stopped-batch recovery and atomic rejected-dose validation.

The real Stop, SendBatch, RestoreDelta, store writer and Finalize execute. Native
inventory, UI and medication transport remain the explicit b209 fixtures; these
checks do not claim to reproduce Arma replication or packet delivery.
"""
import pytest

from test_b209_narc_store_owner import setup
from test_menu_death_lifecycle import execute


def stopped_batch():
    return setup() + r'''
        private _row=["Ketamine",3,1.5,"label",0,[["Ketamine",1.5]],"compoundB13","none","","","","owned-row"];
        _medic setVariable ["ACME_narcStore",[_row]];
        private _job=createHashMapFromArray [
            ["medic",_medic],["patient",_patient],["flowing",true],
            ["providerLocalityEpoch",0],["providerOwner",7],["kitEpoch",0],
            ["identity",[0,1,1]],["stableId","owned-row"],["session","owned-session"],
            ["pendingAcks",0],["unsentDelta",[0.5,0,[[0,"Ketamine",0.5]]]],["batchElapsed",0.5],
            ["pushedMl",0.5],["virtual",true],["kind","compoundB13"],["med","Ketamine"]
        ];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        private _id=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
        missionNamespace setVariable ["ACME_HCMedPushPFH",_id];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
        uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
        // A configuration/route change can make the real SendBatch reject the
        // complete batch before medicationRequest owns an acknowledgement.
        ACME_fnc_medicationRouteAllowed={false};
    '''


@pytest.mark.parametrize('reason', ['manual', 'complete'])
def test_real_pre_dispatch_batch_failure_restores_tail_and_settles_once(reason):
    execute(stopped_batch() + f'["{reason}"] call ACME_fnc_hardcorePushStop;' + r'''
        private _remaining=(_medic getVariable "ACME_narcStore") select 0;
        [(_remaining select 2)==2 && {(_remaining select 5) isEqualTo [["Ketamine",2]]},"failed pre-dispatch batch stranded unsent solution"] call _check;
        [count _requests==0 && {count _returnedMagazines==0},"failed batch dispatched medication or manufactured native syringe"] call _check;
        [count _retiredNotices==0,"failed batch reported a successful completed push"] call _check;
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0,"failed pre-dispatch batch retained stopped UI lock"] call _check;
        [({ _x } count _publicationFlags)==1,"restored stop did not settle exactly once"] call _check;
        [!(uiNamespace getVariable "ACME_SK_InjectionBusy") && {!(uiNamespace getVariable "ACME_SK_CarouselBusy")},"restored stop retained busy controls"] call _check;
        [!((_handlers select _id) select 2) && {(missionNamespace getVariable "ACME_HCMedPushPFH")==-1},"restored stop retained worker"] call _check;
        [!(["manual"] call ACME_fnc_hardcorePushStop),"duplicate stop settled a missing job"] call _check;
        [((_medic getVariable "ACME_narcStore") select 0) isEqualTo _remaining && {({ _x } count _publicationFlags)==1},"duplicate stop refunded or published twice"] call _check;
    ''')


@pytest.mark.parametrize('reason', ['manual', 'complete', 'access'])
def test_failed_tail_refund_retires_evidence_without_finalizing_or_publishing(reason):
    execute(stopped_batch() + r'''
        _medic setVariable ["ACME_narcStore",[]];
    ''' + f'private _result=["{reason}"] call ACME_fnc_hardcorePushStop;' + r'''
        [!_result,"failed tail refund reported settled success"] call _check;
        private _archive=missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]];
        [count _archive==1,"failed refund did not preserve one exact stopped job"] call _check;
        if (count _archive==1) then {
            private _saved=(_archive select 0) select 2;
            [(_saved get "unsentDelta") isEqualTo [0.5,0,[[0,"Ketamine",0.5]]] && {(_saved get "pushedMl")==0.5},"failed refund discharged unresolved volume"] call _check;
        };
        [count _requests==0 && {count _publicationFlags==0} && {count _returnedMagazines==0},"failed refund dispatched, published or returned stock"] call _check;
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0 && {!((_handlers select _id) select 2)},"failed refund left an active controller"] call _check;
    ''')


@pytest.mark.parametrize('replacement', ['dispatch', 'retirement'])
def test_synchronous_successor_during_dispatch_or_retirement_keeps_its_store_ui_and_worker(replacement):
    execute(stopped_batch() + r'''
        private _successorRow=["Ketamine",3,1,"successor",0,[["Ketamine",1]],"compoundB13","none","","","","successor-row"];
        _patient setVariable ["ACME_narcStore",[_successorRow]];
        private _successor=createHashMapFromArray [
            ["medic",_patient],["patient",_medic],["flowing",true],
            ["stableId","successor-row"],["session","successor-session"],
            ["pendingAcks",0],["unsentDelta",[0,0,[]]],["virtual",true]
        ];
        private _successorId=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
        private _overlayCalls=0;
        private _replace={
            missionNamespace setVariable ["ACME_HCMedPushJob",_successor];
            missionNamespace setVariable ["ACME_HCMedPushPFH",_successorId];
            uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
            uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
        };
    ''' + (r'''
        ACME_fnc_medicationRouteAllowed={true};
        ACME_fnc_medicationRequest={_requests pushBack _this; call _replace; true};
        ACME_fnc_hardcorePushOverlay={_overlayCalls=_overlayCalls+1;};
    ''' if replacement == 'dispatch' else r'''
        _medic setVariable ["ACME_narcStore",[]];
        ACME_fnc_hardcorePushOverlay={_overlayCalls=_overlayCalls+1; call _replace;};
    ''') + r'''
        ["manual"] call ACME_fnc_hardcorePushStop;
        [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _successor && {_successor get "flowing"},"old stop finalized or replaced successor"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushPFH")==_successorId && {(_handlers select _successorId) select 2},"old stop removed successor worker"] call _check;
        [uiNamespace getVariable "ACME_SK_InjectionBusy" && {uiNamespace getVariable "ACME_SK_CarouselBusy"},"old stop cleared successor controls"] call _check;
        [(_patient getVariable "ACME_narcStore") isEqualTo [_successorRow] && {count _publicationFlags==0},"old stop published or settled successor stock"] call _check;
    ''' + f'[_overlayCalls=={0 if replacement == "dispatch" else 1},"old stop cleared successor overlay"] call _check;')


def restore_setup():
    return setup() + r'''
        private _row=["Ketamine",3,1.25,"label",0.25,[["Ketamine",1],["Propofol",0.25]],"compoundB13","none","","","","owned-row"];
        _medic setVariable ["ACME_narcStore",[_row]];
        private _before=+(_medic getVariable "ACME_narcStore");
    '''


@pytest.mark.parametrize('delta', [
    '[0.5,0,[[0,"ChangedMedication",0.5]]]',
    '[0.5,0,[[2,"Ketamine",0.5]]]',
    '[0.5,0,[[0.5,"Ketamine",0.5]]]',
    '[0.5,0,[[0,"Ketamine",0.25],[0,"Ketamine",0.25]]]',
    '[0.5,0,[[0,"Ketamine",0.25]]]',
    '[0.5,0,[[0,"Ketamine",0.75]]]',
    '[0.5,0,[]]',
    '[-0.5,0,[[0,"Ketamine",0.5]]]',
    '[0.5,-0.1,[[0,"Ketamine",0.5]]]',
    '[0.5,0,[[0,"Ketamine",-0.5]]]',
    '[0.5,0,[[0,"Ketamine"]]]',
    '[0.5,0,[[0,"Ketamine","wrong-type"]]]',
    '[0.5,0,["invalid-component"]]',
    '["wrong-drug-type",0,[]]',
    '[0.5,"wrong-saline-type",[[0,"Ketamine",0.5]]]',
    '[0.5,0,"wrong-component-array-type"]',
    '"wrong-delta-type"',
    '[2,0,[[0,"Ketamine",2]]]',
])
def test_invalid_component_or_volume_refund_is_atomic_and_does_not_publish(delta):
    execute(restore_setup() + f'private _result=[_medic,"owned-row",{delta}] call ACME_fnc_hardcorePushRestoreDelta;' + r'''
        [!_result,"invalid rejected dose reported restored success"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _before,"invalid rejected dose partially changed syringe"] call _check;
        [count _publicationFlags==0 && {count _requests==0} && {count _returnedMagazines==0},"invalid refund touched stock, transport or publication"] call _check;
    ''')


def test_valid_complete_mixture_refund_preserves_component_volume_and_writes_privately():
    execute(restore_setup() + r'''
        [[_medic,"owned-row",[0.5,0.25,[[0,"Ketamine",0.125],[1,"Propofol",0.375]]]] call ACME_fnc_hardcorePushRestoreDelta,"valid complete mixture rejected"] call _check;
        private _after=(_medic getVariable "ACME_narcStore") select 0;
        [(_after select 2)==1.75 && {(_after select 4)==0.5} && {(_after select 5) isEqualTo [["Ketamine",1.125],["Propofol",0.625]]},"complete mixture restored wrong component or volume"] call _check;
        [(_after select [6,6]) isEqualTo (_row select [6,6]),"mixture refund changed syringe metadata or stable identity"] call _check;
        [_publicationFlags isEqualTo [false] && {count _requests==0} && {count _returnedMagazines==0},"valid private refund published, dispatched or returned native stock"] call _check;
    ''')


@pytest.mark.parametrize('parts', ['["invalid-existing-component"]', '[["Ketamine",1],["Propofol",0.5]]'])
def test_invalid_existing_component_state_is_retained_without_partial_refund(parts):
    execute(restore_setup() + f'_row set [5,{parts}];' + r'''
        _medic setVariable ["ACME_narcStore",[_row]];
        _before=+(_medic getVariable "ACME_narcStore");
        [!([_medic,"owned-row",[0.5,0,[[0,"Ketamine",0.5]]]] call ACME_fnc_hardcorePushRestoreDelta),"invalid current component state was overwritten"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _before && {count _publicationFlags==0},"invalid current components partially refunded or published"] call _check;
    ''')


def test_failed_store_writer_is_not_reported_as_a_successful_refund():
    execute(restore_setup() + r'''
        private _attempts=[];
        ACME_fnc_narcStoreCommit={_attempts pushBack _this;false};
        [!([_medic,"owned-row",[0.5,0.25,[[0,"Ketamine",0.125],[1,"Propofol",0.375]]]] call ACME_fnc_hardcorePushRestoreDelta),"failed store writer discharged refund debt"] call _check;
        [count _attempts==1 && {!((_attempts select 0) select 2)},"valid refund did not request one private store write"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _before && {count _publicationFlags==0},"failed store writer changed source state or published"] call _check;
    ''')


def tick_batch():
    return setup() + r'''
        private _row=["Ketamine",3,2,"label",0,[["Ketamine",2]],"compoundB13","none","","","","owned-row"];
        _medic setVariable ["ACME_narcStore",[_row]];
        private _job=createHashMapFromArray [
            ["medic",_medic],["patient",_patient],["flowing",true],
            ["providerLocalityEpoch",0],["providerOwner",7],["kitEpoch",0],
            ["identity",[0,1,1]],["stableId","owned-row"],["session","owned-session"],
            ["pendingAcks",0],["unsentDelta",[0,0,[]]],["batchElapsed",5],
            ["pushedMl",0],["targetMl",2],["rateMlSec",1],["carryMl",0],["lastTick",10],
            ["virtual",true],["kind","compoundB13"],["med","Ketamine"]
        ];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        private _id=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
        missionNamespace setVariable ["ACME_HCMedPushPFH",_id];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
        uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
        private _validationCalls=0;
        _nowTime=10.05;
    '''


@pytest.mark.parametrize('refund', ['restored', 'retired'])
def test_tick_synchronous_rejection_cannot_recreate_a_finalized_or_retired_job(refund):
    execute(tick_batch() + r'''
        ACME_fnc_medicationRequest={
            _validationCalls=_validationCalls+1;
    ''' + ('_medic setVariable ["ACME_narcStore",[]];' if refund == 'retired' else '') + r'''
            [_medic,_this select 7,false,"local validation failed",""] call ACME_fnc_hardcorePushAck;
            false
        };
        ["owned-session",_id] call ACME_fnc_hardcorePushTick;
        [_validationCalls==1 && {count _requests==0},"tick did not exercise one synchronous local rejection"] call _check;
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0,"tick recreated a ghost job after synchronous rejection"] call _check;
        [!((_handlers select _id) select 2) && {(missionNamespace getVariable "ACME_HCMedPushPFH")==-1},"rejected tick retained or recreated worker"] call _check;
        [!(uiNamespace getVariable "ACME_SK_InjectionBusy") && {!(uiNamespace getVariable "ACME_SK_CarouselBusy")},"rejected tick retained busy controls"] call _check;
    ''' + (r'''
        private _after=(_medic getVariable "ACME_narcStore") select 0;
        [abs ((_after select 2)-2)<0.000001 && {(_after select 5) isEqualTo [["Ketamine",2]]},"synchronous rejection lost or duplicated exact syringe solution"] call _check;
        [({ _x } count _publicationFlags)==1 && {count (missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]])==0},"successful synchronous refund did not settle once"] call _check;
    ''' if refund == 'restored' else r'''
        private _archive=missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]];
        [count _archive==1 && {({ _x } count _publicationFlags)==0},"failed synchronous refund lost archive or published stock"] call _check;
        if (count _archive==1) then {
            private _saved=(_archive select 0) select 2;
            private _tail=_saved get "unsentDelta";
            [abs ((_tail select 0)-0.05)<0.000001 && {(_saved get "pendingAcks")==0},"known local rejection erased tail or invented patient debt"] call _check;
        };
        [(_medic getVariable "ACME_narcStore") isEqualTo [],"failed synchronous refund manufactured usable stock"] call _check;
    '''))


def test_tick_synchronous_rejection_cannot_finish_or_repaint_a_successor_session():
    execute(tick_batch() + r'''
        private _successorRow=["Ketamine",3,1,"successor",0,[["Ketamine",1]],"compoundB13","none","","","","successor-row"];
        _patient setVariable ["ACME_narcStore",[_successorRow]];
        private _successor=createHashMapFromArray [
            ["medic",_patient],["patient",_medic],["flowing",true],
            ["stableId","successor-row"],["session","successor-session"],
            ["pendingAcks",0],["unsentDelta",[0,0,[]]],["virtual",true],
            ["pushedMl",1],["targetMl",1]
        ];
        private _successorId=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
        private _overlayCalls=0;
        ACME_fnc_hardcorePushOverlay={_overlayCalls=_overlayCalls+1;};
        ACME_fnc_medicationRequest={
            _validationCalls=_validationCalls+1;
            [_medic,_this select 7,false,"local validation failed",""] call ACME_fnc_hardcorePushAck;
            missionNamespace setVariable ["ACME_HCMedPushJob",_successor];
            missionNamespace setVariable ["ACME_HCMedPushPFH",_successorId];
            uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
            uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
            _overlayCalls=0;
            false
        };
        ["owned-session",_id] call ACME_fnc_hardcorePushTick;
        [_validationCalls==1,"tick did not exercise synchronous successor boundary"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _successor && {_successor get "flowing"} && {!("finishRequested" in _successor)},"old tick finished or modified successor session"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushPFH")==_successorId && {(_handlers select _successorId) select 2},"old tick removed successor worker"] call _check;
        [uiNamespace getVariable "ACME_SK_InjectionBusy" && {uiNamespace getVariable "ACME_SK_CarouselBusy"},"old tick cleared successor controls"] call _check;
        [(_patient getVariable "ACME_narcStore") isEqualTo [_successorRow] && {({ _x } count _publicationFlags)==1},"old tick settled or published successor stock"] call _check;
        [_overlayCalls==0,"old tick repainted or cleared successor overlay"] call _check;
    ''')
