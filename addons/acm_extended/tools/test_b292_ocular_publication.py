"""Exercise actual ocular ticks with publication snapshots at the engine boundary.

Unchanged structural state and shield tombstones must not broadcast every second.
Changed anatomy, recovery endpoints and terminal deletions must still publish.
This measures publication requests, not Arma bandwidth or packet delivery.
"""
import pytest

from test_b291_ocular_integration import SETUP, source
from test_menu_death_lifecycle import execute


def setup():
    return SETUP + r'''
        private _publications=[];
        private _ocularPublish={params ["_obj","_name","_value"];
            _publications pushBack [_name,str _value];
            _obj setVariable [_name,_value];
        };
    ''' + ''.join(
        f'ACM_ophthalmology_fnc_{name}={{' + source(name, instrument_public=True) + '};'
        for name in ('structuralTick', 'shieldRecover')
    ) + r'''
        private _step={
            [_patient] call ACM_ophthalmology_fnc_shieldRecover;
            [_patient] call ACM_ophthalmology_fnc_structuralTick;
        };
    '''


@pytest.mark.parametrize('side', [0, 1])
def test_healthy_shield_has_no_repeated_structural_or_empty_terminal_publications(side):
    execute(setup() + f'''
        _hmd=["kat_eyecovers_right","kat_eyecovers_left"] select {side};
        _patient setVariable ["ACM_ophthalmology_eyeShieldItem",_hmd];
        _patient setVariable ["ACM_ophthalmology_eyeShieldIndex",{side}];
        for "_i" from 1 to 60 do {{CBA_missionTime=100+_i;call _step;}};
        [count _publications==0,"healthy shield broadcast unchanged state every tick"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeShieldItem")==_hmd,"traffic fix discarded worn shield"] call _check;
    ''')


@pytest.mark.parametrize('eyes,severe', [('[0,0]', 'true'), ('[0,1]', 'false')])
def test_permanent_injury_broadcasts_no_unchanged_anatomy_or_severity(eyes, severe):
    execute(setup() + f'''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",{eyes}];
        _patient setVariable ["ACM_ophthalmology_eyeInjurySevere",{severe}];
        _patient setVariable ["ACM_ophthalmology_ocularPermanent",true];
        _patient setVariable ["ACME_requiresEvac",true];
        for "_i" from 1 to 60 do {{CBA_missionTime=100+_i;call _step;}};
        [count _publications==0,"permanent injury repeatedly broadcast unchanged state"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo {eyes},"permanent injury healed"] call _check;
    ''')


def test_recovery_publishes_changed_eyes_once_and_never_publishes_a_zero_delta_tick():
    execute(setup() + r'''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0.4,1]];
        _patient setVariable ["ACM_ophthalmology_structuralLastTick",100];
        call _step;
        [count _publications==0,"zero-time recovery sent unchanged anatomy"] call _check;
        CBA_missionTime=101;call _step;
        [count _publications==1,"changed eye did not produce exactly one publication"] call _check;
        [((_publications select 0) select 0)=="ACM_ophthalmology_eyeInjuries","recovery sent unrelated unchanged state"] call _check;
        [((_patient getVariable "ACM_ophthalmology_eyeInjuries") select 0)>0.4,"copying anatomy lost local recovery"] call _check;
        [((_publications select 0) select 1)==str (_patient getVariable "ACM_ophthalmology_eyeInjuries"),"wire snapshot missed updated eye"] call _check;
        call _step;
        [count _publications==1,"same-clock retry repeated recovery packet"] call _check;
    ''')


def test_recovery_publishes_exact_endpoint_and_severity_transition_before_retiring():
    execute(setup() + r'''
        _patient setVariable ["ACM_ophthalmology_eyeInjuries",[0.998,0.998]];
        _patient setVariable ["ACM_ophthalmology_eyeInjurySevere",true];
        _patient setVariable ["ACM_ophthalmology_structuralLastTick",99];
        call _step;
        [(_patient getVariable "ACM_ophthalmology_eyeInjuries") isEqualTo [1,1],"recovery did not reach exact healthy endpoint"] call _check;
        [!(_patient getVariable "ACM_ophthalmology_eyeInjurySevere"),"stale severe injury survived recovery"] call _check;
        [count _publications==2,"recovery endpoint/label was lost or sent unrelated state"] call _check;
        call _step;
        [count _publications==2,"healthy endpoint remained a periodic broadcaster"] call _check;
    ''')


def test_removed_shield_metadata_clears_once_without_repeated_empty_state():
    execute(setup() + r'''
        _patient setVariable ["ACM_ophthalmology_eyeShieldItem","kat_eyecovers_left"];
        _patient setVariable ["ACM_ophthalmology_eyeShieldIndex",1];
        _hmd="NVGoggles";
        call _step;call _step;
        [count _publications==2,"removed shield did not clear exactly its two metadata fields"] call _check;
        [(_patient getVariable "ACM_ophthalmology_eyeShieldItem")=="" && {(_patient getVariable "ACM_ophthalmology_eyeShieldIndex")==-1},"stale shield metadata survived"] call _check;
        [_hmd=="NVGoggles","metadata cleanup changed actual equipment"] call _check;
    ''')


@pytest.mark.parametrize('outcome,closed,prune', [
    ('applied', False, True), ('refunded', False, True),
    ('spent', True, True), ('spent', False, False),
])
@pytest.mark.parametrize('living', [True, False])
def test_terminal_history_only_publishes_actual_expiry_and_preserves_unresolved_spent(outcome, closed, prune, living):
    execute(setup() + f'''
        _livePatient={str(living).lower()};
        private _request=[_patient,_medic,"history",7,3,3,0,100,[],7,0,[7,0]];
        private _entry=[_request,"{outcome}"];
        if ({str(closed).lower()}) then {{_entry pushBack true;}};
        private _terminal=createHashMapFromArray [["history",_entry]];
        _patient setVariable ["ACM_ophthalmology_shieldTerminal",_terminal];
        _serverClock=130;[_patient] call ACM_ophthalmology_fnc_shieldRecover;
        [count _publications==0 && {{count (_patient getVariable "ACM_ophthalmology_shieldTerminal")==1}},"terminal was published unchanged or pruned before expiry"] call _check;
        _serverClock=131;[_patient] call ACM_ophthalmology_fnc_shieldRecover;
        [_publications isEqualTo {('[["ACM_ophthalmology_shieldTerminal",str createHashMap]]' if prune else '[]')},"expiry publication did not match actual terminal deletion"] call _check;
        [count (_patient getVariable "ACM_ophthalmology_shieldTerminal")=={0 if prune else 1},"unresolved spent state lost or completed terminal stranded"] call _check;
        [_patient] call ACM_ophthalmology_fnc_shieldRecover;
        [count _publications=={1 if prune else 0},"terminal cleanup kept broadcasting its unchanged result"] call _check;
    ''')
