"""Execute integrated disease persistence, owner enrollment and shared physiology.

Production snapshot/codec/validator/restore and reconciliation execute together.
Native objects/clocks/transport and component tick scheduling are boundaries;
component workers have separate execution suites. This does not certify Arma
savegames, dedicated-server transport or visible clinical calibration.
"""
import json
import re

import pytest

from test_b271_ptx_stability import execute, function, restore_setup
from test_b156_coagulation_runtime import setup as coag_setup, function as coag_function
from test_b281_flight_scheduler import adapt as engine
from test_historical_medication_rows import iteration_scopes
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import ROOT, adapt as namespace_adapt, execute as menu_execute, read
from test_b291_cards import source as card_source
from test_b281_flight_scheduler import function as flight_function
from test_b291_ocular_integration import function as ocular_function


def wrapped(name):
    text = function(name)
    # Native homogeneous-array checks are expanded only for the VM primitive.
    text = text.replace('_v isEqualTypeAll true',
                        '((_v findIf {!(_x isEqualType true)}) < 0)')
    text = text.replace('_document isEqualTypeAll createHashMap',
                        '((_document findIf {!(_x isEqualType createHashMap)}) < 0)')
    return map_defaults(iteration_scopes(text))


def component_reconcile(component):
    text = (ROOT / f'addons/{component}/functions/fnc_reconcile.sqf').read_text()
    text = re.sub(r'\blocal _patient\b', '_patientLocal', text)
    text = text.replace('GET_DUST_INJURY(_patient)',
        '((_patient getVariable ["ACM_ophthalmology_dustInjuryLight",0])+(_patient getVariable ["ACM_ophthalmology_dustInjuryHeavy",0]))')
    text = re.sub(r'\bfinite (_\w+)', r'([\1] call _finite)', text)
    text = namespace_adapt(text, component)
    return 'ACM_' + component + '_fnc_reconcile={' + map_defaults(iteration_scopes(text)) + '};'


def card_document_source():
    # Object setVariable(nil) removes a key in Arma. The VM namespace stand-in
    # retains a nil slot, so supply the identical getVariable default boundary.
    return card_source('getDocument').replace(
        '_patient getVariable ["DD1380_Document", []]',
        '(if (isNil {_patient getVariable "DD1380_Document"}) then {[]} else {_patient getVariable "DD1380_Document"})')


def persistence_setup():
    text = restore_setup() + ''.join(wrapped(n) for n in (
        'clinicalFields', 'clinicalValidate', 'clinicalSnapshot',
        'clinicalRestore', 'medmashReconcile',
    )) + ocular_function('shieldSource') + ocular_function('shieldRecover') + ''.join(component_reconcile(n) for n in ('burns', 'infection', 'ophthalmology')) + card_source('fieldIds') + card_document_source() + r'''
        private _nativeFinite={_this isEqualType 0};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        ACM_burns_burnsEnabled=true;
        private _medicLocal=true;private _serverClock=100;
        private _componentTicks=[];
        ACME_fnc_ownerRegister={_this call ACME_fnc_medmashReconcile;};
        ACM_burns_fnc_tickPatient={params ["_p"];
            if ((_p getVariable ["ACM_burns_SystemicBurden",0])<=0) exitWith {};
            _componentTicks pushBack ["burn",CBA_missionTime-(_p getVariable "ACM_burns_LastTickLocal")];
            _p setVariable ["ACM_burns_HR_Adjust",12];
        };
        ACM_infection_fnc_handleInfectionPFH={_componentTicks pushBack ["infection",0];
            (_this select 0) setVariable ["ACM_infection_RR_Adjust",8];};
        ACM_ophthalmology_fnc_structuralTick={params ["_p"];
            _componentTicks pushBack ["eye",CBA_missionTime-(_p getVariable "ACM_ophthalmology_structuralLastTick")];};
    '''
    return re.sub(r'\bfinite (\([^()\n]*\))', r'([\1] call _finite)', text)


