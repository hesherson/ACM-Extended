"""Run production delayed-posture branches with controlled engine and scheduler boundaries."""
import re

import pytest

from test_menu_death_lifecycle import F, adapt, execute


def posture_engine(source):
    """Mock only engine object/pose operations; retain tokens and callback bodies."""
    source = source.replace('clientOwner', '_ownerNum').replace('serverTime', 'CBA_missionTime')
    # Emulate publication for the migrated presentation fields separately from the local object copy.
    source = re.sub(
        r'(_\w+) setVariable \[("(?:ACME_blast_stanceToken|ACME_obtunded_sprintRagdollToken|ACME_obtunded_sprintRagdollActive)"), ([^;\n]+), (true|false)\];',
        lambda m: m[0] + (f' _publicFallState setVariable [{m[2]}, {m[3]}];' if m[4] == 'true' else ''),
        source,
    )
    for unit in ('_unit', '_u', '_p', '_patient'):
        source = re.sub(r'\blocal ' + re.escape(unit) + r'\b', '_patientLocal', source)
        source = re.sub(r'\balive ' + re.escape(unit) + r'\b', '_patientAlive', source)
        source = re.sub(r'\bobjectParent ' + re.escape(unit) + r'\b', 'objNull', source)
        source = re.sub(r'\battachedTo ' + re.escape(unit) + r'\b', 'objNull', source)
        source = re.sub(r'\bstance ' + re.escape(unit) + r'\b', '_stance', source)
        source = re.sub(re.escape(unit) + r' setUnitPos ("[^"]+")', r'_positions pushBack \1', source)
        source = re.sub(re.escape(unit) + r' setUnconscious (true|false)', r'_engineUnconscious = \1; _ragdolls pushBack \1', source)
        source = re.sub(re.escape(unit) + r' playActionNow ("[^"]+")', r'_moves pushBack \1', source)
    source = re.sub(r'inputAction "([^"]+)"', lambda m: ('_movingInput' if m[1] == 'MoveForward' else '_sprintInput' if m[1] == 'Turbo' else '0'), source)
    return adapt(source)


def setup():
    blast = (F / 'fn_blastApply.sqf').read_text().split('// 3. falling and stance.', 1)[1].split('// 4. the brain.', 1)[0]
    obtunded = (F / 'fn_obtundedTick.sqf').read_text()
    sprint = obtunded.split('    private _moving =', 1)[1].split('    // Small head sway', 1)[0]
    recovery = obtunded.split('            _p setAnimSpeedCoef 1;', 1)[1].split('        private _cc =', 1)[0]
    reset = (F / 'fn_clearAllAilments.sqf').read_text().split('// B156 owned fall cleanup:', 1)[1].split('// End B156 owned fall cleanup.', 1)[0]
    reset = reset.split('\n', 1)[1]
    # Retain the matching !isNull _p block opening for this production recovery tail.
    recovery = 'if (!isNull _p) then {' + recovery
    return '''
        private _patientLocal = true;
        private _publicFallState = missionNamespace;
        private _positions = []; private _ragdolls = [];
        private _stance = "STAND";
        private _engineUnconscious = false;
        private _providerOwnsStance = false;
        private _movingInput = 1; private _sprintInput = 1;
        ACME_fnc_clinicalEpoch = {(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACME_fnc_animBlocked = {false};
        ACME_fnc_providerStanceOwned = {_providerOwnsStance};
        CBA_fnc_waitAndExecute = {_waits pushBack [_this select 0,_this select 1,_this select 2];};
        private _deliver = {private _w = _waits select _this; (_w select 1) call (_w select 0);};
        missionNamespace setVariable ["ACME_obtunded_sprintFallChance",1];
    ''' + 'private _blast = {private _unit = _patient; private _dose = 0.3;' + posture_engine(blast) + '};' + 'private _sprint = {private _p = _patient; private _now = _nowTime; private _moving =' + posture_engine(sprint) + '};' + 'private _recover = {private _p = _patient;' + posture_engine(recovery) + '};' + 'private _fullHeal = {_patient setVariable ["ACME_clinicalEpoch",1];' + posture_engine(reset) + '};'


