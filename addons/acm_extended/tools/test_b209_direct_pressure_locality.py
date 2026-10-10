"""DP ownership transfer with actual workers/claims and explicit engine boundaries.

The queue models owner delivery and the engine's server-only owner query. It does
not simulate actual CBA transport latency or Arma animation replication.
"""
import re

import pytest

from historical_source import switch_case_body
from test_b206_direct_pressure_network import network_source, setup as network_setup
from test_menu_death_lifecycle import execute, read


def source(name, text=None):
    text = read(name) if text is None else text
    text = text.replace('currentWeapon _medic', '_dpWeapon')
    text = text.replace('_medic getUnitMovesInfo 0', '0')
    text = text.replace('_medic switchMove [_main, _phase, 1, false];', '_moves pushBack [_medic,_main];')
    text = text.replace('_m getUnitMovesInfo 1', '_dpNativeElapsed').replace('_m getUnitMovesInfo 2', '_dpNativeDuration')
    text = text.replace('getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _anim >> "speed")', '_dpExitNativeSpeed')
    for command, value in {
        'animationState _medic': '_animation', 'animationState _m': '_animation',
        'animationState _u': '_animation', 'objectParent _unit': 'objNull',
        'objectParent _u': 'objNull', 'objectParent _m': 'objNull',
        'getPosASL _medic': '[0,0,0]', 'getPosVisual _medic': '[0,0,0]',
        'getPosVisual _patient': '[0,1,0]', 'eyeDirection _medic': '_look',
        '_medic setUnitPos "MIDDLE";': '_stanceCalls=_stanceCalls+1;',
        '_m setUnitPos "AUTO";': '_stanceCalls=_stanceCalls+1;',
        'removeMissionEventHandler ["Draw3D", _draw];': '_removedDraw pushBack _draw;',
        'removeMissionEventHandler ["Draw3D", _d3];': '_removedDraw pushBack _d3;',
        '_medic setVariable [_name, _value, _public];': '_medic setVariable [_name, _value];',
    }.items():
        text = re.sub(re.escape(command) + (r'\b' if command[-1].isalnum() else ''), lambda _: value, text)
    text = re.sub(r'\bstance (_medic|_m|_u)\b', '_providerStance', text)
    text = re.sub(r'_(?:medic|m|u) setUnitPos ([^;]+);', r'_stanceCalls=_stanceCalls+1; _stances pushBack (\1);', text)
    text = re.sub(r'inputAction "[^"]+"', '([] call _input)', text)
    return network_source(name, text)


