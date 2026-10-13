"""Execute owner recovery after locality/public-variable delivery is reordered.

The full ownerRegister, recovery predicate, idle discovery and shared recovery
PFH run from production SQF. Native airway/arrest worker creation also executes
production. Objects, transport and CBA schedules are explicit engine boundaries;
this is not a simulation of Arma's real dedicated-server packet delivery.
"""
from pathlib import Path
import re

import pytest

from source_scan import lex, matching
from test_b156_reset_lifecycle import native
from test_b281_flight_scheduler import adapt, fixture
from test_menu_death_lifecycle import execute

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def recovery_body():
    text = source("ownerInit")
    tokens = lex(text)
    pairs = matching(tokens)
    start = text.index('[{\n    [] call ACME_fnc_aiProtectionTick;') + 1
    opening = next(i for i, token in enumerate(tokens) if token.offset == start)
    # Execute the entire shared PFH, including missing-owner audit, new late
    # state recovery, provider reconciliation and registry pruning.
    return text[tokens[opening].offset + 1:tokens[pairs[opening]].offset]


def engine(text):
    text = re.sub(r'\bvalues (_\w+)', r'((keys \1) apply {\1 get _x})', text)
    text = re.sub(r'(\([^()]*\)|_\w+)\s+isEqualType objNull',
                  r'(\1 isEqualTo objNull || {\1 isEqualType profileNamespace})', text)
    text = re.sub(r'objNull,\s*\[objNull\]', 'objNull, [profileNamespace]', text)
    text = re.sub(r'\bisNull (\([^()\n]*\))', r'(\1 isEqualTo objNull)', text)
    text = re.sub(r'\bfinite (\([^()\n]*\))', r'(\1 call _finite)', text)
    text = text.replace('serverTime', '_serverNow')
    return (adapt(text).replace("owner _patient", "7")
            .replace("owner _x", "7").replace("allUnits", "[_patient]")
            .replace("hasInterface", "false"))


def setup():
    # Only unrelated treatment/visual/audio boundaries are omitted. Enrollment,
    # worker existence and native worker creation remain actual production code.
    noops = (
        "piggybackRecover", "lineWarmerRecover", "aiProtectionSync",
        "transientStateReconcile", "coagulationTick", "ptxEnsure",
        "clinicalBagRecover", "aiProtectionTick", "lineWarmerReturnsTick",
        "providerStateReconcile",
    )
    result = fixture() + "".join(f"ACME_fnc_{name}={{}};\n" for name in noops)
    result += r'''
        private _patientLocal=true;
        private _serverNow=10;
        private _registerCalls=[];
        CBA_fnc_serverEvent={_events pushBack _this;};
        ACM_circulation_fnc_updateCirculationState={};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",1]};
        ACM_Rhythm_Asystole=1; ACM_Rhythm_Sinus=0; ACM_Rhythm_PEA=5;
        ACM_Rhythm_VF=2; ACM_Rhythm_PVT=3; ACM_Rhythm_VT=4;
        ACM_ASYSTOLE_BLOODVOLUME=3.5;
        ACME_fnc_headElevWatch={(_this select 0) setVariable ["ACME_headElev_pfh",88];
            (_this select 0) setVariable ["ACME_headElev_killEH",89];};
        ACME_fnc_thoraPassiveDrain={(_this select 0) setVariable ["ACME_thora_drainPFH",88];};
        ACME_fnc_aajtDownedTick={(_this select 0) setVariable ["ACME_AAJT_downedPFH",88];};
        ACME_fnc_aajtPainTick={(_this select 0) setVariable ["ACME_AAJT_painPFH",88];};
        ACME_fnc_junctionalResume={params ["_p"];
            if ((["leftarm","rightarm","leftleg","rightleg"] findIf {
                (_p getVariable [format ["ACME_Junc_%1",_x],""]) in ["open","packed","xstat"]
            }) >= 0) then {_p setVariable ["ACME_juncPFH",88];};
        };
    '''
    for component, name in (
        ("airway", "handleAirwayObstruction_Vomit"),
        ("airway", "handleAirwayCollapse"),
        ("airway", "handleAirwayObstruction_Blood"),
        ("circulation", "handleHemolyticReaction"),
        ("circulation", "handleCardiacArrest"),
        ("circulation", "handleReversibleCardiacArrest"),
        ("circulation", "handleCPR"),
        ("circulation", "cprSessionValid"),
    ):
        result += f"ACM_{component}_fnc_{name}={{" + native(component, name) + "};\n"
    result += "ACME_fnc_aspirationState={" + engine(source("aspirationState")) + "};\n"
    result += "ACME_fnc_ownerRegisterNeedsRecovery={" + engine(source("ownerRegisterNeedsRecovery")) + "};\n"
    result += "ACME_fnc_ventBatteryRequest={" + engine(source("ventBatteryRequest")) + "};\n"
    result += "private _ownerRegister={" + engine(source("ownerRegister")) + "};\n"
    result += "private _sharedTick={" + engine(recovery_body()) + "};\n"
    return result + r'''
        ACME_fnc_ownerRegister={_registerCalls pushBack (_this select 0);_this call _ownerRegister;};
        // A complete first owner event preceded the late clinical packet.
        ACME_clinical_ownedUnits=[];
        [_patient] call ACME_fnc_ownerRegister;
        CBA_missionTime=10.01;[_patient] call ACME_fnc_ownerRegister;
        CBA_missionTime=10.5;[_patient] call ACME_fnc_ownerRegister;
        _registerCalls=[];_events=[];
        CBA_missionTime=12;
    '''


