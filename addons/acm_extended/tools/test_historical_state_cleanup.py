"""Actual HPMK, reset and obtunded cleanup with explicit engine stand-ins.

A single casualty is enrolled in the active HPMK registry. Renderer, sound and animation primitives
are recorded, not executed. Existing visual/timing/clinical rules are not retuned.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_historical_cardiac_execution import code as numeric_engine_adapter

F=ROOT/'addons/acm_extended/functions'


def one_patient(text):
    text=text.replace('allUnits','[_patient]')
    for t in reversed(lex(text)):
        if t.kind=='ident' and t.value=='continue':
            text=text[:t.offset]+'breakOut "singlePatient"'+text[t.offset+len(t.value):]
    return 'scopeName "singlePatient";'+text


def blanket_setup():
    text=(F/'fn_hpmkBlanketTick.sqf').read_text()
    text=text.replace('isServer','_server')
    text=text.replace('allPlayers','[_medic]').replace('alive _x','_alive').replace('_x distance _p','_distance')
    text=text.replace('getPosATL _p','[10,20,0]').replace('getDir _p','90')
    text=text.replace('deleteVehicle _b;','_deleted pushBack _b;')
    text=text.replace('_drop setPosATL ([10,20,0]);','_positions pushBack [_drop,[10,20,0]];')
    text=text.replace('_drop setDir (90);','_directions pushBack [_drop,90];')
    text=text.replace('[_p, "ACM_HPMK_Remove"] remoteExec ["ACME_fnc_remoteSay3D", 0];','_sounds pushBack [_p,"ACM_HPMK_Remove"];')
    state=(F/'fn_hpmkStateCommit.sqf').read_text().replace(', _public]',']')
    return '''
        private _server=true; private _deleted=[]; private _spawns=[];
        private _positions=[]; private _directions=[]; private _sounds=[];
        ACME_fnc_setVarNet={params ["_p","_k","_v"];_p setVariable [_k,_v];};
        ACME_fnc_hpmkSpawnBlanket={_spawns pushBack _this;missionNamespace};
        missionNamespace setVariable ["ACME_sys_hpmk",true];
        missionNamespace setVariable ["ACME_hpmk_blanketClass","mock-blanket"];
        missionNamespace setVariable ["ACME_hpmk_serverPatients",[_patient]];
        CBA_fnc_targetEvent={
            if ((_this select 0)=="ACME_worldSfx") then {_sounds pushBack (_this select 1);} else {_events pushBack _this;};
        };
    '''+'ACME_fnc_hpmkStateCommit={'+adapt(state)+'}; private _tickBlanket={'+adapt(one_patient(text))+'};'


@pytest.mark.parametrize('state',['prepped','wrapped','exposed'])
@pytest.mark.parametrize('condition',['dead','unconscious','lying'])
def test_immobile_patients_retain_hpmk_without_a_patient_attached_world_object(state,condition):
    prepare={'dead':'_patientAlive=false;','unconscious':'_patient setVariable ["ACE_isUnconscious",true];','lying':'_patient setVariable ["ACM_core_Lying_State",true];'}[condition]
    execute(blanket_setup()+f'_patient setVariable ["ACME_hpmk_state","{state}"];'+prepare+'''
        _patient setVariable ["ACME_hpmk_blanket",missionNamespace];
        call _tickBlanket;
        [_deleted isEqualTo [missionNamespace],"legacy blanket not removed"] call _check;
        [(_patient getVariable ["ACME_hpmk_blanket",missionNamespace]) isEqualTo objNull,"legacy handle retained"] call _check;
        [count _spawns==0 && {count _events==0},"immobile patient dropped/returned blanket"] call _check;
    '''+f'[(_patient getVariable ["ACME_hpmk_state",""])=="{state}","immobile state cleared"] call _check;')


@pytest.mark.parametrize('state',['wrapped','exposed'])
def test_mobile_fallback_drops_once_and_clears_only_hpmk_state(state):
    execute(blanket_setup()+f'_patient setVariable ["ACME_hpmk_state","{state}"];'+'''
        _patient setVariable ["ACME_thora_tube_left",true];
        call _tickBlanket; call _tickBlanket;
        [count _spawns==1 && {count _sounds==1},"mobile fallback duplicated drop"] call _check;
        [missionNamespace getVariable ["ACME_hpmk_dropped",false],"drop not pickable"] call _check;
        [(_patient getVariable ["ACME_hpmk_state","bad"])=="" && {!(_patient getVariable ["ACME_hpmk_on",true])},"HPMK state not cleared"] call _check;
        [_patient getVariable ["ACME_thora_tube_left",false],"unrelated equipment removed"] call _check;
    ''')


@pytest.mark.parametrize('recorded',[False,True])
def test_mobile_prepped_kit_returns_to_recorded_provider_or_casualty_only_once(recorded):
    execute(blanket_setup()+('_patient setVariable ["ACME_hpmk_provider",_medic];' if recorded else '')+'''
        _patient setVariable ["ACME_hpmk_state","prepped"];
        call _tickBlanket; call _tickBlanket;
        [count _events==1 && {count _spawns==0},"prep return duplicated or spawned blanket"] call _check;
        private _request=((_events select 0) select 1);
        [(_request select 1)=="hpmkRemove","wrong return action"] call _check;
    '''+f'[((_request select 2) select 0) isEqualTo {"_medic" if recorded else "_patient"},"wrong reusable kit receiver"] call _check;')


def test_disabled_hpmk_visual_cleanup_does_not_remove_kit_or_reposition_patient():
    execute(blanket_setup()+'''
        missionNamespace setVariable ["ACME_sys_hpmk",false];
        _patient setVariable ["ACME_hpmk_state","wrapped"];
        _patient setVariable ["ACME_hpmk_blanket",missionNamespace];
        call _tickBlanket;
        [count _deleted==1 && {count _spawns==0} && {count _events==0},"disabled cleanup changed treatment"] call _check;
        [(_patient getVariable ["ACME_hpmk_state",""])=="wrapped","disabled visual cleanup lost reusable kit state"] call _check;
        [count _moves==0,"visual cleanup repositioned casualty"] call _check;
    ''')


def test_client_cannot_execute_server_blanket_fallback():
    execute(blanket_setup()+'''
        _server=false;
        _patient setVariable ["ACME_hpmk_state","wrapped"];
        call _tickBlanket;
        [count _spawns==0 && {count _events==0},"client ran server fallback"] call _check;
    ''')


def test_only_dropped_anchor_visuals_are_registered_and_pickup_remains_scoped():
    text=(F/'fn_registerHpmkVisualRuntime.sqf').read_text()
    tokens=lex(text); identifiers={t.value for t in tokens if t.kind=='ident'}
    assert text.count('createSimpleObject [')==1
    assert 'createSimpleObject [_model, [0,0,0], true]' in text
    assert 'getPosWorldVisual _anchor' in text
    assert '"ACME_hpmk_isBlanket", false' in text
    assert '"ACME_hpmk_dropped", false' in text
    # The one-time server seed and tracking event legitimately name patients.
    # The visual worker must still use dropped anchors only, with no patient scan.
    visual=text[text.index('ACME_hpmk_visuals = createHashMap;'):]
    visual_identifiers={t.value for t in lex(visual) if t.kind=='ident'}
    assert '_patient' not in visual_identifiers and 'allUnits' not in visual_identifiers
    assert not any(t.value=='allUnits' for t in lex((F/'fn_hpmkBlanketTick.sqf').read_text()))
    assert 'attachTo' not in identifiers and 'createVehicle' not in identifiers
    # No patient-follow loop is reinstated merely to meet B28's old expectation.
    assert 'ACME_hpmk_wrappedVisuals = createHashMap;' in text


def pp_adapter(text):
    text=text.replace('curatorCamera','objNull')
    text=text.replace('attachedTo _p','objNull')
    text=re.sub(r'inputAction "([^"]+)"',r'(missionNamespace getVariable ["input_\1",0])',text)
    text=re.sub(r'ppEffectCreate (\[[^\n]+?\])',r'(\1 call _createEffect)',text)
    # Preserve all effect arguments while recording engine-only operations.
    text=re.sub(r'(_\w+) (ppEffectEnable|ppEffectForceInNVG|ppEffectAdjust|ppEffectCommit) ([^;]+);',
                lambda m:'_effectOps pushBack ["'+m[2]+'",'+m[1]+','+m[3]+'];',text)
    text=text.replace('ppEffectDestroy _h;','_destroyed pushBack _h;')
    text=re.sub(r'(\(missionNamespace getVariable \["ACME_obtunded_muffleFade", 1\.0\]\)) fadeSound\s+([^;]+);',r'_fades pushBack [\1,\2];',text)
    text=text.replace('addCamShake [','_sways pushBack [')
    text=text.replace('_p setAnimSpeedCoef 1;','_speedResets=_speedResets+1;')
    text=re.sub(r'(_[pu]) setUnconscious (true|false);',r'_engineStates pushBack [\1,\2];',text)
    return numeric_engine_adapter(text)


def obtunded_setup():
    voice=(F/'fn_obtundedVoice.sqf').read_text().replace('alive _unit','_patientAlive')
    return '''
        private _effectOps=[]; private _destroyed=[]; private _fades=[];
        private _sways=[]; private _speedResets=0; private _engineStates=[];
        private _voiceCalls=[]; private _lockCalls=[]; private _nextEffect=100;
        private _createEffect={_nextEffect=_nextEffect+1;_nextEffect};
        private _linear={params ["_lo","_hi","_x","_a","_b","_clamp"];
            private _f=(_x-_lo)/(_hi-_lo);if (_clamp) then {_f=(_f max 0) min 1;};_a+(_f*(_b-_a))};
        ACME_fnc_obtundedInputLock={_lockCalls pushBack _this;};
        TFAR_fnc_setForbiddenToSpeak={_voiceCalls pushBack _this;};
        ACE_player=_patient;
        missionNamespace setVariable ["ACME_sys_obtunded",true];
        missionNamespace setVariable ["ACME_obtunded_swayPower",0];
    '''+'ACME_fnc_obtundedVoice={'+adapt(voice)+'}; private _tickObtunded={'+pp_adapter((F/'fn_obtundedTick.sqf').read_text())+'};'


@pytest.mark.parametrize('reason',['masterOff','unconscious','dead','stateCleared'])
def test_obtunded_inactive_cleanup_releases_owned_effects_voice_and_input(reason):
    change={'masterOff':'missionNamespace setVariable ["ACME_sys_obtunded",false];',
            'unconscious':'_patient setVariable ["ACE_isUnconscious",true];',
            'dead':'_patientAlive=false;', 'stateCleared':'_patient setVariable ["ACME_obtunded",false];'}[reason]
    execute(obtunded_setup()+'''
        _patient setVariable ["ACME_obtunded",true];
        call _tickObtunded;
        [uiNamespace getVariable ["ACME_ObtundedActive",false],"active state not started"] call _check;
        [_patient getVariable ["tf_unable_to_use_radio",false],"voice was not muted"] call _check;
        private _cc=uiNamespace getVariable ["ACME_Obtunded_CC",-1];
        private _db=uiNamespace getVariable ["ACME_Obtunded_DB",-1];
    '''+change+'''
        call _tickObtunded;
        [!(uiNamespace getVariable ["ACME_ObtundedActive",true]),"inactive visual state retained"] call _check;
        [!(_patient getVariable ["tf_unable_to_use_radio",true]),"voice remained locked"] call _check;
        [(_patient getVariable ["tf_voiceVolume",0])==1,"voice volume not restored"] call _check;
        [count _lockCalls==2 && {(_lockCalls select 1) isEqualTo [_patient,false]},"old input locks not released"] call _check;
        [count _waits==2,"effect cleanup callbacks missing or duplicated"] call _check;
        {(_x select 1) call (_x select 0);} forEach _waits;
        [_cc in _destroyed && {_db in _destroyed} && {count _destroyed==2},"wrong effect handles destroyed"] call _check;
        [((_fades select ((count _fades)-1)) select 1)==1,"global audio not restored"] call _check;
        [count _engineStates==0,"ordinary inactive cleanup changed medical/engine consciousness"] call _check;
        call _tickObtunded;
        [count _waits==2,"inactive cleanup rescheduled effect destruction"] call _check;
    ''')


def test_manual_obtundation_remains_active_with_master_disabled():
    execute(obtunded_setup()+'''
        missionNamespace setVariable ["ACME_sys_obtunded",false];
        _patient setVariable ["ACME_obtunded",true];
        _patient setVariable ["ACME_obtunded_manual",true];
        call _tickObtunded;
        [uiNamespace getVariable ["ACME_ObtundedActive",false],"manual preview bypassed effects"] call _check;
        [_patient getVariable ["tf_unable_to_use_radio",false],"manual preview bypassed voice state"] call _check;
        [count _waits==0 && {count _engineStates==0},"manual preview invented a collapse"] call _check;
    ''')


def test_old_effect_cleanup_destroys_only_its_captured_handles_after_reactivation():
    execute(obtunded_setup()+'''
        _patient setVariable ["ACME_obtunded",true]; call _tickObtunded;
        _patient setVariable ["ACME_obtunded",false]; call _tickObtunded;
        private _old=+_waits;
        _patient setVariable ["ACME_obtunded",true]; call _tickObtunded;
        private _cc=uiNamespace getVariable ["ACME_Obtunded_CC",-1];
        private _db=uiNamespace getVariable ["ACME_Obtunded_DB",-1];
        {(_x select 1) call (_x select 0);} forEach _old;
        [!(_cc in _destroyed) && {!(_db in _destroyed)},"old cleanup destroyed new effects"] call _check;
        [uiNamespace getVariable ["ACME_ObtundedActive",false],"old cleanup cleared new state"] call _check;
    ''')


def test_obtunded_input_shim_retires_handlers_without_intercepting_weapons_or_projectiles():
    text=(F/'fn_obtundedInputLock.sqf').read_text()
    text=text.replace('_display displayRemoveEventHandler [','_removedInput pushBack [')
    text=text.replace('isNull ACE_player','(ACE_player isEqualTo objNull)')
    execute('private _removedInput=[];'+ 'private _retire={'+adapt(text)+'};'+
            'private _weaponIntent={'+(F/'fn_obtundedWeaponIntent.sqf').read_text()+'};'+'''
        uiNamespace setVariable ["ACME_ObtundedInputDisplay",missionNamespace];
        uiNamespace setVariable ["ACME_ObtundedInputKeyEH",12];
        uiNamespace setVariable ["ACME_ObtundedInputMouseDownEH",13];
        uiNamespace setVariable ["ACME_ObtundedInputLocked",true];
        [_patient,true] call _retire;
        [_removedInput isEqualTo [["KeyDown",12],["MouseButtonDown",13]],"legacy handlers not removed"] call _check;
        [!(uiNamespace getVariable ["ACME_ObtundedInputLocked",true]),"input remained blocked"] call _check;
        [!([_patient,"weapon"] call _weaponIntent),"legacy shim intercepted weapon"] call _check;
        [_medic getVariable ["ACME_obtunded_pendingWeapon","bad"]=="","weapon intent not cleared"] call _check;
    ''')
    ids={t.value for t in lex(text) if t.kind=='ident'}
    assert 'deleteVehicle' not in ids and 'addEventHandler' not in ids


@pytest.mark.parametrize('player',[False,True])
def test_native_reset_clears_bookkeeping_without_getup_or_equipment_removal(player):
    text=(ROOT/'addons/core/functions/fnc_resetVariables.sqf').read_text().replace('isPlayer _patient','_isPlayer')
    execute(f'private _isPlayer={str(player).lower()}; private _generated=0; ACM_core_fnc_generateTargetVitals={{_generated=_generated+1;}};'+
            'private _reset={'+adapt(text)+'};'+'''
        _patient setVariable ["ACM_core_Lying_State",true];
        _patient setVariable ["ACM_core_Sitting_State",true];
        _patient setVariable ["ACM_core_KnockOut_State",true];
        _patient setVariable ["ACME_rollProviderActive",true];
        _patient setVariable ["ACME_rollProviderToken","old"];
        _patient setVariable ["ACME_thora_tube_left",true];
        [_patient] call _reset;
        {[!(_patient getVariable [_x,true]),"reset left stale bookkeeping"] call _check;}
            forEach ["ACM_core_Lying_State","ACM_core_Sitting_State","ACM_core_KnockOut_State","ACME_rollProviderActive"];
        [(_patient getVariable ["ACME_rollProviderToken","bad"])=="","provider roll token retained"] call _check;
        [_generated==1 && {count _moves==0} && {count _waits==0},"reset did not remain bookkeeping-only"] call _check;
        [_patient getVariable ["ACME_thora_tube_left",false],"native reset removed persistent equipment"] call _check;
    ''')


def test_lucid_window_changes_voice_and_audio_once_per_transition():
    execute(obtunded_setup()+'''
        _patient setVariable ["ACME_obtunded",true];
        call _tickObtunded;
        [count _voiceCalls==1 && {(_voiceCalls select 0) isEqualTo [_patient,true]},"initial mute missing"] call _check;
        _nowTime=19; call _tickObtunded;
        [count _voiceCalls==2 && {(_voiceCalls select 1) isEqualTo [_patient,false]},"lucid onset did not release voice"] call _check;
        [((_fades select 1) select 1)==0.78,"lucid audio level changed"] call _check;
        _nowTime=19.1; call _tickObtunded;
        [count _voiceCalls==2 && {count _fades==2},"unchanged lucid state repeated effects"] call _check;
        _nowTime=30; call _tickObtunded;
        [count _voiceCalls==3 && {(_voiceCalls select 2) isEqualTo [_patient,true]},"lucid expiry did not restore mute"] call _check;
        [((_fades select 2) select 1)==0.35,"ordinary muffle level changed"] call _check;
        [count _engineStates==0,"lucid transitions changed consciousness"] call _check;
    ''')