def setup():
    text = network_setup() + '''
        private _animation="amovpknlmstpsnonwnondnon"; private _dpWeapon=""; private _dpExitNativeSpeed=-1.8; private _dpPrepDelay=0; private _dpPrepCalls=0; private _dpNativeElapsed=-1; private _dpNativeDuration=-1; private _stanceCalls=0; private _stances=[]; private _providerStance="CROUCH"; private _look=[0,1,0];
        private _inputCalls=0; private _input={_inputCalls=_inputCalls+1; 0};
        private _removedDraw=[]; private _logs=[]; private _clots=0; private _hints=0;
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);(_handlers select (_this select 0)) set [2,false];};
        ace_common_fnc_isAwake={!((_this select 0) getVariable ["ACE_isUnconscious",false])};
        ACME_fnc_medicAnimationPrep={_dpPrepCalls=_dpPrepCalls+1; _dpPrepDelay};
        ACME_fnc_providerAnimSpeedOwned={(_medic getVariable ["TEST_speedOwner",false])};
        ACME_fnc_animBlocked={false}; ACME_fnc_doAnim={_moves pushBack _this;};
        ACME_fnc_bodyPartName={_this select 0}; ACME_fnc_medLog={_logs pushBack _this;};
        ACME_fnc_directPressureHasFracture={false}; ACME_fnc_patientInteractionDistance={1};
        ace_interaction_fnc_showMouseHint={_hints=_hints+1;};
        ace_interaction_fnc_hideMouseHint={_hints=_hints-1;};
        ACM_damage_fnc_clotWoundsOnBodyPart={_clots=_clots+1;};
    '''
    for name in ('treatmentPoseSync', 'treatmentPoseStop', 'directPressureExitSpeedRelease', 'providerAnimation', 'directPressurePoseBusy', 'directPressurePoseRetire', 'directPressurePoseEnter', 'directPressurePoseExit', 'doAnimHeld', 'directPressureStop', 'directPressurePose', 'directPressureTick',
                 'directPressureLimb', 'directPressureTorso', 'directPressureSelf', 'directPressureRetire'):
        text += f'ACME_fnc_{name}={{' + source(name) + '};'
    # Execute the real Local event's generation/registry prefix. The following unrelated
    # patient lifecycle operations are outside this provider-worker regression's scope.
    local_prefix = read('ownerInit').split('["CAManBase", "Local", {', 1)[1].split('[_unit] call ACME_fnc_aajtDownedStop;', 1)[0]
    text += 'private _localEvent={' + source('ownerInit', local_prefix) + '};'
    text += 'private _dispatch=ACME_fnc_ownerDispatch;ACME_fnc_ownerDispatch={params ["_patient","_command","_args"];'
    for operation in ('directPressureMarker', 'directPressureClot'):
        text += f'if (_command=="{operation}") exitWith {{' + source('ownerDispatch', switch_case_body(read('ownerDispatch'), operation)) + '};'
    text += '_this call _dispatch;};'
    return text + '''
        private _tick={private _handler=_handlers select _this; [_handler select 1,_this] call (_handler select 0);};
        private _retireDelivery={
            private _event=_wire deleteAt 0; _machine=_event select 2;
            [(_event select 0)=="ACME_directPressureRetire","wrong retirement event"] call _check;
            (_event select 1) call ACME_fnc_directPressureRetire;
        };
    '''


@pytest.mark.parametrize('part', ['body', 'head', 'leftarm'])
@pytest.mark.parametrize('replacement', [False, True])
def test_transfer_retires_only_captured_worker_and_claim(part, replacement):
    execute(setup() + f'''
        [_medic,_patient,"{part}"] call ACME_fnc_directPressureStart;
        call _deliver; call _deliver;
        private _oldId=_medic getVariable "ACME_DP_PFH";
        private _token=_medic getVariable "ACME_DP_ClaimToken";
        private _episode=((_handlers select _oldId) select 1) select 4;
        [(_episode select [0,3]) isEqualTo [_token,0,7],"worker did not capture claim identity"] call _check;
        // Old-version key/draw resources are modelled explicitly; modern DP uses only its mission-display guard.
        _episode set [3,["old-key"]];
        _episode set [4,57];
        _removed=[];_removedDraw=[];
        _inputCalls=0;_moves=[];_logs=[];_stanceCalls=0;
        private _beforeHints=_hints;
        _medic setVariable ["TEST_owner",8];
        _medic setVariable ["ACME_DP_PFH",99];
        _medic setVariable ["ACME_DP_KeyIDs",["new-key"]];
        _medic setVariable ["ACME_DP_Draw3D",88];
    ''' + (f'''
        _medic setVariable ["ACME_DP_ClaimToken","replacement"];
        _patient setVariable ["ACME_DP_claim_{part}",[_medic,"replacement",0,8,1000]];
    ''' if replacement else '') + f'''
        _oldId call _tick;
        [_oldId in _removed && {{!(99 in _removed)}},"wrong provider PFH removed"] call _check;
        ["old-key" in _removed && {{!("new-key" in _removed)}},"wrong keyboard handler removed"] call _check;
        [_removedDraw isEqualTo [57],"wrong Draw3D handler removed"] call _check;
        [_inputCalls==0 && {{count _moves==0}} && {{_clots==0}} && {{_stanceCalls==0}},"former owner still acted"] call _check;
        [_hints==_beforeHints && {{count _logs==0}},"former owner changed current hints/log"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"former owner published a provider reset"] call _check;
        [count _wire==2,"claim release or current-owner cleanup missing"] call _check;
        call _deliver; call _retireDelivery;
        [(_medic getVariable ["ACME_DP_Active",false]) isEqualTo {str(replacement).lower()},"current owner retired wrong episode"] call _check;
        [(_medic getVariable "ACME_DP_PFH")==99 && {{(_medic getVariable "ACME_DP_KeyIDs") isEqualTo ["new-key"]}}
            && {{(_medic getVariable "ACME_DP_Draw3D")==88}},"current-owner cleanup touched local handler identities"] call _check;
        private _claim=_patient getVariable ["ACME_DP_claim_{part}",[]];
        [count _claim=={5 if replacement else 0},"claim release cleared wrong token"] call _check;
    ''')


