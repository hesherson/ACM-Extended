"""Execute provider cancellation against reordered episode and preparation tokens."""
import pytest
from test_chest_entry_timing import setup
from test_menu_death_lifecycle import execute


@pytest.mark.parametrize('incoming', ['vest:access:old', 'chestprep:old', ''])
def test_old_same_patient_stop_preserves_new_provider(incoming):
    execute(setup()+r'''
        private _ep=[_medic,_patient,"start",false,"vest:access:current"] call ACME_fnc_chestAccessVestProvider;
        _medic setVariable ["ACME_chestAccessPreflightToken","chestprep:current"];
        private _before=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
    '''+f'private _result=[_medic,_patient,"stop",true,"{incoming}"] call ACME_fnc_chestAccessVestProvider;'+r'''
        [_result==-1,"stale stop was accepted"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _before,"stale stop ended newer pose"] call _check;
        [(_medic getVariable ["ACME_chestAccessProvider",[]]) isEqualTo [_patient,_ep,"vest:access:current"],"stale stop cleared newer provider"] call _check;
        [(_medic getVariable ["ACME_chestAccessProviderReady",[]]) isEqualTo ["vest:access:current",-1],"stale stop cleared newer readiness"] call _check;
    ''')


def test_current_preparation_resolves_provider_token_before_stop():
    execute(setup()+r'''
        private _ep=[_medic,_patient,"start",false,"vest:access:current"] call ACME_fnc_chestAccessVestProvider;
        _medic setVariable ["ACME_chestAccessPreflightToken","chestprep:current"];
        private _provider=_medic getVariable ["ACME_chestAccessProvider",[]];
        private _result=[_medic,_patient,"stop",true,_provider select 2] call ACME_fnc_chestAccessVestProvider;
        [_result==_ep,"current stop was rejected"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo [],"current stop left pose active"] call _check;
        [(_medic getVariable ["ACME_chestAccessProvider",[]]) isEqualTo [],"current stop left provider active"] call _check;
        [(_medic getVariable ["ACME_chestAccessProviderReady",[]]) isEqualTo [],"current stop left readiness active"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_medic setVariable ["ACME_chestAccessPreflightActive",false];',
    '_medic setVariable ["ACME_chestAccessPreflightToken","chestprep:new"];',
    '_medic setVariable ["ACME_chestAccess_treatment",[]];',
])
def test_delayed_access_start_does_not_replace_cancelled_or_newer_preflight(change):
    execute(setup()+r'''
        _medic setVariable ["ACME_chestAccessPreflightActive",true];
        _medic setVariable ["ACME_chestAccessPreflightToken","chestprep:old"];
        _medic setVariable ["ACME_chestAccess_treatment",[_patient,"checkbreathing","lease"]];
    '''+change+r'''
        private _result=[_medic,_patient,"start",false,"vest:access:old","chestprep:old"] call ACME_fnc_chestAccessVestProvider;
        [_result==-1 && {count _moves==0},"late access start reacquired provider animation"] call _check;
        [(_medic getVariable ["ACME_chestAccessProvider",[]]) isEqualTo [],"late access start acquired provider state"] call _check;
    ''')


def test_current_access_start_is_accepted():
    execute(setup()+r'''
        _medic setVariable ["ACME_chestAccessPreflightActive",true];
        _medic setVariable ["ACME_chestAccessPreflightToken","chestprep:current"];
        _medic setVariable ["ACME_chestAccess_treatment",[_patient,"checkbreathing","lease"]];
        private _result=[_medic,_patient,"start",false,"vest:access:current","chestprep:current"] call ACME_fnc_chestAccessVestProvider;
        [_result>=0,"current access start rejected"] call _check;
    ''')
