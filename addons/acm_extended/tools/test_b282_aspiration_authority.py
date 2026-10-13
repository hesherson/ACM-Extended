"""Execute aspiration episode receipts, ownership replicas, native respiration, and restore.

Actual SQF executes; object/locality, random draws and transport are explicit boundaries.
Replication order is controlled, not claimed to model the Arma network engine.
"""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import ROOT, read, execute
from b282_aspiration_fixture import boundary, definitions


def setup(mutation=None):
    tick=read('aspirationTick')
    event=read('aspirationEventKey')
    state=read('aspirationState')
    if mutation=='mutable_key':
        event=event.replace('format ["explicit:%1:%2:%3",_eventId,_eventCount,_serial]', 'format ["explicit:%1:%2:%3:%4",_eventId,_eventCount,_serial,_patient getVariable ["ACM_airway_AirwayObstructionVomit_State",0]]')
    if mutation=='no_highwater': event=event.replace(' || {_serial <= (_state select 4)}','')
    if mutation=='scalar_authority': state=state.replace('+_state','[_epoch,_key,_patient getVariable ["ACME_aspiration_load",0],_patient getVariable ["ACME_aspiration_edema",0],_serial]')
    if mutation=='no_receipt': tick=tick.replace('_state set [4,(_state select 4) max _serial];','')
    rr=(ROOT/'addons/breathing/functions/fnc_updateRespirationRate.sqf').read_text()
    return definitions()+''.join('ACME_fnc_'+n+'={'+boundary(s)+'};' for n,s in [('aspirationState',state),('aspirationEventKey',event),('aspirationTick',tick)])+\
        'ACM_breathing_fnc_updateRespirationRate={'+boundary(rr,'breathing')+'};'+r'''
        private _public=createHashMap;private _logs=[];private _writes=0;
        ACME_fnc_setVarNet={params ["_u","_key","_value"];if !((_u getVariable [_key,[]]) isEqualTo _value) then {_writes=_writes+1;};_u setVariable [_key,_value];_public set [_key,_value];};
        ACME_fnc_setVarNetApprox=ACME_fnc_setVarNet;
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        ACM_core_fnc_setAceMedicalState={params ["_u","_rows"];{_u setVariable ["ace_medical_spo2",_x select 1]} forEach _rows;};
        ACM_core_fnc_setTargetVitalsState={throw "aspiration illegally wrote native target";};
        ACM_airway_fnc_getAirwayState={1};ACM_breathing_fnc_getBreathingState={1};
        ACM_core_fnc_bvmActive={false};ACM_core_fnc_cprActive={false};
        ace_medical_status_fnc_getMedicationCount={0};
        private _a=_patient;private _b=_medic;
        _a setVariable ["ACME_clinicalEpoch",1];_b setVariable ["ACME_clinicalEpoch",1];
        _a setVariable ["ACM_core_TargetVitals_RespirationRate",20];
        _a setVariable ["ACM_core_TargetVitals_OxygenSaturation",99];
        _a setVariable ["ace_medical_spo2",97];
        private _emit={params ["_u","_id",["_stage",4]];private _e=[_u,"make",_id,1,_stage] call ACME_fnc_aspirationEventKey;_u setVariable ["ACME_laryngo_emesis",_e];_u setVariable ["ACM_airway_AirwayObstructionVomit_State",1];_e};
        private _tick={params ["_u"];missionNamespace setVariable ["ACME_aspiration_activePatients",[_u]];call ACME_fnc_aspirationTick;};
        CBA_missionTime=10;
    '''


DEDUP=r'''
    [_a,"first"] call _emit;[_a] call _tick;
    private _first=+(_a getVariable "ACME_aspiration_State");
    _a setVariable ["ACM_airway_AirwayObstructionVomit_State",0];
    [_a] call _tick;
    [(_a getVariable "ACME_aspiration_State") isEqualTo _first && {count _logs==1},"clear replayed the processed episode"] call _check;
    _a setVariable ["ACM_airway_AirwayObstructionVomit_State",3];[_a] call _tick;
    [(_a getVariable "ACME_aspiration_State") isEqualTo _first && {count _logs==1},"obstruction decay/reorder replayed episode"] call _check;
'''


