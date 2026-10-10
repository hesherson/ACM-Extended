"""Execute live syringe arithmetic and publication policy with native inventory/network boundaries mocked.

The real Tick/Stop/ACK/Restore/Finalize and store writer run. Public flags count
requests at the engine boundary, not measured wire traffic or Arma replication.
"""
import pytest

from test_historical_medication_preparation import prep_code
from test_historical_vial_execution import source, setup as vial_setup
from test_menu_death_lifecycle import execute


def function(name):
    text = source(name)
    text = text.replace('local _owner', '_medicLocal').replace('local ACE_player', '_medicLocal')
    text = text.replace('_owner setVariable ["ACME_narcStore", _store, _public];',
                        '_publicationFlags pushBack _public; _owner setVariable ["ACME_narcStore", _store];')
    text = text.replace('_job getOrDefault ["med","Medication"]',
                        '([_job,["med","Medication"]] call _mapDefault)')
    text = text.replace('getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _source >> "concentration")',
                        '([_source,"concentration"] call _configNumber)')
    text = text.replace('isClass (configFile >> "ACM_Medication" >> "Medications" >> _class)', 'true')
    text = text.replace('isClass (configFile >> "ACM_Medication" >> "Medications" >> _source)', 'true')
    text = text.replace('_medic addMagazine [_magClass,_ammo];', '_returnedMagazines pushBack [_magClass,_ammo];')
    text = text.replace('_medic == ACE_player', '_medic isEqualTo ACE_player')
    return 'ACME_fnc_' + name + '={' + prep_code(text) + '};'


def setup():
    return vial_setup() + '''
        private _publicationFlags=[];
        private _requests=[];
        private _returnedMagazines=[];
        private _retiredNotices=[];
        ace_common_fnc_displayTextStructured={_retiredNotices pushBack _this;};
        ACME_fnc_medicationRequest={_requests pushBack _this; true};
        ACME_fnc_hardcorePushOverlay={};
        ACME_fnc_medicationRouteAllowed={true};
        ACME_fnc_patientInteractionDistance={_distance};
        ACME_fnc_medicationLineIdentity={[0,1,1]};
        ACME_fnc_medicationLineBloodBusy={false};
        missionNamespace setVariable ["ACME_hcEff_medications",true];
    ''' + ''.join(function(name) for name in (
        'narcStoreCommit', 'hardcorePushStart', 'hardcorePushTick', 'hardcorePushStop',
        'hardcorePushSendBatch', 'hardcorePushAck', 'hardcorePushFinalize', 'hardcorePushRestoreDelta',
        'hardcorePushRetire'))


@pytest.mark.parametrize('public', [True, False])
def test_remote_provider_store_writes_and_push_start_do_nothing(public):
    execute(setup() + '''
        _medicLocal=false;
        _medic setVariable ["ACME_narcStore",[["original"]]];
    ''' + f'[!([_medic,[["foreign"]],{str(public).lower()}] call ACME_fnc_narcStoreCommit),"remote store accepted"] call _check;' + '''
        [!([] call ACME_fnc_hardcorePushStart),"remote push started"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo [["original"]],"remote write changed store"] call _check;
        [count _publicationFlags==0 && {_inventoryDebits==0},"remote writer published or touched inventory"] call _check;
    ''')