@pytest.mark.parametrize('restart', [12, 7000])
def test_full_disease_snapshot_restore_rebases_timelines_and_rebuilds_owner_workers(restart):
    execute(persistence_setup() + r'''
        CBA_missionTime=7200;
        private _durable=[
            ["ACM_burns_BurnSurface",[0.2,0.4,0,0,0,0]],
            ["ACM_burns_BurnProtected",[true,false,false,false,false,false]],
            ["ACM_burns_BurnBurden",0.3],["ACM_burns_SystemicBurden",0.2],
            ["ACM_burns_PermanentInjury",true],["ACM_burns_AirwayInflammation",30],
            ["ACM_infection_Infection_Stage",3],["ACM_infection_Sepsis_Permanent",true],
            ["ACM_infection_Infection_RiskAccumulator",0.5],
            ["ACM_infection_Infection_TreatmentAccumulator",4],
            ["ACM_ophthalmology_eyeInjuries",[0.2,0.7]],
            ["ACM_ophthalmology_ocularPermanent",true],
            ["ACME_infectionFeverActive",true]
        ];
        private _timelines=[
            ["ACM_burns_LastBurnAt",7000],["ACM_burns_AirwayBurnOnset",6000],
            ["ACM_infection_Infection_EligibleTime",6500],
            ["ACM_infection_Infection_NextStageTime",7300],
            ["ACM_infection_Sepsis_Onset",6000],
            ["ACM_infection_Infection_NextCheck",7230],
            ["ACM_infection_Sepsis_NextPain",7260],
            ["ACM_ophthalmology_eyeShieldAppliedAt",7100]
        ];
        {_patient setVariable [_x select 0,_x select 1];} forEach (_durable+_timelines);
        _patient setVariable ["ACM_burns_HR_Adjust",99];
        _patient setVariable ["ACM_infection_RR_Adjust",99];
        _patient setVariable ["ACM_burns_LastTickLocal",7000];
        _patient setVariable ["ACM_ophthalmology_structuralLastTick",7000];
        private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
        private _names=(_snapshot select 1) apply {_x select 0};
        [!({ _x in _names } count ["ACM_burns_HR_Adjust","ACM_infection_RR_Adjust","ACM_burns_LastTickLocal","ACM_ophthalmology_structuralLastTick"]>0),"derived drive/local clock was serialized"] call _check;
        [([_snapshot] call ACME_fnc_clinicalValidate) select 0,"real snapshot did not validate"] call _check;
        {_patient setVariable [_x select 0,nil];} forEach (_durable+_timelines);
    ''' + f'CBA_missionTime={restart};' + r'''
        [_patient,_snapshot,7] call ACME_fnc_clinicalRestore;
        { [(_patient getVariable (_x select 0)) isEqualTo (_x select 1),"durable disease field did not round-trip"] call _check; } forEach _durable;
        { [abs ((_patient getVariable (_x select 0))-(CBA_missionTime+(_x select 1)-7200))<0.001,"timeline retained previous mission clock"] call _check; } forEach _timelines;
        [_componentTicks isEqualTo [["burn",0],["infection",0],["eye",0]],"owner restore did not rebuild all three components without elapsed-time grants"] call _check;
        [(_patient getVariable "ACM_burns_HR_Adjust")==12 && {(_patient getVariable "ACM_infection_RR_Adjust")==8},"derived endpoints were not rebuilt"] call _check;
    ''')


@pytest.mark.parametrize('field', [
    'ACM_infection_Infection_EligibleTime',
    'ACM_infection_Infection_NextStageTime', 'ACM_infection_Sepsis_Onset',
])
def test_real_tagged_clock_cannot_collapse_into_unset_sentinel(field):
    execute(persistence_setup() + f'''
        CBA_missionTime=7200;_patient setVariable ["{field}",7187];
        private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
        CBA_missionTime=12;[_patient,_snapshot,7] call ACME_fnc_clinicalRestore;
        private _at=_patient getVariable "{field}";
        [_at != -1 && {{abs (_at+1)<0.001}},"real onset/due time became unset"] call _check;
    ''')


@pytest.mark.parametrize('period_change', ['clinical', 'locality'])
def test_repeated_registration_keeps_clock_but_new_owner_period_discards_dormant_time(period_change):
    change = ('_patient setVariable ["ACME_clinicalEpoch",8];' if period_change == 'clinical'
              else '_patient setVariable ["ACME_providerLocalityEpoch",1];')
    execute(persistence_setup() + r'''
        _patient setVariable ["ACM_burns_SystemicBurden",0.3];
        [_patient] call ACME_fnc_medmashReconcile;
        CBA_missionTime=11;[_patient] call ACME_fnc_medmashReconcile;
        [(_componentTicks select 1) isEqualTo ["burn",1],"same-period registration reset active integration clock"] call _check;
    ''' + change + r'''
        CBA_missionTime=100;[_patient] call ACME_fnc_medmashReconcile;
        [(_componentTicks select 2) isEqualTo ["burn",0],"new ownership/clinical period integrated dormant time"] call _check;
    ''')