@pytest.mark.parametrize("registry,flag", [
    ("ACME_nrb_activePatients", "ACME_nrb_on"),
    ("ACME_hpmk_activePatients", "ACME_hpmk_on"),
    ("ACME_tbi_activePatients", "ACME_tbi_HasTBI"),
    ("ACME_cs_activePatients", "ACME_cs_active"),
    ("ACME_autoBP_patients", "ACME_autoBP_Active"),
])
def test_late_treatment_flag_recovers_registry_once(registry, flag):
    execute(setup() + f'''
        ACME_clinical_activePatients=[_patient];
        _patient setVariable ["{flag}",true];
        [] call ACME_fnc_idlePhysDiscovery;call _sharedTick;
        [_patient in (missionNamespace getVariable ["{registry}",[]]),"late flag lost local enrollment"] call _check;
        [count _registerCalls==1,"late clinical state did not trigger exactly one recovery"] call _check;
        for "_i" from 13 to 90 do {{CBA_missionTime=_i;call ACME_fnc_idlePhysDiscovery;call _sharedTick;}};
        [count _registerCalls==1,"known active owner was rebuilt periodically"] call _check;
    ''')


@pytest.mark.parametrize("flag,handle", [
    ("ACME_nativeVomitActive", "ACM_airway_AirwayObstructionVomit_PFH"),
    ("ACME_nativeCollapseActive", "ACM_airway_AirwayCollapse_PFH"),
    ("ACME_nativeBloodObstructionActive", "ACM_airway_AirwayObstructionBlood_PFH"),
    ("ACME_nativeHemolysisActive", "ACM_circulation_HemolyticReaction_PFH"),
])
def test_late_active_native_worker_creates_real_production_worker_once(flag, handle):
    execute(setup() + f'''
        ACME_clinical_activePatients=[_patient];
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",2];
        _patient setVariable ["{flag}",true];
        call _sharedTick;
        [(_patient getVariable ["{handle}",-1])>=0,"late active evidence never created native worker"] call _check;
        [count _handlers==1 && {{count _registerCalls==1}},"recovery created duplicate native work"] call _check;
        for "_i" from 13 to 90 do {{CBA_missionTime=_i;call ACME_fnc_idlePhysDiscovery;call _sharedTick;}};
        [count _handlers==1 && {{count _registerCalls==1}},"live native worker repeatedly restarted"] call _check;
    ''')


@pytest.mark.parametrize("rhythm", [2, 3, 4, 5])
def test_late_arrest_preserves_real_native_rhythm_and_deterioration_deadline(rhythm):
    handle = ("ACM_circulation_ReversibleCardiacArrest_PFH" if rhythm == 5
              else "ACM_circulation_CardiacArrest_PFH")
    execute(setup() + f'''
        ACME_clinical_activePatients=[_patient];
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        _patient setVariable ["ACM_circulation_Cardiac_RhythmState",{rhythm}];
        _patient setVariable ["ACM_circulation_CardiacArrest_DeteriorationTime",5];
        _patient setVariable ["ACM_circulation_ReversibleCardiacArrest_Time",6];
        _patient setVariable ["ACME_peaElectricalHR",82];
        call _sharedTick;
        [(_patient getVariable ["{handle}",-1])>=0,"native arrest worker was not recovered"] call _check;
        [(_patient getVariable ["ACM_circulation_Cardiac_RhythmState",0])=={rhythm},"recovery rerolled arrest rhythm"] call _check;
        [(_patient getVariable ["ACM_circulation_CardiacArrest_DeteriorationTime",-1])==5,
            "recovery restarted arrest deterioration time"] call _check;
        [(_patient getVariable ["ACM_circulation_ReversibleCardiacArrest_Time",-1])==6,
            "recovery restarted PEA deadline"] call _check;
        [(_patient getVariable ["ACME_peaElectricalHR",-1])==82,
            "recovery rerolled existing electrical heart rate"] call _check;
        CBA_missionTime=90;call _sharedTick;
        [count _handlers==1 && {{count _registerCalls==1}},"stalled owner replayed recovered arrest"] call _check;
    ''')


