"""Batch 11: native medication readers and admitted-exposure boundaries.

Execute checked-out SQF, not a Python pharmacology model. Objects/publication,
finite-input primitives, the scheduler interval and selected random outcomes are
explicit fixtures. This is gameplay regression coverage, not dosing guidance.
"""
import json
import re
import pytest
from source_scan import lex, matching
from medication_inventory import subtree
from test_menu_death_lifecycle import ROOT, execute
from test_historical_cardiac_execution import code as cardiac_code
from test_historical_vial_execution import map_defaults

F=ROOT/'addons/acm_extended/functions'
C=ROOT/'addons/circulation/functions'


def per_record_continue(text):
    """VM lacks continue: put an iteration-local named scope around its real loop.

    Only a single identified continue/loop pair is adapted in each source.
    Unrelated records skip to the NEXT record, not terminate the function.
    Reader tests put noise on both sides; catheter tests preserve other bags.
    """
    ts=lex(text);pairs=matching(ts);reverse={v:k for k,v in pairs.items()}
    continues=[t for t in ts if t.kind=='ident' and t.value=='continue']
    if not continues:return text
    loops=[i for i,t in enumerate(ts) if t.kind=='ident' and t.value=='forEach']
    assert len(continues)==1
    loops=[i for i in loops if ts[i-1].value=='}' and ts[reverse[i-1]].offset < continues[0].offset < ts[i-1].offset]
    assert len(loops)==1
    close=loops[0]-1;opening=reverse[close]
    assert ts[opening].value=='{' and ts[opening].offset < continues[0].offset < ts[close].offset
    edits=[(ts[opening].offset+1,ts[opening].offset+1,'call {scopeName "medicationRecord";'),
           (ts[close].offset,ts[close].offset,'};'),
           (continues[0].offset,continues[0].offset+8,'breakOut "medicationRecord"')]
    for a,b,v in sorted(edits,reverse=True):text=text[:a]+v+text[b:]
    return text


def code(text,component='circulation'):
    # These expansions are asserted against the checked-in macro definitions below.
    text=re.sub(r'^TRACE_\d+\([^\n]*\);\s*$', '', text, flags=re.M)
    text=text.replace('VAR_MEDICATIONS','"ace_medical_medications"')
    text=text.replace('local _target','_patientLocal')
    text=text.replace('HAS_AIRWAY_SPASM(_patient)','(_patient getVariable ["ACM_CBRN_AirwaySpasm",false])')
    text=re.sub(r'QGVAR_BUILDUP\((\w+)\)',lambda m:'"ACM_CBRN_'+m[1]+'_Buildup"',text)
    return map_defaults(cardiac_code(per_record_continue(text),component))


def function(name,component='circulation',extended=False,override=False):
    path=(F/('fn_'+name+'.sqf')) if extended else (ROOT/'addons'/component/('overrides' if override else 'functions')/('fnc_'+name+'.sqf'))
    prefix='ACME' if extended else 'ACM_'+component
    return prefix+'_fnc_'+name+'={'+code(path.read_text(),component)+'};'


def setup():
    headers=(ROOT/'addons/main/script_macros.hpp').read_text()
    constants=''
    for name in ('ACM_ROUTE_IM','ACM_ROUTE_IV','ACM_ROUTE_PO','ACM_ROUTE_INHALE'):
        values=re.findall(r'^#define\s+'+name+r'\s+(\d+)\b',headers,re.M)
        assert len(values)==1,(name,values)
        constants+=name+'='+values[0]+';'
    return constants+'''
        private _patientLocal=true;
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _linear={params ["_lo","_hi","_x","_a","_b",["_clamp",false]];
            private _f=(_x-_lo)/(_hi-_lo); if (_clamp) then {_f=(_f max 0) min 1;}; _a+(_f*(_b-_a))};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _record={params ["_name","_dose",["_route",1],["_uid","r"],["_part",2],["_added",80]];
            [_name,_added,10,100,0,0,0,_route,20,0,0,0,_dose,"",_part,_uid]};
        CBA_missionTime=100;
    '''+''.join(function(n) for n in ('getMedicationEffect','getCardiacMedicationEffects','getNauseaMedicationEffects'))+\
        function('medicationCountCompat',extended=True)+function('medicationAvailability',extended=True)+function('getMedicationCount','core',override=True)+'''
        ace_medical_status_fnc_getMedicationCount=ACM_core_fnc_getMedicationCount;
    '''


