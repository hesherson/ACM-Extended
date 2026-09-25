"""B156 executes coagulation, its publication helper and the supplied ACE contract.

Objects/locality/network transport and unsupported VM primitives are boundaries;
the checked-out formulas, active-set decisions and packet suppression run as SQF.
"""
import re
from pathlib import Path

import pytest

from test_menu_death_lifecycle import ROOT, execute, read
from test_historical_cardiac_execution import code as cardiac_code
from test_historical_vial_execution import map_defaults


def code(text):
    for old, new in {
        'local _u': '_patientLocal', 'alive _u': '_patientAlive',
        'local _x': '_patientLocal', 'alive _x': '_patientAlive',
        'local _obj': '_patientLocal', 'owner _obj': '_ownerNum',
        'allUnits': '_units',
    }.items():
        text = re.sub(r'(?<!\w)' + re.escape(old) + r'\b', new, text)
    return map_defaults(cardiac_code(text))


def function(name):
    return 'ACME_fnc_' + name + '={' + code(read(name)) + '};'


def setup():
    return '''
        private _patientLocal=true;
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _units=[_patient];
        private _medResult=0;
        private _medCalls=0;
        private _linear={params ["_lo","_hi","_x","_a","_b",["_clamp",false]];
            private _f=(_x-_lo)/(_hi-_lo); if (_clamp) then {_f=(_f max 0) min 1;}; _a+(_f*(_b-_a))};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        ace_medical_status_fnc_getMedicationCount={_medCalls=_medCalls+1; _medResult};
        ACME_net_count=true;
        ACME_coag_activePatients=[];
        ACME_coag_lastSweep=-1;
        private _sent={private _n=0; private _counts=missionNamespace getVariable ["ACME_net_sent",createHashMap];
            {_n=_n+(_counts get _x);} forEach keys _counts; _n};
    ''' + ''.join(function(n) for n in (
        'setVarNetApprox', 'medicationCountCompat', 'coagulationBase', 'coagulationTick'))


def test_neutral_units_have_no_drug_lookup_packets_or_active_membership():
    execute(setup() + '''
        for "_i" from 0 to 100 do {CBA_missionTime=10+_i*.2; [] call ACME_fnc_coagulationTick;};
        [_medCalls==0,"healthy sweep looked up medication kinetics"] call _check;
        [(call _sent)==0,"healthy sweep broadcast neutral defaults"] call _check;
        [ACME_coag_activePatients isEqualTo [],"healthy unit retained active"] call _check;
    ''')


def test_discovery_is_bounded_and_active_patients_keep_five_hz_response():
    execute(setup() + '''
        [] call ACME_fnc_coagulationTick;
        _patient setVariable ["ACM_circulation_Platelet_Count",1.5];
        CBA_missionTime=11.8; [] call ACME_fnc_coagulationTick;
        [_medCalls==0,"fallback swept sooner than two seconds"] call _check;
        CBA_missionTime=12; [] call ACME_fnc_coagulationTick;
        [ACME_coag_activePatients isEqualTo [_patient],"fallback failed to enroll"] call _check;
        private _before=_patient getVariable ["ACME_coag_clotStrength",1];
        _patient setVariable ["ACM_circulation_Platelet_Count",1];
        CBA_missionTime=12.2; [] call ACME_fnc_coagulationTick;
        [(_patient getVariable ["ACME_coag_clotStrength",1])<_before,"active patient missed next 0.2 second pass"] call _check;
        [_medCalls==2,"active evaluation count changed"] call _check;
    ''')


@pytest.mark.parametrize('med_result', ['0.8', '[19,0.8]'])
def test_txa_scalar_and_pair_contracts_use_effectiveness(med_result):
    execute(setup() + f'_medResult={med_result};' + '''
        _patient setVariable ["ACM_circulation_Platelet_Count",1.5];
        _patient setVariable ["ace_medical_medications",[["TXA_IV"]]];
        [[_patient]] call ACME_fnc_coagulationTick;
        [abs ((_patient getVariable "ACME_coag_clotStrength")-.686)<.000001,"TXA dose slot used as effectiveness"] call _check;
        [ACME_coag_activePatients isEqualTo [_patient],"treatment did not enroll immediately"] call _check;
    ''')


