"""Execute recovery eligibility, support races, and native adjunct/drainage physiology.

Reuses B215's explicit engine/owner boundaries. No live blend or clinical calibration
is claimed; the production recovery and native blood/vomit worker bodies execute.
"""
import re

import pytest

import test_b215_recovery_position as recovery
from test_b156_reset_lifecycle import native
from test_b65_zone3_reboa_smart_bandage import cfg_class
from test_menu_death_lifecycle import ROOT, adapt, execute


ADJUNCTS = [
    ("none", ""),
    ("OPA", '_patient setVariable ["ACM_airway_AirwayItem_Oral","OPA"];'),
    ("NPA", '_patient setVariable ["ACM_airway_AirwayItem_Nasal","NPA"];'),
    ("OPA_NPA", '_patient setVariable ["ACM_airway_AirwayItem_Oral","OPA"]; _patient setVariable ["ACM_airway_AirwayItem_Nasal","NPA"];'),
    ("SGA", '_patient setVariable ["ACM_airway_AirwayItem_Oral","SGA"];'),
    ("ETT", '_patient setVariable ["ACME_ETT_Inserted",true];'),
    ("surgical", '_patient setVariable ["ACM_airway_SurgicalAirway_TubeInserted",true];'),
]
SUPPORT = [
    ("ventilator", '_patient setVariable ["ACME_vent_driving",true];'),
    ("CPR", "_cpr=true;"),
    ("BVM", "_bvm=true;"),
]


def menu_condition():
    cfg = (ROOT / "addons/acm_extended/config.cpp").read_text()
    block = cfg.split("class RecoveryPosition: CheckAirway {", 1)[1].split("\n    };", 1)[0]
    condition = re.search(r'condition\s*=\s*"([^"]+)";', block)[1]
    # Actual config passes the object directly; normalize only this fixture's ACE wrapper.
    condition = condition.replace("_patient call ace_common_fnc_isAwake", "[_patient] call ace_common_fnc_isAwake")
    condition = condition.replace("alive (_patient getVariable ['ACM_breathing_BVM_Medic',objNull])", "_bvm")
    return adapt(condition)


@pytest.mark.parametrize("label,adjunct", ADJUNCTS, ids=[x[0] for x in ADJUNCTS])
def test_fitted_adjunct_is_eligible_and_survives_successful_recovery(label, adjunct):
    execute(recovery.setup() + adjunct + "ACM_airway_enable=true;" +
            "[call {" + menu_condition() + "},'fitted adjunct hidden by menu'] call _check;" +
            recovery.begin() + '''
        private _oral=_patient getVariable ["ACM_airway_AirwayItem_Oral",""];
        private _nasal=_patient getVariable ["ACM_airway_AirwayItem_Nasal",""];
        private _ett=_patient getVariable ["ACME_ETT_Inserted",false];
        private _surgical=_patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted",false];
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"fitted adjunct prevented recovery commit"] call _check;
        [(_patient getVariable ["ACM_airway_AirwayItem_Oral",""])==_oral && {(_patient getVariable ["ACM_airway_AirwayItem_Nasal",""])==_nasal},"recovery removed an adjunct"] call _check;
        [(_patient getVariable ["ACME_ETT_Inserted",false])==_ett && {(_patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted",false])==_surgical},"recovery removed an advanced airway"] call _check;
    ''')


@pytest.mark.parametrize("label,support", SUPPORT, ids=[x[0] for x in SUPPORT])
def test_active_support_is_rejected_by_menu_progress_and_owner_begin(label, support):
    execute(recovery.setup() + '''
        private _args=[_medic,_patient,"Body","RecoveryPosition"];
        _args call ACME_fnc_recoveryPositionStart;
        ACM_airway_enable=true;
    ''' + support + "[!(call {" + menu_condition() + "}),'active support still eligible'] call _check;" + '''
        [!([_args] call ACME_fnc_recoveryPositionProgress),"progress accepted active support"] call _check;
        [_medic,_patient,true,false,"begin","direct"] call ACM_airway_fnc_setRecoveryPosition;
        [count _handlers==0 && {count _moves==0},"owner began recovery during active support"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"rejected begin retained pending work"] call _check;
    ''')