def test_actual_tick_commits_first_zero_delta_event_and_deduplicates_obstruction_changes():
    execute(setup()+DEDUP+r'''
        [(_first select 2)>0 && {(_first select 4)==1},"first zero-delta tick dropped injury/receipt"] call _check;
        [(_a getVariable "ACM_core_TargetVitals_RespirationRate")==20,"aspiration modified native target"] call _check;
    ''')


@pytest.mark.parametrize('order',['state_first','event_first','aliases_first'])
def test_incoming_owner_public_record_and_event_packet_orders_never_replay(order):
    script=r'''
        private _event=[_a,"first"] call _emit;[_a] call _tick;
        private _state=+(_a getVariable "ACME_aspiration_State");
        _b setVariable ["ACM_core_TargetVitals_RespirationRate",20];
        _b setVariable ["ACM_core_TargetVitals_OxygenSaturation",99];
        _b setVariable ["ace_medical_spo2",97];
    '''
    if order=='state_first': script+=' _b setVariable ["ACME_aspiration_State",_state];[_b] call _tick;_b setVariable ["ACME_laryngo_emesis",_event];'
    if order=='event_first': script+=' _b setVariable ["ACME_laryngo_emesis",_event];[_b] call _tick;[isNil {_b getVariable "ACME_aspiration_State"},"event-before-authority was applied"] call _check;_b setVariable ["ACME_aspiration_State",_state];'
    if order=='aliases_first': script+=' _b setVariable ["ACME_laryngo_emesis",_event];_b setVariable ["ACME_aspiration_load",_state select 2];[_b] call _tick;[isNil {_b getVariable "ACME_aspiration_State"},"mixed scalar replica reconstructed authority"] call _check;_b setVariable ["ACME_aspiration_State",_state];'
    execute(setup()+script+r'''
        [_b] call _tick;
        [(_b getVariable "ACME_aspiration_State") isEqualTo _state && {count _logs==1},"incoming owner replayed public processed emesis"] call _check;
        private _rr=[_b,99,0,0,0,2,true] call ACM_breathing_fnc_updateRespirationRate;
        [abs (_rr-(20+14*(_state select 2)))<0.00001,"incoming owner doubled/lost native RR compensation"] call _check;
        [(_b getVariable "ACM_core_TargetVitals_RespirationRate")==20,"endpoint fed compensation into target"] call _check;
    ''')


def test_delayed_old_explicit_event_after_newer_event_is_rejected():
    execute(setup()+r'''
        private _old=[_a,"one"] call _emit;[_a] call _tick;
        [_a,"two"] call _emit;[_a] call _tick;
        private _new=+(_a getVariable "ACME_aspiration_State");
        _a setVariable ["ACME_laryngo_emesis",_old];[_a] call _tick;
        [(_a getVariable "ACME_aspiration_State") isEqualTo _new && {count _logs==2},"old explicit serial replayed after newer event"] call _check;
        [(_new select 4)==2,"new event did not retain monotonic high-water"] call _check;
    ''')


def test_actual_native_suction_does_not_erase_receipt_or_repeat_injury():
    source=(ROOT/'addons/airway/functions/fnc_handleSuctionLocal.sqf').read_text()
    execute(setup()+'ACM_airway_fnc_handleSuctionLocal={'+boundary(source,'airway')+'};'+r'''
        ACM_airway_fnc_clearAirwayCheckedTime={};
        [_a,"first"] call _emit;[_a] call _tick;
        private _before=+(_a getVariable "ACME_aspiration_State");
        [_a] call ACM_airway_fnc_handleSuctionLocal;[_a] call _tick;
        [(_a getVariable "ACM_airway_AirwayObstructionVomit_State")==0,"actual suction did not clear native obstruction"] call _check;
        [(_a getVariable "ACME_aspiration_State") isEqualTo _before && {count _logs==1},"actual suction reapplied injury"] call _check;
        [_a,"new-after-suction"] call _emit;[_a] call _tick;
        [((_a getVariable "ACME_aspiration_State") select 2)>(_before select 2) && {count _logs==2},"new genuine emesis after suction was suppressed"] call _check;
    ''')