@pytest.mark.parametrize('new_fall', [False, True])
def test_blast_callback_rejects_previous_clinical_episode(new_fall):
    execute(setup() + '''
        call _blast;
        [count _waits == 1 && {((_waits select 0) select 2) == 3},"blast delay changed"] call _check;
        call _fullHeal;
        [_positions isEqualTo ["DOWN","AUTO"],"full heal stranded owned blast stance"] call _check;
        _positions = [];
    ''' + ('call _blast; _positions = [];' if new_fall else '') + '''
        0 call _deliver;
        [count _positions == 0,"old blast callback changed healed/replacement stance"] call _check;
    ''' + ('1 call _deliver; [_positions isEqualTo ["AUTO"],"new blast callback failed to release stance"] call _check;' if new_fall else ''))


def test_blast_callback_cannot_release_new_fall_in_same_clinical_episode():
    execute(setup() + '''
        call _blast; call _blast;
        [count _waits == 2,"second blast did not reproduce replacement fall"] call _check;
        _positions = [];
        0 call _deliver;
        [count _positions == 0,"old blast callback released replacement stance"] call _check;
        1 call _deliver;
        [_positions isEqualTo ["AUTO"],"current blast callback failed to release stance"] call _check;
    ''')


@pytest.mark.parametrize('new_fall', [False, True])
def test_obtunded_callback_rejects_previous_clinical_episode(new_fall):
    execute(setup() + '''
        call _sprint;
        [count _waits == 1 && {((_waits select 0) select 2) == 1.25} && {_engineUnconscious},"sprint fall duration changed"] call _check;
        call _fullHeal;
        [!_engineUnconscious,"full heal stranded owned sprint ragdoll"] call _check;
        _ragdolls = [];
    ''' + ('''
        _nowTime = _nowTime + 3;
        uiNamespace setVariable ["ACME_ObtundedSprintWasDown",false];
        call _sprint; _ragdolls = [];
    ''' if new_fall else '') + '''
        0 call _deliver;
        [count _ragdolls == 0,"old sprint callback changed healed/replacement ragdoll"] call _check;
    ''' + ('''
        [_patient getVariable ["ACME_obtunded_sprintRagdollActive",false],"old sprint callback cleared replacement flag"] call _check;
        1 call _deliver;
        [!_engineUnconscious && {!(_patient getVariable ["ACME_obtunded_sprintRagdollActive",true])},"new sprint callback failed to release ragdoll"] call _check;
    ''' if new_fall else ''))


def test_obtunded_callback_cannot_release_recovery_then_new_fall_in_same_episode():
    execute(setup() + '''
        call _sprint; call _recover;
        _nowTime = _nowTime + 3;
        uiNamespace setVariable ["ACME_ObtundedSprintWasDown",false];
        call _sprint; _ragdolls = [];
        [count _waits == 2 && {_engineUnconscious},"new sprint fall setup missing"] call _check;
        0 call _deliver;
        [count _ragdolls == 0 && {_patient getVariable ["ACME_obtunded_sprintRagdollActive",false]},"old callback released replacement fall in same episode"] call _check;
        1 call _deliver;
        [!_engineUnconscious,"new sprint fall did not complete"] call _check;
    ''')


def test_current_sprint_callback_preserves_medical_unconsciousness():
    execute(setup() + '''
        call _sprint;
        _patient setVariable ["ACE_isUnconscious",true];
        _ragdolls = [];
        0 call _deliver;
        [count _ragdolls == 0 && {_engineUnconscious},"sprint callback woke medically unconscious patient"] call _check;
        [!(_patient getVariable ["ACME_obtunded_sprintRagdollActive",true]),"current sprint callback retained completed fall flag"] call _check;
    ''')


@pytest.mark.parametrize('owned', [False, True])
def test_fullheal_only_releases_owned_falls_and_preserves_medical_unconsciousness(owned):
    execute(setup() + ('''
        call _blast; call _sprint;
    ''' if owned else '''
        _engineUnconscious = true;
    ''') + '''
        _patient setVariable ["ACE_isUnconscious",true];
        _positions = []; _ragdolls = [];
        call _fullHeal;
        [count _ragdolls == 0 && {_engineUnconscious},"full heal woke engine state without medical authority"] call _check;
        [(_patient getVariable ["ACME_blast_stanceToken",[]]) isEqualTo [] && {(_patient getVariable ["ACME_obtunded_sprintRagdollToken",[]]) isEqualTo []},"full heal retained a fall token"] call _check;
    ''' + ('[_positions isEqualTo ["AUTO"],"full heal failed to release owned stance"] call _check;' if owned else '[count _positions == 0,"full heal released unrelated stance"] call _check;'))