@pytest.mark.parametrize("label,support", SUPPORT, ids=[x[0] for x in SUPPORT])
@pytest.mark.parametrize("phase", ["commit", "apply", "worker"])
def test_support_race_cancels_only_the_matching_pending_transaction(label, support, phase):
    dispatch = "call _run;" if phase == "worker" else f'[_medic,_patient,true,false,"{phase}","one"] call ACM_airway_fnc_setRecoveryPosition;'
    execute(recovery.setup() + recovery.begin() + '''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=11;
        _patient setVariable ["ACME_patientAnimLock",["successor","support","other",5,100]];
        _moves=[];
    ''' + support + dispatch + '''
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"support race committed recovery"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"support race retained pending recovery"] call _check;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="successor" && {count _moves==0},"recovery cleanup interrupted support successor"] call _check;
        [count _logs==0,"rejected recovery logged success"] call _check;
    ''')


@pytest.mark.parametrize("label,support", SUPPORT, ids=[x[0] for x in SUPPORT])
def test_support_retires_established_recovery_without_reposing_successor(label, support):
    execute(recovery.setup() + recovery.begin() + '''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run;
        _patient setVariable ["ACME_patientAnimLock",["successor","support","other",5,100]];
        _patientAnim="support-pose"; _moves=[];
    ''' + support + '''
        call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"active support retained recovery airway credit"] call _check;
        [!(_patient getVariable ["ACM_airway_HeadTilt_State",false]),"old recovery head-tilt credit survived"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Episode","bad"])=="","old recovery episode survived"] call _check;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="successor" && {count _moves==0},"recovery retirement moved successor"] call _check;
        [count _logs==1 && {!((_handlers select 0) select 2)},"silent support handoff logged cancellation or retained watcher"] call _check;
    ''')


@pytest.mark.parametrize("label,support", SUPPORT, ids=[x[0] for x in SUPPORT])
def test_established_owner_transfer_rechecks_live_support_on_new_owner(label, support):
    execute(recovery.setup() + recovery.begin() + '''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run;
        _patientLocal=false; _moves=[]; call _run;
        [count _events==1 && {(_events select 0 select 0)=="ACM_airway_handleRecoveryPosition"},"established watcher did not transfer"] call _check;
        [!((_handlers select 0) select 2) && {_patient getVariable ["ACM_airway_RecoveryPosition_State",false]},"departed owner mutated recovery evidence"] call _check;
        _patientLocal=true;
    ''' + support + '''
        (_events select 0 select 1) call ACM_airway_fnc_handleRecoveryPosition;
        private _h=_handlers select 1; [_h select 1,1] call (_h select 0);
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"new owner retained recovery during active support"] call _check;
        [count _moves==0 && {!((_handlers select 1) select 2)},"owner transfer forced a pose or retained invalid watcher"] call _check;
    ''')


def test_rejected_stale_commit_does_not_cancel_new_pending_token():
    execute(recovery.setup() + recovery.begin() + '''
        _patient setVariable ["ACME_vent_driving",true];
        [_medic,_patient,true,false,"commit","old"] call ACM_airway_fnc_setRecoveryPosition;
        [((_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) select 0)=="one","stale blocked commit cancelled successor"] call _check;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="one","stale blocked commit released successor pose"] call _check;
    ''')


def physiology_setup():
    code = recovery.setup() + '''
        _patient setVariable ["ACE_isUnconscious",true];
        ACM_airway_airwayObstructionBloodChance=100;
        ACM_airway_airwayObstructionVomitChance=100;
        CBA_missionTime=100;
        private _linear={params ["_lo","_hi","_x","_a","_b",["_clamp",false]];
            private _f=(_x-_lo)/(_hi-_lo); if (_clamp) then {_f=(_f max 0) min 1;}; _a+(_f*(_b-_a))};
        ACM_damage_fnc_isBodyPartBleeding={true};
        ACM_damage_fnc_getBodyPartBleeding={1};
        ACM_circulation_fnc_getNauseaMedicationEffects={0};
        private _sounds=[];
        private _runWorker={private _h=_handlers select _this;
            if (_h select 2) then {[_h select 1,_this] call (_h select 0);};};
    '''
    for name in ["setAirwayState", "handleAirwayObstruction_Blood", "handleAirwayObstruction_Vomit", "getAirwayState"]:
        source = native("airway", name)
        # Sound output and engine position are the only removed vomiting boundaries.
        source = re.sub(r'playSound3D \[[^;]+;', '_sounds pushBack "vomit";', source)
        code += "ACM_airway_fnc_" + name + "={" + source + "};"
    return code