@pytest.mark.parametrize('guard',['dead','nonlocal','restoring','old_epoch'])
def test_owner_lifecycle_guards_skip_old_and_unavailable_patients(guard):
    script='[_a,"first"] call _emit;'
    script += {'dead':'_a setVariable ["testAlive",false];','nonlocal':'_a setVariable ["testLocal",false];','restoring':'_a setVariable ["ACME_clinicalRestoring",true];','old_epoch':'_a setVariable ["ACME_clinicalEpoch",2];'}[guard]
    execute(setup()+script+r'''
        private _before=_writes;[_a] call _tick;
        [_writes==_before && {count _logs==0},"inactive/stale episode mutated aspiration"] call _check;
    ''')


def test_owner_clock_handoff_has_no_elapsed_backlog_and_low_fps_is_capped():
    execute(setup()+r'''
        [_a,"first",8] call _emit;[_a] call _tick;
        private _before=+(_a getVariable "ACME_aspiration_State");
        CBA_missionTime=1000;[_a] call _tick;
        private _after=+(_a getVariable "ACME_aspiration_State");
        [abs ((_before select 2)-(_after select 2)-0.00018)<0.00001,"low-fps delta was not capped at three seconds"] call _check;
        _b setVariable ["ACME_aspiration_State",_after];_b setVariable ["ACME_laryngo_emesis",_a getVariable "ACME_laryngo_emesis"];
        _b setVariable ["ACME_clock_aspiration",10];_b setVariable ["ACME_clock_aspiration_owner",99];
        [_b] call _tick;
        [(_b getVariable "ACME_aspiration_State") isEqualTo _after,"new owner consumed prior owner clock backlog"] call _check;
    ''')


@pytest.mark.parametrize('case,fields,expected',[
    ('normal','',22.8),('blast','_a setVariable ["ACME_blastLung_rrDrive",30];',30),
    ('tbi','_a setVariable ["ACME_rrDrive_tbi",12];',12),
    ('demo','_a setVariable ["ACME_cs_rrDrive",9];',9),
    ('seizure','_a setVariable ["ACME_rrDrive_tbi",12];_a setVariable ["ACME_cs_rrDrive",9];_a setVariable ["ACME_seizure_rrDrive",0];',0),
    ('paralysis','_a setVariable ["ACME_roc_paralyzed",true];',0),
    ('arrest','_a setVariable ["ace_medical_inCardiacArrest",true];',0),
    ('vent','_a setVariable ["ACME_roc_paralyzed",true];_a setVariable ["ACME_vent_driving",true];_a setVariable ["ACME_vent_effectiveRR",17];',17),
    ('bvm','_a setVariable ["ACME_roc_paralyzed",true];ACM_core_fnc_bvmActive={true};',10),
    ('blocked','ACM_airway_fnc_getAirwayState={0};',0),
    ('foreign_high_baseline','_a setVariable ["ACM_core_TargetVitals_RespirationRate",55];',55),
])
def test_actual_native_respiration_composes_once_and_preserves_priorities(case,fields,expected):
    execute(setup()+r'''_a setVariable ["ACME_aspiration_State",[1,"known",0.2,0.1,1]];'''+fields+f'''
        private _base=_a getVariable "ACM_core_TargetVitals_RespirationRate";
        private _rr=[_a,99,0,0,0,2,true] call ACM_breathing_fnc_updateRespirationRate;
        [abs (_rr-{expected})<0.00001,"native respiratory priority failed {case}"] call _check;
        [(_a getVariable "ACM_core_TargetVitals_RespirationRate")==_base,"composition mutated mod/native baseline"] call _check;
        private _again=[_a,99,0,0,0,2,true] call ACM_breathing_fnc_updateRespirationRate;
        [abs (_again-{expected})<0.00001,"second respiratory tick accumulated injury"] call _check;
    ''')


def test_healthy_readers_and_tick_leave_no_state_clocks_or_publication():
    execute(setup()+r'''
        for "_i" from 0 to 119 do {
            CBA_missionTime=10+_i;[_a] call _tick;
            [_a,99,0,0,0,2,true] call ACM_breathing_fnc_updateRespirationRate;
        };
        [isNil {_a getVariable "ACME_aspiration_State"} && {isNil {_a getVariable "ACME_clock_aspiration"}} && {_writes==0},"healthy readers created aspiration/network heartbeat"] call _check;
    ''')