def test_abnormal_base_does_not_feed_back_and_stable_state_stops_broadcasting():
    execute(setup() + '''
        _patient setVariable ["ACME_hypo_temp",32];
        _patient setVariable ["ACM_circulation_Saline_Volume",1.5];
        [[_patient]] call ACME_fnc_coagulationTick;
        private _combined=_patient getVariable "ACME_ca_coagMult";
        private _packets=call _sent;
        [abs ((_patient getVariable "ACME_ca_coagBaseMult")-1.6)<.000001,"base reconstruction changed"] call _check;
        [abs (_combined-3.456)<.00001,"combined formula changed"] call _check;
        for "_i" from 1 to 100 do {CBA_missionTime=10+_i*.2; _nowTime=CBA_missionTime; [] call ACME_fnc_coagulationTick;};
        [(_patient getVariable "ACME_ca_coagMult")==_combined,"combined output fed back into base"] call _check;
        [_packets==5 && {(call _sent)==_packets},"stable state produced redundant packets"] call _check;
    ''')


def test_txa_zero_onset_remains_active_then_effect_recovers():
    execute(setup() + '''
        _patient setVariable ["ace_medical_medications",[["TXA_IV"]]];
        [[_patient]] call ACME_fnc_coagulationTick;
        [ACME_coag_activePatients isEqualTo [_patient],"zero onset discarded treatment"] call _check;
        _medResult=[2000,1]; CBA_missionTime=10.2;
        [] call ACME_fnc_coagulationTick;
        [abs ((_patient getVariable "ACME_coag_clotStrength")-1.12)<.000001,"onset not reflected next active tick"] call _check;
        _patient setVariable ["ace_medical_medications",[]]; _medResult=0;
        [] call ACME_fnc_coagulationTick;
        [(_patient getVariable "ACME_coag_clotStrength")==1 && {ACME_coag_activePatients isEqualTo []},"completed effect not reset and retired"] call _check;
    ''')


def test_recovery_and_heal_do_not_resurrect_legacy_caches():
    execute(setup() + '''
        _patient setVariable ["ACME_coag_lastBase",4];
        _patient setVariable ["ACME_coag_lastPublished",5];
        _patient setVariable ["ACME_ca_coagMult",5];
        _patient setVariable ["ACME_ca_coagBaseMult",3];
        [[_patient]] call ACME_fnc_coagulationTick;
        [(_patient getVariable "ACME_ca_coagMult")==1 && {(_patient getVariable "ACME_ca_coagBaseMult")==1},"heal replayed legacy base/output"] call _check;
        [ACME_coag_activePatients isEqualTo [],"recovered patient retained active"] call _check;
    ''')


def test_owner_handoff_rebuilds_inputs_and_refreshes_once():
    execute(setup() + '''
        _patient setVariable ["ACME_hypo_temp",32];
        [[_patient]] call ACME_fnc_coagulationTick;
        private _before=_patient getVariable "ACME_ca_coagMult";
        private _packets=call _sent;
        _patientLocal=false; [] call ACME_fnc_coagulationTick;
        [ACME_coag_activePatients isEqualTo [] && {(call _sent)==_packets},"old owner retained work or published"] call _check;
        _patientLocal=true; _ownerNum=8;
        _patient setVariable ["ACME_ca_coagBaseMult",99];
        _patient setVariable ["ACME_coag_lastBase",99];
        [[_patient]] call ACME_fnc_coagulationTick;
        [(_patient getVariable "ACME_ca_coagMult")==_before,"handoff compounded output"] call _check;
        [(call _sent)==_packets+5,"new owner did not publish one refresh"] call _check;
        [[_patient]] call ACME_fnc_coagulationTick;
        [(call _sent)==_packets+5,"new owner repeated stable refresh"] call _check;
    ''')