def test_settled_anatomical_burn_stays_dormant_and_nonowner_cannot_reconcile():
    execute(persistence_setup() + r'''
        _patient setVariable ["ACM_burns_BurnBurden",0.3];
        _patient setVariable ["ACM_burns_SystemicBurden",0];
        [_patient] call ACME_fnc_medmashReconcile;
        [_componentTicks isEqualTo [],"settled anatomy reactivated systemic burn worker"] call _check;
        _patientLocal=false;_patient setVariable ["ACM_burns_SystemicBurden",0.3];
        [_patient] call ACME_fnc_medmashReconcile;
        [_componentTicks isEqualTo [],"departed owner restarted physiology"] call _check;
    ''')


@pytest.mark.parametrize('legacy', [False, True])
def test_card_snapshot_restore_is_atomic_and_legacy_migration_replaces_old_document(legacy):
    seed = r'''
        private _data=([_patient,false] call DD1380_card_fnc_getDocument) select 1;
        (_data select 0) set [1001,true];(_data select 2) set [1107,"Unit A"];
        (_data select 4) set [1651,"Antibiotic given"];
    '''
    if legacy:
        snapshot = r'''
            private _rows=[];
            { _rows pushBack [_x,[(_data select _forEachIndex),true] call ACME_fnc_clinicalCodec]; }
                forEach ["DD1380_Priority","DD1380_Checkboxes","DD1380_Text","DD1380_Back_Checkboxes","DD1380_Back_Text"];
            _rows pushBack ["DD1380_Revision",["V",7]];
            private _snapshot=[3,_rows];
        '''
    else:
        snapshot = r'''
            _patient setVariable ["DD1380_Document",[7,_data]];
            _patient setVariable ["DD1380_Text",createHashMapFromArray [[1107,"stale mirror"]]];
            _patient setVariable ["DD1380_Revision",99];
            private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
            private _names=(_snapshot select 1) apply {_x select 0};
            ["DD1380_Document" in _names && {!(("DD1380_Text" in _names) || {"DD1380_Revision" in _names})},"snapshot serialized mixed card generations"] call _check;
        '''
    execute(persistence_setup() + seed + snapshot + r'''
        [([_snapshot] call ACME_fnc_clinicalValidate) select 0,"valid card did not pass clinical validator"] call _check;
        _patient setVariable ["DD1380_Document",[999,[createHashMap,createHashMap,createHashMap,createHashMap,createHashMap]]];
        [_patient,_snapshot,7] call ACME_fnc_clinicalRestore;
        private _document=[_patient,false] call DD1380_card_fnc_getDocument;
        [_document select 0==7 && {(_document select 1 select 2 get 1107)=="Unit A"}
            && {(_document select 1 select 4 get 1651)=="Antibiotic given"},"restored/migrated document mixed old and new generations"] call _check;
        [(_patient getVariable "DD1380_Revision")==7 && {((_patient getVariable "DD1380_Text") get 1107)=="Unit A"},"card mirrors were not rebuilt from canonical document"] call _check;
    ''')


