"""Execute completed clinical maintenance, retirement and late-owner enrollment.

The entire production circHandle, shared indication, owner registration/recovery
and selected cleanup/drug workers execute. Native vitals, waking, transport and
unrelated device workers are explicit boundaries. This does not certify engine
multiplayer scheduling or reproduce every clinical subsystem in SQF-VM.
"""
import re

import pytest

from test_b282_owner_recovery_execution import engine, setup as recovery_setup, source
from test_menu_death_lifecycle import execute


def setup():
    real = {"clinicalEpoch", "clinicalNeedsTick", "clinicalTickDelta", "setVarNet", "setVarNetApprox",
            "circStateCommit", "medicationDriveTick", "ketamineSedationTick", "ettMainstemTick", "ettObstructTick", "hcCircTick"}
    boundaries = sorted(set(re.findall(r'call (ACME_fnc_\w+)', source('circHandle'))) - {f'ACME_fnc_{name}' for name in real})
    code = recovery_setup() + 'private _maintenanceCalls=[];\n'
    code += ''.join(f'{name}={{_maintenanceCalls pushBack "{name}";}};\n' for name in boundaries)
    code += r'''
        ACME_circ_activePatients=[];ACME_tbi_activePatients=[];ACME_infusion_activePatients=[];
        missionNamespace setVariable ["ACME_sys_circ",true];
        missionNamespace setVariable ["ACME_sys_do2",false];
        ACME_fnc_bpNative={[80,120]};
        ACME_fnc_coagulationBase={[1,1,1,1]};
        ACME_fnc_tbiApplyPressorMAP={[0,false]};
        ACME_fnc_tbiGetMAP={93.3333};
        ACME_fnc_rhythmGet={0};
        ace_medical_status_fnc_getMedicationCount={0};
        ACM_airway_fnc_getAirwayState={1};
        ACM_breathing_fnc_getBreathingState={1};
        ACM_breathing_fnc_getEtCO2={35};
        ACM_airway_fnc_setAirwayState={params ["_p","_changes"];
            {if ((_x select 0)=="collapse") then {_p setVariable ["ACM_airway_AirwayCollapse_State",_x select 1];};} forEach _changes;
        };
        ACME_fnc_sedationActive={false};
        private _wakeCalls=[];
        ACM_core_fnc_requestWake={_wakeCalls pushBack _this;(_this select 0) setVariable ["ACE_isUnconscious",false];};
        _patient setVariable ["ACM_breathing_RespirationRate",16];
        _patient setVariable ["ACM_core_TargetVitals_RespirationRate",16];
        _patient setVariable ["ace_medical_spo2",97];
        _patient setVariable ["ACM_circulation_Blood_Volume",6];
        _patient setVariable ["ACME_hrRestBaseline",77];
    '''
    for name in ('circStateCommit', 'medicationDriveTick', 'ketamineSedationTick', 'ettMainstemTick', 'ettObstructTick', 'hcCircTick', 'circHandle'):
        text = source(name)
        if name == 'circHandle':
            # SQF-VM lacks forEach HASHMAP; preserve its exact key/value lookup.
            text = text.replace('_y params [["_pkClear"', '(_pkTable get _x) params [["_pkClear"')
            text = text.replace('} forEach _pkTable;', '} forEach (keys _pkTable);')
            # VM comparison dispatch lacks Boolean !=; retain Boolean inequality.
            text = text.replace('(_offset == 0) != (_prevOffset == 0)',
                                '(_offset == 0) isNotEqualTo (_prevOffset == 0)')
        text = engine(text)
        for optional in ('_bvmProvider', '_bvmMedic'):
            text = text.replace(f'({optional} getVariable ["fixtureAlive",true])',
                                f'(!({optional} isEqualTo objNull) && {{{optional} getVariable ["fixtureAlive",true]}})')
        code += f'ACME_fnc_{name}={{' + text + '};\n'
    return code