@pytest.mark.parametrize('operation', ['directPressurePose', 'directPressureStop', 'directPressureLimb', 'directPressureTorso', 'directPressureSelf'])
def test_remote_provider_entry_points_do_not_change_state_or_presentation(operation):
    arguments = '[true,_medic]' if operation == 'directPressureStop' else '[_medic,_patient,"body"]'
    execute(setup() + '''
        _medic setVariable ["TEST_owner",8];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_ClaimToken","new-owner"];
        _medic setVariable ["ACME_DP_InPose",true];
    ''' + arguments + ' call ACME_fnc_' + operation + ';' + '''
        [count _wire==0 && {count _handlers==0} && {count _moves==0} && {_inputCalls==0} && {_stanceCalls==0},
            "remote provider entry point still performed work"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"remote call cleared active state"] call _check;
        [(_medic getVariable "ACME_DP_ClaimToken")=="new-owner","remote call cleared claim"] call _check;
        [_medic getVariable ["ACME_DP_InPose",false],"remote call changed current pose state"] call _check;
    ''')


@pytest.mark.parametrize('local_only', [False, True])
@pytest.mark.parametrize('returns', [False, True])
def test_held_animation_locality_opt_in_preserves_remote_patient_choreography(local_only, returns):
    execute(setup() + f'''
        [_medic,"ACME_DirectPressureHold",1.1,1,{str(local_only).lower()}] call ACME_fnc_doAnimHeld;
        [count _handlers==1,"held worker never started"] call _check;
        _medic setVariable ["TEST_owner",8];
        [_medic,false] call _localEvent;
    ''' + ('_medic setVariable ["TEST_owner",7];[_medic,true] call _localEvent;' if returns else '') + f'''
        0 call _tick;
        [count _moves=={0 if local_only else 1},"held-animation locality contract changed"] call _check;
        [(0 in _removed) isEqualTo {str(local_only).lower()},"wrong held worker retired"] call _check;
    ''')


def test_fast_away_and_back_transfer_retires_pressure_and_releases_stale_stance_ownership():
    execute(setup() + '''
        [_medic,_patient,"body"] call ACME_fnc_directPressureStart;
        call _deliver; call _deliver;
        private _oldId=_medic getVariable "ACME_DP_PFH";
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        _medic setVariable ["TEST_owner",8]; [_medic,false] call _localEvent;
        _medic setVariable ["TEST_owner",7]; [_medic,true] call _localEvent;
        _inputCalls=0; _moves=[];
        _oldId call _tick;
        [_oldId in _removed && {_inputCalls==0} && {count _moves==0},"old DP worker revived after return"] call _check;
        [!(_medic getVariable ["ACME_DP_InPose",true]) && {!(_medic getVariable ["ACME_DP_TreatmentBusy",true])},
            "retired machine-local pressure still owns stance"] call _check;
        [(_medic getVariable "ACME_DP_PFH")==-1,"retired machine-local handler retained"] call _check;
        call _deliver; call _retireDelivery;
        [!(_medic getVariable ["ACME_DP_Active",true]),"returned owner retained stale public pressure"] call _check;
        _machine=7;
        [_medic,_patient,"body"] call ACME_fnc_directPressureStart;
        call _deliver; call _deliver;
        [_medic getVariable ["ACME_DP_Active",false],"returned owner could not start fresh pressure"] call _check;
        private _newId=_medic getVariable "ACME_DP_PFH";
        [!(_newId in _removed),"new pressure worker was removed"] call _check;
    ''')