@pytest.mark.parametrize("label,adjunct", ADJUNCTS[1:4], ids=[x[0] for x in ADJUNCTS[1:4]])
@pytest.mark.parametrize("substance", ["Blood", "Vomit"])
def test_basic_adjunct_does_not_stop_secretions_but_recovery_drains_new_events(label, adjunct, substance):
    fn = "ACM_airway_fnc_handleAirwayObstruction_" + substance
    state = "ACM_airway_AirwayObstruction" + substance + "_State"
    execute(physiology_setup() + adjunct + '''
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",3];
        _patient setVariable ["ACM_airway_AirwayCollapse_State",1];
        [([_patient] call ACM_airway_fnc_getAirwayState)>=0.95,"basic adjunct lost mild-collapse benefit"] call _check;
    ''' + f'[_patient] call {fn}; 0 call _runWorker;' + f'''
        [(_patient getVariable ["{state}",0])==1,"basic adjunct incorrectly prevented secretions"] call _check;
        [([_patient] call ACM_airway_fnc_getAirwayState)==0,"basic adjunct bypassed accumulated secretions"] call _check;
        [_medic,_patient,true,false,"begin","drain"] call ACM_airway_fnc_setRecoveryPosition;
        1 call _runWorker; _patientAnim="acm_recoveryposition"; 1 call _runWorker;
        [_medic,_patient,true,false,"commit","drain"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; 1 call _runWorker;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"recovery did not establish"] call _check;
        [(_patient getVariable ["{state}",-1])==0,"native mild obstruction did not drain"] call _check;
        [([_patient] call ACM_airway_fnc_getAirwayState)>=0.97,"adjunct with recovery lost airway benefit"] call _check;
        CBA_missionTime=130; 0 call _runWorker;
        [(_patient getVariable ["{state}",-1])==0,"new secretions obstructed while in recovery"] call _check;
    ''' + ('''
        [(_patient getVariable ["ACM_airway_AirwayObstructionVomit_Count",-1])==1 && {count _sounds==2},"recovery stopped vomiting instead of permitting drainage"] call _check;
    ''' if substance == "Vomit" else ""))