def test_wake_completes_actual_cleanup_then_stops_hot_maintenance_and_publication():
    execute(setup() + r'''
        ACME_clinical_activePatients=[_patient];
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_ket_sedated",true];
        _patient setVariable ["ACM_airway_AirwayCollapse_State",2];
        _patient setVariable ["ACME_o2Drain_mainstem",9];
        _patient setVariable ["ACME_vent_complianceMult",0.55];
        _patient setVariable ["ACME_ETT_Obstructing",true];
        _patient setVariable ["ACME_ETT_ObstructUntil",5];
        _patient setVariable ["ACME_laryngo_fluidPersist",true];
        call ACME_fnc_circHandle;
        [count _wakeCalls==1 && {!(_patient getVariable "ACE_isUnconscious")},"production sedation cleanup did not request wake"] call _check;
        [(_patient getVariable "ACM_airway_AirwayCollapse_State")==0,"retired before final conscious airway cleanup"] call _check;
        [(_patient getVariable "ACME_o2Drain_mainstem")==0 && {(_patient getVariable "ACME_vent_complianceMult")==1},"retired before actual mainstem cleanup"] call _check;
        [!(_patient getVariable "ACME_ETT_Obstructing") && {!(_patient getVariable "ACME_laryngo_fluidPersist")},"retired before actual obstruction expiry"] call _check;
        [ACME_clinical_activePatients isEqualTo [] && {ACME_circ_activePatients isEqualTo []},"recovered awake patient stayed in hot registries"] call _check;
        private _before=(allVariables _patient) apply {[_x,str (_patient getVariable _x)]};
        private _calls=count _maintenanceCalls;private _sent=count _publications;
        for "_i" from 1 to 240 do {CBA_missionTime=12+_i*0.25;call ACME_fnc_circHandle;};
        [count _maintenanceCalls==_calls && {count _publications==_sent},"retired patient kept running maintenance or publishing"] call _check;
        [((allVariables _patient) apply {[_x,str (_patient getVariable _x)]}) isEqualTo _before,"retirement changed gameplay or patient clocks"] call _check;
    ''')


@pytest.mark.parametrize('field,value', [
    ('ace_medical_inCardiacArrest','true'), ('ACE_isUnconscious','true'),
    ('ACME_vent_connected','true'), ('ACME_vent_configured','true'), ('ACME_vent_onPatient','true'),
    ('ACME_ETT_Inserted','true'), ('ACME_nrb_on','true'), ('ACME_tbi_HasTBI','true'),
    ('ACME_blastLung_State','0.2'), ('ACM_circulation_IV_Bags','createHashMapFromArray [["leftarm",[]]]'),
    ('ACME_infusion_BagMedications','[["present"]]'), ('ace_medical_medications','[["Ketamine_IV"]]'),
    ('ACME_medicationDriveQueue','[["TraceDrug",1,30,"bolus"]]'),
    ('ACME_yFlushJobs','createHashMapFromArray [["pending",[]]]'), ('ACME_suctionSessions','[["active"]]'),
    ('ACME_suctionExposure','0.3'), ('ACME_o2Drain_suction','1'), ('ACME_laryngo_irritationUntil','100'),
    ('ACME_roc_awakeResistAdd','0.5'), ('ACME_lido_serumLevel','0.1'),
    ('ACME_ketRapidLoad','0.2'), ('ACME_ncd_total','3'),
    ('ACM_breathing_Pneumothorax_State','0.5'), ('ACM_breathing_TensionPneumothorax_State','true'),
    ('ACME_ptx_state','[1,0,0.1,40,0,0,4,0,0]'),
])
def test_full_maintenance_pass_keeps_each_ongoing_indication(field, value):
    # The legitimate circulation-disabled branch isolates admission from unrelated
    # circulation effects; all outer medication/device/airway calls still execute.
    execute(setup() + f'''
        missionNamespace setVariable ["ACME_sys_circ",false];
        ACME_clinical_activePatients=[_patient];
        _patient setVariable ["{field}",{value}];
        call ACME_fnc_circHandle;
        [_patient in ACME_clinical_activePatients,"ongoing indication retired: {field}"] call _check;
        ["ACME_fnc_pressureInfuserTick" in _maintenanceCalls && {{"ACME_fnc_ptxTensionTick" in _maintenanceCalls}},"maintenance body skipped late workers"] call _check;
    ''')


def test_resolved_ptx_tuple_and_latched_chest_history_do_not_pin_recovered_patient():
    execute(setup() + r'''
        _patient setVariable ["ACME_ptx_state",[1,0,0,60,0,1,8,0,0]];
        _patient setVariable ["ACM_breathing_ChestInjury_State",true];
        ACME_clinical_activePatients=[_patient];
        call ACME_fnc_circHandle;
        [ACME_clinical_activePatients isEqualTo [],"resolved PTX history pinned clinical registry"] call _check;
        [(_patient getVariable "ACME_ptx_state") isEqualTo [1,0,0,60,0,1,8,0,0] && {_patient getVariable "ACM_breathing_ChestInjury_State"},"retirement erased chest injury history"] call _check;
        [!([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"neutral PTX caused immediate re-enrollment"] call _check;
    ''')