@pytest.mark.parametrize('med,route,key,weight,cap',[
    ('Morphine',0,'morphine',.3,.5),('Morphine_IV',1,'morphine',.6,.8),
    ('Fentanyl',0,'fentanyl',.3,.5),('Fentanyl_BUC',2,'fentanyl',.3,.5),
    ('Fentanyl_IV',1,'fentanyl',.6,.8),('Epinephrine_IV',1,'epinephrine',1.8,2),
    ('Amiodarone_IV',1,'amiodarone',1,2),('Lidocaine_IV',1,'lidocaine',1,1.5)])
@pytest.mark.parametrize('dose',[-1,0,.25,3])
def test_cardiac_reader_scales_admitted_dose_once_and_preserves_caps(med,route,key,weight,cap,dose):
    expected=min(max(dose,0)*weight,cap)
    execute(setup()+f'_patient setVariable ["ace_medical_medications",[["Foreign",99] call _record,["{med}",{dose},{route}] call _record,["Unrelated",99] call _record]];'+'''
        private _before=+(_patient getVariable ["ace_medical_medications",[]]);
        private _result=[_patient] call ACM_circulation_fnc_getCardiacMedicationEffects;
    '''+f'[abs ((_result get "{key}")-{expected})<0.00001,"dose was ignored or multiplied twice"] call _check;'+'''
        [count _result==5,"reader changed output shape"] call _check;
        [(_patient getVariable ["ace_medical_medications",[]]) isEqualTo _before,"effect read modified medications"] call _check;
    ''')


@pytest.mark.parametrize('med,threshold', [('Morphine_IV',.3),('Fentanyl_IV',.5),('Ketamine_IV',.3),('Lidocaine_IV',.6),('Amiodarone_IV',.5)])
@pytest.mark.parametrize('dose',[0,.2,.75,2])
def test_nausea_reader_uses_dose_thresholds_not_number_of_records(med,threshold,dose):
    value=max(0,(dose-threshold)/(1-threshold))
    expected=min(1.2,value if med=='Amiodarone_IV' else min(1,value))
    execute(setup()+f'_patient setVariable ["ace_medical_medications",[["Foreign",99] call _record,["{med}",{dose}] call _record,["Unrelated",99] call _record]];'+
        'private _result=[_patient] call ACM_circulation_fnc_getNauseaMedicationEffects;'+
        f'[abs (_result-{expected})<0.00001,"nausea dose scaling changed"] call _check;')


@pytest.mark.parametrize('dose,suppression',[(0,0),(.5,0),(1,.9),(3,.45)])
def test_ondansetron_keeps_current_dose_dependent_suppression(dose,suppression):
    execute(setup()+f'_patient setVariable ["ace_medical_medications",[["Morphine_IV",1] call _record,["Ondansetron_IV",{dose}] call _record]];'+
        'private _result=[_patient] call ACM_circulation_fnc_getNauseaMedicationEffects;'+
        f'[abs (_result-{1-suppression})<0.00001,"antiemetic effect changed"] call _check;')


@pytest.mark.parametrize('part,expected',[(-1,1.5),(2,1),(3,.5),(4,0)])
@pytest.mark.parametrize('raw',[False,True])
def test_native_medication_count_accepts_foreign_classes_and_preserves_site_filter(part,expected,raw):
    execute(setup()+'''
        _patient setVariable ["ace_medical_medications",[["OtherMod_Drug",1,1,"a",2] call _record,["OtherMod_Drug",.5,1,"b",3] call _record,["Other",99] call _record]];
    '''+f'private _n=[_patient,"OtherMod_Drug",{str(raw).lower()},{part}] call ace_medical_status_fnc_getMedicationCount;'+
        f'[abs (_n-{expected})<0.000001,"native count lost dose or body-site identity"] call _check;')