@pytest.mark.parametrize('mutation',['mutable_key','no_highwater','scalar_authority','no_receipt'])
def test_semantic_mutation_is_rejected(mutation):
    cases={
      'mutable_key':DEDUP.replace('[_a,"first"] call _emit;','_a setVariable ["ACME_laryngo_emesis",["first",1,4]];'),
      'no_highwater':r'''private _old=[_a,"one"] call _emit;[_a] call _tick;[_a,"two"] call _emit;[_a] call _tick;private _before=+(_a getVariable "ACME_aspiration_State");_a setVariable ["ACME_laryngo_emesis",_old];[_a] call _tick;[(_a getVariable "ACME_aspiration_State") isEqualTo _before,"old replay"] call _check;''',
      'scalar_authority':r'''[_a,"one"] call _emit;[_a] call _tick;private _before=+(_a getVariable "ACME_aspiration_State");_a setVariable ["ACME_aspiration_load",0.9];[_a] call _tick;[(_a getVariable "ACME_aspiration_State") isEqualTo _before,"alias replaced canonical injury"] call _check;''',
      'no_receipt':r'''[_a,"one"] call _emit;[_a] call _tick;[((_a getVariable "ACME_aspiration_State") select 4)==1,"receipt high-water missing"] call _check;''',
    }
    expected={"mutable_key":"obstruction decay/reorder replayed episode","no_highwater":"old replay","scalar_authority":"alias replaced canonical injury","no_receipt":"receipt high-water missing"}
    with pytest.raises(AssertionError,match=expected[mutation]): execute(setup(mutation)+cases[mutation])


def native_producer_definition():
    source=(ROOT/'addons/airway/functions/fnc_handleAirwayObstruction_Vomit.sqf').read_text()
    source=re.sub(r'\brandom (\d+(?:\.\d+)?)',r'(\1 * 0)',source)
    source=re.sub(r'playSound3D \[[^;]+;', '_nativeSounds=_nativeSounds+1;',source)
    return 'ACM_airway_fnc_handleAirwayObstruction_Vomit={'+boundary(source,'airway')+'};'


def test_actual_native_vomit_producer_emits_only_on_a_real_episode_after_laryngoscopy():
    execute(setup()+native_producer_definition()+r'''
        private _handler=[];private _nativeSounds=0;
        CBA_fnc_addPerFrameHandler={_handler=_this;0};CBA_fnc_removePerFrameHandler={};
        ACM_circulation_fnc_getNauseaMedicationEffects={0};ACM_airway_airwayObstructionVomitChance=1;
        [_a,"laryngoscopy"] call _emit;[_a] call _tick;
        private _first=+(_a getVariable "ACME_aspiration_State");
        _a setVariable ["ACE_isUnconscious",true];_a setVariable ["ACM_airway_AirwayObstructionVomit_Count",3];
        [_a] call ACM_airway_fnc_handleAirwayObstruction_Vomit;
        private _run={[_handler select 2,0] call (_handler select 0)};
        _a setVariable ["ACM_airway_AirwayObstructionVomit_GracePeriod",10];
        CBA_missionTime=11;call _run;
        [count (_a getVariable "ACME_laryngo_emesis")==5 && {((_a getVariable "ACME_laryngo_emesis") select 4)==1} && {_nativeSounds==0},"grace-only worker emitted a new aspiration event"] call _check;
        CBA_missionTime=40;call _run;[_a] call _tick;
        private _second=+(_a getVariable "ACME_aspiration_State");
        [(_second select 4)==2 && {(_second select 2)>(_first select 2)} && {_nativeSounds==1},"real native vomit after explicit event lost its receipt/injury"] call _check;
        [(_a getVariable "ACM_airway_AirwayObstructionVomit_Count")==2,"native event changed finite stomach consumption"] call _check;
        // Replica sees a clearing Grace packet before the separate zero-obstruction packet.
        _b setVariable ["ACME_aspiration_State",_second];_b setVariable ["ACME_laryngo_emesis",_a getVariable "ACME_laryngo_emesis"];
        _b setVariable ["ACM_airway_AirwayObstructionVomit_State",2];_b setVariable ["ACM_airway_AirwayObstructionVomit_GracePeriod",50];
        [_b] call _tick;
        [(_b getVariable "ACME_aspiration_State") isEqualTo _second && {count _logs==2},"clearing Grace packet replayed native event"] call _check;
        _b setVariable ["ACM_airway_AirwayObstructionVomit_State",0];[_b] call _tick;
        [(_b getVariable "ACME_aspiration_State") isEqualTo _second,"clear obstruction erased lung injury"] call _check;
    ''')


