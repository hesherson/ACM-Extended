"""Execute the real wake helpers in SQF-VM, with engine/CBA boundaries mocked."""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute


def source(name):
    text = (ROOT / 'addons/core/functions' / ('fnc_' + name + '.sqf')).read_text()
    text = text.replace('local _patient', '_patientLocal').replace('serverTime', 'CBA_missionTime')
    text = adapt(text)
    # SQF-VM uses profileNamespace as the patient stand-in. Mirror the runtime OBJECT type check
    # so direct CBA list-item calls exercise the same normalization branch in this fixture.
    if name == 'canWake':
        text = text.replace('_this isEqualType objNull', '_this isEqualType profileNamespace')
    # Namespace stand-ins have no public-broadcast argument, including multiline writes.
    return re.sub(r'(setVariable \[[^;]*\n[^;]*),\s*(?:true|false)(\];)', r'\1\2', text)


def setup():
    text = '''
        private _patientLocal = true;
        private _stable = true;
        private _sedated = false;
        private _machineState = "Unconscious";
        private _mutations = 0;
        private _transitions = 0;
        private _wakeSawLying = false;
        ace_medical_STATE_MACHINE = profileNamespace;
        ace_medical_status_fnc_hasStableVitals = {_stable};
        ACME_fnc_sedationActive = {_sedated};
        CBA_statemachine_fnc_getCurrentState = {_machineState};
        ACM_core_fnc_setWasTreated = {
            (_this select 0) setVariable ["ACM_core_WasTreated", _this select 1];
            true
        };
        ACM_core_fnc_setLyingState = {
            (_this select 0) setVariable ["ACM_core_Lying_State", _this select 1];
            true
        };
        ace_medical_status_fnc_setUnconsciousState = {
            if !(_this select 1) then {
                _wakeSawLying =
                    ((_this select 0) getVariable ["ACM_core_WasTreated", false])
                    && {((_this select 0) getVariable ["ACM_core_Lying_State", false])};
            };
            (_this select 0) setVariable ["ACE_isUnconscious", _this select 1];
            _mutations = _mutations + 1;
        };
        CBA_statemachine_fnc_manualTransition = {
            _transitions = _transitions + 1;
            (_this select 0) call (_this select 4);
            _machineState = _this select 3;
        };
        _patient setVariable ["ACE_isUnconscious", true];
    '''
    for name in ('isForcedUnconscious', 'canWake', 'reconcileWake', 'requestWake'):
        text += 'ACM_core_fnc_' + name + ' = {' + source(name) + '};\n'
    return text


def test_can_wake_accepts_cba_state_machine_direct_object_call():
    execute(setup() + '''
        private _result = _patient call ACM_core_fnc_canWake;
        [_result,"direct CBA list-item call rejected an eligible patient"] call _check;
    ''')


def test_successful_on_foot_wake_is_armed_for_acm_lying_state_before_unconscious_clears():
    execute(setup() + '''
        private _result = [_patient,true,"ammonia"] call ACM_core_fnc_requestWake;
        [_result,"eligible wake failed"] call _check;
        [_wakeSawLying,"wake cleared unconsciousness before ACM lying state was armed"] call _check;
        [_patient getVariable ["ACM_core_Lying_State",false],"lying state not retained after wake"] call _check;
    ''')


@pytest.mark.parametrize('state', ['Default','Injured','Unconscious','CardiacArrest','FatalInjury','Dead','','CustomState'])
@pytest.mark.parametrize('stable', [True,False])
def test_actual_machine_state_is_required_for_a_repair(state, stable):
    allowed = state in ('Default','Injured','Unconscious') and stable
    execute(setup() + f'_machineState = "{state}"; _stable = {str(stable).lower()};' + '''
        private _result = [_patient,false,"test"] call ACM_core_fnc_requestWake;
    ''' + f'[_result isEqualTo {str(allowed).lower()},"incorrect wake outcome"] call _check;' +
        f'[_mutations == {int(allowed)},"unexpected raw flag mutation"] call _check;' +
        f'[_transitions == {int(allowed and state == "Unconscious")},"incorrect state-machine transition"] call _check;')


@pytest.mark.parametrize('blocker', [
    '_sedated = true;',
    '_patient setVariable ["ACME_roc_paralyzed",true];',
    '_patient setVariable ["ACME_lido_seizureState","active"];',
    '_patient setVariable ["ace_medical_inCardiacArrest",true];',
    '_patient setVariable ["ACM_airway_SurgicalAirway_State",true];',
    '_patient setVariable ["ACM_evacuation_casualtyTicketClaimed",true];',
    '_patient setVariable ["ACME_clinicalRestoring",true];',
    '_patientLocal = false;',
    '_patientAlive = false;',
])
def test_stimulus_does_not_bypass_non_traumatic_blockers(blocker):
    execute(setup() + blocker + '''
        private _result = [_patient,true,"shake"] call ACM_core_fnc_requestWake;
        [!_result,"stimulus bypassed blocker"] call _check;
        [_mutations == 0 && {_transitions == 0},"blocked request changed consciousness"] call _check;
    ''')


def test_only_explicit_successful_stimulus_releases_traumatic_knockout():
    execute(setup() + '''
        _patient setVariable ["ACM_core_KnockOut_State",true];
        private _ordinary = [_patient,false,"washout"] call ACM_core_fnc_requestWake;
        [!_ordinary && {_mutations == 0},"ordinary wake broke traumatic knockout"] call _check;
        private _stimulated = [_patient,true,"shake"] call ACM_core_fnc_requestWake;
        [_stimulated && {_mutations == 1},"eligible stimulus failed"] call _check;
        [!(_patient getVariable ["ACM_core_KnockOut_State",true]),"traumatic latch not cleared"] call _check;
    ''')


def test_repeated_wake_requests_are_idempotent():
    execute(setup() + '''
        for "_i" from 1 to 5 do {[_patient,false,"repeat"] call ACM_core_fnc_requestWake;};
        [_mutations == 1 && {_transitions == 1},"repeated wake changed state again"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_wakeRepairTicket",99];',
    '_ownerNum = 8;',
    '_patientLocal = false;',
    '_sedated = true;',
    '_patient setVariable ["ACME_clinicalRestoring",true];',
    '_machineState = "CardiacArrest";',
])
def test_new_episode_or_blocker_cancels_deferred_event_repair(change):
    text=(ROOT/'addons/core/XEH_postInit.sqf').read_text()
    begin=text.index('[QACEGVAR(medical,WakeUp), {')
    end=text.index('[QGVAR(playWakeUpSound), {',begin)
    block=text[begin:end].replace('owner _unit','_ownerNum').replace('local _unit','_patientLocal').replace('alive _unit','_patientAlive')
    execute(setup() + '''
        private _pending = [];
        CBA_fnc_execNextFrame = {_pending pushBack _this;};
    ''' + adapt(block) + '''
        [_patient] call _track;
        [count _pending == 1,"event callback missing"] call _check;
    ''' + change + '''
        private _job = _pending select 0;
        (_job select 1) call (_job select 0);
        [_mutations == 0 && {_transitions == 0},"stale callback woke a new episode"] call _check;
    ''')
