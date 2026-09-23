"""Current staged-target and explicit-confirmation contracts, not dose delivery."""
from pathlib import Path
import pytest
from source_scan import lex
from test_menu_death_lifecycle import execute
from test_bounded_normal_push_lifetime import setup

F = Path(__file__).resolve().parents[1] / 'functions'


def tokens(text):
    return [(t.kind,t.value) for t in lex(text)]


def contains(text, fragment):
    haystack, needle = tokens(text), tokens(fragment)
    return any(haystack[i:i+len(needle)] == needle for i in range(len(haystack)-len(needle)+1))


def assert_staged_contract(begin, confirm):
    assert contains(begin, 'uiNamespace setVariable ["ACME_SK_PendingInjection",[_bodyPart,_siteIdx,_route]];')
    assert not contains(begin, 'call ACME_fnc_skInjectSite')
    assert not contains(begin, 'call ACME_fnc_skConfirmInjection')
    assert not contains(begin, 'uiNamespace setVariable ["ACME_SK_InjectionBusy",true]')
    assert contains(confirm, 'private _pushSec = 3;')
    assert contains(confirm, 'if (_route != "im") then')
    assert contains(confirm, 'if (_pushDurationValid) then {_pushSec = _typed;};')
    assert contains(confirm, 'private _e = _t * _t * (3 - (2 * _t));')
    assert contains(confirm, '_ctrl ctrlCommit 0;')
    assert contains(confirm, 'uiNamespace setVariable ["ACME_SK_InjectionBusy",true];')
    assert contains(confirm, 'playSound "ACME_SyringePush";')
    assert contains(confirm, '[_bodyPart,_pushSec] call ACME_fnc_skInjectSite;')
    assert contains(confirm, '_pushSec] call CBA_fnc_waitAndExecute;')
    # Instant engine commits are individual smoothstep frames, never a three-second large-control slide.
    assert not contains(confirm, 'ctrlCommit 3.0')


@pytest.mark.parametrize('route,site',[('vascular',1),('vascular',-1),('im',-1)])
def test_site_stages_target_without_starting_flow_or_locking_syringe_selection(route,site):
    execute(setup()+f'''
        uiNamespace setVariable ["ACME_SK_Route","{route}"];
        uiNamespace setVariable ["ACME_SK_SiteIdx",{site}];
        [["rightleg"] call ACME_fnc_skBeginInjection,"staging rejected"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightleg",{site},"{route}"],"wrong target staged"] call _check;
        [count _delivered==0 && {{count _waits==0}} && {{_hcStarts==0}},"staging started flow"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",false]),"staging locked selection"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo [_row,_other],"staging changed inventory payload"] call _check;
    ''')


@pytest.mark.parametrize('denial', ['busy','editor','access'])
def test_staging_denials_preserve_existing_target_and_do_not_administer(denial):
    change={'busy':'uiNamespace setVariable ["ACME_SK_InjectionBusy",true];',
            'editor':'uiNamespace setVariable ["ACME_SK_TagEditMode",true];','access':'_hasAccess=false;'}[denial]
    execute(setup()+change+'''
        [!(["rightleg"] call ACME_fnc_skBeginInjection),"denied target staged"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["leftarm",1,"vascular"],"denial changed target"] call _check;
        [count _delivered==0 && {count _waits==0},"denial started flow"] call _check;
    ''')


@pytest.mark.parametrize('target,old,new',[
    ('begin','true\n','call ACME_fnc_skInjectSite; true\n'),
    ('begin','ACME_SK_PendingInjection','ACME_SK_WrongTarget'),
    ('confirm','private _pushSec = 3;','private _pushSec = 30;'),
    ('confirm','if (_route != "im") then {','if (true) then {'),
    ('confirm','[_bodyPart,_pushSec] call ACME_fnc_skInjectSite;','[_bodyPart] call ACME_fnc_skInjectSite;'),
])
def test_contract_rejects_immediate_flow_wrong_defaults_or_lost_duration_despite_comments(target,old,new):
    texts={n:(F / ('fn_sk'+('BeginInjection' if n=='begin' else 'ConfirmInjection')+'.sqf')).read_text() for n in ['begin','confirm']}
    assert old in texts[target]
    texts[target]=texts[target].replace(old,new,1)+'\n/* '+old+' */\n'
    with pytest.raises(AssertionError):
        assert_staged_contract(texts['begin'],texts['confirm'])
