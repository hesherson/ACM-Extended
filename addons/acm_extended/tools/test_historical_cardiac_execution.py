"""Batch 2: execute the current cardiac boundaries, not obsolete inline text.

Actual SQF is retained. Arma objects/network/UI, CBA callbacks and unsupported
finite-input/linearConversion primitives are explicit stand-ins. This is not a
live monitor, physiology calibration or dedicated-server simulation.
"""
from pathlib import Path
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute

F = ROOT / 'addons/acm_extended/functions'
C = ROOT / 'addons/circulation/functions'


def code(text, component='circulation'):
    # SQF-VM returns nil for the missing typed B279 marker on legacy rows.
    # Preserve Arma's empty-string default without changing a present marker
    # or the physical possession/canonical-claim branch it selects.
    text = text.replace('param [13,"",[""]]', 'param [13,""]')
    fields = {
        'IN_CRDC_ARRST': ('ace_medical_inCardiacArrest', 'false'),
        'GET_CIRCULATIONSTATE': ('ACM_circulation_CirculationState', 'true'),
        'GET_BLOOD_VOLUME': ('ace_medical_bloodVolume', '6'),
        'GET_OXYGEN': ('ace_medical_spo2', '99'),
        'IN_CRITICAL_STATE': ('ACM_core_CriticalVitals_State', 'false'),
    }
    for macro, (field, default) in fields.items():
        text = re.sub(r'\b'+macro+r'\((\w+)\)', lambda m: f'({m[1]} getVariable ["{field}",{default}])', text)
    text = re.sub(r'GET_BLOOD_PRESSURE\((\w+)\)', r'([\1] call ace_medical_status_fnc_getBloodPressure)', text)
    text = text.replace('local _patient', '_patientLocal')
    text = text.replace('owner _patient', '_ownerNum')
    text = text.replace(', _public]', ']')
    # Only finite numeric inputs are used; nonfinite rejection is not claimed.
    text = re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', text)
    ts = lex(text); pairs = matching(ts); edits = []
    for i, t in enumerate(ts[:-1]):
        if t.kind == 'ident' and t.value == 'linearConversion':
            assert ts[i+1].value == '[' and i+1 in pairs
            j = pairs[i+1]
            edits.append((t.offset, ts[j].offset+1, '('+text[ts[i+1].offset:ts[j].offset+1]+' call _linear)'))
    for a,b,v in reversed(edits): text = text[:a]+v+text[b:]
    return adapt(text, component)


def function(name, component='circulation', extended=False):
    path = (F / ('fn_'+name+'.sqf')) if extended else (ROOT/'addons'/component/'functions'/('fnc_'+name+'.sqf'))
    namespace = 'ACME' if extended else 'ACM_'+component
    return namespace+'_fnc_'+name+' = {'+code(path.read_text(),component)+'};\n'


def setup():
    # Pin the constants to their checked-in definitions rather than inventing
    # test thresholds. Complex macros are field reads adapted explicitly above.
    headers = (ROOT/'addons/main/script_macros.hpp').read_text() + (ROOT/'include/z/ace/addons/medical_engine/script_macros_medical.hpp').read_text()
    constants = ''
    for name in ['ACM_REVERSIBLE_CA_BLOODVOLUME','ACM_OXYGEN_HYPOXIA','ACM_TENSIONHEMOTHORAX_THRESHOLD','BLOOD_VOLUME_CLASS_4_HEMORRHAGE']:
        values = re.findall(r'^#define\s+'+name+r'\s+([0-9.]+)\b', headers, re.M)
        assert len(values)==1, (name, values)
        constants += name+' = '+values[0]+';\n'
    proximity = (F/'fn_patientInteractionDistance.sqf').read_text()
    proximity = proximity.replace('objectParent _medic', 'objNull').replace('objectParent _patient', 'objNull')
    proximity = proximity.replace('_medic distance _patient', '_distance')
    return 'ACME_fnc_patientInteractionDistance={' + adapt(proximity) + '};' + constants + '''
        private _patientLocal=true;
        private _linear={params ["_lo","_hi","_x","_a","_b","_clamp"];
            private _f=(_x-_lo)/(_hi-_lo); if (_clamp) then {_f=(_f max 0) min 1;}; _a+(_f*(_b-_a))};
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _pressure=[80,120];
        private _recentShock=false;
        private _rhythm=0;
        private _tourniquet=false;
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",1]};
        ace_medical_status_fnc_getBloodPressure={_pressure};
        ACM_circulation_fnc_recentAEDShock={_recentShock};
        ACME_fnc_rhythmGet={_rhythm};
        ace_medical_treatment_fnc_hasTourniquetAppliedTo={_tourniquet};
        _patient setVariable ["ace_medical_heartRate",80];
        _patient setVariable ["ace_medical_bloodVolume",6];
        _patient setVariable ["ace_medical_spo2",99];
        _patient setVariable ["ACM_circulation_CirculationState",true];
    '''


