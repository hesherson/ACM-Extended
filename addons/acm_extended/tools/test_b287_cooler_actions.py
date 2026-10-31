"""Execute cooler admission, withdrawal and asynchronous menu continuations.

Native inventory/UI commands and the inventory-ledger claim are boundaries.
The production callbacks perform actual capacity, generation, warm-exposure,
placement and intent checks in SQF-VM. These do not certify Arma networking.
"""
import re

import pytest

from test_b287_cooler_timing import fixture as timing_fixture, source as timing_source
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import execute


def source(name):
    code = timing_source(name)
    # SQF-VM does not implement values HASHMAP; retain the exact key/value set.
    code = re.sub(r'\bvalues (_\w+)', r'((keys \1) apply {\1 get _x})', code)
    code = code.replace('local _owner', '(_owner getVariable ["fixtureLocal",true])')
    code = code.replace('alive _owner', '(_owner getVariable ["fixtureAlive",true])')
    code = code.replace('uniformItems _owner', '(_owner getVariable ["fixtureCargo",[]])')
    code = code.replace('vestItems _owner', '[]').replace('backpackItems _owner', '[]')
    code = code.replace('uniformItems _p', '(_p getVariable ["fixtureCargo",[]])')
    code = code.replace('vestItems _p', '[]').replace('backpackItems _p', '[]')
    code = code.replace('_owner canAdd _class', '_nativeCanAdd')
    code = code.replace('_owner addItem _class;',
                        'if (_nativeAddSucceeds) then {[_owner,_class,1] call _cargoAdjust;};')
    code = code.replace('_owner removeItem _bag;',
                        'if (_nativeRemoveSucceeds) then {[_owner,_bag,-1] call _cargoAdjust;};')
    code = code.replace('getNumber(configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl")',
                        '([(_state select 0),"ACME_coolerCapacityMl"] call _config)')
    code = code.replace('findDisplay 86000', '_displayFixture')
    code = code.replace('_display displayCtrl 86005', '_listFixture')
    code = code.replace('_dlg displayCtrl 87410', '_listFixture')
    code = code.replace('lbCurSel _right', '_selectionFixture')
    code = code.replace('lbCurSel _list', '_selectionFixture')
    code = code.replace('_right lbData _selection', '_rowDataFixture')
    code = code.replace('_list lbData _selection', '_rowDataFixture')
    # VM requires an explicit slice length; Arma allows omitted tail length.
    code = code.replace('_loose select [_reserved]',
                        '_loose select [_reserved,(count _loose)-_reserved]')
    return map_defaults(code)