def test_bound_rocuronium_affects_effect_count_but_not_raw_admitted_count():
    execute(setup()+'''
        _patient setVariable ["ace_medical_medications",[["Rocuronium_IV",2,1,"roc"] call _record]];
        _patient setVariable ["ACME_sug_bindings",[["roc",1]]];
        private _raw=[_patient,"Rocuronium_IV",true] call ace_medical_status_fnc_getMedicationCount;
        private _effect=[_patient,"Rocuronium_IV",false] call ace_medical_status_fnc_getMedicationCount;
        [_raw==2 && {_effect==1},"raw count or bound fraction changed"] call _check;
        _patient setVariable ["ACME_sug_bindings",[["different-record",2]]];
        [[_patient,"Rocuronium_IV",false] call ace_medical_status_fnc_getMedicationCount==2,"unrelated binding affected record"] call _check;
    ''')


@pytest.mark.parametrize('raw',[False,True])
def test_onset_is_not_treated_as_full_effect_but_raw_exposure_is_retained(raw):
    execute(setup()+'''
        _patient setVariable ["ace_medical_medications",[["Morphine_IV",.5,1,"a",2,100] call _record]];
    '''+f'private _result=[_patient,"Morphine_IV",{str(raw).lower()}] call ace_medical_status_fnc_getMedicationCount;'+
        f'[abs (_result-{.5 if raw else 0})<0.000001,"onset or raw exposure changed"] call _check;')


def exposure_setup():
    return setup()+function('medicationExposure',extended=True)+function('medicationToxicityFiredCommit',extended=True)+'''
        private _drives=[]; ACME_fnc_medicationDriveAdd={_drives pushBack _this;};
        missionNamespace setVariable ["ACME_hcEff_medications",false];
        _patient setVariable ["ACME_medicationToxicityFired",createHashMapFromArray [["other",7]]];
    '''


def test_naloxone_marks_current_opioid_generation_without_consuming_or_masking_opioid_records():
    execute(exposure_setup()+'''
        _patient setVariable ["ace_medical_medications",[["Morphine_IV",1] call _record]];
        [_patient,"Morphine_IV",2,true,10] call ACME_fnc_medicationExposure;
        [_patient,"Fentanyl_IV",.05,true,.1] call ACME_fnc_medicationExposure;
        private _before=+(_patient getVariable ["ace_medical_medications",[]]);
        [_patient,"Naloxone",.4,true,.4] call ACME_fnc_medicationExposure;
        private _fired=_patient getVariable "ACME_medicationToxicityFired";
        [(_fired get "opioid")==2 && {(_fired get "other")==7},"wrong generation or unrelated latch erased"] call _check;
        [(_patient getVariable ["ace_medical_medications",[]]) isEqualTo _before,"exposure tracker rewrote medication records"] call _check;
        [[_patient,(_before select 0)] call ACME_fnc_medicationAvailability==1,"invented temporary opioid antagonist"] call _check;
        [_patient,"Fentanyl_IV",.05,true,.1] call ACME_fnc_medicationExposure;
        [((_patient getVariable "ACME_medicationGenerations") get "opioid")==3,"new opioid exposure failed to advance"] call _check;
        [((_patient getVariable "ACME_medicationToxicityFired") get "opioid")==2,"new exposure pre-consumed its toxicity latch"] call _check;
    ''')