def pulse_setup():
    return setup()+function('hasPulse')+function('aajtOccludes',extended=True)+function('pulsePerfusionProfile',extended=True)


# The AAJT helper deliberately accepts numeric body indices. The public pulse
# profile accepts names and must convert at its own API boundary.
@pytest.mark.parametrize('placement,side,occluded',[
    ('none','',[]),('zone3','',['leftleg','rightleg']),
    ('inguinal','leftleg',['leftleg']),('inguinal','rightleg',['rightleg']),
    ('axillaleft','',['leftarm']),('axillaright','',['rightarm']),
])
def test_aajt_pulse_occlusion_is_site_specific(placement,side,occluded):
    execute(pulse_setup()+f'_patient setVariable ["ACME_AAJT_{placement}",true]; _patient setVariable ["ACME_AAJT_inguinalSide","{side}"];'+
        'private _blocked='+str(occluded).replace("'",'"')+';'+'''
        {
            private _result=[_patient,_x] call ACME_fnc_pulsePerfusionProfile;
            private _expected=!((toLower _x) in _blocked);
            [(_result select 0) isEqualTo _expected,"AAJT site palpability mismatch: "+_x] call _check;
            [(_result select 1)==80,"occlusion changed electrical HR"] call _check;
            if (!_expected) then {[(_result select 2)==0 && {(_result select 4)=="absent"},"occluded limb has mechanical pulse"] call _check;};
        } forEach ["Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"];
        [(_patient getVariable ["ace_medical_heartRate",0])==80,"pulse read changed physiology"] call _check;
    ''')


def test_pulse_restores_when_the_aajt_is_removed_but_not_with_a_tourniquet():
    execute(pulse_setup()+'''
        _patient setVariable ["ACME_AAJT_zone3",true];
        [!(([_patient,"LeftLeg"] call ACME_fnc_pulsePerfusionProfile) select 0),"zone3 did not block"] call _check;
        _patient setVariable ["ACME_AAJT_zone3",false];
        [([_patient,"LeftLeg"] call ACME_fnc_pulsePerfusionProfile) select 0,"removal did not restore"] call _check;
        _tourniquet=true;
        [!(([_patient,"LeftLeg"] call ACME_fnc_pulsePerfusionProfile) select 0),"AAJT removal bypassed conventional tourniquet"] call _check;
    ''')


@pytest.mark.parametrize('blocker',['_patientAlive=false;', '_recentShock=true;',
    '_patient setVariable ["ace_medical_inCardiacArrest",true];',
    '_pressure=[20,40];', '_patient setVariable ["ACM_circulation_CirculationState",false];'])
def test_aajt_fix_does_not_override_other_pulse_blockers(blocker):
    execute(pulse_setup()+blocker+'''
        { [!(([_patient,_x] call ACME_fnc_pulsePerfusionProfile) select 0),"other pulse blocker bypassed"] call _check; }
        forEach ["Head","LeftArm","LeftLeg"];
    ''')