def test_card_document_survives_actual_medical_reset_field_pass_but_new_life_clears_it():
    reset = read('clinicalReset')
    start = reset.index('{\n    _x params ["_name", "", "_reset"];')
    end = reset.index('} forEach (call ACME_fnc_clinicalFields);', start) + len('} forEach (call ACME_fnc_clinicalFields);')
    execute(persistence_setup() + card_source('resetDocument') + r'''
        private _data=([_patient,false] call DD1380_card_fnc_getDocument) select 1;
        (_data select 2) set [1107,"Preserved history"];
        _patient setVariable ["DD1380_Document",[4,_data]];
        _patient setVariable ["ACM_burns_BurnBurden",0.4];
        private _junctionalEvidence=[];
    ''' + namespace_adapt(reset[start:end]) + r'''
        [(_patient getVariable "DD1380_Document") select 0==4,"medical full-heal erased documentation"] call _check;
        [isNil {_patient getVariable "ACM_burns_BurnBurden"},"medical full-heal retained disease anatomy"] call _check;
        [_patient] call DD1380_card_fnc_resetDocument;
        private _document=[_patient,false] call DD1380_card_fnc_getDocument;
        [_document select 0==0 && {(_document select 1 select 2 get 1107)==""},"new casualty life retained old documentation"] call _check;
    ''')


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('drug', ['Moxifloxacin', 'Ertapenem', 'Ertapenem_IV', 'Ceftriaxone', 'Ceftriaxone_IV'])
def test_basic_ace_mode_admits_real_antibiotic_records_only_for_enabled_infection(enabled, drug):
    text=(ROOT/'addons/core/overrides/fnc_medicationLocal.sqf').read_text()
    start=text.index('private _forceAdvanced')
    end=text.index('// Medication has no effects on dead units',start)
    gate=namespace_adapt(text[start:end])
    menu_execute(f'''
        private _classname={json.dumps(drug)};
        ace_medical_treatment_advancedMedication=false;
        missionNamespace setVariable ["ACM_infection_infectionEnabled",{str(enabled).lower()}];
    '''+gate+f'''
        [_useAdvanced isEqualTo {str(enabled).lower()},"enabled infection consumed antibiotics without records, or changed disabled basic mode"] call _check;
    ''')


@pytest.mark.parametrize('field,value', [
    ('ACM_burns_BurnSurface','[0,0,0,0,0]'),
    ('ACM_burns_BurnSurface','[0,0,0,0,0,2]'),
    ('ACM_burns_BurnProtected','[false,false,false,false,false,0]'),
    ('ACM_burns_SystemicBurden','1.1'),
    ('ACM_burns_AirwayInflammation','101'),
    ('ACM_infection_Infection_Stage','1.5'),
    ('ACM_infection_Infection_Stage','4'),
    ('ACM_infection_Sepsis_Permanent','1'),
    ('ACM_ophthalmology_eyeInjuries','[0.1]'),
    ('ACM_ophthalmology_eyeInjuries','[-0.1,1]'),
    ('ACM_ophthalmology_eyeShieldIndex','2'),
    ('ACM_ophthalmology_dustInjuryHeavy','6'),
    ('DD1380_Document','[1,[createHashMap]]'),
    ('DD1380_Document','[-1,[createHashMap,createHashMap,createHashMap,createHashMap,createHashMap]]'),
    ('DD1380_Revision','0.5'),
])
def test_malformed_disease_and_card_state_is_rejected_before_any_restore_mutation(field, value):
    execute(persistence_setup() + f'''
        private _rows=[["{field}",[{value},true] call ACME_fnc_clinicalCodec]];
        private _payload=[3,_rows];
        [!(([_payload] call ACME_fnc_clinicalValidate) select 0),"malformed state accepted"] call _check;
        _patient setVariable ["ACM_burns_SystemicBurden",0.4];
        [_patient,_payload,7] call ACME_fnc_clinicalRestore;
        [(_patient getVariable "ACM_burns_SystemicBurden")==0.4 && {{_componentTicks isEqualTo []}},"invalid restore mutated patient or resumed workers"] call _check;
    ''')


@pytest.mark.parametrize('infection_mult', [1.5, 2.5])
def test_infection_coagulation_is_derived_once_and_recovery_retires_without_polluting_base(infection_mult):
    menu_execute(coag_setup() + f'''
        _patient setVariable ["ACM_infection_Coag_Mult",{infection_mult}];
        [[_patient]] call ACME_fnc_coagulationTick;
        [(_patient getVariable "ACME_ca_coagBaseMult")==1,"infection overwrote circulation-owned coagulation base"] call _check;
        [(_patient getVariable "ACME_ca_coagMult")>1,"sepsis never reached final clot impairment"] call _check;
        private _first=_patient getVariable "ACME_ca_coagMult";
        CBA_missionTime=10.2;[] call ACME_fnc_coagulationTick;
        [(_patient getVariable "ACME_ca_coagMult")==_first,"sepsis compounded through prior output"] call _check;
        _patient setVariable ["ACM_infection_Coag_Mult",1];
        CBA_missionTime=10.4;[] call ACME_fnc_coagulationTick;
        [(_patient getVariable "ACME_ca_coagMult")==1 && {{ACME_coag_activePatients isEqualTo []}},"resolved infection left coagulation active or impaired"] call _check;
    ''')


