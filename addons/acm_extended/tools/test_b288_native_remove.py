"""Execute native RemoveBag funding/receiver identity and FreshBlood preservation.

Arma inventory placement/locality, transport and rendering are explicit fixture
boundaries. Actual receipt decisions, owner mutation, native readback branching,
used-bag conservation and donor metadata handling execute from production SQF.
"""
import re
import pytest
from test_menu_death_lifecycle import execute, read, namespace_public_arguments
from test_b227_line_service_and_assessments import basic, src


def fixture():
    result=src('transfusionRemoveBagResult').replace('local _provider','true').replace('alive _provider','_alive')
    result=result.replace('uniformItems _provider','_resourceUnitItems').replace('vestItems _provider','[]').replace('backpackItems _provider','[]')
    result=result.replace('nearestObject [_provider,"WeaponHolder"]','_nearHolder')
    result=re.sub(r'itemCargo (_\w+)',r'(\1 getVariable ["items",[]])',result)
    result=result.replace('isNull ACE_player','(ACE_player isEqualTo objNull)')
    result=result.replace('(_placement select 1) isEqualType objNull','((_placement select 1) isEqualType profileNamespace || {(_placement select 1) isEqualType objNull})')
    commit=src('transfusionRemoveBagCommit').replace('finite (_fresh select 4)','((_fresh select 4) call _finite)')
    # Keep real object identities in the production params checks and native-return result.
    return basic()+r'''
        private _resourceUnitItems=[];private _calls=0;private _returns=[];private _placementMode="unit";
        private _nearHolder="GroundWeaponHolder" createVehicle [0,0,0];
        private _reopened=0;private _commitAllowed=true;private _commitOther=false;
        _resourceNearHolder=_nearHolder;
        ace_common_fnc_addToInventory={
            params ["_provider","_class"];_calls=_calls+1;
            if (_placementMode=="unit") exitWith {_resourceUnitItems pushBack _class;[true,_provider]};
            if (_placementMode=="spill") exitWith {
                private _items=+(_nearHolder getVariable ["items",[]]);_items pushBack _class;
                _nearHolder setVariable ["items",_items];[false,_nearHolder]
            };
            if (_placementMode=="refuse") exitWith {[false,_provider]};
            [false]
        };
        ACM_circulation_fnc_getReturnVolume={params ["_ml"];floor (_ml/250)*250};
        ACM_circulation_fnc_formatFluidBagName={params ["_type","_volume"];format ["%1_%2",_type,_volume]};
        ACM_circulation_fnc_getFluidBagString={"fluid"};
        ACM_core_fnc_getBodyPartString={"body"};
        ACM_circulation_fnc_openTransfusionMenu={_reopened=_reopened+1;};
        ACM_circulation_fnc_generateBloodType={2};
        ACM_circulation_fnc_updateActiveFluidBags={};
        ACME_fnc_ivBagsCommit={params ["_p","_map"];if (_commitAllowed) then {_p setVariable ["ACM_circulation_IV_Bags",if (_commitOther) then {createHashMap} else {_map}];};};
        ACME_fnc_freshBloodResolve={params ["_id","_inline","_bt"];if (_inline isEqualTo ["freshMissingV1"]) exitWith {[]};[_patient,500,2,false,0]};
        CBA_fnc_targetEvent={_returns pushBack _this;};
        CBA_fnc_serverEvent={_events pushBack _this;};
        ace_common_fnc_isAwake={true};
        ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
        _medic setVariable ["ACME_usedBags",[]];
        private _bag=["FreshBlood",183.25,4,0,false,2,500,1,"bag",500,["freshV1",false,0,2]];
        private _context={uiNamespace setVariable ["ACME_txRemoveContexts",createHashMapFromArray [["remove",[_medic,_patient,"body"]]]];uiNamespace setVariable ["ACME_txRemovePending","remove"];};
    '''+'ACME_fnc_transfusionRemoveBagResult={'+result+'};ACME_fnc_transfusionRemoveBagCommit={'+commit+'};'+r'''
        private _send={[_patient,"remove",true,_bag,"body",""] call ACME_fnc_transfusionRemoveBagResult;};
        private _remove={
            _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[_bag]]]];
            [_patient,_medic,"body","bag",0,[],1,"remove"] call ACME_fnc_transfusionRemoveBagCommit
        };
        private _packet={
            private _messages=_events select {(_x select 0)=="ACME_resourceReturn"};
            private _wire=(_messages select 0) select 1 select 1;
            [_wire select 0,_wire select 1,_wire select 2,_wire select 3,7,"machineA",1]
        };
        private _deliver={(call _packet) call ACME_fnc_resourceReturnReceive;};
    '''


