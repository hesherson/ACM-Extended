"""Run the production core lifecycle bridges against ACME/ACE protection code.

The shared fixture executes ACE reason composition and ACME reconciliation.
Only engine commands and unrelated treatment/animation services are replaced;
the actual core transition checks, writes and target-event payloads execute.
"""
import pytest

from source_scan import lex, matching
from test_b210_ai_protection import engine, production
from test_menu_death_lifecycle import ROOT, execute, read


def core(name):
    source = (ROOT / 'addons/core/functions' / f'fnc_{name}.sqf').read_text()
    source = source.replace('LYING_ANIMATION', '["ainjppnemstpsnonwrfldnon","acm_lyingstate"]')
    # Namespace stands in for the engine object; the publication argument is
    # transport metadata and cannot be passed to namespace setVariable.
    source = source.replace('QGVAR(Lying_State), _lying, _public', 'QGVAR(Lying_State), _lying')
    source = source.replace('isNull (objectParent _patient)', '((objectParent _patient) isEqualTo objNull)')
    source = source.replace('!isNull ACE_player', '!(ACE_player isEqualTo objNull)')
    source = source.replace('attachedTo _patient', '(_patient getVariable ["TEST_attached",objNull])')
    source = source.replace('_patient setUnitPos "AUTO";', '_engineReleased=true;')
    source = source.replace('_p setUnitPos "AUTO";', '_engineReleased=true;')
    source = source.replace('_patient setUnconscious false;', '_engineUnconsciousClears pushBack _patient;')
    source = source.replace('_p setUnconscious false;', '_engineUnconsciousClears pushBack _p;')
    source = source.replace('lifeState _patient', '(_patient getVariable ["TEST_lifeState","HEALTHY"])')
    return engine(source)


def refresh_handler():
    """Extract the complete production CBA handler, with balanced token ranges."""
    source = read('ownerInit')
    tokens = lex(source)
    pairs = matching(tokens)
    start = next(i for i, t in enumerate(tokens)
                 if t.kind == 'string' and t.value == 'ACME_aiProtectionRefresh')
    opening = start + 2
    assert tokens[opening].value == '{'
    closing = pairs[opening]
    return engine(source[tokens[opening].offset + 1:tokens[closing].offset])


def lifecycle():
    source = production() + '''
        private _engineReleased=false;private _engineUnconsciousClears=[];
        private _putAway=[];private _knockedOut=[];private _nextFrames=[];
        ace_weaponselect_fnc_putWeaponAway={_putAway pushBack _this;};
        ACM_core_fnc_handleKnockOut={_knockedOut pushBack _this;};
        ACME_fnc_doAnim={_moves pushBack _this;};
        CBA_fnc_execNextFrame={_nextFrames pushBack _this;};
    '''
    for name in ('setLyingState', 'onUnconscious', 'getUp'):
        source += 'ACM_core_fnc_' + name + '={' + core(name) + '};'
    source += 'private _refresh={' + refresh_handler() + '};'
    return source


def test_local_set_lying_hook_activates_actual_ace_reason_and_clears_on_release():
    execute(lifecycle() + '''
        [_patient,true] call ACM_core_fnc_setLyingState;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["acme_medical_downed"],
            "local lying writer did not install protection"] call _check;
        [(_patient getVariable "TEST_camouflage")==0,"local lying writer did not apply ACE visibility effect"] call _check;
        [_patient,false] call ACM_core_fnc_setLyingState;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo [],
            "local lying release retained protection"] call _check;
        [count _targeted==0,"local writer unnecessarily routed a remote refresh"] call _check;
    ''')


def test_remote_set_lying_routes_current_state_to_patient_owner_without_remote_reason_mutation():
    execute(lifecycle() + '''
        _patient setVariable ["TEST_owner",8];
        [_patient,true] call ACM_core_fnc_setLyingState;
        [count _broadcasts==0,"non-owner changed the visibility reason"] call _check;
        [count _targeted==1,"remote lying writer did not request owner refresh"] call _check;
        private _event=_targeted select 0;
        [(_event select 0)=="ACME_aiProtectionRefresh" && {(_event select 1) isEqualTo [_patient]}
            && {(_event select 2) isEqualTo _patient},"refresh was not targeted to this patient"] call _check;
        _machine=8;
        (_event select 1) call _refresh;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["acme_medical_downed"],
            "owner did not apply remotely requested medical lying protection"] call _check;
    ''')


