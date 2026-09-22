"""Regression gates for F01-F04. Execute real SQF with engine/transport boundaries mocked.

Hang Bag delivery order is controlled explicitly; this is not a live Arma transport test.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, core, execute, hold_setup

F = ROOT / 'addons/acm_extended/functions'

def surgical():
    s=(ROOT/'addons/airway/functions/fnc_establishSurgicalAirway.sqf').read_text()
    s=re.sub(r'\bIDC_[A-Z_]+\b','9876',s)
    s=s.replace('findDisplay 9876', 'objNull')
    s=s.replace('createDialog QGVAR(SurgicalAirway_Dialog);', '_dialog = true;')
    s=s.replace('SURGICAL_AIRWAY_SELECTED_NONE', '0')
    return adapt(s,'airway').replace('IS_UNCONSCIOUS(_patient)','true')

def surgical_setup():
    return ('ACM_core_fnc_beginContinuousAction = {'+core('beginContinuousAction').replace('isNull (findDisplay _dialogID)', '!_dialog')+'};'
        +'private _start = {'+surgical()+'};'+'''
        private _returned = 0;
        ace_common_fnc_addToInventory = {_returned = _returned + 1;};
    ''')

@pytest.mark.parametrize('reject', ['ACM_core_ContinuousAction_Active = true;','_alive = false;','_unconscious = true;'])
def test_rejected_surgical_start_never_reserves_and_retry_works(reject):
    execute(surgical_setup()+reject+'''
        [_medic,_patient] call _start;
        [!(_patient getVariable ["ACM_airway_SurgicalAirway_InProgress",false]),"rejected startup reserved patient"] call _check;
        [count _handlers == 0 && {count _keys == 0},"rejection installed callbacks"] call _check;
        _alive = true; _unconscious = false; ACM_core_ContinuousAction_Active = false;
        [_medic,_patient] call _start;
        [_patient getVariable ["ACM_airway_SurgicalAirway_InProgress",false],"valid retry did not reserve"] call _check;
        [ACM_core_ContinuousAction_Active && {count _handlers == 1},"valid retry not accepted"] call _check;
        ACM_core_ContinuousAction_Active = false; call _tick; call _tick;
        [!(_patient getVariable ["ACM_airway_SurgicalAirway_InProgress",true]),"cancel retained surgical reservation"] call _check;
        [_returned == 1,"cancel returned kit more than once or lost it"] call _check;
    ''')

def test_rejected_surgical_attempt_does_not_clear_existing_reservation():
    execute(surgical_setup()+'''
        _patient setVariable ["ACM_airway_SurgicalAirway_InProgress",true];
        [_medic,_patient] call _start;
        [_patient getVariable ["ACM_airway_SurgicalAirway_InProgress",false],"another reservation was cleared"] call _check;
        [count _handlers == 0 && {_returned == 0},"rejected attempt ran someone else's cleanup"] call _check;
    ''')

def test_player_handoff_releases_original_hold_without_reopening_new_player_ui():
    execute(hold_setup()+'''
        private _reopened = false;
        CBA_fnc_localEvent = {if ((_this select 0) == "ACM_core_openMedicalMenu") then {_reopened = true;};};
        [_medic,_patient] call _start;
        ACM_core_ContinuousAction_ShouldReopen = true;
        ACE_player = missionNamespace; call _tick;
        [!ACM_core_ContinuousAction_Active,"original controller remained active"] call _check;
        [!(_patient getVariable ["ACM_airway_HeadTilt_State",false]),"original hold remained active"] call _check;
        [_stanceFreed && {!_reopened},"old pose stranded or new player's menu reopened"] call _check;
    ''')

def test_ai_started_hold_is_not_bound_to_player_identity():
    execute(hold_setup()+'''
        ACE_player = missionNamespace;
        [_medic,_patient] call _start;
        ACE_player = _patient; call _tick;
        [ACM_core_ContinuousAction_Active,"AI/scripted provider cancelled by player switch"] call _check;
    ''')

@pytest.mark.parametrize('active',[False,True])
def test_stethoscope_flip_aborts_once_before_reset(active):
    s=(F/'fn_stethoscopeClose.sqf').read_text().split('private _poseEpoch =',1)[0]
    execute('''
        private _providerCancels = []; private _patientCancels = [];
        ACME_fnc_rollProviderCancel = {_providerCancels pushBack _this;};
        ACME_fnc_patientRollCancel = {_patientCancels pushBack _this;};
        _medic setVariable ["ACME_stethMedic",_medic];
        _medic setVariable ["ACME_stethPatient",_patient];
    '''+f'_medic setVariable ["ACME_stethFlipActive",{str(active).lower()}];'+
        'private _close = {'+adapt(s)+'}; [_medic] call _close; [_medic] call _close;'+
        f'[count _providerCancels == {int(active)} && {{count _patientCancels == {int(active)}}},"flip cancellation count"] call _check;'+
        ('''[(_patientCancels select 0) isEqualTo [_patient,"front"],"flip did not settle supine/front"] call _check;''' if active else ''))

# Hang Bag: no real object creation or network delivery; owner claim and client ACK logic run verbatim.
def hang_source(name):
    s=(F/('fn_'+name+'.sqf')).read_text()
    # SQF-VM has no finite command; these tests supply finite numeric values.
    s=s.replace('finite _episode','(_episode isEqualType 0)').replace('finite _flow','(_flow isEqualType 0)')
    s=s.replace('serverTime','CBA_missionTime').replace('alive _holder','_alive')
    s=s.replace('getPosASL _medic','[0,0,0]')
    return adapt(s)

def hang_setup():
    owner=(F/'fn_ownerDispatch.sqf').read_text()
    routes=owner[owner.index('    case "hangBagClaim":'):owner.index('    case "register":')]
    stop=hang_source('hangBagStop').split('private _visualEpoch =',1)[0]
    return '''
        private _acks = []; private _activated = []; private _restores = [];
        ACME_fnc_clinicalEpoch = {(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACME_fnc_hangBagActivate = {_activated pushBack _this;};
        ACME_fnc_hangBagPrepStop = {_restores pushBack _this;};
        ACME_fnc_hangBagFluidType = {"saline"};
        ACME_fnc_hangBagTick = {};
        CBA_fnc_targetEvent = {_acks pushBack (_this select 1);};
    '''+'ACME_fnc_hangBagClaimLocal = {'+hang_source('hangBagClaimLocal')+'};'+\
        'ACME_fnc_ownerDispatch = {params ["_patient","_operation",["_args",[]]]; switch (_operation) do {'+routes+'};};'+\
        'ACME_fnc_hangBagClaimAck = {'+hang_source('hangBagClaimAck')+'};'+\
        'ACME_fnc_hangBagStop = {'+stop+'};'+\
        'private _start = {'+hang_source('hangBagStart')+'};'+'''
        private _deliver = {(_acks select _this) call ACME_fnc_hangBagClaimAck;};
    '''

def test_two_simultaneous_providers_get_one_owner_winner():
    execute(hang_setup()+'''
        private _a = _medic; private _b = missionNamespace;
        [_a,_patient,"leftarm","saline"] call _start;
        // The first provider's Active publication has NOT reached the casualty owner.
        _a setVariable ["ACME_hang_Active",false];
        [_b,_patient,"leftarm","saline"] call _start;
        _a setVariable ["ACME_hang_Active",true];
        [count _activated == 0,"visuals started before owner acceptance"] call _check;
        [(_acks select 0) select 3,"first request not granted"] call _check;
        [!((_acks select 1) select 3),"second request stole unexpired lease"] call _check;
        1 call _deliver; 0 call _deliver;
        [count _activated == 1,"expected one accepted presentation"] call _check;
        [(_patient getVariable ["ACME_hang_Medic",objNull]) isEqualTo _a,"loser cleared winner"] call _check;
        [!(_b getVariable ["ACME_hang_Active",true]),"loser did not unwind"] call _check;
    ''')

def test_duplicate_ack_does_not_repeat_activation():
    execute(hang_setup()+'''
        [_medic,_patient,"leftarm","saline"] call _start;
        0 call _deliver; 0 call _deliver;
        [count _activated == 1,"duplicate ACK repeated props"] call _check;
    ''')

def test_cancelled_pending_claim_restores_prep_and_late_ack_cannot_start_it():
    execute(hang_setup()+'''
        [_medic,_patient,"leftarm","saline"] call _start;
        [true,_medic] call ACME_fnc_hangBagStop;
        0 call _deliver;
        [count _activated == 0 && {count _restores == 1},"late ACK restarted cancelled hold or lost prep"] call _check;
        [(_patient getVariable ["ACME_hang_Medic",objNull]) isEqualTo objNull,"pending lease not released"] call _check;
    ''')

def test_cancel_restart_same_frame_old_reply_cannot_release_new_claim():
    execute(hang_setup()+'''
        [_medic,_patient,"leftarm","saline"] call _start;
        private _old = _medic getVariable "ACME_hang_Start";
        [true,_medic] call ACME_fnc_hangBagStop;
        [_medic,_patient,"rightarm","saline"] call _start;
        private _new = _medic getVariable "ACME_hang_Start";
        [_new > _old,"same-frame episode collision"] call _check;
        0 call _deliver; 1 call _deliver;
        [count _activated == 1 && {(_patient getVariable ["ACME_hang_Episode",-1]) == _new},"old reply released new claim"] call _check;
    ''')

@pytest.mark.parametrize('invalid',[
    '_alive = false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_distance = 5;',
    '_ownerNum = 8;',
    '_patient setVariable ["ACME_clinicalEpoch",1];',
    '_patient setVariable ["ACME_clinicalRestoring",true];',
    'ACME_sys_hang = false;',
    'CBA_missionTime = 17;',
    'ACE_player = missionNamespace;',
])
def test_invalid_or_expired_acceptance_does_not_start_presentation(invalid):
    execute(hang_setup()+'''
        [_medic,_patient,"leftarm","saline"] call _start;
    '''+invalid+'''
        0 call _deliver;
        [count _activated == 0 && {!(_medic getVariable ["ACME_hang_Active",true])},"invalid acceptance started hold"] call _check;
    ''')

def test_dead_patient_is_not_rejected_by_owner_claim():
    execute(hang_setup()+'''
        _patientAlive = false;
        [_medic,_patient,"leftarm","saline"] call _start; 0 call _deliver;
        [count _activated == 1,"dead-patient interaction was removed"] call _check;
    ''')

def test_renewal_is_exact_episode_and_cannot_resurrect_expired_lease():
    execute(hang_setup()+'''
        [_medic,_patient,"leftarm","saline"] call _start; 0 call _deliver;
        private _ep = _medic getVariable "ACME_hang_Start";
        CBA_missionTime = 12;
        [_patient,"hangBagRenew",[_medic,_ep,1.75,0,7]] call ACME_fnc_ownerDispatch;
        [(_patient getVariable "ACME_hang_LeaseUntil") == 18,"valid renewal rejected"] call _check;
        [_patient,"hangBagRelease",[_medic,_ep - 1]] call ACME_fnc_ownerDispatch;
        [(_patient getVariable "ACME_hang_Episode") == _ep,"wrong episode released hold"] call _check;
        CBA_missionTime = 20;
        [_patient,"hangBagRenew",[_medic,_ep,1.75,0,7]] call ACME_fnc_ownerDispatch;
        [!((_acks select ((count _acks)-1)) select 3),"expired renewal reacquired lease"] call _check;
    ''')

def tick_prefix():
    # Run the validity/claim/renewal portion, stopping before unchanged fluid/rendering code.
    return hang_source('hangBagTick').split('// auto-lower when',1)[0]


def test_pending_claim_timeout_unwinds_prep_without_needing_an_ack():
    execute(hang_setup()+'private _tickHang = {'+tick_prefix()+'};'+'''
        [_medic,_patient,"leftarm","saline"] call _start;
        CBA_missionTime = 15;
        [[_medic,_patient],0] call _tickHang;
        [!(_medic getVariable ["ACME_hang_Active",true]),"missing ACK stranded pending hold"] call _check;
        [count _restores == 1,"timeout lost prepared gear"] call _check;
        [(_patient getVariable ["ACME_hang_Medic",objNull]) isEqualTo objNull,"timeout did not release claim"] call _check;
    ''')


def test_existing_tick_renews_at_two_seconds_not_twenty_hz():
    execute(hang_setup()+'private _tickHang = {'+tick_prefix()+'};'+'''
        [_medic,_patient,"leftarm","saline"] call _start; 0 call _deliver;
        CBA_missionTime = 11;
        [[_medic,_patient],0] call _tickHang;
        [count _acks == 1,"renewal sent too early"] call _check;
        CBA_missionTime = 12;
        for "_i" from 1 to 40 do { [[_medic,_patient],0] call _tickHang; };
        [count _acks == 2,"renewal repeated at presentation tick rate"] call _check;
        1 call _deliver;
        [count _activated == 1,"renewal restarted held presentation"] call _check;
    ''')


def test_owner_reconciliation_respects_grant_grace_then_releases_lost_provider():
    src=(F/'fn_transientStateReconcile.sqf').read_text()
    header=src.split('// BVM reservation.',1)[0]
    block=src.split('// Hang Bag claim.',1)[1].split('// Direct Pressure markers.',1)[0]
    source=adapt((header+block+'count _repairs').replace('alive _hangMedic','_alive').replace('serverTime','CBA_missionTime'))
    # Namespace stand-ins retain nil slots; -1 represents the engine's deleted timer.
    source=source.replace('[_key, nil]', '[_key, -1]').replace('finite _at', 'true')
    execute(hang_setup()+'private _reconcile = {'+source+'};'+'''
        [_medic,_patient,"leftarm","saline"] call _start;
        _medic setVariable ["ACME_hang_Active",false];
        CBA_missionTime = 11; [_patient] call _reconcile;
        CBA_missionTime = 14; [_patient] call _reconcile;
        [(_patient getVariable ["ACME_hang_Medic",objNull]) isEqualTo _medic,"unreplicated Active flag stole granted lease"] call _check;
        CBA_missionTime = 17; [_patient] call _reconcile;
        CBA_missionTime = 19; [_patient] call _reconcile;
        [(_patient getVariable ["ACME_hang_Medic",objNull]) isEqualTo objNull,"expired claim stranded owner"] call _check;
        [(_patient getVariable ["ACME_hang_flowMult",0]) == 1,"expired flow boost not cleared"] call _check;
    ''')


def test_older_renewal_ack_cannot_extend_a_newer_deadline():
    execute(hang_setup()+'''
        [_medic,_patient,"leftarm","saline"] call _start; 0 call _deliver;
        private _ep = _medic getVariable "ACME_hang_Start";
        CBA_missionTime = 12;
        [_patient,"hangBagRenew",[_medic,_ep,1.75,0,7]] call ACME_fnc_ownerDispatch;
        1 call _deliver; 0 call _deliver;
        [(_medic getVariable ["ACME_hang_ClaimAckAt",0]) == 12,"old reply rewound last owner confirmation"] call _check;
    ''')


def test_local_owner_rejecting_renewal_stops_tick_before_old_presentation_runs():
    execute(hang_setup()+'private _tickHang = {'+tick_prefix()+'};'+'''
        [_medic,_patient,"leftarm","saline"] call _start; 0 call _deliver;
        // Mock only the unchanged accepted-session visual teardown; ACK/renewal code is real.
        private _stops = 0;
        ACME_fnc_hangBagStop = {_stops = _stops + 1; (_this select 1) setVariable ["ACME_hang_Active",false];};
        CBA_fnc_targetEvent = {(_this select 1) call ACME_fnc_hangBagClaimAck;};
        _patient setVariable ["ACME_hang_Medic",missionNamespace];
        CBA_missionTime = 12; [[_medic,_patient],0] call _tickHang;
        [_stops == 1 && {!(_medic getVariable ["ACME_hang_Active",true])},"synchronous rejection did not cancel"] call _check;
    ''')