@pytest.mark.parametrize('pending',[False,True])
def test_actual_snapshot_codec_validate_restore_rebases_receipt_highwater_and_pending_episode(pending):
    from test_b271_ptx_stability import execute as ptx_execute, restore_setup, function
    from test_historical_medication_rows import iteration_scopes
    code=restore_setup()+iteration_scopes(function('clinicalSnapshot'))+definitions()+r'''
        _patient setVariable ["ACME_aspiration_State",[7,"explicit:saved:1:8",0.3,0.2,8]];
        _patient setVariable ["ACME_aspiration_load",0.99];_patient setVariable ["ACME_aspiration_edema",0.99];
        _patient setVariable ["ACM_core_TargetVitals_RespirationRate",20];
    '''+f'_patient setVariable ["ACME_laryngo_emesis",["saved",1,4,7,{9 if pending else 8}]];'+r'''
        private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
        private _names=(_snapshot select 1) apply {_x select 0};
        ["ACME_aspiration_State" in _names && {!("ACME_aspiration_load" in _names)} && {!("ACME_aspiration_edema" in _names)},"snapshot serialized independent burden mirrors"] call _check;
        private _saved=+(_patient getVariable "ACME_aspiration_State");
        _patient setVariable ["ACME_clinicalEpoch",9];
        _patient setVariable ["ACME_aspiration_State",[]];
        [_patient,_snapshot,9] call ACME_fnc_clinicalRestore;
        private _restored=_patient getVariable "ACME_aspiration_State";
        [(_restored select 0)==9 && {(_restored select 1)==(_saved select 1)} && {(_restored select 2)==0.3} && {(_restored select 3)==0.2} && {(_restored select 4)==8},"restore lost injury/processed receipt/high-water or failed epoch rebind"] call _check;
        [((_patient getVariable "ACME_laryngo_emesis") select 3)==9,"restored emesis retained old epoch"] call _check;
        [(_patient getVariable "ACM_core_TargetVitals_RespirationRate")==20,"restore changed nonserialized native target baseline"] call _check;
        private _episode=[_patient] call ACME_fnc_aspirationEventKey;
    '''+f'[(_episode select 2) isEqualTo {str(pending).lower()},"restore lost pending/processed event distinction"] call _check;'
    ptx_execute(code)


def test_actual_restore_migrates_only_valid_recognized_legacy_burden_without_readding_event():
    from test_b271_ptx_stability import execute as ptx_execute, restore_setup
    ptx_execute(restore_setup()+r'''
        _patient setVariable ["ACME_laryngo_emesis",["old",1,4]];
        private _rows=[["ACME_aspiration_load",["V",0.3]],["ACME_aspiration_edema",["V",0.2]]];
        [_patient,[3,_rows],7] call ACME_fnc_clinicalRestore;
        private _state=_patient getVariable "ACME_aspiration_State";
        [(_state select 2)==0.3 && {(_state select 3)==0.2} && {(_state select 1)=="explicit:old:1:0"},"recognized legacy injury lost or pending event was guessed"] call _check;
        _patient setVariable ["ACME_aspiration_State",[]];
        // Arma treats a nil-cleared object variable as absent; this VM namespace retains it.
        _patient setVariable ["ACME_lineWarmerRestorePlan",[]];
        [_patient,[3,[["ACME_aspiration_load",["V","bad"]],["ACME_aspiration_edema",["V",3]]]],7] call ACME_fnc_clinicalRestore;
        private _invalid=_patient getVariable "ACME_aspiration_State";
        [(_invalid select 2)==0 && {(_invalid select 3)==0},"invalid legacy burden accepted"] call _check;
    ''')


def test_actual_full_heal_registry_reset_clears_authority_and_all_mirrors():
    source=read('clinicalReset')
    source=re.sub(r'_patient forceWalk [^;]+;','',source)
    source=re.sub(r'ACME_fnc_(\w+)',lambda m:m[0],source)
    calls=set(re.findall(r'call (ACME_fnc_\w+|ACM_\w+_fnc_\w+)',source))
    keep={'ACME_fnc_clinicalFields','ACME_fnc_clinicalEpoch','ACME_fnc_setVarNet'}
    stubs=''.join(name+'={};' for name in sorted(calls-keep))
    execute(setup()+definitions()+stubs+'ACME_fnc_clinicalFields={'+boundary(read('clinicalFields'))+'};ACME_fnc_clinicalReset={'+boundary(source)+'};'+r'''
        [_a,"first"] call _emit;[_a] call _tick;
        _a setVariable ["ACME_clinicalEpoch",2];
        [_a,"finish"] call ACME_fnc_clinicalReset;
        {
            [isNil {_a getVariable _x},"full heal retained aspiration field "+_x] call _check;
        } forEach ["ACME_aspiration_State","ACME_aspiration_load","ACME_aspiration_edema","ACME_aspiration_injury","ACME_aspiration_RRDrive","ACME_aspiration_lastEmesisKey"];
    ''')