def test_late_owner_indication_reenrolls_after_retirement_and_consumes_final_queued_mass():
    execute(setup() + r'''
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
        [ACME_clinical_activePatients isEqualTo [],"initial quiet owner did not retire"] call _check;
        _patient setVariable ["fixtureLocal",false];
        _patient setVariable ["ACME_medicationDriveQueue",[["TraceDrug",0.5,0.25,"bolus"]]];
        [!([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"departed owner enrolled late dose"] call _check;
        _patient setVariable ["fixtureLocal",true];
        [([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"late queue did not request owner recovery"] call _check;
        [_patient] call ACME_fnc_ownerRegister;
        [_patient in ACME_clinical_activePatients,"owner recovery lost late clinical work"] call _check;
        CBA_missionTime=13;call ACME_fnc_circHandle;
        [(_patient getVariable "ACME_medicationDriveQueue") isEqualTo [["TraceDrug",0.5,0.25,"bolus"]],"resumed pass charged dormant time to new mass"] call _check;
        CBA_missionTime=13.25;call ACME_fnc_circHandle;
        [(_patient getVariable "ACME_medicationDriveQueue") isEqualTo [],"late final aliquot was stranded"] call _check;
        [ACME_clinical_activePatients isEqualTo [],"completed late work stayed enrolled"] call _check;
    ''')


def test_shock_dwell_unwinds_before_retirement_and_new_hypoperfusion_starts_without_stale_dwell():
    execute(setup() + r'''
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [["shockDwell",60],["acidLastTick",11]]];
        ACME_clinical_activePatients=[_patient];
        call ACME_fnc_circHandle;
        [((_patient getVariable "ACME_circ_State") get "shockDwell")==58,"normal perfusion did not unwind actual shock dwell"] call _check;
        [_patient in ACME_clinical_activePatients,"positive shock dwell retired before recovery"] call _check;
        for "_i" from 1 to 29 do {CBA_missionTime=12+_i;call ACME_fnc_circHandle;};
        [((_patient getVariable "ACME_circ_State") get "shockDwell")==0 && {ACME_clinical_activePatients isEqualTo []},"cleared shock dwell stayed in clinical maintenance"] call _check;
        [!([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"cleared dwell caused permanent recovery enrollment"] call _check;
        ACME_fnc_bpNative={[20,40]};
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient] call ACME_fnc_ownerRegister;
        CBA_missionTime=42;call ACME_fnc_circHandle;
        [((_patient getVariable "ACME_circ_State") get "shockDwell")==0,"resumed shock charged dormant time"] call _check;
        CBA_missionTime=43;call ACME_fnc_circHandle;
        [((_patient getVariable "ACME_circ_State") get "shockDwell")==1,"later new shock reused stale recovered dwell"] call _check;
    ''')


def test_actual_adequate_ventilation_clears_prior_hypoventilation_dwell_before_retirement():
    execute(setup() + r'''
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [["hypoventDwell",60],["acidLastTick",12]]];
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
        [((_patient getVariable "ACME_circ_State") get "hypoventDwell")==0,"adequate ventilation retained old dwell"] call _check;
        [ACME_clinical_activePatients isEqualTo [],"cleared respiratory dwell did not retire"] call _check;
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACM_breathing_RespirationRate",0];
        [_patient] call ACME_fnc_ownerRegister;
        CBA_missionTime=13;call ACME_fnc_circHandle;
        [((_patient getVariable "ACME_circ_State") get "hypoventDwell")==0,"resumed hypoventilation charged dormant time"] call _check;
        CBA_missionTime=14;call ACME_fnc_circHandle;
        [((_patient getVariable "ACME_circ_State") get "hypoventDwell")==1,"new hypoventilation inherited stale dwell"] call _check;
    ''')


def test_queued_buffer_waits_for_its_actual_acid_clock_then_retires_without_losing_credit():
    execute(setup() + r'''
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [["acidLastTick",12]]];
        _patient setVariable ["ACME_plasmaLyteAcidCredit",0.2];
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
        [(_patient getVariable "ACME_plasmaLyteAcidCredit")==0.2 && {_patient in ACME_clinical_activePatients},"queued buffer lost or retired before acid tick"] call _check;
        CBA_missionTime=13;call ACME_fnc_circHandle;
        [(_patient getVariable "ACME_plasmaLyteAcidCredit")==0 && {ACME_clinical_activePatients isEqualTo []},"completed buffer credit stayed stranded/enrolled"] call _check;
    ''')