def test_neutral_recovery_publishes_even_below_normal_threshold():
    execute(setup() + '''
        _patient setVariable ["ACM_circulation_Platelet_Count",2.99];
        [[_patient]] call ACME_fnc_coagulationTick;
        private _packets=call _sent;
        _patient setVariable ["ACM_circulation_Platelet_Count",3];
        [] call ACME_fnc_coagulationTick;
        [(call _sent)==_packets+3,"neutral recovery suppressed a final strength/extra/output publication"] call _check;
        private _cache=_patient getVariable "ACME_net_approxCache";
        [((_cache get "acme_ca_coagmult") select 0)==1,"observer stranded at non-neutral multiplier"] call _check;
        [ACME_coag_activePatients isEqualTo [],"recovery did not retire"] call _check;
    ''')


def test_base_rebuild_preserves_calcium_acidosis_and_treatment_response():
    execute(setup() + '''
        _patient setVariable ["ACM_circulation_TransfusedBlood_Volume",3.5];
        _patient setVariable ["ACME_hypo_temp",32];
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [["acidosis",1]]];
        [[_patient]] call ACME_fnc_coagulationTick;
        [abs ((_patient getVariable "ACME_ca_coagBaseMult")-2.912)<.000001,"triad factor calculation changed"] call _check;
        _patient setVariable ["ACME_ca_caCl2Given",4];
        [[_patient]] call ACME_fnc_coagulationTick;
        [abs ((_patient getVariable "ACME_ca_coagBaseMult")-2.08)<.000001,"calcium treatment not reflected immediately"] call _check;
        ACME_sys_circ=false;
        [[_patient]] call ACME_fnc_coagulationTick;
        [(_patient getVariable "ACME_ca_coagBaseMult")==1 && {(_patient getVariable "ACME_ca_coagMult")==1},"disabled triad retained stale base"] call _check;
    ''')


@pytest.mark.parametrize('raw', ['true', 'false'])
def test_compat_forwards_count_mode_and_body_site_and_uses_effect_slot(raw):
    execute(setup() + '''
        private _seen=[];
        ace_medical_status_fnc_getMedicationCount={_seen=+_this; [900,0.25]};
    ''' + f'private _result=[_patient,"Lidocaine",{raw},4] call ACME_fnc_medicationCountCompat;' +
        f'[_seen isEqualTo [_patient,"Lidocaine",{raw},4],"adapter altered count/body-site arguments"] call _check;' + '''
        [_result==0.25,"adapter returned accumulated dose instead of requested effectiveness"] call _check;
    ''')


def test_extended_drug_readers_preserve_scalar_behavior_with_current_ace_pairs():
    readers = ('ketamineOnBoard', 'propofolOnBoard', 'fentanylOnBoard',
               'sugammadexOnBoard', 'rocuroniumOnBoard', 'sedationComponents',
               'proceduralAnalgesiaOnBoard', 'midazolamTick')
    definitions = ''.join(function(n) for n in readers)
    definitions = definitions.replace('_patient isKindOf "CAManBase"', 'true')
    execute(setup() + definitions + '''
        private _pair=false;
        ace_medical_status_fnc_getMedicationCount={if (_pair) then {[900,0.4]} else {0.4}};
        ACME_fnc_setVarNet={params ["_obj","_key","_value"];_obj setVariable [_key,_value]};
        private _sample={[
            [_patient] call ACME_fnc_ketamineOnBoard,
            [_patient] call ACME_fnc_propofolOnBoard,
            [_patient] call ACME_fnc_fentanylOnBoard,
            [_patient] call ACME_fnc_sugammadexOnBoard,
            [_patient] call ACME_fnc_rocuroniumOnBoard,
            [_patient] call ACME_fnc_sedationComponents,
            [_patient,"leftleg"] call ACME_fnc_proceduralAnalgesiaOnBoard
        ]};
        private _scalar=call _sample;
        [_patient] call ACME_fnc_midazolamTick;
        private _mid=_patient getVariable "ACME_midaz_sedEffective";
        _pair=true;
        private _array=call _sample;
        [_patient] call ACME_fnc_midazolamTick;
        [_scalar isEqualTo _array,"array contract changed drug reader behavior"] call _check;
        [(_patient getVariable "ACME_midaz_sedEffective")==_mid,"midazolam used raw dose slot"] call _check;
        [abs ((_array select 0)-1.28)<.000001 && {(_array select 3)==0.8},"route coefficients changed"] call _check;
    ''')


