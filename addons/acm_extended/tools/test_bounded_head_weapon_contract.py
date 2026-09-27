"""Actual one-shot prep integrated with head-provider controller, not real weapon visuals."""
import re
import pytest
from source_scan import lex
from test_menu_death_lifecycle import adapt, execute
from test_bounded_head_completion import source
from test_bounded_head_pose_contracts import contains
from test_bounded_head_provider_sequence import setup as provider_setup, REST, FIRST, SECOND


def weapon_contract(prep=None,seq=None):
    prep=source('medicAnimationPrep') if prep is None else prep
    seq=source('headElevMedicSeq') if seq is None else seq
    for fragment in (
        'if (_elapsed >= 0 && {_elapsed < 3.2}) exitWith {',
        'if (_weapon == "") exitWith {0.05};',
        '[_medic] call ace_weaponselect_fnc_putWeaponAway;',
        '_medic action ["SwitchWeapon", _medic, _medic, 299];',
    ): assert contains(prep,fragment),fragment
    assert not any(t.value=='selectWeapon' for t in lex(prep))
    tokens=lex(seq)
    assert sum(t.value=='ACME_fnc_medicAnimationPrep' for t in tokens)==1
    selections=[tokens[i+1] for i,t in enumerate(tokens[:-1]) if t.value=='selectWeapon']
    assert len(selections)==2 and all(t.kind=='string' and t.value=='' for t in selections)
    assert contains(seq,'if (currentWeapon _u != "" && {_now < _prepUntil}) exitWith {};')
    assert contains(seq,'if (currentWeapon _u != "") then {_u selectWeapon "";};')


def setup(ace=True):
    s=source('medicAnimationPrep')
    for old,new in (
        ('local _medic','_local'),('alive _medic','_alive'),
        ('animationState _medic','_anim'),('currentWeapon _medic','_weapon'),
        ('handgunWeapon _medic','"pistol"'),
        ('_medic action ["SwitchWeapon", _medic, _medic, 299];','_holsters pushBack ["engine",_medic];'),
    ):
        s=re.sub(re.escape(old)+(r'\b' if old[-1].isalnum() else ''),lambda _:new,s)
    start=provider_setup()+'''private _holsters=[];
        ace_weaponselect_fnc_putWeaponAway={_holsters pushBack ["ace",_this select 0];};
    '''
    if not ace:start+='ace_weaponselect_fnc_putWeaponAway=nil;'
    return start+'ACME_fnc_medicAnimationPrep={'+adapt(s)+'};\n'


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('weapon,delay',[('pistol',0.95),('rifle',0.70),('launcher',0.70)])
@pytest.mark.parametrize('ace',[False,True])
def test_real_preflight_is_once_then_provider_fallback_never_redraws_weapon(mode,weapon,delay,ace):
    execute(setup(ace)+f'''
        _weapon="{weapon}";
        [_medic,"{mode}"] call ACME_fnc_headElevMedicSeq;
        [count _jobs==1,"no provider controller"] call _check;
        [_holsters isEqualTo [["{'ace' if ace else 'engine'}",_medic]],"wrong or repeated holster"] call _check;
        private _job=_jobs select 0;
        private _reserve=+(_medic getVariable ["ACME_medicAnimationPrep",[]]);
        // The existing shared choreography rate also speeds the weapon preparation.
        CBA_missionTime=10+({delay}/1.5)-0.01;
        for "_i" from 0 to 3 do {{[_job] call _tick;}};
        [count _moves==0 && {{_weapon=="{weapon}"}},"head controller bypassed prep grace"] call _check;
        CBA_missionTime=10+({delay}/1.5)+0.01;
        [_job] call _tick;
        [_weapon=="" && {{count _moves==1}},"existing empty-selection fallback lost"] call _check;
        _anim=toLower "{REST}"; [_job] call _tick;
        _anim=toLower "{FIRST}"; [_job] call _tick;
        _anim=toLower "{SECOND}"; [_job] call _tick;
        _anim=toLower "{REST}"; [_job] call _tick;
        [_waits select 0] call _deliver;
        [count _holsters==1 && {{_weapon==""}},"provider exit reholstered or redrew weapon"] call _check;
        [(_medic getVariable ["ACME_medicAnimationPrep",[]]) isEqualTo _reserve,"provider replaced prep reservation"] call _check;
        [count _moves==3 && {{_removed isEqualTo [73]}},"Putdown adoption or finalization changed"] call _check;
        [_stances isEqualTo ["MIDDLE","MIDDLE","AUTO"],"normal provider stance flow changed"] call _check;
    ''')


@pytest.mark.parametrize('where,old,new',[
    ('prep','if (_elapsed >= 0 && {_elapsed < 3.2}) exitWith {','if (false) exitWith {'),
    ('seq','private _prepDelay = [_medic] call ACME_fnc_medicAnimationPrep;',
     'private _prepDelay = [_medic] call ACME_fnc_medicAnimationPrep; [_medic] call ACME_fnc_medicAnimationPrep;'),
    ('seq','_u selectWeapon "";','_u selectWeapon "rifle";'),
])
def test_weapon_contract_rejects_restart_or_redraw_despite_comment_decoys(where,old,new):
    values={'prep':source('medicAnimationPrep'),'seq':source('headElevMedicSeq')}
    assert old in values[where]
    values[where]=values[where].replace(old,new)+'\n/* '+old+' */'
    with pytest.raises(AssertionError):weapon_contract(**values)