def test_do2_flags_receive_final_reconciliation_without_erasing_reperfusion_history():
    execute(setup() + r'''
        missionNamespace setVariable ["ACME_sys_do2",true];
        ACME_fnc_oxygenDelivery={1};
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [["do2Deficit",true],["do2WasArrest",true]]];
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
        private _s=_patient getVariable "ACME_circ_State";
        [!(_s get "do2Deficit") && {!(_s get "do2WasArrest")} && {(_s get "do2RecoveredAt")==12},"DO2 reconciliation lost current reperfusion event"] call _check;
        [ACME_clinical_activePatients isEqualTo [],"absolute reperfusion history pinned neutral patient"] call _check;
    ''')


@pytest.mark.parametrize('enabled', [False, True])
def test_hardcore_pressor_debt_obeys_actual_disabled_cleanup_or_enabled_clearance(enabled):
    execute(setup() + f'missionNamespace setVariable ["ACME_hcEff_circ",{str(enabled).lower()}];' + r'''
        _patient setVariable ["ACME_hc_pressorDebt",0.3];
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
    ''' + (r'''
        [(_patient getVariable "ACME_hc_pressorDebt")>0 && {_patient in ACME_clinical_activePatients},"live finite pressor debt retired"] call _check;
        for "_i" from 1 to 12 do {CBA_missionTime=12+_i*0.25;call ACME_fnc_circHandle;};
    ''' if enabled else '') + r'''
        [abs (_patient getVariable "ACME_hc_pressorDebt")<0.000001 && {ACME_clinical_activePatients isEqualTo []},"resolved/disabled pressor debt pinned clinical worker"] call _check;
    ''')


@pytest.mark.parametrize('bleeding_seal', [False, True])
def test_resolved_air_does_not_retire_real_communicating_wounds_or_bleeding_seals(bleeding_seal):
    execute(setup() + f'private _covered={str(bleeding_seal).lower()};' + r'''
        _patient setVariable ["ACME_ptx_state",[1,0,0,60,0,0,8,0,0]];
        _patient setVariable ["ACME_CS_holeData",[["front",0,0,true,_covered]]];
    ''' + (r'''
        missionNamespace setVariable ["ACM_breathing_ChestInjury_Chances",createHashMapFromArray [[7,true]]];
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["body",[[7,1,0.2]]]]];
    ''' if bleeding_seal else '') + r'''
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
        [_patient in ACME_clinical_activePatients,"real open wound/bleeding vent lost maintenance"] call _check;
    ''')


@pytest.mark.parametrize('direct_entry', [False, True])
def test_long_dormancy_rebaselines_only_maintenance_clocks_before_new_drug_or_device_work(direct_entry):
    execute(setup() + r'''
        missionNamespace setVariable ["ACME_sys_circ",false];
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [["acidLastTick",12]]];
        _patient setVariable ["ACME_vent_battLastT",12];
        _patient setVariable ["ACME_clock_ncdLeakPending",4];
        _patient setVariable ["ACME_clock_altitude",4];
        _patient setVariable ["ACME_nrb_lastTickLocal",3];
        _patient setVariable ["ACME_preox_lastTick",2];
        private _epoch=_patient getVariable ["ACME_clinicalEpoch",1];
        CBA_missionTime=70;
        _patient setVariable ["ACME_medicationDriveQueue",[["TraceDrug",1,30,"bolus"]]];
    ''' + ('ACME_circ_activePatients pushBackUnique _patient;' if direct_entry else '[_patient] call ACME_fnc_ownerRegister;') + r'''
        call ACME_fnc_circHandle;
        [(_patient getVariable "ACME_medicationDriveQueue") isEqualTo [["TraceDrug",1,30,"bolus"]],"idle interval became a new medication bolus"] call _check;
        {
            [(_patient getVariable ["ACME_clock_"+_x,-1])==70 && {(_patient getVariable ["ACME_clock_"+_x+"_owner",-1])==7},"maintenance clock retained dormant elapsed time: "+_x] call _check;
        } forEach ["clinicalMaintenance","rocuronium","ventDrive","blastLung","hcCirc","hcVent","sealOcclusion","ptx","ettMainstem","ncdLeak"];
        [((_patient getVariable "ACME_circ_State") get "acidLastTick")==70 && {(_patient getVariable "ACME_vent_battLastT")==70} && {(_patient getVariable "ACME_clock_ncdLeakPending")==0},"manual clinical clocks retained dormant debt"] call _check;
        [(_patient getVariable "ACME_clock_altitude")==4 && {(_patient getVariable "ACME_nrb_lastTickLocal")==3} && {(_patient getVariable "ACME_preox_lastTick")==2} && {(_patient getVariable ["ACME_clinicalEpoch",1])==_epoch},"clinical reentry reset independent physiology or epoch"] call _check;
        CBA_missionTime=70.25;call ACME_fnc_circHandle;
        [abs (((_patient getVariable "ACME_medicationDriveQueue") select 0 select 2)-29.75)<0.000001,"resumed drug did not follow actual new active cadence"] call _check;
    ''')