@pytest.mark.parametrize('value',['[7,"key",0.3,0.2]','[7,"key",2,0.2,1]','[7,"key",0.3,0.2,-1]','[7,"key",0.3,0.2,1.5]','[-1,"key",0.3,0.2,1]','[7,9,0.3,0.2,1]','"bad"'])
def test_actual_snapshot_validator_rejects_malformed_authority_before_any_patient_change(value):
    from test_b271_ptx_stability import execute as ptx_execute, restore_setup
    ptx_execute(restore_setup()+f'''
        private _before=[7,"known",0.4,0.1,3];_patient setVariable ["ACME_aspiration_State",_before];
        private _payload=[3,[["ACME_aspiration_State",[{value},true] call ACME_fnc_clinicalCodec]]];
        [!(([_payload] call ACME_fnc_clinicalValidate) select 0),"malformed authoritative tuple passed validator"] call _check;
        [_patient,_payload,7] call ACME_fnc_clinicalRestore;
        [(_patient getVariable "ACME_aspiration_State") isEqualTo _before,"rejected malformed snapshot changed patient"] call _check;
    ''')


def test_serial_creation_remains_representable_and_invalid_state_defers_without_publication():
    execute(setup()+r'''
        _a setVariable ["ACME_aspiration_State",[1,"known",0.2,0.1,16777216]];
        private _event=[_a,"make","large",1,4] call ACME_fnc_aspirationEventKey;
        [(_event select 4)>16777216 && {(_event select 4)==floor (_event select 4)},"large serial stopped advancing or became fractional"] call _check;
        _a setVariable ["ACME_aspiration_State",[1,"bad",0.2,0.1,1.5]];
        private _before=_writes;[_a] call _tick;
        [([_a] call ACME_fnc_aspirationState) isEqualTo [] && {_writes==_before},"malformed authority was reconstructed or published"] call _check;
    ''')


def test_actual_fluid_state_preserves_five_field_randomized_explicit_volume_and_native_volume():
    execute(setup()+'ACME_fnc_laryngoFluidState={'+boundary(read('laryngoFluidState'))+'};'+r'''
        _a setVariable ["ACM_airway_AirwayObstructionVomit_State",2];
        _a setVariable ["ACME_laryngo_emesis",["laryngoscopy",2,7,1,1]];
        [(([_a] call ACME_fnc_laryngoFluidState) select 2)==7,"five-field explicit receipt lost randomized visible volume"] call _check;
        _a setVariable ["ACME_laryngo_emesis",["ACME-native-vomit:1:20",2,2,1,2]];
        [(([_a] call ACME_fnc_laryngoFluidState) select 2)==4,"native receipt changed native obstruction volume"] call _check;
    ''')


@pytest.mark.parametrize('order',['mirrors_first','receipt_first','state_last'])
def test_first_native_obstruction_packets_wait_for_canonical_episode_receipt(order):
    script=r'''private _neutral=[1,"",0,0,0];private _event=["ACME-native-vomit:1:10",1,2,1,1];'''
    if order!='state_last': script+='_a setVariable ["ACME_aspiration_State",_neutral];'
    if order=='receipt_first': script+='_a setVariable ["ACME_laryngo_emesis",_event];[_a] call _tick;'
    script+=r'''
        _a setVariable ["ACME_nativeVomitActive",true];_a setVariable ["ACM_airway_AirwayObstructionVomit_State",1];
        _a setVariable ["ACM_airway_AirwayObstructionVomit_GracePeriod",10];[_a] call _tick;
    '''
    if order!='receipt_first': script+='[count _logs==0,"native mirrors fabricated unreceipted aspiration"] call _check;_a setVariable ["ACME_laryngo_emesis",_event];[_a] call _tick;'
    if order=='state_last': script+='[count _logs==0,"receipt ahead of initial authority fabricated injury"] call _check;_a setVariable ["ACME_aspiration_State",_neutral];[_a] call _tick;'
    execute(setup()+script+r'''
        private _state=+(_a getVariable "ACME_aspiration_State");[_a] call _tick;
        [count _logs==1 && {(_state select 4)==1} && {abs ((_state select 2)-0.097142857)<0.00001},"first native episode counted other than once"] call _check;
        _a setVariable ["ACME_laryngo_emesis",[]];_a setVariable ["ACM_airway_AirwayObstructionVomit_GracePeriod",20];[_a] call _tick;
        [(_a getVariable "ACME_aspiration_State") isEqualTo _state && {count _logs==1},"clearing emesis/Grace before zero obstruction fabricated injury"] call _check;
    ''')


