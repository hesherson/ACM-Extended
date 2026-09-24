"""Keep confirmation on the patient actually shown by its owning Body Map.

The complete confirmation and callback code executes. UI and medication handoffs
are explicit fixtures; these tests do not deliver drugs or simulate live input.
"""
import pytest
from test_bounded_normal_push_lifetime import setup
from test_menu_death_lifecycle import execute


@pytest.mark.parametrize('route,site,hardcore', [
    ('vascular', 2, False), ('vascular', -1, False),
    ('im', -1, False), ('vascular', 2, True),
])
@pytest.mark.parametrize('wrong_patient', ['_medic', 'parsingNamespace'])
def test_conflicting_shared_patient_is_rejected_before_push_or_hardcore_dispatch(route, site, hardcore, wrong_patient):
    execute(setup() + f'''
        uiNamespace setVariable ["ACME_SK_Patient",{wrong_patient}];
        uiNamespace setVariable ["ACME_SK_PendingInjection",["rightarm",{site},"{route}"]];
        missionNamespace setVariable ["ACME_hcEff_medications",{str(hardcore).lower()}];
        private _beforeStore=+(_medic getVariable ["ACME_narcStore",[]]);
        [!(call ACME_fnc_skConfirmInjection),"conflicting displayed patient accepted"] call _check;
        [count _waits==0 && {{_hcStarts==0}} && {{count _delivered==0}},"wrong-patient work scheduled"] call _check;
        [count _enables==0 && {{count _sounds==0}},"rejected confirmation touched controls"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",false]),"rejected confirmation locked UI"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightarm",{site},"{route}"],"rejection replaced staged target"] call _check;
        [(uiNamespace getVariable ["ACME_SK_Patient",objNull]) isEqualTo {wrong_patient},"rejection silently rewrote patient"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo _beforeStore,"rejection altered inventory"] call _check;
    ''')


@pytest.mark.parametrize('boundary', ['settle', 'complete'])
@pytest.mark.parametrize('replacement', ['parsingNamespace', 'objNull'])
def test_display_patient_change_rejects_old_normal_push_even_when_shared_patient_is_unchanged(boundary, replacement):
    execute(setup() + '''
        [call ACME_fnc_skConfirmInjection,"initial confirmation failed"] call _check;
    ''' + ('0 call _runWait;' if boundary=='complete' else '') + f'''
        _drawDisplay setVariable ["ACME_SK_ReturnPatient",{replacement}];
        {1 if boundary=='complete' else 0} call _runWait;
        [count _delivered==0,"old push ignored the displayed patient change"] call _check;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo [],"rejected job did not retire"] call _check;
        [count _waits=={2 if boundary=='complete' else 1},"rejected settle scheduled completion"] call _check;
    ''')


@pytest.mark.parametrize('route,site', [('vascular', 2), ('vascular', -1), ('im', -1)])
@pytest.mark.parametrize('shared_cleared', [False, True])
def test_matching_display_or_existing_return_fallback_keeps_exact_handoff(route, site, shared_cleared):
    execute(setup() + f'''
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",{site},"{route}"]];
    ''' + ('uiNamespace setVariable ["ACME_SK_Patient",objNull];' if shared_cleared else '') + f'''
        [call ACME_fnc_skConfirmInjection,"valid displayed patient rejected"] call _check;
        [count _delivered==0,"premature handoff"] call _check;
        0 call _runWait;
        [count _delivered==0,"settle committed early"] call _check;
        1 call _runWait;
        [_delivered isEqualTo [[_medic,_patient,"id-one",["leftarm",3],{site},"{route}"]],"valid handoff changed"] call _check;
        1 call _runWait;
        [count _delivered==1,"duplicate completion delivered twice"] call _check;
    ''')


def test_self_view_with_explicit_self_patient_still_works():
    execute(setup() + '''
        _drawDisplay setVariable ["ACME_SK_ReturnPatient",objNull];
        uiNamespace setVariable ["ACME_SK_Patient",_medic];
        [call ACME_fnc_skConfirmInjection,"self confirmation rejected"] call _check;
        0 call _runWait; 1 call _runWait;
        [count _delivered==1 && {((_delivered select 0) select 1) isEqualTo _medic},"self handoff changed"] call _check;
    ''')


@pytest.mark.parametrize('boundary', ['settle','complete'])
def test_existing_shared_patient_change_rejection_is_not_weakened(boundary):
    execute(setup() + '''call ACME_fnc_skConfirmInjection;''' + ('0 call _runWait;' if boundary=='complete' else '') + f'''
        uiNamespace setVariable ["ACME_SK_Patient",parsingNamespace];
        {1 if boundary=='complete' else 0} call _runWait;
        [count _delivered==0,"shared patient guard lost"] call _check;
    ''')


def test_matching_hardcore_still_delegates_without_normal_callback():
    execute(setup()+'''
        missionNamespace setVariable ["ACME_hcEff_medications",true];
        [call ACME_fnc_skConfirmInjection,"Hardcore delegation rejected"] call _check;
        [_hcStarts==1 && {count _waits==0} && {count _delivered==0},"Hardcore path replaced"] call _check;
    ''')


def test_missing_display_still_rejects():
    execute(setup()+'''
        _drawDisplay=objNull;
        [!(call ACME_fnc_skConfirmInjection),"missing display accepted"] call _check;
        [count _waits==0 && {_hcStarts==0},"missing display started work"] call _check;
    ''')
