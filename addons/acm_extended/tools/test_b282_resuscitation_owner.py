"""Execute the B282 patient-owner CPR/BVM protocol with a reorderable transport queue.

Actual admission, request ledger, grant acknowledgement, release/toggle and breath
commits execute. Native provider animation and controller start are explicit API
boundaries; native startup/lifecycle is independently exercised by retained tests.
The fixture does not claim native CBA transport, simulation FPS or PhysX coverage.
"""
import re
import pytest
from test_b206_direct_pressure_network import network_source
from test_menu_death_lifecycle import ROOT, execute, read


def source(name):
    s=read(name)
    s=re.sub(r'objectParent (_\w+)',r'(\1 getVariable ["TEST_vehicle",objNull])',s)
    s=re.sub(r'isNull (\(_patient getVariable \[[^\n]+?\]\))',r'(\1 isEqualTo objNull)',s)
    s=s.replace('((_row select 0) isEqualType objNull)', '((_row select 0) isEqualType profileNamespace)')
    s=s.replace('!= _patient','isNotEqualTo _patient')
    return network_source(name,s)


def setup():
    s=r'''
        private _machine=7; private _networkTime=1000; private _wire=[];
        private _starts=[];private _clinical=[];private _cprStarts=[];private _notices=[];
        private _other=parsingNamespace;
        _medic setVariable ["TEST_owner",7];_other setVariable ["TEST_owner",8];
        _patient setVariable ["TEST_owner",2];_patient setVariable ["TEST_awake",false];
        private _engineOwner={if (_machine==2) then {(_this select 0) getVariable ["TEST_owner",-1]} else {0}};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ace_common_fnc_isAwake={(_this select 0) getVariable ["TEST_awake",true]};
        ACME_fnc_patientInteractionDistance={_distance};
        ACM_breathing_fnc_canUseBVM={private _p=_this select 1;!(_p getVariable ["TEST_awake",false]) || {_p getVariable ["ACM_core_Lying_State",false]}};
        ACM_circulation_fnc_cprSessionValid={private _m=_this select 0;!(_m isEqualTo objNull) && {_m getVariable ["TEST_legacy",false]}};
        ACM_breathing_fnc_bvmSessionValid=ACM_circulation_fnc_cprSessionValid;

        ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
        ACM_circulation_fnc_handleCPR={_cprStarts pushBack _this;};
        ace_common_fnc_displayTextStructured={_notices pushBack _this;};
        CBA_fnc_serverEvent={_wire pushBack [_this select 0,_this select 1,2];};
        CBA_fnc_targetEvent={_wire pushBack [_this select 0,_this select 1,(_this select 2) getVariable ["TEST_owner",-1]];};
        ACME_fnc_ownerDispatch={params ["_p","_op","_args"];_wire pushBack ["resus",[_p,_args],_p getVariable ["TEST_owner",-1]];};
        ACM_circulation_fnc_beginCPR={
            params ["_m","_p","_state"];_starts pushBack ["cpr",_this];
            ACM_circulation_CPR_Epoch=_state select 5;
            _m setVariable ["ACM_circulation_CPR_Epoch",_state select 5];
            _m setVariable ["ACM_circulation_CPR_Sequence",_state select 5];
            [_p,"resus",["activate","cpr",_m,_state select 1,_state select 2,_state select 3,_state select 4,_state select 5,_networkTime,[]]] call ACME_fnc_ownerDispatch;
        };
        ACM_breathing_fnc_useBVM={
            params ["_m","_p","_oxygen","_portable","_state"];_starts pushBack ["bvm",_this];
            ACM_core_ContinuousAction_Epoch=_state select 5;
            ACM_breathing_BVM_LocalSession=[_m,_p,_state select 5];
            [_p,"resus",["activate","bvm",_m,_state select 1,_state select 2,_state select 3,_state select 4,_state select 5,_networkTime,[_oxygen]]] call ACME_fnc_ownerDispatch;
        };
    '''
    for addon in ('circulation','breathing'):
        endpoint=native_release('cpr' if addon=='circulation' else 'bvm','setRuntimeState').replace(', _public]', ']')
        s+=f'ACM_{addon}_fnc_setRuntimeStateRaw={{'+endpoint+'};'
        s+=f'ACM_{addon}_fnc_setRuntimeState={{'+(
            'if (((_this select 1) findIf {(_x select 0)=="bvmLastBreath"})>=0) then {_clinical pushBack _this;};' if addon=='breathing' else '')+f'_this call ACM_{addon}_fnc_setRuntimeStateRaw'+'};'
    s+='ACME_fnc_flightAirframe={(_this select 0) getVariable ["TEST_air",objNull]};'
    for name in ('patientInteractionContact','actionClaimValidate','actionClaimLedger','resusRequest','resusCommit','resusAck'):
        s+=f'ACME_fnc_{name}={{'+source(name)+'};'
    return s+r'''
        private _deliver={
            private _i=if (isNil "_this") then {0} else {_this};
            private _message=_wire deleteAt _i;
            _message params ["_event","_payload","_destination"];
            _machine=_destination;
            if (_event in ["resus","ACME_resusValidate","ACME_resusCommit"]) then {_payload call ACME_fnc_resusCommit;};
            if (_event=="ACME_resusAck") then {_payload call ACME_fnc_resusAck;};
        };
        private _begin={params ["_kind"];[_kind,_medic,_patient,[true,false]] call ACME_fnc_resusRequest;while {count _wire>0} do {0 call _deliver;};};
        private _command={params ["_kind","_op",["_payload",[]],["_captured",[]]];
            private _state=if (_captured isEqualTo []) then {_medic getVariable ["ACME_resusToken_"+_kind,[]]} else {_captured};
            [_patient,[_op,_kind,_medic,_state select 1,_state select 2,_state select 3,_state select 4,_state select 5,_networkTime,_payload]] call ACME_fnc_resusCommit;
        };
    '''