def test_self_pressure_release_follows_both_patient_and_provider_to_new_owner():
    execute(setup() + '''
        [_medic,_medic,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver; call _deliver;
        private _oldId=_medic getVariable "ACME_DP_PFH";
        _medic setVariable ["TEST_owner",8]; [_medic,false] call _localEvent;
        _oldId call _tick;
        [count _wire==2 && {((_wire select 0) select 2)==8} && {((_wire select 1) select 2)==8},
            "self-pressure cleanup targeted previous owner"] call _check;
        call _deliver; call _retireDelivery;
        [!(_medic getVariable ["ACME_DP_Active",true]),"self pressure active after transfer"] call _check;
        [(_medic getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"self pressure claim retained"] call _check;
    ''')


def test_delayed_pressure_pose_repair_cannot_revive_after_away_and_back_transfer():
    execute(setup() + '''
        [_medic,_patient,"body"] call ACME_fnc_directPressureStart;
        call _deliver; call _deliver;
        _animation="acme_directpressurehold"; _look=[0,-1,0];
        [_medic,_patient] call ACME_fnc_directPressurePose;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isNotEqualTo [],"pose exit callback was not reached"] call _check;
        private _exitId=count _handlers-1;
        _medic setVariable ["TEST_owner",8]; [_medic,false] call _localEvent;
        _medic setVariable ["TEST_owner",7]; [_medic,true] call _localEvent;
        _moves=[];_stanceCalls=0;
        _exitId call _tick;
        [count _moves==0 && {_stanceCalls==0},"old delayed repair changed returned provider"] call _check;
    ''')


@pytest.mark.parametrize('patient_owner', [2, 8])
def test_transferred_provider_active_marker_does_not_block_fresh_claim(patient_owner):
    execute(setup() + f'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver; call _deliver;
        _medic setVariable ["TEST_owner",8];
        _patient setVariable ["TEST_owner",{patient_owner}];_machine={patient_owner};
        [_patient,"claim",[_medic,"leftarm","fresh",0,8,_networkTime]] call ACME_fnc_directPressureClaimLocal;
        [((_patient getVariable ["ACME_DP_claim_leftarm",[]]) param [1,""])=="fresh",
            "transferred active claim blocked fresh provider owner"] call _check;
    ''')


@pytest.mark.parametrize('patient_owner', [2, 8])
@pytest.mark.parametrize('operation', ['directPressureMarker', 'directPressureClot'])
def test_patient_owner_rejects_effects_from_claim_previous_provider_owner(patient_owner, operation):
    arguments = '[_medic,"leftarm",true,"old",0]' if operation == 'directPressureMarker' else '[_medic,"leftarm","old",0]'
    execute(setup() + f'''
        _patient setVariable ["TEST_owner",{patient_owner}]; _machine={patient_owner};
        _medic setVariable ["TEST_owner",8];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Part","leftarm"];
        _patient setVariable ["ACME_DP_claim_leftarm",[_medic,"old",0,7,1000]];
        _patient setVariable ["ACME_DP_press_leftarm",objNull];
    ''' + ('_patient setVariable ["ACME_DP_press_leftarm",_medic];' if operation == 'directPressureClot' else '') +
        f'[_patient,"{operation}",{arguments}] call ACME_fnc_ownerDispatch;' + '''
        [_clots==0,"stale provider claim clotted wounds"] call _check;
    ''' + ('[(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo objNull,"stale provider claim restored pressure"] call _check;' if operation == 'directPressureMarker' else ''))