def test_fresh_native_remove_returns_exact_used_bag_without_native_donorless_item():
    execute(fixture()+r'''
        [call _remove,"source removal refused"] call _check;
        call _deliver;call _deliver;
        private _used=_medic getVariable "ACME_usedBags";
        [count _used==1 && {(_used select 0 select 2)==183.25},"fresh product duplicated/lost/rounded"] call _check;
        [(_used select 0 select 8) isEqualTo (_bag select 10),"fresh donor facts lost"] call _check;
        [_calls==0,"donor-IDless native fresh bag created"] call _check;
    ''')


def test_unsolicited_accepted_remove_result_cannot_create_inventory():
    execute(fixture()+r'''
        call _send;
        [(_medic getVariable "ACME_usedBags") isEqualTo [] && {_calls==0},"unsolicited result funded inventory"] call _check;
    ''')


def test_ui_acknowledgement_is_presentation_only_and_cannot_duplicate_server_product():
    execute(fixture()+r'''
        call _remove;call _context;call _send;call _send;
        [(_medic getVariable "ACME_usedBags") isEqualTo [],"UI reply materialized product outside journal"] call _check;
        call _deliver;call _deliver;
        [count (_medic getVariable "ACME_usedBags")==1,"certified delivery duplicated after UI reply"] call _check;
    ''')


def test_switched_controlled_player_does_not_receive_old_providers_return():
    execute(fixture()+r'''
        call _remove;call _context;ACE_player=missionNamespace;call _send;call _deliver;
        [count (_medic getVariable "ACME_usedBags")==1,"captured provider lost return"] call _check;
        [isNil {ACE_player getVariable "ACME_usedBags"},"new controlled unit received old return"] call _check;
        [_reopened==0,"old ACK reopened different provider menu"] call _check;
    ''')


@pytest.mark.parametrize('placement',['unit','spill'])
def test_native_readback_counts_ace_ground_spill_as_one_delivered_product(placement):
    execute(fixture()+f'_placementMode="{placement}";'+r'''
        _bag set [0,"Saline"];_bag set [1,499];call _remove;
        call _deliver;call _deliver;
        [_calls==1,"native delivery repeated"] call _check;
        [(_medic getVariable "ACME_usedBags") isEqualTo [],"ACE spill duplicated into used store"] call _check;
        [count _resourceUnitItems+count (_nearHolder getVariable ["items",[]])==1,"native return missing/cloned"] call _check;
    ''')


def test_proven_native_refusal_retries_same_funding_without_creating_a_second_product():
    execute(fixture()+r'''
        _placementMode="refuse";_bag set [0,"Saline"];_bag set [1,499];call _remove;
        call _deliver;
        private _decision=(missionNamespace getVariable "ACME_resourceReturnDecisions") get "remove:1";
        [(_decision select 1)=="unplaced","proven refusal was not retryable"] call _check;
        _placementMode="unit";call _deliver;call _deliver;
        [_calls==2 && {count _resourceUnitItems==1},"retry minted or lost product"] call _check;
    ''')


def test_unknown_native_outcome_is_held_and_never_speculatively_repeated():
    execute(fixture()+r'''
        _placementMode="malformed";_bag set [0,"Saline"];_bag set [1,499];call _remove;
        call _deliver;call _deliver;
        private _decision=(missionNamespace getVariable "ACME_resourceReturnDecisions") get "remove:1";
        [(_decision select 1)=="uncertain" && {_calls==1},"unknown outcome retried/reminted"] call _check;
    ''')