def test_healthy_shock_observer_is_silent_and_retires_without_creating_neutral_drives():
    menu_execute(coag_setup() + coag_function('setVarNet') + flight_function('shockPhenotypeTick') + r'''
        ACME_shock_activePatients=[_patient];
        for "_i" from 0 to 40 do {CBA_missionTime=10+_i*0.5;_nowTime=CBA_missionTime;call ACME_fnc_shockPhenotypeTick;};
        [(call _sent)==0 && {ACME_shock_activePatients isEqualTo []},"healthy shock observer generated packets or retained active membership"] call _check;
        [isNil {_patient getVariable "ACME_shock_hrAdj"} && {isNil {_patient getVariable "ACME_shock_resistDelta"}},"healthy observer created neutral endpoint drives"] call _check;
    ''')


@pytest.mark.parametrize('field,phenotype,severity', [
    ('ACM_burns_ShockSeverity','burn',0.8),
    ('ACM_infection_Sepsis_Severity','distributive',0.7),
])
def test_disease_shock_classifies_once_without_duplicating_hemodynamic_drives_or_heartbeats(field, phenotype, severity):
    menu_execute(coag_setup() + coag_function('setVarNet') + flight_function('shockPhenotypeTick') + f'''
        ACME_shock_activePatients=[_patient];
        _patient setVariable ["{field}",{severity}];
        _patient setVariable ["ACM_infection_HR_Adjust",18];
        _patient setVariable ["ACM_burns_HR_Adjust",14];
        call ACME_fnc_shockPhenotypeTick;
        [(_patient getVariable "ACME_shock_phenotype")=="{phenotype}" && {{(_patient getVariable "ACME_shock_severity")=={severity}}},"disease phenotype was not discovered"] call _check;
        [(_patient getVariable "ACME_shock_hrAdj")==0 && {{(_patient getVariable "ACME_shock_resistDelta")==0}},"observer doubled component-owned HR/SVR compensation"] call _check;
        private _first=call _sent;
        for "_i" from 1 to 20 do {{CBA_missionTime=10+_i;_nowTime=CBA_missionTime;call ACME_fnc_shockPhenotypeTick;}};
        [(call _sent)==_first,"stable disease generated heartbeat packets"] call _check;
        _patient setVariable ["{field}",0];call ACME_fnc_shockPhenotypeTick;
        [(_patient getVariable "ACME_shock_phenotype")=="none" && {{ACME_shock_activePatients isEqualTo []}},"resolved disease label did not neutralize/retire"] call _check;
        [(_patient getVariable "ACM_infection_HR_Adjust")==18 && {{(_patient getVariable "ACM_burns_HR_Adjust")==14}},"phenotype observer overwrote independent endpoint sources"] call _check;
    ''')


@pytest.mark.parametrize('permanent', [None, 'ACM_burns_PermanentInjury',
    'ACM_infection_Sepsis_Permanent', 'ACM_ophthalmology_ocularPermanent'])
def test_recovered_stage_one_tbi_cannot_clear_other_permanent_evacuation_causes(permanent):
    text = read('tbiHandle')
    start = text.index('    // the evacuation requirement.')
    end = text.index('    _state set ["severityFloor"', start)
    snippet = engine(text[start:end])
    menu_execute(r'''
        private _maxStage=1;private _stage=0;private _severity=0;private _severityFloor=0;
        private _state=createHashMapFromArray [["herniating",false]];
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        ACME_fnc_setVarNet={params ["_p","_name","_value"];
            if (isNil "_value") then {_p setVariable [_name,nil];} else {_p setVariable [_name,_value];};};
        _patient setVariable ["ACME_requiresEvac",true];
    ''' + ('_patient setVariable ['+json.dumps(permanent)+',true];' if permanent else '')
        + wrapped('evacuationRequirementCommit')
        + snippet + ('[(_patient getVariable "ACME_requiresEvac"),"TBI recovery cleared a permanent disease cause"] call _check;'
                     if permanent else '[isNil {_patient getVariable "ACME_requiresEvac"},"recovered TBI retained its own evacuation requirement"] call _check;'))