@pytest.mark.parametrize('change',['_patientLocal=false;','_patientAlive=false;'])
def test_invalid_exposure_does_not_mark_or_count_medication(change):
    execute(exposure_setup()+change+'''
        [_patient,"Naloxone",.4,true,.4] call ACME_fnc_medicationExposure;
        [!(("Naloxone") in (_patient getVariable ["ACME_medicationAdmitted",createHashMap])),"invalid exposure counted"] call _check;
        [!(("opioid") in (_patient getVariable "ACME_medicationToxicityFired")),"invalid exposure marked"] call _check;
    ''')


@pytest.mark.parametrize('total,bolus,expected',[(.05,.05,0),(.1,.1,0),(.101,0,1),(0,.101,1),(.2,.2,1)])
def test_submilligram_overdose_threshold_checks_total_and_bolus_without_double_callback(total,bolus,expected):
    execute(setup()+function('onMedicationUsage','core',override=True)+f'private _total={total};'+'''
        private _calls=[]; ACM_circulation_fnc_handleOverdose={_calls pushBack _this;};
        ace_medical_status_fnc_getMedicationCount={_total;};
    '''+f'[_patient,"Fentanyl_IV",.1,0,{bolus},1,83,[]] call ACM_core_fnc_onMedicationUsage;'+
        f'[count _calls=={expected},"submilligram gate disabled or duplicate callback"] call _check;')


@pytest.mark.parametrize('limit,local',[(0,True),(-1,True),(.1,False)])
def test_disabled_or_remote_overdose_check_does_not_emit_callback(limit,local):
    execute(setup()+function('onMedicationUsage','core',override=True)+f'_patientLocal={str(local).lower()};'+'''
        private _calls=[]; ACM_circulation_fnc_handleOverdose={_calls pushBack _this;};
        ace_medical_status_fnc_getMedicationCount={100;};
    '''+f'[_patient,"Fentanyl_IV",{limit},0,100,1,83,[]] call ACM_core_fnc_onMedicationUsage;'+
        '[count _calls==0,"disabled/remote overdose callback"] call _check;')


def cbrn_setup():
    return setup()+function('medicationCBRNTick',extended=True)+'''
        private _dt=.5; ACME_fnc_clinicalTickDelta={_dt};
        _patient setVariable ["ACM_CBRN_Chemical_Sarin_Buildup",.5];
        _patient setVariable ["ACM_CBRN_Chemical_Lewisite_Buildup",10];
        _patient setVariable ["ACM_CBRN_AirwaySpasm",true];
    '''


@pytest.mark.parametrize('med',['Atropine','Atropine_IV','Atropine_L','Atropine_IV_L'])
def test_atropine_clears_the_same_airway_spasm_flag_consumed_by_native_airway(med):
    execute(cbrn_setup()+f'_patient setVariable ["ace_medical_medications",[["{med}",4] call _record]];'+'''
        [_patient] call ACME_fnc_medicationCBRNTick;
        [!(_patient getVariable ["ACM_CBRN_AirwaySpasm",true]),"effective atropine wrote the wrong spasm namespace"] call _check;
        [isNil {_patient getVariable "ACM_circulation_AirwaySpasm"},"stray circulation spasm state written"] call _check;
        [(_patient getVariable ["ACM_CBRN_Chemical_Sarin_Buildup",1])<.5,"chemical effect disappeared"] call _check;
    ''')


def test_native_spasm_and_buildup_macro_expansions_match_the_test_adapter():
    headers=(ROOT/'addons/main/script_macros.hpp').read_text()
    assert '#define QGVAR_BUILDUP(type)' in headers and 'QEGVAR(CBRN,##type##_Buildup)' in headers
    assert '#define HAS_AIRWAY_SPASM(unit)' in headers and '(unit getVariable [QEGVAR(CBRN,AirwaySpasm), false])' in headers
    assert '#include "\\x\\ACM\\addons\\circulation\\script_component.hpp"' in (F/'fn_medicationCBRNTick.sqf').read_text()