def test_filled_fbtk_returns_portable_fresh_product_with_owner_frozen_collection_facts():
    execute(fixture()+r'''
        _bag set [0,"FBTK"];_bag set [1,499.9];call _remove;call _deliver;
        private _used=(_medic getVariable "ACME_usedBags") select 0;
        [(_used select 1)=="FreshBlood" && {(_used select 2)==500},"filled collection volume/type lost"] call _check;
        [(_used select 8) isEqualTo ["freshV1",true,10,2],"collection facts recaptured after source removal"] call _check;
        [_calls==0,"portable collection consumed session-specific native ID"] call _check;
    ''')


@pytest.mark.parametrize('placement',['unit','spill'])
def test_empty_fbtk_returns_one_real_collection_kit(placement):
    execute(fixture()+f'_placementMode="{placement}";'+r'''
        _bag set [0,"FBTK"];_bag set [1,0];call _remove;call _deliver;call _deliver;
        [_calls==1 && {count _resourceUnitItems+count (_nearHolder getVariable ["items",[]])==1},"empty collection kit duplicated/lost"] call _check;
    ''')


def test_failed_source_write_keeps_bag_and_never_publishes_positive_funding():
    execute(fixture()+r'''
        _commitAllowed=false;
        [!call _remove,"failed source write accepted"] call _check;
        [count ((_patient getVariable "ACM_circulation_IV_Bags") get "body")==1,"failed source write destroyed original bag"] call _check;
        [count (_patient getVariable ["ACME_resourceReturnFunded",createHashMap])==0,"failed debit published positive proof"] call _check;
        [(_events select {(_x select 0)=="ACME_resourceReturn"}) isEqualTo [],"failed debit dispatched product"] call _check;
        [(((missionNamespace getVariable "ACME_resourceReturnSources") get "remove") select 1)=="cancelled","failed debit left positive private outcome"] call _check;
    ''')


def test_unknown_source_write_retains_pending_evidence_without_positive_funding():
    execute(fixture()+r'''
        _commitOther=true;
        [!call _remove,"unknown source write accepted"] call _check;
        [count (_patient getVariable ["ACME_resourceReturnFunded",createHashMap])==0,"unknown debit published positive proof"] call _check;
        [(((missionNamespace getVariable "ACME_resourceReturnSources") get "remove") select 1)=="uncertain","unknown source outcome not held"] call _check;
        [count (_patient getVariable ["ACME_resourceReturnSourcePending",createHashMap])==1,"unknown source lost checkpoint blocker"] call _check;
    ''')


def test_accepted_source_replay_resends_same_certificate_without_second_debit():
    execute(fixture()+r'''
        call _remove;
        private _before=[((missionNamespace getVariable "ACME_resourceReturnSources") get "remove")] call ACME_fnc_syringeDeliveryCopy;
        [_patient,_medic,"body","bag",0,[],1,"remove"] call ACME_fnc_transfusionRemoveBagCommit;
        [(((missionNamespace getVariable "ACME_resourceReturnSources") get "remove") select 0) isEqualTo (_before select 0),"source replay changed immutable products"] call _check;
        [count (_events select {(_x select 0)=="ACME_resourceReturn"})==2,"source replay did not nudge lost transport"] call _check;
        [((_patient getVariable "ACM_circulation_IV_Bags") get "body") isEqualTo [],"source replay resurrected source bag"] call _check;
    ''')


@pytest.mark.parametrize('actor',['_patient','_medic'])
def test_frozen_admission_keeps_attached_bag_and_does_not_stage_funding(actor):
    execute(fixture()+actor+r''' setVariable ["ACME_persistenceFrozen",true];
        [!call _remove,"frozen source admitted removal"] call _check;
        [count ((_patient getVariable "ACM_circulation_IV_Bags") get "body")==1,"frozen source debited bag"] call _check;
        [count (missionNamespace getVariable ["ACME_resourceReturnSources",createHashMap])==0,"frozen source staged funding"] call _check;
    ''')