@pytest.mark.parametrize("label,adjunct", ADJUNCTS[1:4], ids=[x[0] for x in ADJUNCTS[1:4]])
@pytest.mark.parametrize("severity", [2, 3])
def test_recovery_never_erases_major_established_obstruction(label, adjunct, severity):
    execute(physiology_setup() + adjunct + f'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",{severity}];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",{severity}];
    ''' + recovery.begin() + '''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"obstruction prevented positioning"] call _check;
    ''' + f'''
        [(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",0])=={severity} && {{(_patient getVariable ["ACM_airway_AirwayObstructionVomit_State",0])=={severity}}},"positioning erased major established obstruction"] call _check;
        [([_patient] call ACM_airway_fnc_getAirwayState)==0,"major obstruction no longer requires clearance"] call _check;
    ''')


def insertion_patient_start(classname):
    """Run the production native patient-start block with actual inherited config flags.

    Configuration queries and the animation lease request are engine boundaries;
    cancellation, body-part fallback, recovery pose exclusion, and adjunct insertion
    are production SQF. Body also probes the native fallback beyond the Head UI route.
    """
    cfg = (ROOT / "addons/acm_extended/config.cpp").read_text()
    blocks = [cfg_class(cfg, "InsertOPA")]
    if classname != "InsertOPA":
        block = cfg_class(cfg, classname)
        assert f"class {classname}: InsertOPA" in block
        blocks.append(block)
    flags = {}
    for block in blocks:
        for key, value in re.findall(r'\b(ACM_cancelRecovery|ACM_rollToBack|ACME_neverRollToBack)\s*=\s*([01])\s*;', block):
            flags[key] = value
    assert len(flags) == 3, "adjunct positioning policy must be explicit or inherited"
    source = (ROOT / "addons/core/functions/fnc_treatmentNative.sqf").read_text()
    source = source[source.index("private _rollToBack = false;"):source.index("if (_medic isNotEqualTo player")]
    for key, value in flags.items():
        source = source.replace(f'isNumber (_config >> "{key}")', "true")
        source = source.replace(f'getNumber (_config >> "{key}")', value)
    source = source.replace('isNumber (_config >> "ACM_ignoreAnimCoef")', "false")
    source = source.replace('getNumber (_config >> "ACM_ignoreAnimCoef")', "0")
    source = source.replace('getArray (_config >> "animationPatientUnconsciousExcludeOn")', "[]")
    source = source.replace('isText (_config >> "animationPatientUnconscious")', "true")
    source = source.replace('getText (_config >> "animationPatientUnconscious")', '""')
    source = source.replace("IS_UNCONSCIOUS(_patient)", "_patientUnconscious")
    source = source.replace("animationState _patient", "_patientAnim")
    header = (ROOT / "addons/main/script_macros.hpp").read_text()
    lying = re.search(r'^#define LYING_ANIMATION\s+(.+)$', header, re.M)[1]
    source = source.replace("LYING_ANIMATION", lying)
    insertion = native("airway", "insertAirwayItem")
    insertion = insertion.replace("GET_AIRWAY_INFLAMMATION(_patient)", '(_patient getVariable ["ACM_CBRN_AirwayInflammation",0])')
    threshold = re.search(r'^#define AIRWAY_INFLAMMATION_THRESHOLD_SERIOUS\s+(\d+)', header, re.M)[1]
    insertion = insertion.replace("AIRWAY_INFLAMMATION_THRESHOLD_SERIOUS", threshold)
    callback = re.search(r'callbackSuccess\s*=\s*"([^"]+)";', blocks[-1])[1]
    return '''
        private _patientRequests=[]; private _returned=[];
        private _isSelf=false; private _treatmentTime=3;
        _patient setVariable ["ACE_isUnconscious",true];
        ACME_fnc_patientAnimRequest={_patientRequests pushBack +_this; "lease"};
        ace_common_fnc_addToInventory={_returned pushBack +_this;};
        ace_medical_treatment_fnc_addToTriageCard={};
    ''' + "ACM_airway_fnc_insertAirwayItem={" + insertion + "};" + \
        "private _nativePatientStart={" + adapt(source) + "[_rollToBack,_cancelsRecoveryPosition]};" + \
        "private _insertSuccess={" + callback + "};"


@pytest.mark.parametrize("classname,slot,adjunct", [
    ("InsertOPA", "Oral", "OPA"), ("InsertNPA", "Nasal", "NPA"),
])
@pytest.mark.parametrize("part", ["Head", "Body"])
def test_native_basic_adjunct_insertion_preserves_existing_recovery(classname, slot, adjunct, part):
    execute(recovery.setup() + recovery.begin() + '''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run; _moves=[];
    ''' + insertion_patient_start(classname) + f'''
        private _bodyPart="{part}"; private _classname="{classname}";
        private _flags=call _nativePatientStart;
        [_flags isEqualTo [false,false],"basic adjunct inherited roll or cancellation"] call _check;
        [count _patientRequests==0 && {{count _moves==0}},"basic adjunct moved patient out of recovery"] call _check;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"basic adjunct start cleared recovery"] call _check;
        [_medic,_patient,_bodyPart,_classname] call _insertSuccess;
        [(_patient getVariable ["ACM_airway_AirwayItem_{slot}",""])=="{adjunct}" && {{count _returned==0}},"adjunct did not insert while in recovery"] call _check;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"adjunct success cleared recovery"] call _check;
        [_patient getVariable ["ACM_airway_HeadTilt_State",false],"adjunct cleared recovery airway credit"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Episode",""])=="one","adjunct replaced recovery episode"] call _check;
    ''')


@pytest.mark.parametrize("part", ["Head", "Body"])
def test_native_igel_insertion_retains_supine_placement_sequence(part):
    execute(recovery.setup() + recovery.begin() + '''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run; _moves=[];
    ''' + insertion_patient_start("InsertIGel") + f'''
        private _bodyPart="{part}"; private _classname="InsertIGel";
        private _flags=call _nativePatientStart;
        [_flags isEqualTo [true,true],"i-gel inherited basic-adjunct positioning exemption"] call _check;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"i-gel placement retained recovery"] call _check;
        [count _patientRequests==1 && {{(_patientRequests select 0 select 1)=="AinjPpneMstpSnonWrflDnon_rolltoback"}},"i-gel omitted supine placement request"] call _check;
        [_medic,_patient,_bodyPart,_classname] call _insertSuccess;
        [(_patient getVariable ["ACM_airway_AirwayItem_Oral",""])=="SGA" && {{count _returned==0}},"i-gel success lost native insertion"] call _check;
    ''')