@pytest.mark.parametrize('dose',[0,2.99,3,3.99])
def test_atropine_below_existing_spasm_threshold_preserves_spasm(dose):
    execute(cbrn_setup()+f'_patient setVariable ["ace_medical_medications",[["Atropine_IV",{dose}] call _record]];'+'''
        [_patient] call ACME_fnc_medicationCBRNTick;
        [_patient getVariable ["ACM_CBRN_AirwaySpasm",false],"spasm threshold changed"] call _check;
    ''')


@pytest.mark.parametrize('arrest',[False,True])
def test_cbrn_effect_waits_for_onset_and_remains_time_normalized(arrest):
    execute(cbrn_setup()+f'_patient setVariable ["ace_medical_inCardiacArrest",{str(arrest).lower()}];'+'''
        _patient setVariable ["ACM_CBRN_Chemical_Sarin_Buildup",10];
        _patient setVariable ["ACM_CBRN_AirwaySpasm",false];
        _patient setVariable ["ace_medical_medications",[["Atropine_IV",3,1,"a",2,100] call _record,["Dimercaprol",1,1,"b",2,100] call _record]];
        [_patient] call ACME_fnc_medicationCBRNTick;
        [(_patient getVariable "ACM_CBRN_Chemical_Sarin_Buildup")==10 && {(_patient getVariable "ACM_CBRN_Chemical_Lewisite_Buildup")==10},"zero-onset dose treated as active"] call _check;
        CBA_missionTime=120;
        for "_i" from 1 to 10 do {[_patient] call ACME_fnc_medicationCBRNTick;};
    '''+f'[abs ((_patient getVariable "ACM_CBRN_Chemical_Sarin_Buildup")-{10-.4*(.5 if arrest else 1)})<.00001,"atropine dt/arrest scaling changed"] call _check;'+
        f'[abs ((_patient getVariable "ACM_CBRN_Chemical_Lewisite_Buildup")-{10-1.6*(.5 if arrest else 1)})<.00001,"dimercaprol dt/arrest scaling changed"] call _check;')


@pytest.mark.parametrize('change',['_patientAlive=false;','_patientLocal=false;','_dt=0;'])
def test_ineligible_cbrn_tick_preserves_clinical_state(change):
    execute(cbrn_setup()+f'_patient setVariable ["ace_medical_medications",[["Atropine_IV",4] call _record]];'+change+'''
        [_patient] call ACME_fnc_medicationCBRNTick;
        [(_patient getVariable "ACM_CBRN_Chemical_Sarin_Buildup")==.5 && {_patient getVariable ["ACM_CBRN_AirwaySpasm",false]},"invalid CBRN tick mutated patient"] call _check;
    ''')


@pytest.mark.parametrize('drug',['Atropine','Dimercaprol'])
def test_cbrn_entrypoint_registers_owner_without_a_disposable_effect_timer(drug):
    execute(setup()+function('handleMed_'+drug+'Local')+'''
        private _registered=[]; ACME_fnc_ownerRegister={_registered pushBack _this;};
    '''+f'[_patient] call ACM_circulation_fnc_handleMed_{drug}Local;'+'''
        [_registered isEqualTo [[_patient]],"native medication entrypoint lost owner registration"] call _check;
        [count _waits==0 && {count _handlers==0},"entrypoint created extra timer"] call _check;
    ''')
    text=(ROOT/'addons/core/overrides/fnc_handleUnitVitals.sqf').read_text()
    assert 'call ACME_fnc_medicationCBRNTick' in text


def test_native_count_registration_replaces_retired_external_delegate():
    cfg=subtree((ROOT/'addons/core/CfgFunctions.hpp').read_text(),'CfgFunctions')
    cls=cfg['classes']['overwrite_medical_status']
    assert cls['props']['tag']=='ace_medical_status'
    path=cls['classes']['ace_medical_status']['classes']['getMedicationCount']['props']['file']
    assert ''.join(path.split())==r'QPATHTOF(overrides\fnc_getMedicationCount.sqf)'
    assert 'class ACME_native' not in (ROOT/'addons/acm_extended/config.cpp').read_text()