def test_interactions_preserve_scalar_behavior_with_current_ace_pairs():
    # Config is an engine fixture; both API shapes use the same reference ratios.
    source = read('medicationInteractions')
    source = source.replace('private _cfg = configFile >> "ACM_Medication" >> "Medications";', '')
    source = re.sub(r'isNumber \(_cfg >> _class >> "maxEffectDose"\)', 'true', source)
    source = re.sub(r'getNumber \(_cfg(?: >> _class| >> _canonical)? >> "maxEffectDose"\)', '1', source)
    execute(setup() + 'ACME_fnc_medicationInteractions={' + code(source) + '};' + '''
        private _pair=false;
        ace_medical_status_fnc_getMedicationCount={if (_pair) then {[900,0.4]} else {0.4}};
        private _scalar=[_patient,[.2,.3,.4],.8] call ACME_fnc_medicationInteractions;
        _pair=true;
        private _array=[_patient,[.2,.3,.4],.8] call ACME_fnc_medicationInteractions;
        [_scalar isEqualTo _array,"array contract dropped interaction effects"] call _check;
        [(_array select 2)<0,"fixture failed to exercise respiratory interaction"] call _check;
    ''')


def test_cbrn_treatment_accepts_pair_from_the_real_scalar_medication_reader():
    from test_historical_medication_effects import cbrn_setup
    execute(cbrn_setup() + '''
        private _nativeCount=ace_medical_status_fnc_getMedicationCount;
        ace_medical_status_fnc_getMedicationCount={[900,_this call _nativeCount]};
        _patient setVariable ["ace_medical_medications",[["Atropine_IV",4] call _record,["Dimercaprol",1] call _record]];
        [_patient] call ACME_fnc_medicationCBRNTick;
        [!(_patient getVariable ["ACM_CBRN_AirwaySpasm",true]),"pair contract prevented atropine response"] call _check;
        [abs ((_patient getVariable "ACM_CBRN_Chemical_Lewisite_Buildup")-9.84)<.00001,"dimercaprol response used dose slot"] call _check;
    ''')


def test_supplied_ace_function_runs_with_actual_pair_return_contract():
    path = ROOT.parent / 'references/ACE3-master/ACE3-master/addons/medical_status/functions/fnc_getMedicationCount.sqf'
    if not path.is_file():
        pytest.skip('supplied ACE checkout required for external contract execution')
    source = path.read_text().replace('VAR_MEDICATIONS', '"ace_medical_medications"')
    source = re.sub(r'^TRACE_\d+\([^\n]*\);\s*$', '', source, flags=re.M)
    assert '[_medDose, _effectiveness]' in source
    execute(setup() + 'ace_medical_status_fnc_getMedicationCount={' + code(source) + '};' + '''
        CBA_missionTime=20;
        _patient setVariable ["ACM_circulation_Platelet_Count",1.5];
        _patient setVariable ["ace_medical_medications",[["TXA_IV",0,10,100,0,0,0,2000]]];
        [[_patient]] call ACME_fnc_coagulationTick;
        [abs ((_patient getVariable "ACME_coag_clotStrength")-.686)<.000001,"real ACE pair caused wrong TXA effect"] call _check;
    ''')


def test_circulation_has_only_dedicated_base_writer_and_owner_hook_is_immediate():
    circ = read('circHandle')
    assert '[_patient,"ACME_ca_coagMult"' not in circ
    assert 'call ACME_fnc_coagulationBase' in circ
    assert '[[_patient]] call ACME_fnc_coagulationTick' in circ
    assert '[[_patient]] call ACME_fnc_coagulationTick' in read('ownerRegister')
    volume = (ROOT / 'addons/circulation/functions/fnc_getBloodVolumeChange.sqf').read_text()
    hook = volume.index('[[_unit]] call ACME_fnc_coagulationTick')
    assert hook > volume.index('_unit setVariable [QEGVAR(circulation,Saline_Volume)')
    assert hook > volume.index('_unit setVariable [QEGVAR(circulation,Platelet_Count)')