@pytest.mark.parametrize('kind', ['blast', 'sprint'])
def test_departed_owner_does_not_change_engine_posture(kind):
    execute(setup() + f'call _{kind};' + '''
        _patientLocal = false;
        _positions = []; _ragdolls = [];
        0 call _deliver;
        [count _positions == 0 && {count _ragdolls == 0},"departed owner changed engine posture"] call _check;
    ''')


@pytest.mark.parametrize('kind', ['blast', 'sprint'])
def test_locality_transfer_releases_exact_owned_fall(kind):
    local_change = (F / 'fn_ownerInit.sqf').read_text().split('["CAManBase", "Local", {', 1)[1].split('}] call CBA_fnc_addClassEventHandler;', 1)[0]
    execute(setup() + '''
        ACME_fnc_aajtDownedStop = {};
        ACME_fnc_ownerRegister = {};
        CBA_fnc_execNextFrame = {};
    ''' + 'private _localChange = {' + posture_engine(local_change) + '};' + f'call _{kind};' + '''
        _patientLocal = false;
        [_patient,false] call _localChange;
        0 call _deliver;
        // The new owner's object copy receives only published presentation state.
        {_patient setVariable [_x,_publicFallState getVariable [_x,[]]];} forEach ["ACME_blast_stanceToken","ACME_obtunded_sprintRagdollToken"];
        _patient setVariable ["ACME_obtunded_sprintRagdollActive",_publicFallState getVariable ["ACME_obtunded_sprintRagdollActive",false]];
        _patientLocal = true; _ownerNum = 8;
        [_patient,true] call _localChange;
    ''' + ('[(_positions select ((count _positions)-1)) == "AUTO","owner transfer stranded blast stance"] call _check;' if kind == 'blast' else '[!_engineUnconscious,"owner transfer stranded sprint ragdoll"] call _check;') + '''
        [(_publicFallState getVariable ["ACME_blast_stanceToken",[]]) isEqualTo [] && {(_publicFallState getVariable ["ACME_obtunded_sprintRagdollToken",[]]) isEqualTo []},"new owner did not publish fall retirement"] call _check;
        _positions = []; _ragdolls = [];
        _ownerNum = 7; 0 call _deliver;
        [count _positions == 0 && {count _ragdolls == 0},"away/back callback altered retired fall"] call _check;
    ''')


@pytest.mark.parametrize('kind', ['blast', 'sprint'])
@pytest.mark.parametrize('pose_owner', ['patient_lease', 'provider_controller'])
def test_transfer_cleanup_preserves_newer_provider_pose_and_medical_unconsciousness(kind, pose_owner):
    cleanup = (F / 'fn_ownerInit.sqf').read_text().split('// B156 transferred fall cleanup:', 1)[1].split('// End B156 transferred fall cleanup.', 1)[0].split('\n', 1)[1]
    execute(setup() + 'private _gain = {private _unit = _patient;' + posture_engine(cleanup) + '};' + f'call _{kind};' + ('_patient setVariable ["ACME_patientAnimLock",["newer-provider",objNull,"pose",0,CBA_missionTime+5]];' if pose_owner == 'patient_lease' else '_providerOwnsStance = true;') + '''
        _patient setVariable ["ACE_isUnconscious",true];
        _positions = []; _ragdolls = [];
        _ownerNum = 8; call _gain;
        [count _positions == 0 && {count _ragdolls == 0},"transfer cleanup overrode provider pose or medical unconsciousness"] call _check;
        [(_patient getVariable ["ACME_blast_stanceToken",[]]) isEqualTo [] && {(_patient getVariable ["ACME_obtunded_sprintRagdollToken",[]]) isEqualTo []},"guarded transfer left stale fall tokens"] call _check;
    ''')


def test_normal_obtunded_off_publishes_fall_retirement():
    off = (F / 'fn_obtundedApply.sqf').read_text().split('    // Clearing the cognitive state', 1)[1].rsplit('};', 1)[0]
    off = off.split('\n', 1)[1]
    execute(setup() + 'private _off = {' + posture_engine(off) + '};' + '''
        call _sprint; call _off;
        [!(_publicFallState getVariable ["ACME_obtunded_sprintRagdollActive",true]) && {(_publicFallState getVariable ["ACME_obtunded_sprintRagdollToken",[1]]) isEqualTo []},"ordinary obtundation recovery retained published fall"] call _check;
        _ragdolls = []; 0 call _deliver;
        [count _ragdolls == 0,"old callback changed recovered engine state"] call _check;
    ''')