@pytest.mark.parametrize("field,value", [
    ("ACM_breathing_Pneumothorax_State", "0.5"),
    ("ACM_breathing_ChestInjury_State", "true"),
    ("ACME_suctionExposure", "0.3"),
    ("ACME_o2Drain_suction", "1"),
    ("ACME_laryngo_irritationUntil", "50"),
    ("ACME_vent_connected", "true"),
    ("ACME_ETT_Inserted", "true"),
])
def test_late_general_clinical_indication_enrolls_independent_maintenance(field, value):
    execute(setup() + f'''
        _patient setVariable ["{field}",{value}];call _sharedTick;
        [_patient in ACME_clinical_activePatients,"late general indication lost independent maintenance"] call _check;
        [count _registerCalls==1,"general clinical recovery did not occur once"] call _check;
    ''')


@pytest.mark.parametrize("field,value,handles", [
    ("ACME_thora_tube_left", "true", ["ACME_thora_drainPFH"]),
    ("ACME_headElevated", "true", ["ACME_headElev_pfh", "ACME_headElev_killEH"]),
    ("ACME_AAJT_zone3", "true", ["ACME_AAJT_downedPFH", "ACME_AAJT_painPFH"]),
    ("ACME_AAJT_axillaright", "true", ["ACME_AAJT_painPFH"]),
    ("ACME_Junc_rightleg", '"packed"', ["ACME_juncPFH"]),
])
def test_late_device_flag_recovers_missing_local_handle(field, value, handles):
    checks = "".join(f'[(_patient getVariable ["{handle}",-1])>=0,"missing device worker {handle}"] call _check;'
                     for handle in handles)
    execute(setup() + f'_patient setVariable ["{field}",{value}];call _sharedTick;' + checks + r'''
        CBA_missionTime=90;call _sharedTick;
        [count _registerCalls==1,"late device flag repeatedly created handlers"] call _check;
    ''')


def test_healthy_ground_owner_remains_read_only_across_two_recovery_sweeps():
    execute(setup() + r'''
        private _before=allVariables _patient;
        for "_i" from 12 to 90 do {CBA_missionTime=_i;call ACME_fnc_idlePhysDiscovery;call _sharedTick;};
        [count _registerCalls==0 && {count _events==0} && {count _handlers==0},
            "healthy owner produced registration, network events or workers"] call _check;
        [allVariables _patient isEqualTo _before,"healthy recovery wrote local state"] call _check;
        [_airReads==0,"healthy recovery requested airframe/geometry"] call _check;
    ''')


def test_stomach_contents_and_nonarrest_rhythm_never_start_a_new_native_episode():
    execute(setup() + r'''
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",2];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",1];
        _patient setVariable ["ACM_circulation_Cardiac_RhythmState",4];
        for "_i" from 12 to 90 do {CBA_missionTime=_i;call _sharedTick;};
        [count _registerCalls==0 && {count _handlers==0},"historical contents/rhythm guessed a new native episode"] call _check;
    ''')


@pytest.mark.parametrize("guard", ["restore", "nonlocal", "dead"])
def test_recovery_respects_restore_locality_and_death_before_enrollment(guard):
    field = {"restore": "ACME_clinicalRestoring", "nonlocal": "fixtureLocal", "dead": "fixtureAlive"}[guard]
    value = "true" if guard == "restore" else "false"
    execute(setup() + f'''
        _patient setVariable ["ACME_nativeCollapseActive",true];
        _patient setVariable ["{field}",{value}];
        [!([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"invalid owner passed recovery predicate"] call _check;
        call _sharedTick;
        [count _registerCalls==0 && {{count _handlers==0}},"invalid owner started clinical recovery"] call _check;
    ''')


def test_reset_clears_live_evidence_and_later_new_episode_can_recover():
    execute(setup() + r'''
        _patient setVariable ["ACME_nativeVomitActive",false];
        _patient setVariable ["ACME_clinicalEpoch",2];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",2];
        call _sharedTick;
        [count _handlers==0,"reset history recreated native vomiting"] call _check;
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_nativeVomitActive",true];call _sharedTick;
        [count _handlers==1,"new live episode failed to recover"] call _check;
        private _args=(_handlers select 0) select 1;
        [(_args select 1)==2,"new worker adopted obsolete reset epoch"] call _check;
    ''')