def rosc_setup():
    update=(C/'fnc_updateCirculationState.sqf').read_text().replace('createHashMap','missionNamespace').replace('_cs getOrDefault','_cs getVariable')
    return setup()+'ACM_circulation_fnc_updateCirculationState={'+code(update)+'};'+function('roscEligibility')+function('attemptROSC')+'''
        ACM_circulation_Hardcore_PostCardiacArrest=false;
        private _successes=0; private _fallbacks=0;
        CBA_fnc_localEvent={
            if ((_this select 0)=="ace_medical_CPRSucceeded") then {_successes=_successes+1; (_this select 1) setVariable ["ace_medical_inCardiacArrest",false];};
            if ((_this select 0)=="ACM_circulation_handleReversibleCardiacArrest") then {_fallbacks=_fallbacks+1;};
        };
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        _patient setVariable ["ACM_circulation_CardiacArrest_Time",2];
        missionNamespace setVariable ["ACME_hcEff_rhythm",true];
        missionNamespace setVariable ["ACME_sys_rhythm",true];
    '''


@pytest.mark.parametrize('volume,expected',[(3.5,False),(4.19,False),(4.2,False),(4.2001,True),(6,True)])
def test_rosc_requires_strict_native_blood_volume_gate(volume,expected):
    execute(rosc_setup()+f'_patient setVariable ["ace_medical_bloodVolume",{volume}];'+'''
        private _result=[_patient] call ACM_circulation_fnc_attemptROSC;
    '''+f'[_result isEqualTo {str(expected).lower()},"volume gate mismatch"] call _check;'+
        f'[_successes=={int(expected)} && {{_fallbacks=={int(not expected)}}},"wrong transition"] call _check;')


@pytest.mark.parametrize('blocker,reason',[
    ('_patient setVariable ["ace_medical_spo2",66];','HYPOXIA'),
    ('_patient setVariable ["ACM_breathing_TensionPneumothorax_State",true];','TENSION PNEUMOTHORAX'),
    ('_patient setVariable ["ACM_breathing_Hemothorax_Fluid",1.3];','HEMOTHORAX'),
    ('_patient setVariable ["ACME_hypo_temp",29];','HYPOTHERMIA'),
    ('missionNamespace setVariable ["paCO2",85];','ACIDOSIS'),
    ('_patient setVariable ["ACME_lidoTox_arrestFired",true];','LA TOXICITY'),
])
def test_rosc_composes_native_and_extended_reversible_causes(blocker,reason):
    execute(rosc_setup()+blocker+'''
        private _result=[_patient] call ACM_circulation_fnc_attemptROSC;
        [!_result && {_successes==0} && {_fallbacks==1},"ROSC bypassed reversible cause"] call _check;
    '''+f'[(_patient getVariable ["ACME_rosc_lastBlockedReason",""])=="{reason}","wrong reason"] call _check;')


@pytest.mark.parametrize('blocker',['_patientLocal=false;','_patientAlive=false;','_patient setVariable ["ace_medical_inCardiacArrest",false];'])
def test_rosc_requires_live_local_arrested_patient(blocker):
    execute(rosc_setup()+blocker+'''
        [!([_patient] call ACM_circulation_fnc_attemptROSC),"invalid ROSC accepted"] call _check;
        [_successes==0 && {_fallbacks==0},"invalid ROSC emitted a transition"] call _check;
    ''')


def test_extended_rosc_vetoes_do_not_disable_perfusion_outside_arrest():
    execute(rosc_setup()+'''
        _patient setVariable ["ace_medical_inCardiacArrest",false];
        _patient setVariable ["ACME_hypo_temp",28];
        _patient setVariable ["ACME_lidoTox_arrestFired",true];
        missionNamespace setVariable ["paCO2",100];
        [_patient] call ACM_circulation_fnc_updateCirculationState;
        [_patient getVariable ["ACM_circulation_CirculationState",false],"ROSC-only veto removed perfusion"] call _check;
        _patient setVariable ["ace_medical_spo2",66];
        [_patient] call ACM_circulation_fnc_updateCirculationState;
        [!(_patient getVariable ["ACM_circulation_CirculationState",true]),"native hypoxia veto lost"] call _check;
    ''')