def test_actual_native_recovery_position_emesis_retains_reduced_aspiration_without_obstruction():
    execute(setup()+native_producer_definition()+r'''
        private _handler=[];private _nativeSounds=0;
        CBA_fnc_addPerFrameHandler={_handler=_this;0};CBA_fnc_removePerFrameHandler={};
        ACM_circulation_fnc_getNauseaMedicationEffects={0};ACM_airway_airwayObstructionVomitChance=1;
        _a setVariable ["ACE_isUnconscious",true];_a setVariable ["ACM_airway_AirwayObstructionVomit_Count",3];
        _a setVariable ["ACM_airway_RecoveryPosition_State",true];
        [_a] call ACM_airway_fnc_handleAirwayObstruction_Vomit;
        CBA_missionTime=40;[_handler select 2,0] call (_handler select 0);[_a] call _tick;
        private _state=_a getVariable "ACME_aspiration_State";
        [(_a getVariable ["ACM_airway_AirwayObstructionVomit_State",0])==0,"native recovery position acquired obstruction"] call _check;
        [(_state select 4)==1 && {abs ((_state select 2)-0.097142857*0.35)<0.00001} && {count _logs==1},"protected real emesis lost its reduced aspiration"] call _check;
        [(_a getVariable "ACM_airway_AirwayObstructionVomit_Count")==2 && {_nativeSounds==1},"protected native episode changed stomach/sound behavior"] call _check;
    ''')



def test_actual_megacode_reset_clears_injury_but_retains_same_epoch_receipt_against_late_packets():
    source=read('megacodeResetUnit')
    calls=set(re.findall(r'call (ACME_fnc_\w+|ACM_\w+_fnc_\w+|ace_\w+_fnc_\w+)',source))
    keep={'ACME_fnc_aspirationState','ACME_fnc_clinicalEpoch','ACM_core_fnc_setTargetVitalsState'}
    stubs=''.join(name+'={};' for name in sorted(calls-keep))
    execute(setup()+stubs+'ACME_fnc_megacodeResetUnit={'+boundary(source)+'};'+r'''
        ACM_core_fnc_setTargetVitalsState={params ["_u","_rows"];{if ((_x select 0)=="respirationRate") then {_u setVariable ["ACM_core_TargetVitals_RespirationRate",_x select 1]}} forEach _rows;};
        private _old=[_a,"before-reset"] call _emit;[_a] call _tick;
        [_a] call ACME_fnc_megacodeResetUnit;
        private _state=+(_a getVariable "ACME_aspiration_State");
        [(_state select 2)==0 && {(_state select 3)==0} && {(_state select 4)==1},"dummy reset lost receipt or retained lung injury"] call _check;
        _a setVariable ["ACME_laryngo_emesis",_old];[_a] call _tick;
        [(_a getVariable "ACME_aspiration_State") isEqualTo _state && {count _logs==1},"late pre-dummy-reset event recreated injury"] call _check;
        [_a,"after-reset"] call _emit;[_a] call _tick;
        [((_a getVariable "ACME_aspiration_State") select 4)==2 && {count _logs==2},"dummy reset blocked genuine new emesis"] call _check;
    ''')



