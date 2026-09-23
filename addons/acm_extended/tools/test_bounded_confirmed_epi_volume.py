"""Actual staged epinephrine confirmation through store debit and request creation.

Arma objects, UI, timers, access/distance and network transport are fixtures. The
complete confirmation, injection and measured debit functions execute. Finite
inputs only; no clinical kinetics, real inventory or live transport is simulated.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_normal_push_lifetime import F, setup as push_setup
from test_historical_cardiac_execution import code, function


def setup(total=10):
    inject = (F/'fn_skInjectSite.sqf').read_text().replace('findDisplay 84000','_drawDisplay')
    inject = inject.replace('ACE_player distance _patient','_distance')
    inject = inject.replace('objectParent ACE_player','objNull')
    return push_setup()+'''
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _requests=[]; private _storeAtRequest=[]; private _removedRows=[];
        ACME_fnc_skSiteName={"selected site"}; ACME_fnc_bodyPartName={"left arm"};
        ACME_fnc_skAfterStoredRemoval={_removedRows pushBack +_this;};
        ACME_fnc_skRefreshDrawn={};
        ACME_fnc_medicationRequest={
            _storeAtRequest pushBack (+(_medic getVariable ["ACME_narcStore",[]]));
            _requests pushBack +_this;
        };
    '''+function('epinephrinePushStored',extended=True)+'ACME_fnc_skInjectSite={'+code(inject)+'};'+f'''
        _row=["EpinephrineCardiac",10,{total/10},"measured",{total*0.9},[],"epiMixB12","none","a","b","c","id-one"];
        [_medic,[_row,_other]] call ACME_fnc_narcStoreCommit;
    '''


def assert_debit(volume, total=10, duration=3, site=1):
    return f'''
        [count _requests==1,"wrong request count"] call _check;
        if (count _requests==1) then {{
            private _r=_requests select 0;
            private _dose=(_r select 3) select 0;
            [abs ((_dose select 1)-{volume*0.01})<0.000001,"confirmed epinephrine volume drifted"] call _check;
            [(_dose select 4)=={duration} && {{(_r select 5)=={site}}},"duration or site lost"] call _check;
            [(_r select 0) isEqualTo _medic && {{(_r select 1) isEqualTo _patient}},"target changed"] call _check;
            private _refund=((_r select 6) select 1) select 0;
            [abs (((_refund select 2)+(_refund select 4))-{volume})<0.000001,"refund not exact confirmed volume"] call _check;
            private _left=_medic getVariable ["ACME_narcStore",[]];
            [(_storeAtRequest select 0) isEqualTo _left,"request preceded debit"] call _check;
            private _remaining=if ({total-volume}<0.001) then {{0}} else {{((_left select 0) select 2)+((_left select 0) select 4)}};
            [abs (_remaining-{total-volume})<0.000001,"remainder drifted"] call _check;
            [(_left select ((count _left)-1)) isEqualTo _other,"unrelated syringe modified"] call _check;
        }};
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",true]),"completed push left lock"] call _check;
    '''


@pytest.mark.parametrize('choice',[0,1,2])
@pytest.mark.parametrize('later',[0,1,2])
@pytest.mark.parametrize('boundary',['settle','commit'])
def test_confirmation_amount_not_later_selector_controls_debit(choice,later,boundary):
    volume=[1,2,10][choice]
    change=f'uiNamespace setVariable ["ACME_SK_EpiDoseChoice",{later}];'
    execute(setup()+f'''
        uiNamespace setVariable ["ACME_SK_EpiDoseChoice",{choice}];
        [call ACME_fnc_skConfirmInjection,"confirmation rejected"] call _check;
        [count _requests==0,"premature debit"] call _check;
    '''+(change if boundary=='settle' else '')+'''
        0 call _runWait;
        [count _requests==0,"settle administered"] call _check;
    '''+(change if boundary=='commit' else '')+f'''
        _nowTime=13; 0 call _runAnim;
        [abs (((_positions get "84422") select 1)-(0.3+0.17*{(10-volume)/10}))<0.000001,"stroke disagrees with confirmed volume"] call _check;
        1 call _runWait;
        [uiNamespace getVariable ["ACME_SK_EpiDoseChoice",-1]=={later},"handoff rewrote later selector"] call _check;
    '''+assert_debit(volume))


@pytest.mark.parametrize('total',[0.5,1.5,10])
@pytest.mark.parametrize('choice',[0,1,2])
def test_partial_full_and_dead_patient_preserve_exact_volume_and_typed_duration(total,choice):
    volume=min([1,2,total][choice],total)
    execute(setup(total)+f'''
        _patientAlive=false; _durationText="30";
        uiNamespace setVariable ["ACME_SK_EpiDoseChoice",{choice}];
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",-1,"vascular"]];
        call ACME_fnc_skConfirmInjection; 0 call _runWait;
        [((_waits select 1) select 2)==30 && {{count _requests==0}},"duration or early commit changed"] call _check;
        1 call _runWait; 1 call _runWait;
    '''+assert_debit(volume,total,30,-1))


@pytest.mark.parametrize('change',[
    '_hasAccess=false;', '_distance=6;',
    'ACM_circulation_fnc_hasIV={count _this<4}; ACM_circulation_fnc_hasIO={false};',
])
def test_authoritative_access_and_distance_checks_still_reject_after_animation(change):
    execute(setup()+'''
        uiNamespace setVariable ["ACME_SK_EpiDoseChoice",1];
        call ACME_fnc_skConfirmInjection; 0 call _runWait;
        private _before=+(_medic getVariable ["ACME_narcStore",[]]);
    '''+change+'''
        1 call _runWait;
        [count _requests==0,"invalid access or distance still administered"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo _before,"rejected request consumed store"] call _check;
    ''')


@pytest.mark.parametrize('choice',[0,1,2])
def test_legacy_direct_injection_retains_live_selector_when_no_amount_is_supplied(choice):
    execute(setup()+f'''
        uiNamespace setVariable ["ACME_SK_EpiDoseChoice",{choice}];
        ["leftarm",3] call ACME_fnc_skInjectSite;
        uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
    '''+assert_debit([1,2,10][choice]))


def test_reduced_remaining_solution_rejects_instead_of_silently_shrinking_confirmed_amount():
    execute(setup()+'''
        uiNamespace setVariable ["ACME_SK_EpiDoseChoice",2];
        call ACME_fnc_skConfirmInjection; 0 call _runWait;
        private _smaller=+_row; _smaller set [2,0.5]; _smaller set [4,4.5];
        [_medic,[_smaller,_other]] call ACME_fnc_narcStoreCommit;
        1 call _runWait;
        [count _requests==0,"insufficient remainder changed confirmed amount"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo [_smaller,_other],"rejected amount consumed store"] call _check;
    ''')