def test_successful_rosc_does_not_fire_twice_for_the_same_arrest():
    execute(rosc_setup()+'''
        ACM_circulation_Hardcore_PostCardiacArrest=true;
        [[_patient] call ACM_circulation_fnc_attemptROSC,"first ROSC failed"] call _check;
        [!([_patient] call ACM_circulation_fnc_attemptROSC),"second ROSC accepted"] call _check;
        [_successes==1 && {_fallbacks==0},"duplicate cardiac transition"] call _check;
        [isNil {_patient getVariable "ACM_circulation_CardiacArrest_Time"},"arrest clock retained"] call _check;
        [_patient getVariable ["ACM_circulation_Hardcore_PostCardiacArrest",false],"postarrest flag omitted"] call _check;
    ''')


@pytest.mark.parametrize('allowed,epoch',[(False,1),(True,1),(True,2)])
def test_shock_rosc_consumes_same_gate_and_rejects_old_episode(allowed,epoch):
    execute(rosc_setup()+function('shockROSC',extended=True)+'''
        private _released=0; private _sinus=0;
        ACME_fnc_rhythmRelease={_released=_released+1;};
        ACME_fnc_rhythmSet={_sinus=_sinus+1;};
        ACME_fnc_setVarNet={params ["_p","_k","_v"]; _p setVariable [_k,_v];};
    '''+('' if allowed else '_patient setVariable ["ace_medical_bloodVolume",3];')+
        f'private _result=[_patient,{epoch}] call ACME_fnc_shockROSC;'+
        f'[_result isEqualTo {str(allowed and epoch==1).lower()},"incorrect shock result"] call _check;'+
        f'[_released=={int(allowed and epoch==1)} && {{_sinus=={int(allowed and epoch==1)}}},"shock cleared rhythm without ROSC"] call _check;')


def braced(text, opening):
    ts=lex(text); pairs=matching(ts)
    starts=[i for i,t in enumerate(ts) if t.offset==opening and t.value=='{']
    assert len(starts)==1
    return text[opening:ts[pairs[starts[0]]].offset+1]


def test_rosc_event_clears_banked_paralytic_and_ventilator_stress():
    event=(F/'fn_registerRoscBreathingRuntime.sqf').read_text()
    event=re.sub(r'private _targets = allPlayers inAreaArray \[[^;]+;', 'private _targets = [];',event)
    execute(setup()+function('rocStressStateCommit',extended=True)+'''
        ACM_circulation_fnc_setRuntimeState={params ["_p","_changes"]; {_p setVariable ["ACM_circulation_ROSC_Time",_x select 1];} forEach _changes;};
        ACM_core_fnc_setAceMedicalState={};
        _patient setVariable ["ACM_circulation_ROSC_Time",CBA_missionTime];
        _patient setVariable ["ACME_roc_awakeDwell",55];
        _patient setVariable ["ACME_roc_awakeResistAdd",20];
        _patient setVariable ["ACME_hrDrive_roc",138];
        _patient setVariable ["ACME_roc_awarenessEvent",true];
        _patient setVariable ["ACME_vent_fightHRAdjust",18];
        _patient setVariable ["ACME_vent_fightResistAdjust",9];
    '''+code(event)+'''
        [_patient] call _track;
        [(_patient getVariable ["ACME_roc_postROSCGraceUntil",0]) == CBA_missionTime+15,"missing ROSC grace"] call _check;
        [(_patient getVariable ["ACME_roc_awakeDwell",-1])==0,"banked awareness dwell"] call _check;
        [(_patient getVariable ["ACME_roc_awakeResistAdd",-1])==0,"banked resistance"] call _check;
        [(_patient getVariable ["ACME_hrDrive_roc",0]) == -1,"banked HR drive"] call _check;
        [(_patient getVariable ["ACME_vent_fightHRAdjust",-1])==0 && {(_patient getVariable ["ACME_vent_fightResistAdjust",-1])==0},"banked vent stress"] call _check;
        [_patient getVariable ["ACME_roc_awarenessEvent",false],"ROSC erased historical awareness event"] call _check;
        [(_patient getVariable ["ACM_circulation_ROSC_Time",0]) < CBA_missionTime,"zero ROSC elapsed divisor"] call _check;
    ''')