@pytest.mark.parametrize('virtual', [False, True])
@pytest.mark.parametrize('reason,accepted', [('manual', True), ('manual', False), ('access', False), ('leash', False)])
def test_twenty_hz_push_refund_and_settlement_publish_only_once(virtual, reason, accepted):
    execute(setup() + f'private _virtual={str(virtual).lower()};' + '''
        private _row=["Ketamine",3,2,"label",0,if (_virtual) then {[["Ketamine",2]]} else {[]},
            if (_virtual) then {"compoundB13"} else {""},"none","","","","owned-row"];
        _medic setVariable ["ACME_narcStore",[_row]];
        private _job=createHashMapFromArray [
            ["medic",_medic],["patient",_patient],["flowing",true],
            ["providerLocalityEpoch",0],
            ["identity",[0,1,1]],["stableId","owned-row"],["session","owned-session"],
            ["virtual",_virtual],["kind",if (_virtual) then {"compoundB13"} else {""}],
            ["med","Ketamine"],["magClass","ACM_Syringe_3_Ketamine"],["magContainer",objNull],
            ["targetMl",2],["rateMlSec",1],["pushedMl",0],["carryMl",0],["lastTick",10]
        ];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        for "_i" from 1 to 20 do {
            _nowTime=10+_i*0.05;
            call ACME_fnc_hardcorePushTick;
        };
        [count _publicationFlags==20 && {({ _x } count _publicationFlags)==0},"live plunger published store or missed tick"] call _check;
        [abs (((_medic getVariable "ACME_narcStore") select 0 select 2)-1)<0.000001,"tick arithmetic changed"] call _check;
    ''' + f'["{reason}"] call ACME_fnc_hardcorePushStop;' + ('''
        [count _requests==1,"manual stop lost pending dose"] call _check;
        [({ _x } count _publicationFlags)==0,"store published before acknowledgement"] call _check;
        private _meta=(_requests select 0) select 7;
    ''' + f'[_medic,_meta,{str(accepted).lower()},"test"] call ACME_fnc_hardcorePushAck;' +
        f'[_medic,_meta,{str(accepted).lower()},"test"] call ACME_fnc_hardcorePushAck;' if reason == 'manual' else '''
        [count _requests==0,"unsafe tail submitted after access loss"] call _check;
    ''') + f'private _expected={1 if reason == "manual" and accepted else 2};' + '''
        [({ _x } count _publicationFlags)==1 && {_publicationFlags select (count _publicationFlags-1)},"settlement did not publish exactly once"] call _check;
        private _remaining=(_medic getVariable "ACME_narcStore") select 0;
        [abs ((_remaining select 2)-_expected)<0.000001,"resume volume lost or duplicated"] call _check;
        if (_virtual) then {
            [abs ((_remaining select 5 select 0 select 1)-_expected)<0.000001 && {count _returnedMagazines==0},"virtual component or inventory duplicated"] call _check;
        } else {
            [_returnedMagazines isEqualTo [["ACM_Syringe_3_Ketamine",round (_expected*100)]],"physical partial syringe returned incorrectly"] call _check;
        };
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0,"settled job retained"] call _check;
    ''')


def active_job():
    return '''
        private _row=["Ketamine",3,1.5,"label",0,[["Ketamine",1.5]],"compoundB13","none","","","","owned-row"];
        _medic setVariable ["ACME_narcStore",[_row]];
        _medic setVariable ["ACME_medicationEscrow",createHashMapFromArray [["receipt",["unsettled"]]]];
        private _job=createHashMapFromArray [
            ["medic",_medic],["patient",_patient],["flowing",true],
            ["providerLocalityEpoch",0],
            ["identity",[0,1,1]],["stableId","owned-row"],["session","owned-session"],
            ["pendingAcks",1],["unsentDelta",[0.25,0,[[0,"Ketamine",0.25]]]],["pushedMl",0.5]
        ];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        private _id=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
        missionNamespace setVariable ["ACME_HCMedPushPFH",_id];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
        uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
    '''


@pytest.mark.parametrize('loss', ['_medicLocal=false;', 'ACE_player=_patient;', '_job set ["medic",objNull];',
                                 '_medic setVariable ["ACME_providerLocalityEpoch",2];'])
def test_provider_loss_retires_worker_and_preserves_unsettled_evidence(loss):
    execute(setup()+active_job()+loss+'''
        for "_i" from 1 to 5 do {call ACME_fnc_hardcorePushTick;};
        [(missionNamespace getVariable ["ACME_HCMedPushPFH",-1]) == -1 && {!((_handlers select _id) select 2)},"owner loss retained 20 Hz worker"] call _check;
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0,"old job blocks unrelated provider"] call _check;
        private _retired=missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]];
        [count _retired==1,"repeated retirement lost or duplicated evidence"] call _check;
        private _saved=(_retired select 0) select 2;
        [(_saved get "unsentDelta") isEqualTo [0.25,0,[[0,"Ketamine",0.25]]] && {(_saved get "pendingAcks")==1},"retirement discarded unsettled volume or ACK debt"] call _check;
        [(_saved get "pushedMl")==0.5 && {!(_saved get "flowing")},"retirement relabeled dose as settled"] call _check;
        [count _publicationFlags==0 && {count _returnedMagazines==0} && {count _requests==0},"old owner settled or published inventory"] call _check;
        [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.5,"retirement rewrote provider ledger"] call _check;
        [!(uiNamespace getVariable "ACME_SK_InjectionBusy") && {!(uiNamespace getVariable "ACME_SK_CarouselBusy")},"retired UI retained busy flags"] call _check;
    ''')


@pytest.mark.parametrize('stale', ['["old-session",_id]', '["owned-session",_id+1]'])
def test_stale_retirement_cannot_touch_new_active_controller(stale):
    execute(setup()+active_job()+f'[!({stale} call ACME_fnc_hardcorePushRetire),"stale retirement accepted"] call _check;'+'''
        [((_handlers select _id) select 2) && {(missionNamespace getVariable "ACME_HCMedPushPFH")==_id},"stale retirement removed current worker"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _job && {_job get "flowing"},"stale retirement altered new job"] call _check;
        [uiNamespace getVariable "ACME_SK_InjectionBusy","stale retirement cleared new UI"] call _check;
    ''')