def test_fenced_unknown_fresh_bag_can_be_detached_as_unusable_preserved_evidence():
    execute(fixture()+r'''
        _bag set [5,8];_bag set [10,["freshMissingV1"]];
        [call _remove,"fenced unknown blood could not be cleared from line"] call _check;call _deliver;
        private _used=(_medic getVariable "ACME_usedBags") select 0;
        [(_used select 4)==-1 && {(_used select 8) isEqualTo ["freshMissingV1"]},"unknown blood became usable donor product"] call _check;
    ''')


@pytest.mark.parametrize('kind',['tagged','propofol','legacy'])
def test_plain_pull_cannot_discard_medication_remaining_in_an_attached_infusion(kind):
    from test_b228_line_service_network_audit import salvage_setup
    change={'tagged':'','propofol':'_bag set [0,"ACME_Propofol"];','legacy':'_bag set [8,""];_drug set [23,""];'}[kind]
    execute(salvage_setup('transfusionPullCommit')+r'''
        private _bag=["Saline",100,4,0,false,-1,500,-1,"drug-bag"];
        private _drug=[];_drug set [1,"body"];_drug set [2,0];_drug set [4,0];_drug set [5,false];_drug set [15,8.25];_drug set [23,"drug-bag"];
        private _deliveries=0;ACME_fnc_infusionDeliver={_deliveries=_deliveries+1;};
    '''+change+r'''
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[_bag]]]];
        _patient setVariable ["ACME_infusion_BagMedications",[_drug]];
        private _before=str [_patient getVariable "ACM_circulation_IV_Bags",_patient getVariable "ACME_infusion_BagMedications"];
        private _request=[_patient,_medic,"body",_bag select 8,0,_bag select [0,8],1,"pull-drug",_serverTime];
        [!(_request call ACME_fnc_transfusionPullCommit),"Pull Bag removed a medicated infusion"] call _check;
        [str [_patient getVariable "ACM_circulation_IV_Bags",_patient getVariable "ACME_infusion_BagMedications"]==_before,"refused pull changed remaining medication or bag"] call _check;
        [_deliveries==0 && {count (missionNamespace getVariable ["ACME_resourceReturnSources",createHashMap])==0},"refused pull caused clinical/resource side effects"] call _check;
    ''')


def test_source_stage_is_not_positive_proof_until_verified_funding_and_retries_stop_on_admission():
    execute(fixture()+r'''
        private _prepared=["pull",_patient,"staged",[_bag]] call ACME_fnc_resourceReturnProducts;
        private _args=[_medic,_patient,"staged",_prepared select 1];
        [["stage",_args] call ACME_fnc_resourceReturnSource,"valid source stage failed"] call _check;
        [count (_patient getVariable ["ACME_resourceReturnFunded",createHashMap])==0,"mere staging became public funding"] call _check;
        [(_events select {(_x select 0)=="ACME_resourceReturn"}) isEqualTo [],"stage dispatched unremoved product"] call _check;
        [["funded",_args] call ACME_fnc_resourceReturnSource,"verified funding failed"] call _check;
        private _requests=_events select {(_x select 0)=="ACME_resourceReturn"};
        [count _requests==1 && {count (_requests select 0 select 1 select 1)==5},"funding lacks source certificate"] call _check;
        private _record=(missionNamespace getVariable "ACME_resourceReturnSources") get "staged";
        [["admitted",["staged",_record select 2]] call ACME_fnc_resourceReturnSource,"source admission failed"] call _check;
        [(missionNamespace getVariable "ACME_resourceReturnSourceActive") isEqualTo [],"admitted outbox kept retrying"] call _check;
        [count (_patient getVariable ["ACME_resourceReturnSourcePending",createHashMap])==0,"admitted source retained transient blocker"] call _check;
    ''')