def test_on_unconscious_wake_hook_preserves_acme_reason_after_ace_reason_is_removed():
    execute(lifecycle() + '''
        _patient setVariable ["TEST_camouflage",0.67];
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient,"setHidden","ace_unconscious",true] call ace_common_fnc_statusEffect_set;
        [_patient,true] call ACM_core_fnc_onUnconscious;
        [count _knockedOut==1 && {count _putAway==1},"actual unconscious branch did not execute"] call _check;
        _patient setVariable ["ACM_core_WasTreated",true];
        _patient setVariable ["ACE_isUnconscious",false];
        [_patient,"setHidden","ace_unconscious",false] call ace_common_fnc_statusEffect_set;
        [_patient,false] call ACM_core_fnc_onUnconscious;
        [(_patient getVariable "ACM_core_Lying_State") && {!(_patient getVariable "ACM_core_WasTreated")},
            "wake hook did not retain the medically lying state"] call _check;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["acme_medical_downed"],
            "actual wake hook lost the ACME reason"] call _check;
        [(_patient getVariable "TEST_camouflage")==0,"actual wake hook exposed the still-lying patient"] call _check;
        [count (_targeted select {(_x select 0)=="ACM_core_getUpPrompt"})==1,"wake did not retain Get Up prompt"] call _check;
    ''')


def test_accepted_get_up_clears_lying_and_releases_only_acme_reason():
    execute(lifecycle() + '''
        [_patient,true] call ACM_core_fnc_setLyingState;
        [_patient,"setHidden","third_party",true] call ace_common_fnc_statusEffect_set;
        [_patient,true,_medic] call ACM_core_fnc_getUp;
        [!(_patient getVariable "ACM_core_Lying_State") && {_engineReleased},"actual Get Up did not accept release"] call _check;
        [count _engineUnconsciousClears==1 && {count _moves==1},"Get Up did not run engine animation repair"] call _check;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["third_party"],
            "Get Up retained ACME protection or removed a different reason"] call _check;
        [_patient,"setHidden","third_party",false] call ace_common_fnc_statusEffect_set;
        [(_patient getVariable "TEST_camouflage")==1,"accepted Get Up left visibility hidden after final reason ended"] call _check;
    ''')


@pytest.mark.parametrize('rejection', ['unauthorized', 'carried'])
def test_rejected_get_up_retains_medical_lying_protection(rejection):
    state = '_patient setVariable ["TEST_attached",missionNamespace];' if rejection == 'carried' else ''
    authorized = 'false' if rejection == 'unauthorized' else 'true'
    execute(lifecycle() + '''
        [_patient,true] call ACM_core_fnc_setLyingState;
    ''' + state + f'[_patient,{authorized},_medic] call ACM_core_fnc_getUp;' + '''
        [_patient getVariable "ACM_core_Lying_State","rejected Get Up consumed lying state"] call _check;
        [!_engineReleased && {count _moves==0},"rejected Get Up mutated engine pose"] call _check;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["acme_medical_downed"],
            "rejected Get Up removed downed protection"] call _check;
    ''')


def test_deferred_owner_refresh_rereads_lying_release_instead_of_replaying_stale_activation():
    execute(lifecycle() + '''
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call _refresh;
        [count _nextFrames==1,"owner refresh did not schedule state reread"] call _check;
        [_patient,false] call ACM_core_fnc_setLyingState;
        private _queued=_nextFrames select 0;
        (_queued select 1) call (_queued select 0);
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo [],
            "deferred refresh reactivated old lying state"] call _check;
        [(_patient getVariable "TEST_camouflage")==1,"deferred refresh re-hid the released patient"] call _check;
    ''')


def test_deferred_owner_refresh_after_transfer_cannot_clear_new_owners_shared_reason():
    execute(lifecycle() + '''
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call _refresh;
        private _sent=count _broadcasts;
        _patient setVariable ["TEST_owner",8];
        private _queued=_nextFrames select 0;
        (_queued select 1) call (_queued select 0);
        [count _broadcasts==_sent,"old-owner deferred refresh emitted visibility changes"] call _check;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["acme_medical_downed"],
            "old-owner deferred refresh removed shared protection"] call _check;
    ''')