@pytest.mark.parametrize('native',[-1,1,2,3,4])
def test_threshold_observer_never_clears_native_critical_rhythm_without_treatment(native):
    text=(F/'fn_rhythmThresholdTick.sqf').read_text().replace('forEach allUnits;','forEach [_patient];')
    text=text.replace('alive _u','_patientAlive').replace('local _u','_patientLocal')
    # SQF-VM lacks continue; for this single-patient execution, leave a named
    # enclosing scope instead. Conditions/writes and original branch order remain.
    for token in reversed(lex(text)):
        if token.kind=='ident' and token.value=='continue':
            text=text[:token.offset]+'breakOut "onePatient"'+text[token.offset+len(token.value):]
    text='scopeName "onePatient";'+text
    execute(setup()+'''
        private _changed=0; private _arrests=0; private _released=0;
        ACME_fnc_rhythmGet={(_this select 0) getVariable ["ACM_circulation_Cardiac_RhythmState",0]};
        ACME_fnc_rhythmRelease={_released=_released+1;};
        ACME_fnc_rhythmSet={_changed=_changed+1;};
        ACME_fnc_arrestLocal={_arrests=_arrests+1;};
        ACME_fnc_rhythmNativeHoldCommit={};
        ACME_fnc_rhythmNativeHighHRFloorCommit={};
    '''+f'_patient setVariable ["ACM_circulation_Cardiac_RhythmState",{native}];'+
        'private _observe={'+code(text)+'}; call _observe;'+'''
        [_changed==0 && {_arrests==0},"threshold tick overrode native rhythm"] call _check;
    ''')


@pytest.mark.parametrize('visual',[-1,0,1,2,3,4,5])
def test_custom_ecg_proxy_respects_native_visual_precedence(visual):
    text=(C/'fnc_displayAEDMonitor_generateEKG.sqf').read_text()
    a=text.index('private _target = '); b=text.index('// ACME custom rhythms keep',a)
    expected=visual if visual in [-1,1,2] else 104
    execute(setup()+'''
        missionNamespace setVariable ["ACM_circulation_AED_Monitor_Target",_patient];
        ACME_fnc_rhythmGet={104};
    '''+f'private _visual={visual};'+
        'private _select={params ["_rhythm"];'+code(text[a:b])+'_rhythm};'+
        f'private _result=[_visual] call _select; [_result=={expected},"proxy overrode native visual priority"] call _check;')


def test_rhythm_write_invalidates_both_monitor_caches():
    text=(F/'fn_rhythmSet.sqf').read_text()
    a=text.index('private _forceMonitorRefresh = ')+len('private _forceMonitorRefresh = ')
    body=braced(text,a)
    execute(setup()+'''
        private _writes=[];
        ACM_circulation_fnc_setRuntimeState={_writes append (_this select 1);};
    '''+'private _refresh='+code(body)+'; [_patient] call _refresh;'+'''
        [_writes isEqualTo [["aedPadsLastSync",-1],["aedEkgRhythm",-99]],"rhythm cache not invalidated"] call _check;
    ''')
    writer=(C/'fnc_setRuntimeState.sqf').read_text()
    assert '[QGVAR(AED_EKGRhythm), _value]' in writer
    assert '[QGVAR(AED_Pads_LastSync), _value]' in writer
    monitor=(C/'fnc_displayAEDMonitor.sqf').read_text()
    assert 'QGVAR(AED_EKGRhythm)' in monitor
    assert 'call FUNC(displayAEDMonitor_generateEKG)' in monitor