@pytest.mark.parametrize('reuse_id', [False, True])
def test_actual_queued_old_worker_cannot_drive_or_retire_replacement_job(reuse_id):
    # Execute the installed CBA callback from Start, including its immutable captured session payload.
    start = source('hardcorePushStart')
    worker = 'private _h = ' + start.split('private _h = ', 1)[1].split('missionNamespace setVariable ["ACME_HCMedPushPFH",_h];', 1)[0]
    execute(setup()+active_job()+'''private _session="old-session";'''+prep_code(worker)+'''
        private _oldWorker=+(_handlers select _h);
        private _newId=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
    '''+('''_newId=_h; _handlers set [_newId,[{},["owned-session"],true]];''' if reuse_id else '')+'''
        missionNamespace setVariable ["ACME_HCMedPushPFH",_newId];
        // A new active job may itself have a nonlocal provider; the obsolete callback still cannot retire it.
        _medicLocal=false;
        [_oldWorker select 1,_h] call (_oldWorker select 0);
        [(missionNamespace getVariable "ACME_HCMedPushPFH")==_newId && {(_handlers select _newId) select 2},"old callback removed replacement worker"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _job && {_job get "flowing"},"old callback changed replacement job"] call _check;
        [count (missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]])==0 && {uiNamespace getVariable "ACME_SK_InjectionBusy"},"old callback retired replacement UI/job"] call _check;
        [count _publicationFlags==0 && {count _requests==0} && {count _returnedMagazines==0},"old callback processed replacement medication"] call _check;
    ''')


def test_failed_restore_preserves_tail_and_retires_without_fabricating_refund():
    execute(setup()+active_job()+'''
        _medic setVariable ["ACME_narcStore",[]];
        ["access"] call ACME_fnc_hardcorePushStop;
        private _saved=((missionNamespace getVariable "ACME_HCMedPushRetiredJobs") select 0) select 2;
        [(_saved get "unsentDelta") isEqualTo [0.25,0,[[0,"Ketamine",0.25]]] && {(_saved get "pushedMl")==0.5},"failed refund erased unsent dose"] call _check;
        [!((_handlers select _id) select 2) && {count _returnedMagazines==0} && {count _publicationFlags==0},"failed refund leaked worker or duplicated stock"] call _check;
    ''')


@pytest.mark.parametrize('count', [1, 32])
def test_retired_provider_and_capacity_blocks_precede_inventory_reservation(count):
    execute(setup()+f'private _count={count};'+'''
        _drawDisplay=missionNamespace;
        uiNamespace setVariable ["ACME_SK_View","body"];
        private _retired=[];
        for "_i" from 1 to _count do {_retired pushBack [if (_count==1) then {_medic} else {_patient},str _i];};
        missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",_retired];
        [!([] call ACME_fnc_hardcorePushStart),"unsettled provider/capacity accepted"] call _check;
        [count _retiredNotices==1 && {_inventoryDebits==0} && {count _publicationFlags==0},"retirement guard ran after inventory mutation"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushRetiredJobs") isEqualTo _retired,"capacity guard evicted evidence"] call _check;
        if (_count==1) then {
            ACE_player=_patient;
            [] call ACME_fnc_hardcorePushStart;
            [count _retiredNotices==1,"retired provider blocked an unrelated provider"] call _check;
        };
    ''')


def test_fresh_kit_reset_clears_only_that_providers_retired_records():
    execute(setup()+function('resetPersonalMedicationKit')+'''
        ACME_fnc_openVialStoreCommit={};
        ACME_fnc_vialLeaseRelease={};
        missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",[[_medic,"first"],[_patient,"second"]]];
        [_medic] call ACME_fnc_resetPersonalMedicationKit;
        [(missionNamespace getVariable "ACME_HCMedPushRetiredJobs") isEqualTo [[_patient,"second"]],"fresh kit cleared another provider's evidence or retained old inventory"] call _check;
    ''')