def fixture():
    code = timing_fixture() + r'''
        private _nativeCanAdd=true;
        private _nativeAddSucceeds=true;
        private _nativeRemoveSucceeds=true;
        private _stateFixture=[_class,0,[],0];
        private _mutationResult=[];
        private _mutationCalls=[];
        private _deferMutation=false;
        private _deferredMutation=[];
        private _displayFixture=missionNamespace;
        private _listFixture=profileNamespace;
        private _selectionFixture=0;
        private _rowDataFixture=_bag+"|Blood500|COOLER";
        private _resumes=[];
        _holder setVariable ["fixtureLocal",true];
        _holder setVariable ["fixtureAlive",true];
        _holder setVariable ["ACME_equipmentKitEpoch",0];
        _holder setVariable ["ACME_providerLocalityEpoch",0];
        _holder setVariable ["ACME_bloodSeedPending",createHashMap];
        ACE_player=_holder;
        missionNamespace setVariable ["ACME_bloodExposurePending",createHashMap];
        missionNamespace setVariable ["ACME_bloodExposureSerial",0];
        missionNamespace setVariable ["ACME_coolerManualOut",0];
        missionNamespace setVariable ["ACME_coolerAutoStoreBusy",false];
        uiNamespace setVariable ["ACME_CLR_Id","one"];
        uiNamespace setVariable ["ACME_CLR_DLG",_displayFixture];
        uiNamespace setVariable ["ACME_preparedListMode",false];
        missionNamespace setVariable ["ACME_piggybackPending",[]];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_box];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
        CBA_fnc_serverEvent={_events pushBack _this;};
        ACME_fnc_coolerRows={[["one",_stateFixture]]};
        ACME_fnc_coolerMutate={
            params ["_owner","_sid","_code",["_args",[]]];
            _mutationCalls pushBack [_owner,_sid,_args];
            if (_deferMutation) exitWith {_deferredMutation=[_owner,_sid,_code,_args];true};
            private _advanced=[_stateFixture,_clock] call ACME_fnc_coolerAdvance;
            _mutationResult=[_owner,_sid,_advanced,_args,"claim"] call _code;
            if (_mutationResult isNotEqualTo []) then {_stateFixture=_mutationResult # 1;};
            true
        };
        private _runDeferred={
            _deferredMutation params ["_owner","_sid","_code","_args"];
            private _advanced=[_stateFixture,_clock] call ACME_fnc_coolerAdvance;
            _mutationResult=[_owner,_sid,_advanced,_args,"claim"] call _code;
            if (_mutationResult isNotEqualTo []) then {_stateFixture=_mutationResult # 1;};
        };
        ACME_fnc_transfusionSpikeOrAdd={_resumes pushBack _this;};
        ACME_fnc_coolerAutoStore={};
        ACME_fnc_coolerRefresh={};
        ACME_fnc_coolerIssue={};
    '''
    code += r'''private _patientEpoch=0;ACME_fnc_clinicalEpoch={_patientEpoch};'''
    for name in ('coolerLoadRequest', 'bloodExposureReply', 'coolerGiveBag',
                 'coolerDrawDone', 'coolerUnload', 'coolerContentsTick'):
        code += f'ACME_fnc_{name}={{' + source(name) + '};'
    return map_defaults(code)


def pending():
    return r'''
        [_holder,"one",_bag] call ACME_fnc_coolerLoadRequest;
        private _request=((_events # ((count _events)-1)) # 1) # 3;
    '''


def test_load_request_deduplicates_pending_and_records_exact_generations():
    execute(fixture() + r'''
        _holder setVariable ["ACME_equipmentKitEpoch",17];
        _holder setVariable ["ACME_providerLocalityEpoch",23];
        [[_holder,"one",_bag] call ACME_fnc_coolerLoadRequest,"request rejected"] call _check;
        [!([_holder,"one",_bag] call ACME_fnc_coolerLoadRequest),"duplicate request accepted"] call _check;
        [count _events==1,"duplicate request sent"] call _check;
        private _requests=missionNamespace getVariable "ACME_bloodExposurePending";
        private _record=(_requests get ((keys _requests) # 0));
        [_record # 4==17 && {_record # 5==23},"request omitted its generations"] call _check;
    ''')


@pytest.mark.parametrize('field', ['ACME_equipmentKitEpoch', 'ACME_providerLocalityEpoch'])
def test_late_exposure_reply_after_generation_change_never_claims_or_consumes(field):
    execute(fixture() + pending() + f'''
        _holder setVariable ["fixtureCargo",[_bag]];
        _holder setVariable ["{field}",1];
        [_holder,_request,_bag,600,0] call ACME_fnc_bloodExposureReply;
        [count _mutationCalls==0,"late generation claimed cooler"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"late generation consumed replacement bag"] call _check;
        [count (missionNamespace getVariable "ACME_bloodExposurePending")==0,"late request not retired"] call _check;
    ''')


def test_expired_reply_and_duplicate_reply_are_inert():
    execute(fixture() + pending() + r'''
        _holder setVariable ["fixtureCargo",[_bag]];
        _clock=31;
        [_holder,_request,_bag,600,0] call ACME_fnc_bloodExposureReply;
        [_holder,_request,_bag,600,0] call ACME_fnc_bloodExposureReply;
        [count _mutationCalls==0,"expired or repeated reply claimed cooler"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"expired reply consumed source"] call _check;
    ''')


def test_contents_tick_retries_lost_read_with_same_nonce_then_releases_expired_slot():
    execute(fixture() + pending() + r'''
        _clock=2;call ACME_fnc_coolerContentsTick;
        [count _events==2,"lost read was not retried"] call _check;
        [((_events # 1) # 1) # 3 isEqualTo _request,"retry changed request identity"] call _check;
        _clock=31;call ACME_fnc_coolerContentsTick;
        [count (missionNamespace getVariable "ACME_bloodExposurePending")==0,"expired read permanently blocks admissions"] call _check;
        [[_holder,"one",_bag] call ACME_fnc_coolerLoadRequest,"expired slot cannot be reused"] call _check;
    ''')