def test_mature_torsades_arrest_request_is_rate_limited_and_stops_after_acknowledgement():
    text=(F/'fn_rhythmTick.sqf').read_text()
    a=text.index('\n    if (_code == 102) then {')
    body=braced(text,text.index('{',a))
    execute(setup()+'''
        private _u=_patient; private _code=102; private _torsadesNonPerf=false;
        private _torsadesPerfusion=1; private _curRhythm=0; private _requests=0;
        ACME_fnc_setVarNet={params ["_p","_k","_v"]; _p setVariable [_k,_v];};
        ACME_fnc_arrestLocal={_requests=_requests+1;};
        ACME_fnc_rhythmNative={3};
        _patient setVariable ["ACME_rhythm_torsadesStart",0];
    '''+'private _advance='+code(body)+';'+'''
        CBA_missionTime=5; call _advance;
        [_requests==0,"early torsades forced arrest"] call _check;
        CBA_missionTime=16; call _advance;
        [_requests==1,"mature torsades failed to request"] call _check;
        CBA_missionTime=16.5; call _advance;
        [_requests==1,"torsades request flooded"] call _check;
        CBA_missionTime=16.75; call _advance;
        [_requests==2,"missing retry after no acknowledgement"] call _check;
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        CBA_missionTime=18; call _advance;
        [_requests==2,"request continued after arrest acknowledgement"] call _check;
    ''')


@pytest.mark.parametrize('part,expected',[
    ('Body',['leftleg','rightleg']),('LeftLeg',['leftleg']),('RightLeg',['rightleg']),
    ('LeftArm',['leftarm']),('RightArm',['rightarm']),
])
def test_aajt_application_routes_only_the_selected_limbs(part,expected):
    apply=function('aajtApply',extended=True).replace('daytime','12')
    execute(setup()+function('aajtOccludes',extended=True)+function('aajtStateCommit',extended=True)+apply+'''
        private _limbs=[];
        ACME_fnc_aajtSetLegTQ={_limbs pushBack (_this select 1);};
        ACME_fnc_aajtPainTick={}; ACME_fnc_aajtDownedTick={}; ACME_fnc_netNotice={};
    '''+f'private _result=[_medic,_patient,"{part}"] call ACME_fnc_aajtApply;'+
        f'private _expected={str(expected).replace(chr(39),chr(34))};'+'''
        [_result && {_limbs isEqualTo _expected},"AAJT application targeted wrong limbs"] call _check;
        {
            private _name=["head","body","leftarm","rightarm","leftleg","rightleg"] select _x;
            [([_patient,_x] call ACME_fnc_aajtOccludes) isEqualTo (_name in _expected),"placement/occlusion disagree"] call _check;
        } forEach [0,1,2,3,4,5];
    ''')


@pytest.mark.parametrize('part,zone3,tourniquet,expected',[
    ('Head',True,False,True),('LeftArm',True,False,True),
    ('LeftLeg',True,False,False),('RightLeg',True,False,False),
    ('LeftArm',False,True,False),('RightLeg',False,True,False),
    ('LeftLeg',False,False,True),
])
def test_compression_generated_pulses_do_not_bypass_proximal_occlusion(part,zone3,tourniquet,expected):
    text=(ROOT/'addons/core/overrides/fnc_checkPulseLocal.sqf').read_text()
    text=text.replace('alive _cprProvider','true').replace('localize _k','_k')
    # VM lacks triangular random; select its mode without changing the pulse gate.
    text=text.replace('random [100,110,120]','([100,110,120] select 1)')
    text=text.replace('localize "STR_ACE_medical_treatment_Check_Pulse_Log"','"pulse log"')
    execute(pulse_setup()+'''
        ACME_fnc_clinTerm={""}; ace_medical_treatment_fnc_isMedic={true};
    '''+f'_patient setVariable ["ACME_AAJT_zone3",{str(zone3).lower()}]; _tourniquet={str(tourniquet).lower()};'+
        'private _checkPulse={'+code(text)+'};'+f'[_medic,_patient,"{part}"] call _checkPulse;'+'''
        private _message=(_events select 0) select 1;
        private _rate=(_message select 0) select 2;
    '''+f'[(_rate>0) isEqualTo {str(expected).lower()},"CPR pulse bypassed occlusion"] call _check;')