def test_registration_of_an_already_active_patient_preserves_elapsed_clinical_cadence():
    execute(setup() + r'''
        missionNamespace setVariable ["ACME_sys_circ",false];
        _patient setVariable ["ACME_medicationDriveQueue",[["TraceDrug",1,30,"bolus"]]];
        ACME_clinical_activePatients=[_patient];call ACME_fnc_circHandle;
        CBA_missionTime=12.5;[_patient] call ACME_fnc_ownerRegister;
        CBA_missionTime=13;[_patient] call ACME_fnc_ownerRegister;call ACME_fnc_circHandle;
        [abs (((_patient getVariable "ACME_medicationDriveQueue") select 0 select 2)-29)<0.000001,"active registration restarted elapsed drug cadence"] call _check;
        [!(_patient getVariable ["ACME_clinicalMaintenanceDormant",false]),"active maintenance was classified dormant"] call _check;
    ''')


def test_external_final_infusion_retirement_is_observed_before_direct_late_enrollment():
    execute(setup() + r'''
        ACME_infusion_activePatients=[_patient];call ACME_fnc_circHandle;
        [!(_patient getVariable ["ACME_clinicalMaintenanceDormant",false]),"live independent registry was marked dormant"] call _check;
        ACME_infusion_activePatients=[];
        CBA_missionTime=13;call ACME_fnc_circHandle;
        CBA_missionTime=70;
        _patient setVariable ["ACME_medicationDriveQueue",[["TraceDrug",1,30,"bolus"]]];
        ACME_circ_activePatients pushBackUnique _patient;call ACME_fnc_circHandle;
        [(_patient getVariable "ACME_medicationDriveQueue") isEqualTo [["TraceDrug",1,30,"bolus"]],"external retirement left a stale maintenance clock"] call _check;
        CBA_missionTime=70.25;call ACME_fnc_circHandle;
        [abs (((_patient getVariable "ACME_medicationDriveQueue") select 0 select 2)-29.75)<0.000001,"external retirement reset ongoing reentry repeatedly"] call _check;
    ''')


def test_circulation_only_eased_calcium_cleanup_is_not_rebaselined_while_still_active():
    execute(setup() + r'''
        _patient setVariable ["ACME_ca_mapDropEased",0.2];
        ACME_circ_activePatients=[_patient];call ACME_fnc_circHandle;
        [_patient in ACME_circ_activePatients && {!(_patient getVariable ["ACME_clinicalMaintenanceDormant",false])},"circulation-only cleanup was marked dormant"] call _check;
        CBA_missionTime=12.25;call ACME_fnc_circHandle;
        [abs ((_patient getVariable "ACME_ca_mapDropEased")-0.15)<0.000001,"active calcium cleanup clock was reset"] call _check;
    ''')


def test_legacy_bare_chest_flag_receives_actual_ptx_adoption_without_permanent_enrollment():
    publish = engine(source('ptxPublish')).replace('_tension!=_wasTension', '_tension isNotEqualTo _wasTension')
    execute(setup() + 'ACME_fnc_ptxEnsure={' + engine(source('ptxEnsure')) + '};' +
            'ACME_fnc_ptxPublish={' + publish + '};' + r'''
        ACM_breathing_fnc_setRuntimeState={params ["_p","_rows"];
            {
                private _key=switch (_x select 0) do {
                    case "pneumothoraxPFH":{"ACM_breathing_Pneumothorax_PFH"};
                    case "pneumothorax":{"ACM_breathing_Pneumothorax_State"};
                    case "tensionPneumothorax":{"ACM_breathing_TensionPneumothorax_State"};
                    default {"fixtureOtherBreathingState"};
                };
                _p setVariable [_key,_x select 1];
            } forEach _rows;
        };
        ACM_breathing_fnc_updateLungState={};
        _patient setVariable ["ACM_breathing_ChestInjury_State",true];
        [([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"legacy chest flag lost its adoption pass"] call _check;
        [_patient] call ACME_fnc_ownerRegister;
        [(_patient getVariable ["ACME_ptx_state",[]]) isEqualTo [1,0,0,0,0,0,0,0,0],"legacy chest adoption invented gas or injury"] call _check;
        [ACME_clinical_activePatients isEqualTo [] && {!([_patient] call ACME_fnc_ownerRegisterNeedsRecovery)},"adopted neutral chest flag pinned maintenance"] call _check;
        [_patient getVariable "ACM_breathing_ChestInjury_State","adoption erased native chest injury history"] call _check;
    ''')