@pytest.mark.parametrize('kind',['cpr','bvm'])
@pytest.mark.parametrize('patient_owner',[2,7,8,9],ids=['dedicated','local-client','remote-client','headless'])
def test_owner_grant_starts_exactly_one_native_episode(kind,patient_owner):
    execute(setup()+f'_patient setVariable ["TEST_owner",{patient_owner}];'+f'''["{kind}"] call _begin;
        [count _starts==1,"owner grant did not start native episode"] call _check;
        private _row=_patient getVariable ["ACME_resus_{kind}",[]];
        [count _row==11 && {{_row select 7}},"accepted episode did not activate"] call _check;
        [(_patient getVariable ["ACME_resusPending",[]]) isEqualTo [],"patient got provider pending state"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_two_providers_cannot_both_claim_same_resuscitation_role(kind):
    execute(setup()+f'''
        ["{kind}",_medic,_patient] call ACME_fnc_resusRequest;
        _machine=8; ["{kind}",_other,_patient] call ACME_fnc_resusRequest;
        0 call _deliver; 0 call _deliver;
        private _acks=+_wire;
        [count _acks==2 && {{((_acks select 0) select 1) select 3}} && {{!(((_acks select 1) select 1) select 3)}},"two providers granted same role"] call _check;
        0 call _deliver; 0 call _deliver; 0 call _deliver;
        [count _starts==1,"losing provider started controller"] call _check;
        [((_patient getVariable ["ACME_resus_{kind}",[]]) select 0) isEqualTo _medic,"winner displaced"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_duplicate_ack_cannot_restart_or_release_active_episode(kind):
    execute(setup()+f'''
        ["{kind}",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;
        private _ack=+(_wire select 0);0 call _deliver;0 call _deliver;
        _wire pushBack _ack;0 call _deliver;
        [count _starts==1 && {{count _wire==0}},"duplicate ACK changed active controller"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_cancel_before_claim_is_terminal_for_exact_token(kind):
    execute(setup()+f'''
        ["{kind}",_medic,_patient] call ACME_fnc_resusRequest;
        private _pending=_medic getVariable ["ACME_resusPending",[]];
        [_patient,"resus",["release","{kind}",_medic,_pending select 2,_pending select 3,_pending select 4,_pending select 5,_pending select 6,_networkTime,[]]] call ACME_fnc_ownerDispatch;
        _medic setVariable ["ACME_resusPending",[]];1 call _deliver;0 call _deliver;0 call _deliver;
        [count _starts==0 && {{(_patient getVariable ["ACME_resus_{kind}",[]]) isEqualTo []}},"cancelled claim resurrected"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
@pytest.mark.parametrize('change',[
    '_medic setVariable ["TEST_awake",false];',
    '_medic setVariable ["TEST_alive",false];',
    '_medic setVariable ["ACME_providerLocalityEpoch",2];',
    '_patient setVariable ["ACME_clinicalEpoch",1];',
    '_networkTime=1011;',
    'ACM_core_ContinuousAction_Active=true;',
])
def test_late_ack_never_starts_after_provider_patient_or_controller_changes(kind,change):
    execute(setup()+f'''["{kind}",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;'''+change+'''
        0 call _deliver;
        [count _starts==0,"stale ACK started clinical work"] call _check;
        if (count _wire>0) then {0 call _deliver;};
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_old_release_and_toggle_cannot_touch_replacement_same_provider_episode(kind):
    execute(setup()+f'''
        ["{kind}"] call _begin;private _old=+(_medic getVariable ["ACME_resusToken_{kind}",[]]);
        ["{kind}","release"] call _command;
        _machine=7;_medic setVariable ["ACME_resusToken_{kind}",[]];["{kind}"] call _begin;
        private _winner=+(_patient getVariable ["ACME_resus_{kind}",[]]);
        ["{kind}","release",[],_old] call _command;
        ["{kind}","toggle",[],_old] call _command;
        [(_patient getVariable ["ACME_resus_{kind}",[]]) isEqualTo _winner,"old release/toggle changed replacement"] call _check;
    ''')


def test_retired_repeated_and_batched_breaths_cannot_credit_new_or_burst_ventilation():
    execute(setup()+r'''
        ["bvm"] call _begin;private _old=+(_medic getVariable ["ACME_resusToken_bvm",[]]);
        ["bvm","breath",[true,2]] call _command;
        ["bvm","breath",[true,2]] call _command;
        ["bvm","breath",[true,3]] call _command;
        [count _clinical==1,"duplicate/batched breaths credited"] call _check;
        _networkTime=1006;["bvm","breath",[true,3]] call _command;
        [count _clinical==2,"new spaced breath rejected"] call _check;
        ["bvm","release"] call _command;
        _machine=7;_medic setVariable ["ACME_resusToken_bvm",[]];["bvm"] call _begin;
        ["bvm","breath",[true,10],_old] call _command;
        ["bvm","telemetry",[12],_old] call _command;
        [count _clinical==2 && {(_patient getVariable ["ACME_bvm_rate",0])==0},"retired breath/telemetry credited replacement"] call _check;
    ''')


def test_first_bvm_breath_at_mission_zero_and_exact_four_second_spacing():
    execute(setup()+r'''
        _networkTime=0;["bvm"] call _begin;
        ["bvm","breath",[true,1]] call _command;
        [count _clinical==1 && {(_patient getVariable ["ACME_bvm_lastBreathServer",-1])==0},"first mission-zero breath was delayed"] call _check;
        ["bvm","breath",[true,1]] call _command;
        _networkTime=3.99;["bvm","breath",[true,2]] call _command;
        [count _clinical==1,"duplicate or sub-four-second breath credited"] call _check;
        _networkTime=4;["bvm","breath",[true,2]] call _command;
        [count _clinical==2 && {(_patient getVariable ["ACME_bvm_lastBreathServer",-1])==4},"next breath at exact four seconds was rejected"] call _check;
        ["bvm","breath",[true,3]] call _command;
        _networkTime=8;["bvm","breath",[true,2]] call _command;
        [count _clinical==2,"same-frame or later duplicate breath credited"] call _check;
        ["bvm","breath",[true,3]] call _command;
        [count _clinical==3,"fresh spaced breath after duplicate was lost"] call _check;
    ''')


def test_oxygen_exhaustion_cannot_be_reversed_by_duplicate_activate():
    execute(setup()+r'''
        ["bvm"] call _begin;
        ["bvm","oxygen",[false]] call _command;
        ["bvm","activate",[true]] call _command;
        ["bvm","breath",[true,2]] call _command;
        [!(_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen",true]),"duplicate activation restored oxygen"] call _check;
        [count ((_clinical select 0) select 1)==1,"exhausted oxygen credited as delivered"] call _check;
    ''')


def test_cpr_clinical_start_and_stop_are_stamped_by_patient_owner_clock():
    execute(setup()+r'''
        ["cpr"] call _begin;CBA_missionTime=500;
        ["cpr","start"] call _command;
        CBA_missionTime=502;["cpr","start"] call _command;
        [count _cprStarts==1 && {((_cprStarts select 0) select 1)==500},"CPR start clock reset or used provider time"] call _check;
        CBA_missionTime=510;_networkTime=1010;["cpr","release"] call _command;
        [(_patient getVariable ["ACM_circulation_CPR_StoppedTotal",-1])==10 && {(_patient getVariable ["ACM_circulation_CPR_StoppedTime",-1])==510},"CPR stopped history used provider time"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_unactivated_pending_grant_expiry_allows_fresh_provider_without_renewal(kind):
    execute(setup()+f'''
        ["{kind}",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;
        private _until=(_patient getVariable ["ACME_resus_{kind}",[]]) select 6;
        private _original=+((_wire select 0) select 1 select 2);
        _machine=2;
        [_patient,["claim","{kind}",_medic,_original select 2,0,7,0,1,1000,[]]] call ACME_fnc_resusCommit;
        [((_patient getVariable ["ACME_resus_{kind}",[]]) select 6)==_until,"duplicate renewed pending deadline"] call _check;
        _wire=[];_networkTime=1011;_machine=8;["{kind}",_other,_patient] call ACME_fnc_resusRequest;0 call _deliver;
        [((_patient getVariable ["ACME_resus_{kind}",[]]) select 0) isEqualTo _other,"expired pending claim blocked new provider"] call _check;
    ''')


def worker_setup():
    from test_historical_cardiac_execution import code as cardiac_code, setup as cardiac_setup
    from test_cpr_lifecycle import source as native_source
    s=(ROOT/'addons/circulation/functions/fnc_handleCPR.sqf').read_text()
    s=s.replace('alive _medic','(_medic isNotEqualTo objNull && {_alive})')
    return cardiac_setup()+r'''
        private _awake=true; private _local=true; private _medicVehicle=objNull;private _patientVehicle=objNull;
        private _clinicalCalls=0;
        CBA_missionTime=500;
        ACM_Rhythm_Sinus=0;ACM_Rhythm_PEA=4;ACM_Rhythm_VF=2;ACM_Rhythm_PVT=3;ACM_Rhythm_Asystole=1;
        ACM_circulation_CPREffectiveness=1;BLOOD_VOLUME_CLASS_2_HEMORRHAGE=5.1;
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        _patient setVariable ["ACM_circulation_Cardiac_RhythmState",2];
        _patient setVariable ["ACM_circulation_CPR_session",[_medic,1]];
        _patient setVariable ["ACM_circulation_CPR_Medic",_medic];
        _patient setVariable ["ace_medical_CPR_provider",_medic];
        _medic setVariable ["ACM_circulation_CPR_Patient",_patient];
        _medic setVariable ["ACM_circulation_CPR_Epoch",1];
        private _grant=[_medic,"worker",1,7,0,1,1010,true,500,-1,-1];
        _patient setVariable ["ACME_resus_cpr",_grant];
        ace_common_fnc_isAwake={_awake};
        ace_medical_treatment_fnc_isMedic={true};
        ACM_circulation_fnc_getCardiacMedicationEffects={_clinicalCalls=_clinicalCalls+1;
            createHashMapFromArray [["epinephrine",0],["morphine",0],["fentanyl",0],["amiodarone",0],["lidocaine",0]]};
        private _tickClinical={private _h=_handlers select 0;[_h select 1,0] call (_h select 0);};
    '''+'ACM_circulation_fnc_cprSessionValid={'+native_source('cprSessionValid')+'};'+\
    'ACM_circulation_fnc_handleCPR={'+cardiac_code(s)+'};'+r'''
        [_patient,500,_grant] call ACM_circulation_fnc_handleCPR;
    '''


def test_actual_native_cpr_pause_keeps_worker_and_resume_performs_clinical_processing():
    execute(worker_setup()+r'''
        _patient setVariable ["ace_medical_CPR_provider",objNull];CBA_missionTime=505;call _tickClinical;
        [_clinicalCalls==0 && {(_handlers select 0) select 2},"pause did work or retired valid reserved worker"] call _check;
        _patient setVariable ["ace_medical_CPR_provider",_medic];CBA_missionTime=510;call _tickClinical;
        [_clinicalCalls==1 && {(_handlers select 0) select 2},"resume silently lost clinical CPR"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;',
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_resus_cpr",[_medic,"replacement",1,7,0,2,1020,true,510,-1,-1]];',
])
def test_actual_native_cpr_worker_cannot_process_after_owner_reset_or_grant_replacement(change):
    execute(worker_setup()+change+r'''
        call _tickClinical;
        [_clinicalCalls==0 && {!((_handlers select 0) select 2)},"retired owner/grant processed CPR"] call _check;
    ''')


def test_old_native_cpr_worker_retirement_does_not_clear_new_worker_id():
    execute(worker_setup()+r'''
        _patient setVariable ["ACM_circulation_CPR_PFH",9];
        _patient setVariable ["ACME_resus_cpr",[_medic,"replacement",1,7,0,2,1020,true,510,-1,-1]];
        call _tickClinical;
        [(_patient getVariable ["ACM_circulation_CPR_PFH",-1])==9,"old worker erased replacement native handle"] call _check;
    ''')


def test_cpr_start_overtaking_activation_promotes_exact_lease_once():
    execute(setup()+r'''
        ["cpr",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;0 call _deliver;
        // Native startup's Activate is queued; owner-route migration lets Start arrive first.
        _machine=2;["cpr","start"] call _command;
        [_patient getVariable ["ACME_resus_cpr",[]] select 7,"clinical start left expiring pending grant"] call _check;
        0 call _deliver;
        [count _cprStarts==1,"late Activate restarted clinical CPR"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_tracking_old_token_after_new_preserves_live_watchdog(kind):
    from test_cpr_lifecycle import execute as cpr_execute
    from test_server_bvm_lifecycle import execute as bvm_execute
    run=cpr_execute if kind=='cpr' else bvm_execute
    prefix='ACM_circulation_CPR' if kind=='cpr' else 'ACM_breathing_BVM'
    run(f'''
        private _oldGrant=[_patient,"old",0,7,0,4];
        private _newGrant=[_patient,"new",0,7,1,5];
        [_medic,_patient,5,_newGrant] call _trackHandler;
        [_medic,_patient,4,_oldGrant] call _trackHandler;
        private _records={prefix}_Sessions select {{(_x param [{7 if kind=='cpr' else 5},[]]) isEqualTo _newGrant}};
        [count _records==1,"old Track erased live replacement watchdog"] call _check;
    ''',runtime=True)


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_duplicate_tracking_does_not_refresh_watchdog_receive_or_heartbeat_age(kind):
    from test_cpr_lifecycle import execute as cpr_execute
    from test_server_bvm_lifecycle import execute as bvm_execute
    run=cpr_execute if kind=='cpr' else bvm_execute
    prefix='ACM_circulation_CPR' if kind=='cpr' else 'ACM_breathing_BVM'
    clock='_serverClock' if kind=='cpr' else 'CBA_missionTime'
    run(f'''
        private _grant=[_patient,"same",0,7,0,4];
        [_medic,_patient,4,_grant] call _trackHandler;
        private _before=+({prefix}_Sessions select {{(_x param [{7 if kind=='cpr' else 5},[]]) isEqualTo _grant}});
        {clock}={clock}+8;
        [_medic,_patient,4,_grant] call _trackHandler;
        private _after={prefix}_Sessions select {{(_x param [{7 if kind=='cpr' else 5},[]]) isEqualTo _grant}};
        [_before isEqualTo _after,"duplicate Track renewed captured watchdog"] call _check;
    ''',runtime=True)


def native_release(kind, function=None):
    addon='circulation' if kind=='cpr' else 'breathing'
    function = function or kind+'Release'
    s=(ROOT/f'addons/{addon}/functions/fnc_{function}.sqf').read_text()
    for macro,prefix,quoted in [('QGVAR',f'ACM_{addon}_',True),('GVAR',f'ACM_{addon}_',False)]:
        s=re.sub(r'\b'+macro+r'\((\w+)\)',lambda m:('"' if quoted else '')+prefix+m[1]+('"' if quoted else ''),s)
    s=re.sub(r'\bQACEGVAR\((\w+),\s*(\w+)\)',lambda m:f'"ace_{m[1]}_{m[2]}"',s)
    s=re.sub(r'\bFUNC\((\w+)\)',lambda m:f'ACM_{addon}_fnc_{m[1]}',s)
    s=re.sub(r'\bQEGVAR\((\w+),\s*(\w+)\)',lambda m:f'"ACM_{m[1]}_{m[2]}"',s)
    s=re.sub(r'\bEGVAR\((\w+),\s*(\w+)\)',lambda m:f'ACM_{m[1]}_{m[2]}',s)
    s=re.sub(r'\bACEFUNC\((\w+),\s*(\w+)\)',lambda m:f'ace_{m[1]}_fnc_{m[2]}',s)
    s=re.sub(r'_medic removeEventHandler \[[^;]+;', '_removed pushBack "anim";',s)
    s=s.replace('_medic distance2D _patient','_distance')
    return network_source(kind+'Release',s)


@pytest.mark.parametrize('kind',['cpr','bvm'])
@pytest.mark.parametrize('machine',[2,7],ids=['server-old-watchdog','provider-old-callback'])
def test_old_native_release_cannot_clear_new_same_patient_and_numeric_epoch(kind,machine):
    addon='circulation' if kind=='cpr' else 'breathing'
    marker='CPR' if kind=='cpr' else 'BVM'
    patient_key='CPR_Patient' if kind=='cpr' else 'BVM_patient'
    epoch_key='CPR_Epoch' if kind=='cpr' else 'BVM_epoch'
    action_key='isPerformingCPR' if kind=='cpr' else 'isUsingBVM'
    execute(setup()+f'ACM_{addon}_fnc_{kind}Release={{'+native_release(kind)+'};'+f'''
        private _old=[_patient,"old",0,7,0,1];
        private _new=[_patient,"new",0,7,2,1];
        _medic setVariable ["ACME_resusToken_{kind}",_new];
        _medic setVariable ["ACM_{addon}_{patient_key}",_patient];
        _medic setVariable ["ACM_{addon}_{epoch_key}",1];
        _medic setVariable ["ACM_{addon}_{action_key}",true];
        _patient setVariable ["ACME_resus_{kind}",[_medic,"new",0,7,2,1,1010,true,500,-1,-1]];
        _patient setVariable ["ACM_{addon}_{marker}_session",[_medic,1]];
        _patient setVariable ["ACM_{addon}_{marker}_Medic",_medic];
        _machine={machine};
        [_medic,_patient,1,_old] call ACM_{addon}_fnc_{kind}Release;
        while {{count _wire>0}} do {{0 call _deliver;}};
        [_medic getVariable ["ACM_{addon}_{action_key}",false],"stale stop cleared current provider active flag"] call _check;
        [(_medic getVariable ["ACM_{addon}_{patient_key}",objNull]) isEqualTo _patient,"stale stop cleared provider target"] call _check;
        [(_medic getVariable ["ACME_resusToken_{kind}",[]]) isEqualTo _new,"stale stop cleared exact new token"] call _check;
    ''')


def test_manual_bvm_cannot_replace_active_mechanical_ventilation_sentinel():
    execute(setup()+r'''
        _patient setVariable ["ACM_breathing_BVM_provider",_patient];
        _patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",true];
        ["bvm",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;0 call _deliver;
        [count _starts==0,"hand bag displaced mechanical ventilation"] call _check;
        [(_patient getVariable ["ACM_breathing_BVM_provider",objNull]) isEqualTo _patient && {_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen",false]},"machine provider/oxygen was changed by rejected bag"] call _check;
    ''')


def test_mechanical_takeover_before_manual_activation_preserves_machine_channel():
    execute(setup()+r'''
        ["bvm",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;0 call _deliver;
        _patient setVariable ["ACM_breathing_BVM_provider",_patient];
        _patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",true];
        0 call _deliver;
        [(_patient getVariable ["ACME_resus_bvm",[]]) isEqualTo [],"lost manual grant remained held"] call _check;
        [(_patient getVariable ["ACM_breathing_BVM_provider",objNull]) isEqualTo _patient && {_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen",false]},"late manual activation damaged machine channel"] call _check;
    ''')


def test_manual_release_after_machine_takeover_preserves_machine_oxygen():
    execute(setup()+r'''
        ["bvm"] call _begin;
        _patient setVariable ["ACM_breathing_BVM_provider",_patient];
        _patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",true];
        ["bvm","release"] call _command;
        [(_patient getVariable ["ACM_breathing_BVM_provider",objNull]) isEqualTo _patient && {_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen",false]},"manual release cleared machine oxygen"] call _check;
    ''')


@pytest.mark.parametrize('patient_owner',[8,9],ids=['remote-client-patient','headless-patient'])
def test_server_gateway_rejects_remote_provider_ownership_change_before_breath_commit(patient_owner):
    execute(setup()+f'_patient setVariable ["TEST_owner",{patient_owner}];'+r'''
        ["bvm"] call _begin;
        _medic setVariable ["TEST_owner",11];
        // This patient owner cannot query the remote provider owner; it sends the exact request to server.
        ["bvm","breath",[true,2]] call _command;
        [count _wire==1 && {((_wire select 0) select 0)=="ACME_resusValidate"},"client owner skipped server truth check"] call _check;
        0 call _deliver;
        [count _wire==0 && {count _clinical==0},"stale provider owner delivered breath"] call _check;
    ''')


def test_gateway_does_not_refresh_original_breath_age_or_validation_stamp_on_reroute():
    execute(setup()+r'''
        _patient setVariable ["TEST_owner",8];["bvm"] call _begin;
        ["bvm","breath",[true,2]] call _command;
        0 call _deliver; // server verifies and forwards
        private _issued=((_wire select 0) select 1 select 1) select 8;
        _networkTime=1003;_patient setVariable ["TEST_owner",9];0 call _deliver;
        [count _clinical==0,"expired server verification credited breath"] call _check;
        [_issued==1000,"gateway changed original breath issue time"] call _check;
    ''')


def test_delayed_manual_oxygen_depletion_cannot_overwrite_machine_channel():
    execute(setup()+r'''
        ["bvm"] call _begin;
        _patient setVariable ["ACM_breathing_BVM_provider",_patient];
        _patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",true];
        ["bvm","oxygen",[false]] call _command;
        [_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen",false],"late hand-bag depletion changed mechanical oxygen"] call _check;
    ''')


def test_actual_new_cpr_start_replaces_old_worker_before_old_five_second_tick():
    execute(worker_setup()+r'''
        private _new=[_medic,"replacement",1,7,0,2,1020,true,510,1010,-1];
        _patient setVariable ["ACME_resus_cpr",_new];
        _patient setVariable ["ACM_circulation_CPR_session",[_medic,2]];
        _medic setVariable ["ACM_circulation_CPR_Epoch",2];
        [_patient,510,_new] call ACM_circulation_fnc_handleCPR;
        [count _handlers==2 && {!((_handlers select 0) select 2)} && {(_patient getVariable ["ACM_circulation_CPR_PFH",-1])==1},"new clinical start waited behind obsolete worker"] call _check;
        call _tickClinical;
        [(_patient getVariable ["ACM_circulation_CPR_PFH",-1])==1,"old callback cleared new worker"] call _check;
    ''')


def test_actual_owner_generation_adoption_replaces_worker_with_same_grant():
    execute(worker_setup()+r'''
        _patient setVariable ["ACME_providerLocalityEpoch",2];
        [_patient,500,_grant] call ACM_circulation_fnc_handleCPR;
        [count _handlers==2 && {!((_handlers select 0) select 2)},"same grant blocked new-owner worker"] call _check;
        call _tickClinical;
        [_clinicalCalls==0 && {(_patient getVariable ["ACM_circulation_CPR_PFH",-1])==1},"old owner callback processed or cleared new owner"] call _check;
    ''')


def local_release_block():
    s=read('ownerInit')
    start=s.index('    // Release only captured resuscitation grants')
    end=s.index('    _unit setVariable ["ACME_providerLocalityEpoch"',start)
    return network_source('ownerInit',s[start:end])


@pytest.mark.parametrize('replacement',[False,True])
def test_actual_locality_release_uses_old_exact_token_after_provider_owner_changed(replacement):
    execute(setup()+r'''
        _patient setVariable ["TEST_owner",8];["bvm"] call _begin;
        private _unit=_medic;private _isLocal=false;
        _medic setVariable ["TEST_owner",11];
        _machine=7;
    '''+(r'''
        _patient setVariable ["ACME_resus_bvm",[_medic,"replacement",0,11,2,1,1010,true,-1,-1,-1]];
    ''' if replacement else '')+local_release_block()+r'''
        while {count _wire>0} do {0 call _deliver;};
    '''+(r'''
        [((_patient getVariable ["ACME_resus_bvm",[]]) select 1)=="replacement","old Local release erased replacement owner"] call _check;
    ''' if replacement else r'''
        [(_patient getVariable ["ACME_resus_bvm",[]]) isEqualTo [],"provider handoff retained old patient grant"] call _check;
    '''))


@pytest.mark.parametrize('bad',['[]','["claim"]','["claim","bvm",objNull,"bad",0,7,0,1,1000,[]]','["unknown","bvm",uiNamespace,"bad",0,7,0,1,1000,[]]'])
def test_malformed_gateway_requests_cannot_mutate_or_raise_engine_errors(bad):
    execute(setup()+f'''_machine=2;[_patient,{bad}] call ACME_fnc_resusCommit;
        [count _wire==0 && {{(_patient getVariable ["ACME_resus_bvm",[]]) isEqualTo []}},"malformed request mutated state"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_old_native_cleanup_cannot_clear_replacement_inputs_or_animation_at_same_numeric_epoch(kind):
    addon='circulation' if kind=='cpr' else 'breathing'
    prefix=f'ACM_{addon}_{kind.upper()}'
    execute(setup()+f'ACM_{addon}_fnc_{kind}Release={{'+native_release(kind)+'};'+
    f'ACM_{addon}_fnc_{kind}CleanupLocal={{'+native_release(kind,kind+'CleanupLocal')+'};'+f'''
        private _old=[_patient,"old",0,7,0,1];private _new=[_patient,"new",0,7,2,1];
        {prefix}_LocalSession=[_medic,_patient,1];{prefix}_LocalGrant=_new;
        _medic setVariable ["ACME_resusToken_{kind}",_new];
        _medic setVariable ["{prefix}_Epoch",1];
        _medic setVariable ["{prefix}_Loop",true];
        {prefix}_ControllerPFH=9;
        ACM_core_ContinuousAction_Epoch=1;ACM_core_ContinuousAction_Active=true;
        private _cleaned=[_medic,_patient,1,_old] call ACM_{addon}_fnc_{kind}CleanupLocal;
        [!_cleaned && {{{prefix}_LocalSession isEqualTo [_medic,_patient,1]}} && {{{prefix}_LocalGrant isEqualTo _new}},"old cleanup changed replacement controller record"] call _check;
        [count _removed==0 && {{ACM_core_ContinuousAction_Active}},"old cleanup cleared replacement input/UI"] call _check;
        [_medic getVariable ["{prefix}_Loop",false],"old cleanup disabled replacement animation"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_patient_waking_after_grant_cannot_start_or_credit_stale_clinical_work(kind):
    execute(setup()+f'''
        ["{kind}"] call _begin;
        _patient setVariable ["TEST_awake",true];
        ["{kind}","{'start' if kind=='cpr' else 'breath'}",[true,2]] call _command;
        [count _clinical==0 && {{count _cprStarts==0}} && {{(_patient getVariable ["ACME_resus_{kind}",[]]) isEqualTo []}},"provider stale replica credited work after patient woke"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_legacy_track_arriving_late_cannot_erase_current_protocol_watchdog(kind):
    from test_cpr_lifecycle import execute as cpr_execute
    from test_server_bvm_lifecycle import execute as bvm_execute
    run=cpr_execute if kind=='cpr' else bvm_execute
    prefix='ACM_circulation_CPR' if kind=='cpr' else 'ACM_breathing_BVM'
    run(f'''
        private _new=[_patient,"new",0,7,2,5];
        [_medic,_patient,5,_new] call _trackHandler;
        [_medic,_patient,4] call _trackHandler;
        private _current={prefix}_Sessions select {{(_x param [{7 if kind=='cpr' else 5},[]]) isEqualTo _new}};
        [count _current==1,"late legacy Track erased live protocol watchdog"] call _check;
    ''',runtime=True)


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_suspended_client_cannot_accept_grant_after_original_pending_deadline(kind):
    execute(setup()+f'''
        ["{kind}",_medic,_patient] call ACME_fnc_resusRequest;
        _networkTime=1004;0 call _deliver; // still valid request; owner gives a later grant deadline
        _networkTime=1011;0 call _deliver; // client's timeout callback has not run during suspension
        [count _starts==0,"late ACK used later owner deadline to revive expired caller intent"] call _check;
        while {{count _wire>0}} do {{0 call _deliver;}};
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_late_track_remembers_origin_owner_instead_of_new_owner_at_receive(kind):
    from test_cpr_lifecycle import execute as cpr_execute
    from test_server_bvm_lifecycle import execute as bvm_execute
    run=cpr_execute if kind=='cpr' else bvm_execute
    prefix='ACM_circulation_CPR' if kind=='cpr' else 'ACM_breathing_BVM'
    run(f'''
        private _grant=[_patient,"late",0,7,0,4];
        _testOwner=11;
        [_medic,_patient,4,_grant] call _trackHandler;
        private _row=({prefix}_Sessions select {{(_x param [{7 if kind=='cpr' else 5},[]]) isEqualTo _grant}}) select 0;
        [(_row select 3)==7,"watchdog captured new receiving owner as old episode origin"] call _check;
    ''',runtime=True)


def test_single_player_native_bvm_release_also_preserves_mechanical_provider_and_oxygen():
    from test_server_bvm_lifecycle import execute as bvm_execute
    bvm_execute(r'''
        _patient setVariable ["ACM_breathing_BVM_provider",_patient];
        _patient setVariable ["ACM_breathing_BVM_ConnectedOxygen",true];
        [_medic,_patient,4] call ACM_breathing_fnc_bvmRelease;
        [(_patient getVariable ["ACM_breathing_BVM_provider",objNull]) isEqualTo _patient && {_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen",false]},"legacy single-player hand-bag stop damaged mechanical ventilation"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_player_bound_pending_ack_cannot_start_on_abandoned_zeus_remote_control_unit(kind):
    execute(setup()+f'''
        ["{kind}",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;
        ACE_player=_other; // Old actor remains local/alive, but the player controls a different unit.
        0 call _deliver;
        [count _starts==0,"pending ACK started care on abandoned controlled unit"] call _check;
        while {{count _wire>0}} do {{0 call _deliver;}};
    ''')


def prepared_setup():
    return setup()+r'''
        private _listeners=[];private _watches=[];private _leases=[];
        CBA_fnc_addEventHandler={_listeners pushBack _this;};
        CBA_fnc_localEvent={params ["_event","_args"];{if ((_x select 0)==_event) then {_args call (_x select 1);};} forEach _listeners;};
        CBA_fnc_waitUntilAndExecute={_watches pushBack _this;};
        ACME_fnc_chestAccessVestEvent={_leases pushBack _this;};
        ACME_fnc_chestAccessManeuverActive={false};
        ace_medical_treatment_fnc_canTreatCached={true};ace_common_fnc_canInteractWith={true};
        ACM_circulation_fnc_beginCPR={["cpr",_this select 0,_this select 1] call ACME_fnc_resusRequest;};
        _medic setVariable ["ACME_chestAccess_treatment",[_patient,"cpr","prepared-lease"]];
    '''+source('registerChestAccessVestRuntime')+'ACME_fnc_cprAfterChestPrep={'+source('cprAfterChestPrep')+'};'


def test_actual_prepared_cpr_handoff_and_plate_carrier_watch_preserve_pending_owner_admission():
    execute(prepared_setup()+r'''
        [[_medic,_patient,"Body","CPR"] call ACME_fnc_cprAfterChestPrep,"prepared CPR misreported queued owner request as failure"] call _check;
        [count _watches==1 && {count _leases==0} && {count _starts==0},"pending CPR closed/reopened carrier custody"] call _check;
        private _watch=_watches select 0;
        [!((_watch select 2) call (_watch select 0)),"plate carrier restored during owner ACK round trip"] call _check;
        _networkTime=1011;
        [(_watch select 2) call (_watch select 0),"expired pending admission retained carrier lease"] call _check;
        (_watch select 2) call (_watch select 1);
        [count _leases==1 && {!((_leases select 0) select 3)},"expired pending admission failed to release captured carrier lease"] call _check;
    ''')


def test_owner_cpr_grant_reserves_chest_before_provider_public_fields_replicate():
    execute(setup()+'ACM_circulation_fnc_cprSessionValid={'+native_release('cpr','cprSessionValid')+'};'+r'''
        ["cpr",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;
        [[_medic,_patient] call ACM_circulation_fnc_cprSessionValid,"owner grant did not reserve chest before provider field replication"] call _check;
        _networkTime=1011;
        [!([_medic,_patient] call ACM_circulation_fnc_cprSessionValid),"expired pending owner grant reserved chest"] call _check;
    ''')


def test_paused_local_cpr_still_owns_provider_hands_until_explicit_bvm_swap_teardown():
    execute(setup()+r'''
        ACM_circulation_CPR_LocalSession=[_medic,_patient,1];
        _medic setVariable ["ACM_circulation_isPerformingCPR",false];
        [!(["bvm",_medic,_patient] call ACME_fnc_resusRequest) && {count _wire==0},"paused CPR acquired simultaneous BVM input/controller"] call _check;
        ACM_circulation_CPR_LocalSession=[];
        [["bvm",_medic,_patient] call ACME_fnc_resusRequest,"actual swap teardown still blocked BVM"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_actual_core_manual_provider_unconsciousness_removes_phantom_clinical_support(kind):
    field='ace_medical_CPR_provider' if kind=='cpr' else 'ACM_breathing_BVM_provider'
    native=(ROOT/f'addons/core/functions/fnc_{kind}Active.sqf').read_text()
    execute(setup()+f'ACM_core_fnc_{kind}Active={{'+network_source(kind+'Active',native)+'};'+f'''
        _patient setVariable ["{field}",_medic];
        [[_patient] call ACM_core_fnc_{kind}Active,"awake manual provider lost support"] call _check;
        _medic setVariable ["ACE_isUnconscious",true];
        [!([_patient] call ACM_core_fnc_{kind}Active),"unconscious manual provider still delivered support"] call _check;
    ''')


def test_actual_core_mechanical_bvm_sentinel_remains_effective_on_unconscious_patient():
    native=(ROOT/'addons/core/functions/fnc_bvmActive.sqf').read_text()
    execute(setup()+'ACM_core_fnc_bvmActive={'+network_source('bvmActive',native)+'};'+r'''
        _patient setVariable ["ACM_breathing_BVM_provider",_patient];
        _patient setVariable ["ACE_isUnconscious",true];
        [[_patient] call ACM_core_fnc_bvmActive,"patient mechanical sentinel was suppressed by unconsciousness"] call _check;
        _patient setVariable ["TEST_alive",false];
        [!([_patient] call ACM_core_fnc_bvmActive),"dead mechanical sentinel still advertised support"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
@pytest.mark.parametrize('contact',[
    '_distance=18;_medic setVariable ["TEST_vehicle",missionNamespace];_patient setVariable ["TEST_vehicle",missionNamespace];',
    '_medic setVariable ["TEST_vehicle",uiNamespace];_patient setVariable ["TEST_vehicle",profileNamespace];_medic setVariable ["TEST_air",parsingNamespace];_patient setVariable ["TEST_air",parsingNamespace];',
    '_patient setVariable ["TEST_vehicle",profileNamespace];_medic setVariable ["TEST_air",parsingNamespace];_patient setVariable ["TEST_air",parsingNamespace];',
],ids=['native-distant-seats','distinct-aircraft-helpers','walking-floor-to-seated'])
def test_actual_contact_contract_survives_owner_grant_ack_and_native_session(kind,contact):
    addon='circulation' if kind=='cpr' else 'breathing'
    execute(setup()+f'ACM_{addon}_fnc_{kind}SessionValid={{'+native_release(kind,kind+'SessionValid')+'};'+contact+f'''
        ["{kind}"] call _begin;
        [count _starts==1,"valid aircraft contact lost during owner handshake"] call _check;
        [[_medic,_patient] call ACM_{addon}_fnc_{kind}SessionValid,"native reservation rejected admitted aircraft contact"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
@pytest.mark.parametrize('contact',[
    '_distance=10;',
    '_medic setVariable ["TEST_vehicle",uiNamespace];',
    '_medic setVariable ["TEST_vehicle",uiNamespace];_patient setVariable ["TEST_vehicle",profileNamespace];_medic setVariable ["TEST_air",parsingNamespace];_patient setVariable ["TEST_air",missionNamespace];',
    '_distance=10;_medic setVariable ["TEST_vehicle",uiNamespace];_patient setVariable ["TEST_vehicle",profileNamespace];_medic setVariable ["TEST_air",parsingNamespace];_patient setVariable ["TEST_air",parsingNamespace];',
],ids=['ground-too-far','different-parent-no-air','different-airframes','same-airframe-too-far'])
def test_actual_contact_contract_rejects_request_before_provider_mutation(kind,contact):
    execute(setup()+contact+f'''
        [!(["{kind}",_medic,_patient] call ACME_fnc_resusRequest),"unreachable contact acquired provider pending state"] call _check;
        [count _wire==0 && {{(_medic getVariable ["ACME_resusPending",[]]) isEqualTo []}},"unreachable request sent claim"] call _check;
    ''')


@pytest.mark.parametrize('kind',['cpr','bvm'])
def test_contact_loss_after_claim_prevents_ack_start_and_retires_exact_reservation(kind):
    execute(setup()+f'''
        ["{kind}",_medic,_patient] call ACME_fnc_resusRequest;0 call _deliver;
        _distance=20;0 call _deliver;
        [count _starts==0,"contact-loss ACK started native controller"] call _check;
        while {{count _wire>0}} do {{0 call _deliver;}};
        [(_patient getVariable ["ACME_resus_{kind}",[]]) isEqualTo [],"contact-loss ACK retained patient reservation"] call _check;
    ''')


def test_actual_active_cpr_worker_lost_contact_cannot_process_before_stop_packet_arrives():
    execute(worker_setup()+r'''
        _distance=20;CBA_missionTime=505;call _tickClinical;
        [_clinicalCalls==0 && {!((_handlers select 0) select 2)} && {(_patient getVariable ["ACM_circulation_CPR_PFH",-1])==-1},"out-of-contact active CPR credited clinical processing"] call _check;
    ''')