def _empty_restore_continuation_case(mutation=False):
    from test_b271_ptx_stability import execute as ptx_execute, restore_setup
    source=read('clinicalRestore')
    if mutation:
        source=source.replace('    [_patient] call ACME_fnc_ownerRegister;', '    [_patient,_payload] call ACME_fnc_aspirationRestore;\n    [_patient] call ACME_fnc_ownerRegister;',1)
    ptx_execute(restore_setup()+'ACME_fnc_clinicalRestore={'+boundary(source)+'};'+r'''
        private _state=[7,"explicit:loaded:1:5",0.4,0.2,5];
        _patient setVariable ["ACME_aspiration_State",_state];
        _patient setVariable ["ACME_aspiration_load",0.4];_patient setVariable ["ACME_aspiration_edema",0.2];
        _patient setVariable ["ACME_aspiration_RRDrive",5.6];
        _patient setVariable ["ACME_laryngo_emesis",["loaded",1,4,7,5]];
        _patient setVariable ["ACM_core_TargetVitals_RespirationRate",20];
        [_patient,[],7] call ACME_fnc_clinicalRestore;
        [(_patient getVariable "ACME_aspiration_State") isEqualTo _state,
            "empty continuation erased already loaded/current aspiration authority"] call _check;
        [(_patient getVariable "ACME_aspiration_load")==0.4 && {(_patient getVariable "ACME_aspiration_edema")==0.2}
            && {(_patient getVariable "ACME_aspiration_RRDrive")==5.6},"empty continuation reran payload migration or changed mirrors"] call _check;
        [(_patient getVariable "ACM_core_TargetVitals_RespirationRate")==20,"empty continuation changed native baseline"] call _check;
    ''')


def test_actual_empty_restore_continuation_preserves_already_loaded_injury_receipt_and_mirrors():
    _empty_restore_continuation_case()


def test_semantic_mutation_empty_continuation_reset_is_rejected():
    with pytest.raises(AssertionError,match="empty continuation erased already loaded/current aspiration authority"): _empty_restore_continuation_case(True)



def test_actual_fluid_reader_keeps_legacy_numeric_identity_safe_without_string_prefix_assumption():
    execute(setup()+'ACME_fnc_laryngoFluidState={'+boundary(read('laryngoFluidState'))+'};'+r'''
        _a setVariable ["ACM_airway_AirwayObstructionVomit_State",2];
        _a setVariable ["ACME_laryngo_emesis",[42,2,7]];
        [(([_a] call ACME_fnc_laryngoFluidState) select 2)==7,"legacy visible-fluid identity became a string-only native prefix error"] call _check;
    ''')



def test_actual_legacy_numeric_episode_applies_once_across_suction_and_obstruction_decay():
    suction=(ROOT/'addons/airway/functions/fnc_handleSuctionLocal.sqf').read_text()
    execute(setup()+'ACM_airway_fnc_handleSuctionLocal={'+boundary(suction,'airway')+'};'+r'''
        ACM_airway_fnc_clearAirwayCheckedTime={};
        _a setVariable ["ACME_laryngo_emesis",[7,1,4]];_a setVariable ["ACM_airway_AirwayObstructionVomit_State",4];
        [_a] call _tick;private _state=+(_a getVariable "ACME_aspiration_State");
        [(_state select 1)=="explicit:7:1:0" && {abs ((_state select 2)-0.171428571)<0.00001} && {count _logs==1},"legacy numeric identity silently lost real injury"] call _check;
        _a setVariable ["ACM_airway_AirwayObstructionVomit_State",3];[_a] call _tick;
        [_a] call ACM_airway_fnc_handleSuctionLocal;[_a] call _tick;
        [(_a getVariable "ACME_aspiration_State") isEqualTo _state && {count _logs==1},"legacy numeric episode replayed on decay/suction"] call _check;
    ''')


def test_actual_legacy_numeric_restore_migration_retains_known_burden_and_marks_stable_receipt():
    from test_b271_ptx_stability import execute as ptx_execute, restore_setup
    ptx_execute(restore_setup()+r'''
        _patient setVariable ["ACME_laryngo_emesis",[7,1,4]];
        [_patient,[3,[["ACME_aspiration_load",["V",0.3]],["ACME_aspiration_edema",["V",0.2]]]],7] call ACME_fnc_clinicalRestore;
        private _state=_patient getVariable "ACME_aspiration_State";
        [(_state select 1)=="explicit:7:1:0" && {(_state select 2)==0.3} && {(_state select 3)==0.2},"numeric legacy restore lost burden or guessed a new gain"] call _check;
    ''')
