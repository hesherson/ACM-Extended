"""Execute imported infection/sepsis with current medication and owner boundaries.

Production progression, risk, treatment and retirement run in SQF-VM. Objects,
replication, scheduling and medical effects are explicit engine boundaries;
these fixtures do not certify multiplayer transport or clinical calibration.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from test_historical_cardiac_execution import code as cardiac_code
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import ROOT, execute, read


I = ROOT / "addons/infection"
PARTS = '["head","body","leftarm","rightarm","leftleg","rightleg"]'


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def code(source):
    fields = {
        "OPEN": "ace_medical_openWounds",
        "BANDAGED": "ace_medical_bandagedWounds",
        "STITCHED": "ace_medical_stitchedWounds",
        "CLOTTED": "ACM_damage_ClottedWounds",
        "WRAPPED": "ACM_damage_WrappedWounds",
    }
    for macro, field in fields.items():
        source = re.sub(r'GET_' + macro + r'_WOUNDS\((\w+)\)',
                        lambda m: f'({m[1]} getVariable ["{field}",createHashMap])', source)
    source = re.sub(r'GET_PAIN\((\w+)\)',
                    lambda m: f'({m[1]} getVariable ["ace_medical_pain",0])', source)
    source = source.replace("ALL_BODY_PARTS", PARTS)
    # Namespace stand-ins accept no dynamic public flag; reset's value is retained exactly.
    source = source.replace(",_public]", "]")
    source = source.replace("local _x", "_patientLocal").replace("alive _x", "_patientAlive")
    source = source.replace('allUnits', '_units').replace('_patient isKindOf "CAManBase"', 'true')
    source = re.sub(r'LINKFUNC\((\w+)\)', r'ACM_infection_fnc_\1', source)
    return map_defaults(cardiac_code(source, "infection"))


def function(name):
    return f'ACM_infection_fnc_{name}={{' + code((I / "functions" / f"fnc_{name}.sqf").read_text()) + '};'


def setup():
    return '''
        private _patientLocal=true;
        private _units=[_patient];
        private _medCoverage=createHashMap;
        private _pair=false;
        private _painCalls=[];
        private _evacCalls=[];
        private _medCalls=[];
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _linear={params ["_lo","_hi","_x","_a","_b",["_clamp",false]];
            private _f=(_x-_lo)/(_hi-_lo);if (_clamp) then {_f=(_f max 0) min 1;};_a+(_f*(_b-_a))};
        CBA_missionTime=4000;
        ACM_infection_infectionEnabled=true;
        ACM_infection_infectionStageTime=30;
        ACM_infection_infectionRiskMultiplier=1;
        ACM_infection_hardcoreSepsisEvacMinutes=10;
        ACM_infection_activePatients=[_patient];
        ACME_circ_activePatients=[];
        missionNamespace setVariable ["ACME_hcEff_infection",false];
        ace_medical_status_fnc_getMedicationCount={
            _medCalls pushBack +_this;
            private _v=[_medCoverage,[_this select 1,0]] call _mapDefault;
            if (_pair) then {[999,_v]} else {_v}
        };
        ace_medical_status_fnc_adjustPainLevel={_painCalls pushBack +_this;};
        ACME_fnc_evacuationRequirementCommit={
            _evacCalls pushBack +_this;(_this select 0) setVariable ["ACME_requiresEvac",_this select 1];
        };
        ACME_fnc_setVarNetApprox={params ["_obj","_key","_value"];_obj setVariable [_key,_value];};
        _patient setVariable ["ace_medical_bandagedWounds",createHashMapFromArray [["leftarm",[[0,1]]]]];
        _patient setVariable ["ace_medical_pain",0];
        _patient setVariable ["ACME_hypo_temp",37];
    ''' + 'ACME_fnc_medicationCountCompat={' + code(read("medicationCountCompat")) + '};' + ''.join(
        function(n) for n in ("getAntibioticLevel", "getWoundCount", "getInfectionRisk", "applyInfectionStage",
                             "resetVariables", "handleSepsisPFH", "handleInfectionPFH", "fullHealLocal", "initUnit", "gui_updateInjuryListPart", "reconcile"))


@pytest.mark.parametrize("medication", ["Ertapenem_IV", "Ertapenem", "Ceftriaxone_IV", "Ceftriaxone", "Moxifloxacin"])
@pytest.mark.parametrize("pair", [False, True])
def test_each_current_antibiotic_identity_uses_effectiveness_for_scalar_and_pair(medication, pair):
    execute(setup() + f'_pair={str(pair).lower()};_medCoverage set ["{medication}",0.8];' + '''
        private _level=[_patient] call ACM_infection_fnc_getAntibioticLevel;
        [abs (_level-.8)<.000001,"antibiotic reader ignored current identity or consumed dose slot"] call _check;
        [_medCalls findIf {_x select 2}<0,"antibiotic reader discarded onset"] call _check;
        _patient setVariable ["ACM_infection_Infection_EligibleTime",1];
        private _risk=[_patient] call ACM_infection_fnc_getInfectionRisk;
        [abs (_risk-.024)<.000001,"risk did not use compatible antibiotic coverage"] call _check;
    ''')


def test_medCoverage_sums_real_routes_and_preserves_existing_cap():
    execute(setup() + '''
        _medCoverage set ["Moxifloxacin",1.2];_medCoverage set ["Ceftriaxone_IV",1.2];
        [([_patient] call ACM_infection_fnc_getAntibioticLevel)==2,"combined coverage bypassed cap"] call _check;
        _patient setVariable ["ACM_infection_Infection_EligibleTime",1];
        [([_patient] call ACM_infection_fnc_getInfectionRisk)==0,"full coverage retained new infection risk"] call _check;
    ''')


def test_risk_eligibility_burn_drive_and_treatment_states_are_composed_once():
    execute(setup() + '''
        _patient setVariable ["ACM_infection_Infection_EligibleTime",4001];
        [([_patient] call ACM_infection_fnc_getInfectionRisk)==0,"risk began before eligibility"] call _check;
        _patient setVariable ["ACM_infection_Infection_EligibleTime",1];
        _patient setVariable ["ACM_damage_ClottedWounds",createHashMapFromArray [["head",[[0,2]]]]];
        _patient setVariable ["ACM_damage_WrappedWounds",createHashMapFromArray [["rightleg",[[0,3]]]]];
        _patient setVariable ["ace_medical_stitchedWounds",createHashMapFromArray [["body",[[0,4]]]]];
        _patient setVariable ["ACM_burns_InfectionRiskMult",1.5];
        [([_patient] call ACM_infection_fnc_getWoundCount) isEqualTo [2,1,3,4],"wound-state totals changed"] call _check;
        [abs (([_patient] call ACM_infection_fnc_getInfectionRisk)-.282)<.000001,
            "regional wounds and burn infection drive were not composed once"] call _check;
    ''')


@pytest.mark.parametrize("pair", [False, True])
def test_ceftriaxone_prevents_progression_and_regresses_infection_after_twenty_checks(pair):
    execute(setup() + f'_pair={str(pair).lower()};' + '''
        _medCoverage set ["Ceftriaxone_IV",1];
        _patient setVariable ["ACM_infection_Infection_Stage",2];
        _patient setVariable ["ACM_infection_Infection_NextStageTime",1];
        for "_i" from 0 to 18 do {
            CBA_missionTime=4000+30*_i;[_patient] call ACM_infection_fnc_handleInfectionPFH;
        };
        [(_patient getVariable "ACM_infection_Infection_Stage")==2,"infection regressed before sustained treatment"] call _check;
        CBA_missionTime=4570;[_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Infection_Stage")==1,"current Ceftriaxone route could not treat infection"] call _check;
        [count _painCalls>0,"infection pain used missing native function"] call _check;
    ''')


def test_owner_handoff_before_replicated_deadlines_cannot_award_extra_treatment_or_pain():
    execute(setup() + '''
        _medCoverage set ["Moxifloxacin",1];
        _patient setVariable ["ACM_infection_Infection_Stage",3];
        _patient setVariable ["ACM_infection_Sepsis_Onset",3900];
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
        private _treatment=_patient getVariable "ACM_infection_Infection_TreatmentAccumulator";
        private _pain=count _painCalls;
        _patientLocal=false;CBA_missionTime=4002;[_patient] call ACM_infection_fnc_handleInfectionPFH;
        _patientLocal=true;CBA_missionTime=4004;[_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Infection_TreatmentAccumulator")==_treatment,
            "ownership transfer awarded an additional antibiotic check"] call _check;
        [count _painCalls==_pain,"ownership transfer repeated septic pain before deadline"] call _check;
    ''')
    worker = (I / "functions/fnc_handleInfectionPFH.sqf").read_text()
    sepsis = (I / "functions/fnc_handleSepsisPFH.sqf").read_text()
    assert 'setVariable [QGVAR(Infection_NextCheck), _now + 30, true]' in worker
    assert 'setVariable [QGVAR(Sepsis_NextPain), CBA_missionTime + 60, true]' in sepsis


@pytest.mark.parametrize("hardcore", [False, True])
def test_permanent_sepsis_only_latches_under_hardcore_and_requires_evacuation(hardcore):
    execute(setup() + f'missionNamespace setVariable ["ACME_hcEff_infection",{str(hardcore).lower()}];' + '''
        _patient setVariable ["ACM_infection_Infection_Stage",3];
        _patient setVariable ["ACM_infection_Sepsis_Onset",1];
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
    ''' + f'''
        [(_patient getVariable ["ACM_infection_Sepsis_Permanent",false]) isEqualTo {str(hardcore).lower()},
            "permanent sepsis ignored selected mode"] call _check;
        [(count _evacCalls>0) isEqualTo {str(hardcore).lower()},"evacuation latch ignored selected mode"] call _check;
    ''')


def test_permanent_sequelae_survive_stage_resolution_and_full_heal_clears_only_infection_source():
    execute(setup() + '''
        _patient setVariable ["ACM_infection_Sepsis_Permanent",true];
        _patient setVariable ["ACM_burns_HR_Adjust",17];
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Metabolic_Demand")>=1.08
            && {(_patient getVariable "ACM_infection_EffectiveVolumeDeficitL")>=.35},
            "field treatment cleared hardcore sequelae"] call _check;
        [_patient] call ACM_infection_fnc_fullHealLocal;
        [!(_patient getVariable "ACM_infection_Sepsis_Permanent")
            && {(_patient getVariable "ACM_infection_EffectiveVolumeDeficitL")==0}
            && {(_patient getVariable "ACM_infection_Coag_Mult")==1}
            && {ACM_infection_activePatients isEqualTo []},"full heal did not clear infection source and membership"] call _check;
        [(_patient getVariable "ACM_burns_HR_Adjust")==17,"infection reset erased unrelated pathology"] call _check;
    ''')


def test_naturally_healed_patient_retires_eligibility_and_neutralizes_drives_despite_residual_heat():
    execute(setup() + '''
        _patient setVariable ["ace_medical_bandagedWounds",createHashMap];
        _patient setVariable ["ACM_infection_Infection_EligibleTime",1];
        _patient setVariable ["ACM_infection_Infection_RiskAccumulator",.8];
        _patient setVariable ["ACME_hypo_temp",39];
        _patient setVariable ["ACM_infection_HR_Adjust",9];
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Infection_EligibleTime")==-1
            && {(_patient getVariable "ACM_infection_Infection_RiskAccumulator")==0}
            && {(_patient getVariable "ACM_infection_HR_Adjust")==0}
            && {(_patient getVariable "ACM_infection_RR_Adjust")==0}
            && {ACM_infection_activePatients isEqualTo []},"healthy patient retained ticking or stale infection drives"] call _check;
    ''')


def test_reopened_wound_retains_existing_infection_timeline():
    execute(setup() + '''
        _patient setVariable ["ace_medical_bandagedWounds",createHashMap];
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["leftarm",[[0,1]]]]];
        _patient setVariable ["ACM_infection_Infection_EligibleTime",1];
        _patient setVariable ["ACM_infection_Infection_RiskAccumulator",.8];
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Infection_EligibleTime")==1
            && {(_patient getVariable "ACM_infection_Infection_RiskAccumulator")==.8},
            "reopened wound lost its infection clock"] call _check;
    ''')


@pytest.mark.parametrize("operation", ["applyInfectionStage", "resetVariables", "initUnit", "handleInfectionPFH", "handleSepsisPFH"])
def test_nonowner_cannot_reset_advance_or_apply_infection(operation):
    execute(setup() + f'''
        _patient setVariable ["ACM_infection_Infection_Stage",3];
        _patientLocal=false;
        [_patient,0] call ACM_infection_fnc_{operation};
        [(_patient getVariable "ACM_infection_Infection_Stage")==3 && {{count _painCalls==0}}
            && {{count _medCalls==0}},"nonowner mutated infection or its medical effects"] call _check;
    ''')


def test_disabled_system_clears_derived_drives_without_erasing_durable_pathology():
    execute(setup() + '''
        _patient setVariable ["ACM_infection_Infection_Stage",3];
        _patient setVariable ["ACM_infection_Sepsis_Permanent",true];
        _patient setVariable ["ACM_infection_HR_Adjust",24];
        _patient setVariable ["ACM_infection_Coag_Mult",1.2];
        ACM_infection_infectionEnabled=false;
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Infection_Stage")==3
            && {_patient getVariable "ACM_infection_Sepsis_Permanent"},"temporary disable erased durable pathology"] call _check;
        [(_patient getVariable "ACM_infection_HR_Adjust")==0
            && {(_patient getVariable "ACM_infection_Coag_Mult")==1},"disabled source retained active physiology"] call _check;
    ''')


def test_replayed_runtime_registration_has_one_global_worker_and_full_heal_retires_its_registry():
    post = code((I / "XEH_postInit.sqf").read_text())
    execute(setup() + 'private _register={' + post + '};call _register;call _register;' + '''
        [count _handlers==1,"replayed initialization created duplicate infection workers"] call _check;
        _patient setVariable ["ACM_infection_Infection_Stage",2];
        [[],0] call (_handlers select 0 select 0);
        [ACM_infection_activePatients isEqualTo [_patient],"active infection was retired"] call _check;
        [_patient] call ACM_infection_fnc_fullHealLocal;
        [ACM_infection_activePatients isEqualTo [],"full heal retained registry membership"] call _check;
    ''')


@pytest.mark.parametrize("eligible", [-900, -2, 0])
def test_rebased_past_eligibility_is_due_rather_than_unset(eligible):
    execute(setup() + f'CBA_missionTime=12;_patient setVariable ["ACM_infection_Infection_EligibleTime",{eligible}];' + '''
        [abs (([_patient] call ACM_infection_fnc_getInfectionRisk)-.03)<.000001,
            "restored past eligibility was discarded"] call _check;
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
    ''' + f'''
        [(_patient getVariable "ACM_infection_Infection_EligibleTime")=={eligible},
            "restored past clock restarted its one-hour eligibility delay"] call _check;
    ''')


@pytest.mark.parametrize("deadline", [-90, 0])
def test_rebased_stage_deadline_progresses_once_when_overdue(deadline):
    execute(setup() + f'CBA_missionTime=12;_patient setVariable ["ACM_infection_Infection_NextStageTime",{deadline}];' + '''
        _patient setVariable ["ACM_infection_Infection_Stage",2];
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Infection_Stage")==3,
            "restored past stage deadline could not progress"] call _check;
        [(_patient getVariable "ACM_infection_Sepsis_Onset")==12,
            "new sepsis did not get current onset"] call _check;
    ''')


def test_rebased_established_sepsis_keeps_its_duration_and_hardcore_threshold():
    execute(setup() + '''
        CBA_missionTime=12;
        missionNamespace setVariable ["ACME_hcEff_infection",true];
        _patient setVariable ["ACM_infection_Infection_Stage",3];
        _patient setVariable ["ACM_infection_Sepsis_Onset",-1200];
        [_patient] call ACM_infection_fnc_handleInfectionPFH;
        [(_patient getVariable "ACM_infection_Sepsis_Onset")==-1200,
            "restore restarted established septic shock"] call _check;
        [_patient getVariable "ACM_infection_Sepsis_Permanent",
            "restored established shock lost elapsed evacuation threshold"] call _check;
        [abs ((_patient getVariable "ACM_infection_Sepsis_Severity")-.85)<.000001,
            "restored sepsis lost elapsed severity"] call _check;
    ''')


def test_rebased_eligible_casualty_stays_in_global_active_registry():
    post = code((I / "XEH_postInit.sqf").read_text())
    execute(setup() + 'private _register={' + post + '};call _register;' + '''
        CBA_missionTime=12;
        _patient setVariable ["ACM_infection_Infection_EligibleTime",-900];
        [[],0] call (_handlers select 0 select 0);
        [ACM_infection_activePatients isEqualTo [_patient],
            "negative restored eligibility was retired from runtime"] call _check;
    ''')


@pytest.mark.parametrize("new_period", [False, True])
def test_native_reconcile_enrolls_past_eligibility_without_resetting_durable_deadlines(new_period):
    execute(setup() + '''
        CBA_missionTime=12;
        ACM_infection_activePatients=[];
        _patient setVariable ["ACM_infection_Infection_EligibleTime",-900];
        _patient setVariable ["ACM_infection_Infection_NextCheck",40];
        _patient setVariable ["ACM_infection_Sepsis_NextPain",50];
    ''' + f'[_patient,{str(new_period).lower()},false] call ACM_infection_fnc_reconcile;' + '''
        [ACM_infection_activePatients isEqualTo [_patient],"native reconciliation missed restored infection timeline"] call _check;
        [(_patient getVariable "ACM_infection_Infection_NextCheck")==40
            && {(_patient getVariable "ACM_infection_Sepsis_NextPain")==50}
            && {count _medCalls==0},"native reconciliation restarted clocks or granted an extra progression check"] call _check;
        [_patient,false,false] call ACM_infection_fnc_reconcile;
        [count ACM_infection_activePatients==1,"native reconciliation duplicated membership"] call _check;
    ''')


@pytest.mark.parametrize("change", ["_patientLocal=false;", "_patientAlive=false;"])
def test_native_reconcile_cannot_advance_remote_or_dead_patient(change):
    execute(setup() + '''
        ACM_infection_activePatients=[];
        _patient setVariable ["ACM_infection_Infection_Stage",3];
    ''' + change + '''
        [_patient,true,false] call ACM_infection_fnc_reconcile;
        [ACM_infection_activePatients isEqualTo [] && {count _painCalls==0}
            && {count _medCalls==0},"remote/dead reconciliation advanced infection"] call _check;
    ''')


def test_native_registry_retirement_preserves_other_patients_and_durable_pathology():
    execute(setup() + '''
        ACM_infection_activePatients=[_patient,_medic];
        _patient setVariable ["ACM_infection_Infection_Stage",3];
        _patient setVariable ["ACM_infection_Sepsis_Permanent",true];
        [_patient,false,true] call ACM_infection_fnc_reconcile;
        [ACM_infection_activePatients isEqualTo [_medic]
            && {(_patient getVariable "ACM_infection_Infection_Stage")==3}
            && {_patient getVariable "ACM_infection_Sepsis_Permanent"},
            "retirement changed another membership or erased disease state"] call _check;
    ''')


def test_native_reconcile_keeps_healthy_patients_dormant_without_medication_work():
    execute(setup() + '''
        _patient setVariable ["ace_medical_bandagedWounds",createHashMap];
        [_patient,true,false] call ACM_infection_fnc_reconcile;
        [ACM_infection_activePatients isEqualTo [] && {count _medCalls==0}
            && {count _painCalls==0},"healthy reconciliation retained registry or performed treatment work"] call _check;
    ''')
