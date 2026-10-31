"""B237: real IO callback + Local handler and the clinical reset/persistence registry.

Pain, object locality, scheduling and transport are explicit engine stand-ins.
ACME_B237_REFERENCE_ROOT permits this exact reproduction against the unmodified
B236 checkout; it does not alter the test assertions or production code.
"""
import os
from pathlib import Path
import pytest
import test_historical_io_lifecycle as io
from test_menu_death_lifecycle import ROOT, execute

SOURCE_ROOT = Path(os.environ.get('ACME_B237_REFERENCE_ROOT', str(ROOT)))
F = SOURCE_ROOT/'addons/acm_extended/functions'
PARTS = ('body', 'leftarm', 'rightarm', 'leftleg', 'rightleg', 'head')


def setup():
    old = io.F
    try:
        io.F = F
        body = io.setup()
        local = io.adapted(io.locality_body().replace("alive _unit","_patientAlive"))
    finally:
        io.F = old
    return body + r'''
        _patient setVariable ["ACME_medicationLineGenerations",createHashMapFromArray [["body:-1",1]]];
        ACME_fnc_aiProtectionSync={};ACME_fnc_aajtDownedStop={};ACME_fnc_ownerRegister={};
        ACME_fnc_providerStanceOwned={false}; CBA_fnc_execNextFrame={};
    ''' + 'private _locality='+local+';'


@pytest.mark.parametrize('run_while_away',[False,True])
def test_old_io_callback_cannot_resume_after_away_and_back_to_same_owner(run_while_away):
    execute(setup()+r'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [count _waits==1,"initial eligible IO did not schedule exactly once"] call _check;
        _patientLocal=false;[_patient,false] call _locality;
    '''+('0 call _fire;' if run_while_away else '')+r'''
        _patientLocal=true;
        private _schedule=CBA_fnc_waitAndExecute;CBA_fnc_waitAndExecute={};
        [_patient,true] call _locality;CBA_fnc_waitAndExecute=_schedule;
        0 call _fire;
        [count _publicRequests==0,"departed ownership period knocked out returning patient"] call _check;
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [count _waits==1,"ownership return retriggered consumed physical IO episode"] call _check;
    ''')


@pytest.mark.parametrize('initially_awake',[False,True])
def test_full_heal_registry_retires_episode_when_physical_generation_is_reused(initially_awake):
    # Exercise the actual field list consumed by clinicalReset. Its reset loop deletes
    # only declared clear-on-heal fields. Unrelated native teardown remains a boundary.
    registry = (F/'fn_clinicalFields.sqf').read_text()
    execute(setup()+'private _fields=call {'+registry+'};'+f'''
        _patient setVariable ["ACE_isUnconscious",{str(not initially_awake).lower()}];
    '''+r'''
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        private _oldCount=count _waits;
        {
            _x params ["_name","","_reset"];
            if (_reset) then {_patient setVariable [_name,nil];};
        } forEach (_fields select {(_x select 0)=="ACME_medicationLineGenerations" || {((_x select 0) find "ACME_ioFluidSyncopeEpisode_")==0}});
        // VM namespace stand-ins keep nil-valued keys; emulate Arma's [] read default
        // only after the real registry loop has actually cleared the episode.
        if (isNil {_patient getVariable "ACME_ioFluidSyncopeEpisode_body"}) then {
            _patient setVariable ["ACME_ioFluidSyncopeEpisode_body",[]];
        };
        _patient setVariable ["ACME_clinicalEpoch",2];
        // A removed/replaced line after full heal legitimately begins at generation 1.
        _patient setVariable ["ACME_medicationLineGenerations",createHashMapFromArray [["body:-1",1]]];
        _patient setVariable ["ACE_isUnconscious",false];
        [_patient,"body","fluid"] call ACME_fnc_ioPainResponse;
        [count _waits==_oldCount+1,"healed patient inherited previous IO eligibility/consumption"] call _check;
        if (_oldCount>0) then {0 call _fire;};
        [count _publicRequests==0,"pre-heal callback crossed clinical epoch"] call _check;
        _oldCount call _fire;
        [_publicRequests isEqualTo [[_patient,true,3,true]],"fresh physical IO lost normal transient transition"] call _check;
    ''')


@pytest.mark.parametrize('part',PARTS)
def test_io_episode_is_saved_and_cleared_with_its_physical_line(part):
    registry=(F/'fn_clinicalFields.sqf').read_text()
    execute('private _fields=call {'+registry+'};'+f'''
        private _rows=_fields select {{(_x select 0)=="ACME_ioFluidSyncopeEpisode_{part}"}};
        [count _rows==1,"physical IO eligibility is absent/duplicated in clinical registry"] call _check;
        if (count _rows==1) then {{
            [(_rows select 0 select 2) && {{(_rows select 0 param [3,true])}},"IO eligibility must reset on heal and persist with line"] call _check;
        }};
    ''')