@pytest.mark.parametrize('field', ['ACME_equipmentKitEpoch', 'ACME_providerLocalityEpoch'])
def test_contents_tick_retires_lost_read_when_its_generation_changes(field):
    execute(fixture() + pending() + f'''
        _holder setVariable ["{field}",1];
        _clock=2;call ACME_fnc_coolerContentsTick;
        [count _events==1,"stale generation retried exposure read"] call _check;
        [count (missionNamespace getVariable "ACME_bloodExposurePending")==0,"stale generation retained pending admission"] call _check;
    ''')


def test_loading_preserves_measured_exposure_plus_round_trip_elapsed():
    execute(fixture() + pending() + r'''
        _holder setVariable ["fixtureCargo",[_bag]];
        _clock=20;
        [_holder,_request,_bag,600,10] call ACME_fnc_bloodExposureReply;
        [(_holder getVariable "fixtureCargo") isEqualTo [],"source bag not debited"] call _check;
        [(_stateFixture # 2) isEqualTo [[_bag,610]],"cooler admission refreshed warm clock"] call _check;
        [_holder,_request,_bag,600,10] call ACME_fnc_bloodExposureReply;
        [count _mutationCalls==1 && {count (_stateFixture # 2)==1},"replayed read duplicated blood"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_holder setVariable ["ACME_equipmentKitEpoch",1];',
    '_holder setVariable ["ACME_providerLocalityEpoch",1];',
    '_holder setVariable ["fixtureAlive",false];',
    '_holder setVariable ["fixtureLocal",false];',
])
def test_admission_revalidates_after_inventory_claim_waits(change):
    execute(fixture() + pending() + r'''
        _holder setVariable ["fixtureCargo",[_bag]];
        _deferMutation=true;
        [_holder,_request,_bag,600,0] call ACME_fnc_bloodExposureReply;
        [count _deferredMutation>0,"claim continuation not captured"] call _check;
    ''' + change + r'''
        call _runDeferred;
        [_mutationResult isEqualTo [],"retired claim admitted a replacement source"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"retired claim removed source bag"] call _check;
        [(_stateFixture # 2) isEqualTo [],"retired claim generated virtual blood"] call _check;
    ''')


@pytest.mark.parametrize('bag,existing', [
    ('ACM_BloodBag_ON_1000', '[]'),
    pytest.param('ACM_BloodBag_ON_500', '[["ACM_FreshBloodBag_250_7",70]]', id='ACM_BloodBag_ON_500-[["ACM_FreshBloodBag_A_250",70]]'),
])
def test_loading_enforces_total_millilitres_before_native_debit(bag, existing):
    execute(fixture() + f'_bag="{bag}";' + pending() + f'''
        _holder setVariable ["fixtureCargo",[_bag]];
        _stateFixture=[_class,0,{existing},0];
        [_holder,_request,_bag,600,0] call ACME_fnc_bloodExposureReply;
        [_mutationResult isEqualTo [],"over-capacity admission accepted"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"over-capacity admission debited source"] call _check;
        [(_stateFixture # 2) isEqualTo {existing},"over-capacity admission changed stored bags"] call _check;
    ''')


def test_loading_requires_native_removal_readback_and_preserves_existing_entries():
    execute(fixture() + pending() + r'''
        _holder setVariable ["fixtureCargo",[_bag]];
        _nativeRemoveSucceeds=false;
        [_holder,_request,_bag,600,0] call ACME_fnc_bloodExposureReply;
        [_mutationResult isEqualTo [],"failed native removal admitted virtual bag"] call _check;
        [(_stateFixture # 2) isEqualTo [],"failed removal created cooler contents"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"failed removal lost source"] call _check;
    ''')


@pytest.mark.parametrize('native_setting', ['_nativeCanAdd=false;', '_nativeAddSucceeds=false;'])
def test_give_bag_failure_keeps_native_inventory_and_exposure_unmodified(native_setting):
    execute(fixture() + native_setting + r'''
        [!([_holder,[_bag,600],true] call ACME_fnc_coolerGiveBag),"unproved materialization succeeded"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [],"failed placement changed inventory"] call _check;
        [count _events==0 && {count (_holder getVariable "ACME_bloodSeedPending")==0},"failed placement created age seed"] call _check;
        [(missionNamespace getVariable "ACME_coolerManualOut")==0,"failed placement changed manual reservation"] call _check;
    ''')


def test_give_bag_success_records_durable_seed_and_awaits_matching_ack():
    execute(fixture() + r'''
        [[_holder,[_bag,600],true] call ACME_fnc_coolerGiveBag,"native placement failed"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"native bag missing"] call _check;
        private _seeds=_holder getVariable "ACME_bloodSeedPending";
        [count _seeds==1 && {count _events==1},"seed was not durably queued"] call _check;
        private _args=(_events # 0) # 1;
        private _request=_args # 3;
        [_holder,_request,_bag,-1,0] call ACME_fnc_bloodExposureReply;
        [count (_holder getVariable "ACME_bloodSeedPending")==1,"missing native evidence discarded seed"] call _check;
        [_holder,_request,_bag,600,0] call ACME_fnc_bloodExposureReply;
        [count (_holder getVariable "ACME_bloodSeedPending")==0,"matching seed ACK not retired"] call _check;
    ''')


def test_contents_tick_retries_unacknowledged_seed_without_materializing_a_second_bag():
    execute(fixture() + r'''
        [_holder,[_bag,600],false] call ACME_fnc_coolerGiveBag;
        private _original=(_events # 0) # 1;
        _clock=2;call ACME_fnc_coolerContentsTick;
        [count _events==2,"unacknowledged seed was not retried"] call _check;
        private _retry=(_events # 1) # 1;
        [(_retry select [0,4]) isEqualTo (_original select [0,4]),"seed retry changed funded identity"] call _check;
        [(_retry # 4)==600 && {(_retry # 5)==0},"retry restarted seed exposure clock"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"retry duplicated native bag"] call _check;
    ''')


def test_spoiled_withdrawal_materializes_inert_item_without_age_seed():
    execute(fixture() + r'''
        [[_holder,[_bag,1800],false] call ACME_fnc_coolerGiveBag,"spoiled placement failed"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo ["ACME_SpoiledBlood"],"spoiled blood became transfusable"] call _check;
        [count _events==0,"spoiled item seeded a fresh blood clock"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    'uiNamespace setVariable ["ACME_preparedListMode",true];',
    'missionNamespace setVariable ["ACME_piggybackPending",["armed"]];',
    '_rowDataFixture=_bag+"|Blood500|USED|other";',
    '_rowDataFixture="ACM_BloodBag_AN_500|Blood500|COOLER";',
    '_rowDataFixture=_bag+"|Blood1000|COOLER";',
    'missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",1];',
    'missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",objNull];',
    '_patientEpoch=1;',
    'missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",1];',
    '_selectionFixture=-1;',
    '_displayFixture=objNull;',
])
def test_draw_done_does_not_redirect_to_changed_menu_intent(change):
    execute(fixture() + r'''
        private _context=[_box,"leftarm",true,0,0,0];
    ''' + change + r'''
        [true,[_bag,"Blood500",_context]] call ACME_fnc_coolerDrawDone;
        [count _resumes==0,"draw resumed a different menu intent"] call _check;
    ''')


def test_draw_done_resumes_only_original_bag_action_and_access_once_invoked():
    execute(fixture() + r'''
        private _context=[_box,"leftarm",true,0,0,0];
        [true,[_bag,"Blood500",_context]] call ACME_fnc_coolerDrawDone;
        [_resumes isEqualTo [[[_bag,"Blood500",_context]]],"exact draw intent did not resume"] call _check;
    ''')


@pytest.mark.parametrize('shown,current', [
    ('[["ACM_BloodBag_ON_500",0]]', '[["ACM_BloodBag_AN_500",0]]'),
    ('[["ACM_BloodBag_ON_500",0]]', '[["ACM_BloodBag_ON_500",100]]'),
    ('[["ACM_BloodBag_ON_500",0]]', '[]'),
])
def test_unload_rejects_stale_displayed_entry_without_withdrawing_another_bag(shown, current):
    execute(fixture() + f'''
        _stateFixture=[_class,0,{current},0];
        _displayFixture setVariable ["ACME_CLR_RenderState",["one",[_class,0,{shown},0]]];
        _rowDataFixture="0";
        call ACME_fnc_coolerUnload;
        [_mutationResult isEqualTo [],"stale selection changed cooler contents"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [],"stale selection withdrew another bag"] call _check;
        [(_stateFixture # 2) isEqualTo {current},"stale selection removed current entry"] call _check;
    ''')


def test_unload_compares_displayed_entry_after_projecting_elapsed_warming():
    execute(fixture() + r'''
        _stateFixture=[_class,0,[[_bag,100]],90];
        _displayFixture setVariable ["ACME_CLR_RenderState",["one",[_class,0,[[_bag,100]],90]]];
        _rowDataFixture="0";_clock=110;
        call ACME_fnc_coolerUnload;
        [(_stateFixture # 2) isEqualTo [],"elapsed display snapshot rejected valid withdrawal"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [_bag],"valid withdrawal not materialized"] call _check;
        private _args=(_events # 0) # 1;
        [abs ((_args # 4)-102)<0.001,"withdrawal lost elapsed warm exposure"] call _check;
    ''')


def test_unload_full_inventory_retains_the_same_cooler_entry():
    execute(fixture() + r'''
        _stateFixture=[_class,0,[[_bag,100]],0];
        _displayFixture setVariable ["ACME_CLR_RenderState",["one",[_class,0,[[_bag,100]],0]]];
        _rowDataFixture="0";_nativeCanAdd=false;
        call ACME_fnc_coolerUnload;
        [_mutationResult isEqualTo [],"full inventory withdrew a virtual unit"] call _check;
        [(_stateFixture # 2) isEqualTo [[_bag,100]],"full inventory lost cooler blood"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [],"full inventory generated a loose bag"] call _check;
    ''')


def test_auto_store_skips_an_oversized_bag_and_admits_a_later_fitting_bag():
    execute(fixture() + 'ACME_fnc_coolerAutoStore={' + source('coolerAutoStore') + '};' + r'''
        _holder setVariable ["fixtureCargo",["ACM_BloodBag_ON_1000",_bag]];
        call ACME_fnc_coolerAutoStore;
        [count _events==1,"available volume was never filled"] call _check;
        private _args=(_events # 0) # 1;
        [(_args # 2)==_bag,"auto-store chose oversized unit"] call _check;
    ''')


def test_auto_store_preserves_manually_withdrawn_reservation():
    execute(fixture() + 'ACME_fnc_coolerAutoStore={' + source('coolerAutoStore') + '};' + r'''
        _holder setVariable ["fixtureCargo",[_bag]];
        missionNamespace setVariable ["ACME_coolerManualOut",1];
        call ACME_fnc_coolerAutoStore;
        [count _events==0,"manual withdrawal was immediately auto-stored"] call _check;
        _holder setVariable ["fixtureCargo",[]];
        call ACME_fnc_coolerAutoStore;
        [(missionNamespace getVariable "ACME_coolerManualOut")==0,"used manual reservation remained pinned"] call _check;
    ''')


@pytest.mark.parametrize('place', [False, True])
def test_contents_spoilage_never_loses_a_unit_when_native_placement_is_unavailable(place):
    execute(fixture() + f'_nativeCanAdd={str(place).lower()};' + r'''
        _stateFixture=[_class,0,[[_bag,1800]],0];
        call ACME_fnc_coolerContentsTick;
    ''' + (r'''
        [(_stateFixture # 2) isEqualTo [],"spoiled bag remained twice"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo ["ACME_SpoiledBlood"],"spoiled bag not materialized inert"] call _check;
    ''' if place else r'''
        [(_stateFixture # 2) isEqualTo [[_bag,1800]],"failed placement discarded expired bag"] call _check;
        [(_holder getVariable "fixtureCargo") isEqualTo [],"failed placement created another bag"] call _check;
    '''))
