"""Normal-push callbacks must not retire a successor's shared UI workspace.

Runs actual confirmation, registration prefix and Unload with recorded engine
boundaries. No drug/inventory transactions, display destruction or network timing.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_narc_close_generation import setup


@pytest.mark.parametrize('boundary', ['start', 'commit'])
@pytest.mark.parametrize('replacement', ['new_display', 'same_display', 'closed_successor'])
def test_old_push_without_replacement_job_preserves_successor_workspace(boundary, replacement):
    execute(setup() + '''
        call ACME_fnc_skConfirmInjection;
    ''' + ('0 call _runWait;' if boundary == 'commit' else '') + (
        '_drawDisplay=parsingNamespace;' if replacement != 'same_display' else '') + '''
        call _register;
    ''' + ('[_drawDisplay] call ACME_fnc_skClose;' if replacement == 'closed_successor' else '') + '''
        // No new normal push replaces the old global job. The new workspace still owns these values.
        uiNamespace setVariable ["ACME_SK_PendingInjection",["rightleg",2,"vascular"]];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
        uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",99];
        _effects=[]; _removed=[]; _sounds=[]; _enables=[]; _refreshes=0;
        private _countBefore=count _waits;
    ''' + f'{1 if boundary == "commit" else 0} call _runWait;' + '''
        [count _delivered==0 && {count _waits==_countBefore},"superseded workspace continued old push"] call _check;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo [],"old job record retained"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightleg",2,"vascular"],"old retirement cleared successor target"] call _check;
        [uiNamespace getVariable ["ACME_SK_InjectionBusy",false],"old retirement cleared successor injection lock"] call _check;
        [uiNamespace getVariable ["ACME_SK_CarouselBusy",false],"old retirement cleared successor carousel lock"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1])==99,"successor handler changed"] call _check;
        [count _effects==0 && {count _removed==0} && {count _sounds==0} && {count _enables==0} && {_refreshes==0},"old retirement touched successor presentation"] call _check;
    ''')


@pytest.mark.parametrize('boundary', ['start', 'commit'])
def test_changed_provider_is_not_unlocked_by_the_old_push(boundary):
    execute(setup() + 'call ACME_fnc_skConfirmInjection;' + (
        '0 call _runWait;' if boundary == 'commit' else '') + '''
        ACE_player=parsingNamespace;
        uiNamespace setVariable ["ACME_SK_PendingInjection",["rightleg",2,"vascular"]];
    ''' + f'{1 if boundary == "commit" else 0} call _runWait;' + '''
        [count _delivered==0,"previous provider handed off medication"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightleg",2,"vascular"],"previous provider cleared target"] call _check;
        [uiNamespace getVariable ["ACME_SK_InjectionBusy",false],"previous provider cleared lock"] call _check;
    ''')


def test_plunger_stops_after_same_display_is_registered_as_a_new_workspace():
    execute(setup() + '''
        call ACME_fnc_skConfirmInjection; 0 call _runWait;
        call _register;
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",99];
        _writes=[]; _commits=[]; _removed=[];
        0 call _runAnim;
        [count _writes==0 && {count _commits==0},"old plunger moved in successor workspace"] call _check;
        [_removed isEqualTo [0],"old plunger did not remove only itself"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1])==99,"old plunger cleared new handle"] call _check;
    ''')


@pytest.mark.parametrize('boundary', ['start', 'commit'])
def test_still_owned_invalid_page_keeps_existing_unlock_cleanup(boundary):
    execute(setup() + 'call ACME_fnc_skConfirmInjection;' + (
        '0 call _runWait;' if boundary == 'commit' else '') + '''
        uiNamespace setVariable ["ACME_SK_View","syringe"];
    ''' + f'{1 if boundary == "commit" else 0} call _runWait;' + '''
        [count _delivered==0,"cancelled current push delivered"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",true]),"own invalid push stayed locked"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_CarouselBusy",true]),"own invalid carousel stayed locked"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[1]]) isEqualTo [],"own cancelled target survived"] call _check;
    ''')


@pytest.mark.parametrize('route,site', [('vascular',1), ('vascular',-1), ('im',-1)])
@pytest.mark.parametrize('patient_alive', [False,True])
def test_current_registered_workspace_retains_exact_handoff(route,site,patient_alive):
    execute(setup() + f'''
        _patientAlive={str(patient_alive).lower()};
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftleg",{site},"{route}"]];
        [call ACME_fnc_skConfirmInjection,"current registered push rejected"] call _check;
        0 call _runWait; 1 call _runWait; 1 call _runWait;
        [_delivered isEqualTo [[_medic,_patient,"id-one",["leftleg",3],{site},"{route}"]],"current duration/target/dead-patient handoff changed"] call _check;
    ''')


@pytest.mark.parametrize('epoch', [-1,0])
def test_unowned_registration_cannot_start_a_normal_push(epoch):
    execute(setup() + f'''
        _drawDisplay setVariable ["ACME_SK_CloseEpoch",{epoch}];
        [!(call ACME_fnc_skConfirmInjection),"unowned display started push"] call _check;
        [count _waits==0 && {{count _delivered==0}},"unowned display scheduled medication"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",false]),"unowned display locked workspace"] call _check;
    ''')
