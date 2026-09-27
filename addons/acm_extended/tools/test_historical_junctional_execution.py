"""Batch 7: existing junctional calibration, rate worker and evidence presentation.

No independent clinical model replaces the worker. Hash-map iteration is adapted
for this VM to keys plus the corresponding value, preserving SQF's _x/_y scope.
Engine sound, scheduling and controls are mocked; actual network/rendering and
full native blood-volume integration are not simulated.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, execute
from test_historical_cardiac_execution import code as cardiac_code, setup as cardiac_setup
from test_historical_procedure_trays import ui_code, controls

F=ROOT/'addons/acm_extended/functions'
PARTS=['leftarm','rightarm','leftleg','rightleg']


def map_iteration(text):
    ts=lex(text);pairs=matching(ts);reverse={v:k for k,v in pairs.items()};edits=[]
    for i,t in enumerate(ts[:-1]):
        if t.kind=='ident' and t.value=='forEach' and ts[i+1].value=='_activeBandages':
            assert ts[i-1].value=='}' and i-1 in reverse
            opening=reverse[i-1]
            edits.append((ts[opening].offset+1,ts[opening].offset+1,'private _y=_activeBandages get _x;'))
            edits.append((ts[i+1].offset,ts[i+1].offset,'(keys '))
            edits.append((ts[i+1].offset+len(ts[i+1].value),ts[i+1].offset+len(ts[i+1].value),')'))
    for a,b,new in sorted(edits,reverse=True):text=text[:a]+new+text[b:]
    return text


def worker_setup():
    text=(F/'fn_junctionalStartBleed.sqf').read_text()
    text=text.replace('local _unit','_patientLocal').replace('alive _unit','_patientAlive').replace('serverTime','_serverTime')
    text=re.sub(r'\btime\b','CBA_missionTime',text)
    native = ''
    for name in ('bandageProgressStart','bandageProgressStop'):
        body=(ROOT/'addons/damage/functions'/('fnc_'+name+'.sqf')).read_text().replace('serverTime','_serverTime')
        native+='ACM_damage_fnc_'+name+'={'+cardiac_code(body,'damage')+'};'
    return cardiac_setup()+native+'''
        private _serverTime=10;
        ACME_fnc_aajtOccludes={false};
        ace_medical_status_fnc_updateWoundBloodLoss={};
        _patient setVariable ["ACME_SfxBusyUntil",1e9];
        _patient setVariable ["ACME_JuncLeakNext",1e9];
        missionNamespace setVariable ["ACME_junctionalCompDepth",0];
        missionNamespace setVariable ["ACME_junctionalBleedNorm",0.10];
        missionNamespace setVariable ["ACME_junctionalGauzeControl",0.50];
        missionNamespace setVariable ["ACME_junctionalGauzeDPControl",0];
        missionNamespace setVariable ["ACME_junctionalRefHR",80];
        missionNamespace setVariable ["ace_medical_bleedingCoefficient",1];
        private _runJunction={private _id=_patient getVariable ["ACME_juncPFH",-1];
            private _job=_handlers select _id;[_job select 1,_id] call (_job select 0);};
    '''+'ACME_fnc_junctionalStartBleed={'+cardiac_code(map_iteration(text))+'};'


@pytest.mark.parametrize('part',PARTS)
@pytest.mark.parametrize('fraction',[0.0,0.5,1.0])
def test_packing_progress_uses_wound_part_not_transaction_key(part,fraction):
    execute(worker_setup()+f'_patient setVariable ["ACME_Junc_{part}","open"]; _patient setVariable ["ACME_Junc_Packing_{part}",true];'+
        f'_patient setVariable ["ACME_Junc_PackStamp_{part}",0];'+
        f'_serverTime=0; [_patient,"{part.upper()}","ACME_PackJunctional",10,"provider:transaction"] call ACM_damage_fnc_bandageProgressStart;'+'''
        [_patient] call ACME_fnc_junctionalStartBleed;
    '''+f'_serverTime={fraction}*10; CBA_missionTime=_serverTime; call _runJunction;'+
        f'private _expected=0.10*(1-(0.50*{fraction}*{fraction}))*(0.095*80/60);'+'''
        [abs ((_patient getVariable ["ACME_junctionalBleedLPS",-1])-_expected)<0.000001,"packing did not apply existing progress curve"] call _check;
        [(_patient getVariable ["ace_medical_bloodVolume",0])==6,"rate worker directly drained blood volume"] call _check;
    '''+f'[(_patient getVariable ["ACME_Junc_{part}",""])=="open","partial progress permanently packed wound"] call _check;')


@pytest.mark.parametrize('recordpart,recordclass',[('rightleg','ACME_PackJunctional'),('leftarm','FieldDressing'),('leftarm','ACME_WrapJunctional')])
def test_other_limb_or_other_treatment_progress_cannot_control_this_open_junction(recordpart,recordclass):
    execute(worker_setup()+'''
        _patient setVariable ["ACME_Junc_leftarm","open"];
        _patient setVariable ["ACME_Junc_Packing_leftarm",true];
        _patient setVariable ["ACME_Junc_PackStamp_leftarm",0];
    '''+f'_patient setVariable ["ACM_damage_BandageProgress",createHashMapFromArray [["record",["{recordpart}",_medic,0,10,"{recordclass}"]]]];'+'''
        [_patient] call ACME_fnc_junctionalStartBleed; call _runJunction;
        [abs ((_patient getVariable ["ACME_junctionalBleedLPS",-1])-(0.10*0.095*80/60))<0.000001,"unrelated progress controlled wound"] call _check;
    ''')


def test_cancelled_packing_returns_to_open_rate_without_losing_wound_evidence():
    execute(worker_setup()+'''
        _patient setVariable ["ACME_Junc_leftarm","open"];
        _patient setVariable ["ACME_Junc_Packing_leftarm",true];
        _patient setVariable ["ACME_Junc_PackStamp_leftarm",0];
        _patient setVariable ["ACM_damage_BandageProgress",createHashMapFromArray [["record",["leftarm",0,0,10,"ACME_PackJunctional"]]]];
        [_patient] call ACME_fnc_junctionalStartBleed;
        _serverTime=5;CBA_missionTime=5;call _runJunction;
        private _during=_patient getVariable ["ACME_junctionalBleedLPS",-1];
        [_patient,"record"] call ACM_damage_fnc_bandageProgressStop;call _runJunction;
        private _after=_patient getVariable ["ACME_junctionalBleedLPS",-1];
        [_after>_during && {abs (_after-(0.10*0.095*80/60))<0.000001},"cancel retained temporary bleed control"] call _check;
        [(_patient getVariable ["ACME_Junc_leftarm",""])=="open","cancel lost evidence"] call _check;
    ''')


@pytest.mark.parametrize('state,multiplier',[('open',1),('packed',0.5),('wrapped',0),('xstat',0)])
def test_completed_wound_states_keep_existing_control_and_do_not_directly_drain_blood(state,multiplier):
    execute(worker_setup()+f'_patient setVariable ["ACME_Junc_leftarm","{state}"];'+'''
        _patient setVariable ["ACME_Junc_XStatAt_leftarm",0];
        [_patient] call ACME_fnc_junctionalStartBleed;
        _serverTime=30;CBA_missionTime=30;call _runJunction;
    '''+f'[abs ((_patient getVariable ["ACME_junctionalBleedLPS",-1])-(0.10*0.095*80/60*{multiplier}))<0.000001,"completed-state rate changed"] call _check;'+'''
        [(_patient getVariable ["ace_medical_bloodVolume",0])==6,"second blood volume integrator"] call _check;
    ''')


@pytest.mark.parametrize('hardcore',[False,True])
@pytest.mark.parametrize('multiplier',[0.5,1.0,2.0])
def test_junctional_difficulty_uses_current_base_and_multiplier_without_compounding(hardcore,multiplier):
    init=(F/'fn_initJunctionalConfig.sqf').read_text()
    apply=(F/'fn_applyHardcore.sqf').read_text()
    a=apply.index('if (ACME_hcEff_junc) then {');b=apply.index('// TBI.',a)
    # Execute the actual whole junctional difficulty branch, not a copied
    # formula. Other difficulty systems are outside this case's scope.
    execute(cardiac_setup()+cardiac_code(init)+'''
        ACME_hcBase_junctionalDPControl=ACME_junctionalDPControl;
        ACME_hcBase_junctionalGauzeControl=ACME_junctionalGauzeControl;
        ACME_hcBase_junctionalGauzeDPControl=ACME_junctionalGauzeDPControl;
        private _juncFreqMult=1;
    '''+f'ACME_hcEff_junc={str(hardcore).lower()};private _juncBleedMult={multiplier};'+
        'private _apply={'+cardiac_code(apply[a:b])+'};call _apply;call _apply;'+
        f'[abs (ACME_junctionalBleedNorm-({0.15 if hardcore else 0.10}*{multiplier}))<0.000001,"baseline/multiplier compounded"] call _check;'+'''
        ACME_hcEff_junc=false;call _apply;
        [abs (ACME_junctionalBleedNorm-(0.10*_juncBleedMult))<0.000001,"normal mode did not restore baseline"] call _check;
        [ACME_junctionalGauzeControl==0.50 && {ACME_junctionalGauzeDPControl==0},"normal completed packing controls changed"] call _check;
    ''')


def image_code(text):
    text=re.sub(r'_ctrlGroup controlsGroupCtrl (_\w+|\d+)',r'\1',text)
    text=re.sub(r'\(ctrlParent _ctrlGroup\) ctrlCreate \["RscPicture", (_\w+), _ctrlGroup\]',r'\1',text)
    text=text.replace('ctrlPosition _ref','[0,0,1,1]').replace('ctrlPosition _source','[0,0,1,1]')
    text=text.replace('ctrlText _source','"tourniquet"').replace('ctrlShown _source','false')
    text=text.replace('_x ctrlSetFade 0;','[_x,"ctrlSetFade",0] call _controlWrite;')
    return ui_code(text)


@pytest.mark.parametrize('state',['open','packed','xstat','wrapped',''])
@pytest.mark.parametrize('alive',[True,False])
def test_junctional_body_evidence_uses_current_layers_on_live_and_dead_patients(state,alive):
    # Large fixture control IDs need exact decimal keys; SQF-VM str rounds them.
    execute(controls().replace('(str _c)','(_c toFixed 0)')+f'_patientAlive={str(alive).lower()};'+
        'private _draw={'+image_code((F/'fn_updateJunctionalImage.sqf').read_text())+'};'+
        f'{{_patient setVariable ["ACME_Junc_"+_x,"{state}"];}} forEach ["leftarm","rightarm","leftleg","rightleg"];'+'''
        [uiNamespace,_patient] call _draw;
        for "_i" from 0 to 3 do {
            private _base=((7290004+_i) toFixed 0)+":ctrlShow";
            private _packed=((7290040+_i) toFixed 0)+":ctrlShow";
            private _wrap=((7290000+_i) toFixed 0)+":ctrlShow";
    '''+f'[(_controlValues get _base) isEqualTo {str(state in ("open","packed","xstat")).lower()},"base evidence incorrect"] call _check;'+
        f'[(_controlValues get _packed) isEqualTo {str(state=="packed").lower()},"gauze layer covered XStat incorrectly"] call _check;'+
        f'[(_controlValues get _wrap) isEqualTo {str(state=="wrapped").lower()},"wrap evidence incorrect"] call _check;'+'''
        };
        [count _events==0 && {count _moves==0},"evidence rendering mutated patient/workers"] call _check;
    ''')


@pytest.mark.parametrize('alive',[True,False])
@pytest.mark.parametrize('rebled',[True,False])
def test_junctional_injury_label_reads_frozen_state_without_advancing_rebleed(alive,rebled):
    body=(F/'fn_junctionalInjuryEntry.sqf').read_text()
    execute(cardiac_setup()+f'_patientAlive={str(alive).lower()};'+'''
        ACME_fnc_a11yColor={[1,1,1,1]};
        _patient setVariable ["ACME_Junc_leftleg","xstat"];
    '''+f'_patient setVariable ["ACME_Junc_XStatRebled_leftleg",{str(rebled).lower()}];'+
        'private _render={'+cardiac_code(body)+'};'+'''
        private _rows=[];CBA_missionTime=1e6;
        [objNull,_patient,4,_rows] call _render;
        [count _rows==1,"missing XStat evidence"] call _check;
    '''+f'[(((_rows select 0) select 0) find "REBLEEDING" >= 0) isEqualTo {str(alive and rebled).lower()},"wrong live rebleed label"] call _check;'+
        f'[(_patient getVariable ["ACME_Junc_XStatRebled_leftleg",false]) isEqualTo {str(rebled).lower()},"render advanced rebleed"] call _check;')