@pytest.mark.parametrize('accepted', [False, True])
@pytest.mark.parametrize('at_capacity', [False, True])
def test_fresh_kit_invalidates_active_push_before_rows_and_fences_old_worker_and_ack(accepted, at_capacity):
    start = source('hardcorePushStart')
    worker = 'private _h = ' + start.split('private _h = ', 1)[1].split('missionNamespace setVariable ["ACME_HCMedPushPFH",_h];', 1)[0]
    dependencies = ''.join(function(name) for name in ('resetPersonalMedicationKit', 'medicationAck', 'medicationRefund', 'medicationEscrowCommit'))
    execute(setup()+dependencies+active_job()+'''
        ACME_fnc_openVialStoreCommit={};
        ACME_fnc_vialLeaseRelease={};
        private _session="owned-session";
    '''+prep_code(worker)+'''
        missionNamespace setVariable ["ACME_HCMedPushPFH",_h];
        private _oldWorker=+(_handlers select _h);
        private _meta=["hcPush","owned-session","owned-row",[0.25,0,[[0,"Ketamine",0.25]]]];
        // Actual HC SendBatch reserves no generic refund payload; only its matching job can settle the delta.
        _medic setVariable ["ACME_medicationEscrow",createHashMapFromArray [["receipt",[_patient,[],[],0,0,_meta]]]];
    '''+('''
        private _archive=[];
        for "_i" from 1 to 32 do {_archive pushBack [_patient,str _i];};
        missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",_archive];
    ''' if at_capacity else '')+'''
        [_medic] call ACME_fnc_resetPersonalMedicationKit;
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0 && {!((_handlers select _h) select 2)},"fresh kit retained previous controller"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushPFH")==-1 && {(_medic getVariable "ACME_narcStore") isEqualTo []},"fresh kit retained previous row/worker"] call _check;
        [(missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]]) findIf {(_x select 0) isEqualTo _medic} == -1,"fresh kit retained own retired blocker"] call _check;
        // A fresh kit can reuse a stable ID; the session fence must still reject the old request.
        private _newRow=["Ketamine",3,3,"new kit",0,[["Ketamine",3]],"compoundB13","none","","","","owned-row"];
        _medic setVariable ["ACME_narcStore",[_newRow]];
        private _newJob=createHashMapFromArray [["medic",_medic],["session","new-session"],["flowing",true],["pendingAcks",1]];
        missionNamespace setVariable ["ACME_HCMedPushJob",_newJob];
        private _newId=[{},0.05,[]] call CBA_fnc_addPerFrameHandler;
        missionNamespace setVariable ["ACME_HCMedPushPFH",_newId];
        [_oldWorker select 1,_h] call (_oldWorker select 0);
    '''+f'[_medic,"receipt",{str(accepted).lower()},"late"] call ACME_fnc_medicationAck;'+
        f'[_medic,"receipt",{str(accepted).lower()},"duplicate"] call ACME_fnc_medicationAck;'+'''
        [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _newJob && {_newJob get "flowing"} && {(_newJob get "pendingAcks")==1},"old callback/ACK altered replacement job"] call _check;
        [(_handlers select _newId) select 2,"old callback removed replacement worker"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo [_newRow] && {count _publicationFlags==1} && {count _returnedMagazines==0},"old ACK inserted previous-kit medication"] call _check;
        [(missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]]) findIf {(_x select 0) isEqualTo _medic} == -1,"late callback re-created reset blocker"] call _check;
    ''')


def test_fresh_kit_for_other_provider_preserves_active_controller_and_ui():
    execute(setup()+function('resetPersonalMedicationKit')+active_job()+'''
        ACME_fnc_openVialStoreCommit={};
        ACME_fnc_vialLeaseRelease={};
        [_patient] call ACME_fnc_resetPersonalMedicationKit;
        [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _job && {_job get "flowing"},"other kit reset changed active job"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushPFH")==_id && {(_handlers select _id) select 2},"other kit reset removed active worker"] call _check;
        [uiNamespace getVariable "ACME_SK_InjectionBusy","other kit reset cleared current UI"] call _check;
        [((_medic getVariable "ACME_narcStore") select 0 select 2)==1.5,"other kit reset altered provider medication"] call _check;
    ''')


@pytest.mark.parametrize('accepted', [False, True])
def test_late_ack_after_away_and_back_locality_retires_without_settlement(accepted):
    execute(setup()+active_job()+'''
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        private _meta=["hcPush","owned-session","owned-row",[0.25,0,[[0,"Ketamine",0.25]]]];
    '''+f'[!([_medic,_meta,{str(accepted).lower()},"late"] call ACME_fnc_hardcorePushAck),"old owner epoch settled after returning"] call _check;'+'''
        [count (missionNamespace getVariable "ACME_HCMedPushJob")==0 && {!((_handlers select _id) select 2)},"epoch-change ACK retained controller"] call _check;
        [count _publicationFlags==0 && {count _returnedMagazines==0},"old epoch ACK returned medication"] call _check;
        private _saved=((missionNamespace getVariable "ACME_HCMedPushRetiredJobs") select 0) select 2;
        [(_saved get "pendingAcks")==1 && {(_saved get "unsentDelta") isEqualTo [0.25,0,[[0,"Ketamine",0.25]]]},"old epoch ACK discarded unsettled evidence"] call _check;
    ''')