def test_late_state_after_long_scheduler_stall_recovers_once_without_replaying_tick_time():
    execute(setup() + r'''
        CBA_missionTime=240;
        _patient setVariable ["ACME_nrb_on",true];
        _patient setVariable ["ACME_hpmk_on",true];call _sharedTick;
        [(_patient getVariable ["ACME_nrb_lastTickLocal",-1])==240,
            "late NRB recovery granted a catch-up oxygen bolus"] call _check;
        [(_patient getVariable ["ACME_hpmk_lastTickLocal",-1])==240,
            "late HPMK recovery granted a catch-up heat bolus"] call _check;
        call _sharedTick;
        [count _registerCalls==1,"scheduler stall caused repeated clinical rebuild"] call _check;
    ''')


def test_production_recovery_predicate_has_no_mutating_or_geometry_commands():
    values = [token.value for token in lex(source("ownerRegisterNeedsRecovery")) if token.kind == "ident"]
    assert not set(values) & {"setVariable", "setPosWorld", "setVelocity", "lineIntersectsSurfaces", "allUnits"}
    assert not any(value.startswith("CBA_fnc_") for value in values)


@pytest.mark.parametrize("order", [
    ("row", "session", "provider"), ("row", "provider", "session"),
    ("session", "row", "provider"), ("session", "provider", "row"),
    ("provider", "row", "session"), ("provider", "session", "row"),
])
def test_cpr_clinical_recovery_waits_for_separate_grant_session_provider_replicas(order):
    steps = {
        "row": '_patient setVariable ["ACME_resus_cpr",_grant];',
        "session": '_patient setVariable ["ACM_circulation_CPR_session",[_medic,5]];',
        "provider": '_patient setVariable ["ace_medical_CPR_provider",_medic];',
    }
    case = setup() + r'''
        ACME_clinical_activePatients=[_patient];
        _serverNow=500;CBA_missionTime=100;
        private _grant=[_medic,"accepted-cpr",1,7,0,5,600,true,10,482,-1];
    '''
    for i, step in enumerate(order):
        case += steps[step] + 'call _sharedTick;\n'
        if i < 2:
            case += '[count _handlers==0 && {count _registerCalls==0},"partial CPR replicas started clinical processing"] call _check;\n'
    case += r'''
        [count _handlers==1 && {count _registerCalls==1},"complete accepted CPR replicas failed to enroll"] call _check;
        private _args=(_handlers select 0) select 1;
        [(_args select 1)==82 && {(_args select 2) isEqualTo _grant},
            "CPR recovery restarted elapsed time or changed accepted identity"] call _check;
        CBA_missionTime=101;_serverNow=501;call _sharedTick;
        [count _handlers==1 && {count _registerCalls==1},"live CPR identity repeatedly restarted clinical worker"] call _check;
    '''
    execute(case)


@pytest.mark.parametrize("invalid", [
    '_grant set [7,false];', '_grant set [9,-1];', '_grant set [2,2];',
    '_patient setVariable ["ACM_circulation_CPR_session",[_medic,6]];',
    '_patient setVariable ["ace_medical_CPR_provider",missionNamespace];',
    '_grant set [0,13];',
])
def test_cpr_recovery_never_guesses_an_unactivated_stale_or_unrelated_native_episode(invalid):
    execute(setup() + r'''
        ACME_clinical_activePatients=[_patient];
        _serverNow=500;CBA_missionTime=100;
        private _grant=[_medic,"accepted-cpr",1,7,0,5,600,true,10,482,-1];
        _patient setVariable ["ACM_circulation_CPR_session",[_medic,5]];
        _patient setVariable ["ace_medical_CPR_provider",_medic];
    ''' + invalid + r'''
        _patient setVariable ["ACME_resus_cpr",_grant];call _sharedTick;
        [count _handlers==0 && {count _registerCalls==0},"invalid grant/native identity started clinical CPR"] call _check;
    ''')


def test_cpr_ownership_generation_replaces_stale_worker_and_old_callback_cannot_clear_successor():
    execute(setup() + r'''
        ACME_clinical_activePatients=[_patient];
        _serverNow=500;CBA_missionTime=100;
        private _grant=[_medic,"accepted-cpr",1,7,0,5,600,true,10,482,-1];
        _patient setVariable ["ACM_circulation_CPR_session",[_medic,5]];
        _patient setVariable ["ace_medical_CPR_provider",_medic];
        _patient setVariable ["ACME_resus_cpr",_grant];call _sharedTick;
        _patient setVariable ["ACME_providerLocalityEpoch",2];call _sharedTick;
        [count _handlers==2 && {!((_handlers select 0) select 2)},"new ownership failed to replace old CPR worker"] call _check;
        [(_patient getVariable ["ACM_circulation_CPR_PFH",-1])==1,"new CPR handle was not installed"] call _check;
        private _old=_handlers select 0;[_old select 1,0] call (_old select 0);
        [(_patient getVariable ["ACM_circulation_CPR_PFH",-1])==1 && {(_handlers select 1) select 2},
            "departed CPR callback cleared its successor"] call _check;
    ''')
