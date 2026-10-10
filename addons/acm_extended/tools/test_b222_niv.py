"""B222 NIV route, custody, delivery and stop regressions against real SQF.

Engine objects, inventory transactions and transport are modeled explicitly.
Normal settings/delivery/mask gates/ACK/clear code run, not a second Python model.
These tests are not an Arma client/server session or clinical validation.
"""
import hashlib
import json
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute, read
from test_historical_cardiac_execution import code as clinical_code, setup as clinical_setup
from test_b156_procedure_supplies import primitives
from test_b156_shared_action_gates import setup as gate_setup, ACTIONS
from test_b208_dead_device_interventions import breath_setup, breath_call
from test_historical_procedure_trays import ui_code


def production(name):
    s=read(name)
    s=re.sub(r'_\w+ isKindOf "CAManBase"','true',s)
    s=s.replace('getPlayerUID _medic','"provider"').replace('getPlayerUID (_origin select 0)','"donor"')
    s=s.replace('getPosASL _patient','[0,0,0]').replace('serverTime','_serverTime')
    # Test strings are ASCII item/interface identifiers.
    s=s.replace('toUpperANSI ', 'toUpper ')
    return primitives(clinical_code(s))


def func(name): return 'ACME_fnc_'+name+'={'+production(name)+'};\n'


def setup():
    return clinical_setup()+'''
        private _serverTime=100;
        ace_common_fnc_isAwake={!((_this select 0) getVariable ["ACE_isUnconscious",false])};
        ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
        ACME_fnc_setVarNetApprox=ACME_fnc_setVarNet;
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        _patient setVariable ["ACME_resp_neuralRR",18];
        _patient setVariable ["ACM_breathing_RespirationRate",18];
        _patient setVariable ["ACE_isUnconscious",false];
        uiNamespace setVariable ["ACME_vent_target",_patient];
    '''+func('ventNivEligible')+func('ventMaskSelected')+func('ventSyncMask')+func('ventEffectiveSettings')


BLOCKERS={
    'dead':'_patientAlive=false;',
    'unconscious':'_patient setVariable ["ACE_isUnconscious",true];',
    'arrest':'_patient setVariable ["ace_medical_inCardiacArrest",true];',
    'paralyzed':'_patient setVariable ["ACME_roc_paralyzed",true];',
    'no-effort':'_patient setVariable ["ACME_resp_neuralRR",0];',
    'bad-effort':'_patient setVariable ["ACME_resp_neuralRR","unknown"];',
    'recovery':'_patient setVariable ["ACM_airway_RecoveryPosition_State",true];',
    'ett':'_patient setVariable ["ACME_ETT_Inserted",true];',
    'igel':'_patient setVariable ["ACM_airway_AirwayItem_Oral","SGA"];',
    'cric':'_patient setVariable ["ACM_airway_SurgicalAirway_TubeInserted",true];',
    'nrb':'_patient setVariable ["ACME_nrb_on",true];',
}


@pytest.mark.parametrize('blocker',BLOCKERS)
def test_actual_niv_eligibility_rejects_unsuitable_patient(blocker):
    execute(setup()+BLOCKERS[blocker]+'''[!([_patient] call ACME_fnc_ventNivEligible),"ineligible NIV accepted"] call _check;''')


@pytest.mark.parametrize('sharing,expected',[(0,True),(1,True),(2,False),(3,True)])
@pytest.mark.parametrize('kit',[False,True])
def test_actual_mask_action_uses_shared_loose_or_kit_supply_policy(sharing,expected,kit):
    condition=ACTIONS['ACME_ConnectNIVVent']['props']['condition']
    s=gate_setup('ACME_ConnectNIVVent')+setup()+f'ace_medical_treatment_allowSharedEquipment={sharing};'
    s+=func('itemCount')
    if kit:
        s+='''_patient setVariable ["items",[]];_patient setVariable ["kitItems",["ACME_Ventilator"]];
            efak_medical_fnc_countItem={params ["_u","_i"];{_x==_i} count ((_u getVariable ["items",[]])+(_u getVariable ["kitItems",[]]))};'''
    execute(s+'private _gate={'+clinical_code(condition)+'};'+f'[(call _gate) isEqualTo {str(expected).lower()},"mask visibility disagrees with supply policy"] call _check;'+'''
        _roleAllowed=false;[!(call _gate),"shared mask bypassed role requirement"] call _check;
        _roleAllowed=true;_patient setVariable ["items",[]];_patient setVariable ["kitItems",[]];
        [!(call _gate),"mask visible without device"] call _check;
    ''')


def test_mask_route_has_no_stance_or_ai_gate_and_no_added_disposable():
    assert not re.search(r'\b(?:stance|isPlayer|animationState)\b',read('ventNivEligible'))
    a=ACTIONS['ACME_ConnectNIVVent']; assert a['parent']=='ACME_ConnectETVent'
    assert ACTIONS['ACME_ConnectETVent']['props']['items']==[]
    assert ACTIONS['ACME_ConnectETVent']['props']['treatmentTime']==0
    s=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    assert 'if !(_classname in ["ACME_ConnectETVent", "ACME_ConnectNIVVent"]) exitWith' in s
    assert '["INVASIVE", "MASK"] select (_classname == "ACME_ConnectNIVVent")' in s
    assert 'case "ACME_ConnectNIVVent";' in read('procedureActionAllowed')


def custody_setup():
    return setup()+'''
        private _near=true;private _allowed=true;private _ticks=0;
        ACME_fnc_ventRecoveryNear={_near};ACME_fnc_procedureAllowed={_allowed};
        ACME_fnc_ventCustodyTick={_ticks=_ticks+1;};
        ACME_fnc_ventDeviceFields={[]};
        missionNamespace setVariable ["ACME_vent_custody",createHashMap];
        missionNamespace setVariable ["ACME_vent_custodyPFH",0];
    '''+func('ventCustodyRequest')+func('ventCustodyAck')+func('ventPatientClear')


@pytest.mark.parametrize('interface',['MASK','INVASIVE'])
def test_server_ack_installs_exactly_one_stopped_device_with_explicit_physical_interface(interface):
    airway='_patient setVariable ["ACME_ETT_Inserted",true];' if interface=='INVASIVE' else ''
    execute(custody_setup()+airway+f'["attach",_medic,_patient,"{interface}"] call ACME_fnc_ventCustodyRequest;'+'''
        private _id=_patient getVariable ["ACME_vent_custodyId",""];
        private _records=missionNamespace getVariable ["ACME_vent_custody",createHashMap];
        [count _records==1,"attachment not allocated once"] call _check;
        [!(_patient getVariable ["ACME_vent_onPatient",false]),"attached before inventory ACK"] call _check;
    '''+f'["attach",_medic,_patient,"{interface}"] call ACME_fnc_ventCustodyRequest;'+'''
        [count _records==1,"double click allocated another ventilator"] call _check;
        ["take",_id,_medic,true,[]] call ACME_fnc_ventCustodyAck;
        private _eventCount=count _events;
        ["take",_id,_medic,true,[]] call ACME_fnc_ventCustodyAck;
        [count _events==_eventCount,"duplicate inventory ACK replayed attachment"] call _check;
        [_patient getVariable ["ACME_vent_onPatient",false],"no deployed device after ACK"] call _check;
        [!(_patient getVariable ["ACME_vent_connected",true]),"ACK auto-started ventilation"] call _check;
        [!(_patient getVariable ["ACME_vent_powerOn",true]),"ACK auto-powered ventilation"] call _check;
    '''+f'[(_patient getVariable ["ACME_vent_nivMask",false]) isEqualTo {str(interface=="MASK").lower()},"wrong physical interface"] call _check;'+('''
        [(_patient getVariable ["ACME_vent_iface",""])=="NON INVASIVE","mask marked invasive"] call _check;
        [(_patient getVariable ["ACME_vent_mode",""])=="CPAP PS HF","mask did not select CPAP"] call _check;
        [(_patient getVariable ["ACME_vent_psup",-1])==0,"mask did not start at CPAP without pressure support"] call _check;
        [!(_patient getVariable ["ACME_ETT_Inserted",false]),"mask faked intubation"] call _check;
    ''' if interface=='MASK' else ''))


@pytest.mark.parametrize('blocker',list(BLOCKERS)+['no-permission','out-of-range','disabled','recovering','bad-interface'])
def test_server_revalidates_niv_before_any_inventory_request(blocker):
    b=BLOCKERS.get(blocker,{'no-permission':'_allowed=false;','out-of-range':'_near=false;',
        'disabled':'missionNamespace setVariable ["ACME_sys_vent",false];','recovering':'_patient setVariable ["ACME_vent_recovering",true];','bad-interface':''}.get(blocker,''))
    interface='BAD' if blocker=='bad-interface' else 'MASK'
    execute(custody_setup()+b+f'["attach",_medic,_patient,"{interface}"] call ACME_fnc_ventCustodyRequest;'+'''
        [count (missionNamespace getVariable ["ACME_vent_custody",createHashMap])==0,"invalid attachment reserved device"] call _check;
        [_ticks==0,"invalid attachment requested inventory"] call _check;
    ''')


def test_missing_inventory_ack_releases_mask_reservation():
    execute(custody_setup()+'''
        ["attach",_medic,_patient,"MASK"] call ACME_fnc_ventCustodyRequest;
        private _id=_patient getVariable ["ACME_vent_custodyId",""];
        ["take",_id,_medic,false,[]] call ACME_fnc_ventCustodyAck;
        [count (missionNamespace getVariable ["ACME_vent_custody",createHashMap])==0,"failed stock left custody locked"] call _check;
        [(_patient getVariable ["ACME_vent_custodyId",""])=="","failed stock left patient reservation"] call _check;
        [!(_patient getVariable ["ACME_vent_onPatient",false]),"failed debit granted free ventilator"] call _check;
    ''')


def drive_setup():
    return setup()+'''
        private _runtime=[];
        ACME_fnc_clinicalTickDelta={0.25};
        ACME_fnc_ventShuntCommit={};
        ACM_core_fnc_setTargetVitalsState={};ACM_core_fnc_setAceMedicalState={};
        ACM_circulation_fnc_setRuntimeState={};
        ACM_breathing_fnc_setRuntimeState={params ["_p","_changes"];
            _runtime pushBack _this;
            {if ((_x select 0)=="bvmProvider") then {_p setVariable ["ACM_breathing_BVM_provider",_x select 1];};} forEach _changes;
        };
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_custodyId","device:1"];
        _patient setVariable ["ACME_vent_nivMask",true];
        _patient setVariable ["ACME_vent_mode","CPAP PS HF"];
        _patient setVariable ["ACME_vent_iface","NON INVASIVE"];
        _patient setVariable ["ACME_vent_circuit",true];
        _patient setVariable ["ACME_vent_powerOn",true];
        _patient setVariable ["ACME_vent_configured",true];
        _patient setVariable ["ACME_vent_connected",true];
        _patient setVariable ["ACME_vent_psup",0];
    '''+func('ventOxygenation')+func('ventDriveTick')+func('ventMinuteVolume')+func('ventMVLimits')+func('ventAlarmTick')


@pytest.mark.parametrize('simple',[False,True])
@pytest.mark.parametrize('rr',[4,18,32])
def test_mask_uses_spontaneous_delivery_even_when_global_simple_mode_is_on(simple,rr):
    execute(drive_setup()+f'missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];_patient setVariable ["ACME_resp_neuralRR",{rr}];'+'''
        private _effective=[_patient] call ACME_fnc_ventEffectiveSettings;
        [!(_effective select 0) && {(_effective select 1)=="CPAP PS HF"},"mask became SIMPLE mandatory ventilation"] call _check;
        [_patient] call ACME_fnc_ventDriveTick;
        [_patient getVariable ["ACME_vent_driving",false],"awake mask did not drive"] call _check;
        [(_patient getVariable ["ACME_vent_rrDrive",-2])==-1,"mask pinned a mandatory rate"] call _check;
        [(_patient getVariable ["ACME_vent_mvDelivered",0])>0,"mask produced no exhaled volume"] call _check;
    '''+f'[(_patient getVariable ["ACME_vent_spontRR",-1])=={rr},"delivered rate is not patient effort"] call _check;')


@pytest.mark.parametrize('blocker',['unconscious','arrest','paralyzed','no-effort','recovery','ett','igel','cric','nrb','power-off','circuit-off','no-battery','wrong-mode','wrong-interface'])
def test_active_mask_stops_support_on_unsuitability_or_equipment_loss(blocker):
    b=BLOCKERS.get(blocker,{'power-off':'_patient setVariable ["ACME_vent_powerOn",false];',
        'circuit-off':'_patient setVariable ["ACME_vent_circuit",false];','no-battery':'_patient setVariable ["ACME_vent_battery",0];',
        'wrong-mode':'_patient setVariable ["ACME_vent_mode","SIMV VC PS"];','wrong-interface':'_patient setVariable ["ACME_vent_iface","INVASIVE"];'}.get(blocker,''))
    execute(drive_setup()+'''
        [_patient] call ACME_fnc_ventDriveTick;
        [_patient getVariable ["ACME_vent_driving",false],"fixture never started mask"] call _check;
    '''+b+'''
        [_patient] call ACME_fnc_ventDriveTick;
        [!(_patient getVariable ["ACME_vent_driving",true]),"mask kept supporting invalid patient/circuit"] call _check;
        [(_patient getVariable ["ACME_vent_effectiveRR",-1])==0,"invalid mask retained artificial breaths"] call _check;
        [(_patient getVariable ["ACM_breathing_BVM_provider",objNull]) isEqualTo objNull,"invalid mask kept gas-exchange provider"] call _check;
    ''')


def test_trigger_off_with_pressure_support_never_creates_mandatory_mask_backup():
    execute(drive_setup()+'''
        _patient setVariable ["ACME_vent_psup",10];_patient setVariable ["ACME_vent_trigSensCmH2O",0];
        [_patient] call ACME_fnc_ventDriveTick;
        [(_patient getVariable ["ACME_vent_effectiveRR",-1])==0,"mask backup manufactured breaths"] call _check;
        [(_patient getVariable ["ACME_vent_mvDelivered",-1])==0,"mask backup created ventilation"] call _check;
    ''')


def test_explicit_niv_cpap_selections_override_simple_invasive_delivery():
    execute(drive_setup()+'''
        _patient setVariable ["ACME_vent_nivMask",false];_patient setVariable ["ACME_ETT_Inserted",true];
        missionNamespace setVariable ["ACME_vent_simpleMode",true];
        [_patient] call ACME_fnc_ventDriveTick;
        [!(_patient getVariable ["ACME_vent_driving",false]),"explicit NIV incorrectly delivered invasive breaths"] call _check;
        [_patient getVariable ["ACME_vent_nivMask",false],"explicit NIV pair did not fit the mask"] call _check;
    ''')


@pytest.mark.parametrize('simple',[False,True])
def test_owner_rejects_manual_mask_breath_even_with_stale_ett_flag(simple):
    execute(breath_setup(simple)+'''_patientAlive=true;_patient setVariable ["ACME_vent_nivMask",true];'''+breath_call(simple)+'''
        [count _clinical==0 && {count _events==0},"mask accepted manual rescue breath"] call _check;
        [(_patient getVariable ["ACME_vent_manualRR",0])==0,"mask created manual breath ledger"] call _check;
    ''')


def test_mask_unsuitability_raises_existing_high_priority_circuit_alarm():
    execute(drive_setup()+'''
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient] call ACME_fnc_ventAlarmTick;
        ["CIRCUIT DISCONNECT" in (_patient getVariable ["ACME_vent_alarms",[]]),"invalid mask has no alarm"] call _check;
        [(_patient getVariable ["ACME_vent_alarmPrio",0])==3,"invalid mask alarm not high priority"] call _check;
    ''')


def test_final_clear_removes_physical_mask_and_rejects_stale_other_device():
    execute(drive_setup()+func('ventPatientClear')+'''
        ACME_fnc_ventDeviceFields={[]};
        _patient setVariable ["ACME_vent_custodyId","mask-one"];
        [_patient,"old-device",true] call ACME_fnc_ventPatientClear;
        [_patient getVariable ["ACME_vent_nivMask",false],"old clear removed current mask"] call _check;
        [_patient,"mask-one",true] call ACME_fnc_ventPatientClear;
        [!(_patient getVariable ["ACME_vent_nivMask",true]),"final clear left mask behind"] call _check;
    ''')


def test_physical_mask_is_registered_patient_state_not_carried_device_settings():
    assert '"ACME_vent_nivMask"' in read('clinicalFields')
    assert '"ACME_vent_nivMask"' not in read('ventDeviceFields')
    execute(setup()+'private _fields={'+production('clinicalFields')+'};'+'''
        private _rows=call _fields;
        private _mask=_rows select {(_x select 0)=="ACME_vent_nivMask"};
        [count _mask==1 && {count (_mask select 0)==3},"malformed patient field registration"] call _check;
    ''')


def nav_setup():
    """Real navigation logic, mocked sound/UI route and engine distance only."""
    nav=production('ventPanelNavClick').replace('playSound "ACME_VentClick";', '')
    nav=nav.replace('(ACE_player distance _vTgt)','0').replace('objectParent ACE_player','objNull').replace('objectParent _vTgt','objNull')
    return drive_setup()+'''
        private _screens=[]; private _hints=[]; private _allowed=true;
        ACME_fnc_procedureAllowed={_allowed};
        ACME_fnc_ventPanelShowScreen={_screens pushBack (_this select 0);};
        ace_common_fnc_displayTextStructured={_hints pushBack _this;};
        uiNamespace setVariable ["ACME_vent_flipped",false];
        uiNamespace setVariable ["ACME_vent_powered",true];
        uiNamespace setVariable ["ACME_vent_screen","connect"];
        uiNamespace setVariable ["ACME_vent_listCount",4];
        uiNamespace setVariable ["ACME_vent_selIdx",0];
        uiNamespace setVariable ["ACME_vent_presetMode",false];
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_connected",false];
        _patient setVariable ["ACME_vent_configured",false];
    '''+'ACME_fnc_ventPanelNavClick={'+nav+'};'


@pytest.mark.parametrize('simple',[False,True])
def test_real_mask_setup_start_and_stop_with_simple_setting(simple):
    execute(nav_setup()+f'missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];'+'''
        ["confirm"] call ACME_fnc_ventPanelNavClick;
        [_patient getVariable ["ACME_vent_configured",false],"mask setup did not configure"] call _check;
        [_patient getVariable ["ACME_vent_connected",false],"mask setup did not start"] call _check;
        [_screens isEqualTo ["live"],"mask setup routed back through invasive wizard"] call _check;
        uiNamespace setVariable ["ACME_vent_screen","menu"];
        ["confirm"] call ACME_fnc_ventPanelNavClick;
        [!(_patient getVariable ["ACME_vent_connected",true]),"STOP mask failed"] call _check;
        ["confirm"] call ACME_fnc_ventPanelNavClick;
        [_patient getVariable ["ACME_vent_connected",false],"START mask failed"] call _check;
    ''')


@pytest.mark.parametrize('blocker',['unconscious','arrest','paralyzed','no-effort','recovery','ett','nrb'])
def test_real_mask_start_rechecks_patient_after_setup(blocker):
    execute(nav_setup()+BLOCKERS[blocker]+'''
        ["confirm"] call ACME_fnc_ventPanelNavClick;
        [!(_patient getVariable ["ACME_vent_connected",false]),"setup bypassed mask eligibility"] call _check;
        _patient setVariable ["ACME_vent_configured",true];
        uiNamespace setVariable ["ACME_vent_screen","menu"];
        ["confirm"] call ACME_fnc_ventPanelNavClick;
        [!(_patient getVariable ["ACME_vent_connected",false]),"START bypassed mask eligibility"] call _check;
        [count _hints==2,"rejected START gave no feedback"] call _check;
        _patient setVariable ["ACME_vent_connected",true];
        ["confirm"] call ACME_fnc_ventPanelNavClick;
        [!(_patient getVariable ["ACME_vent_connected",true]),"ineligible patient blocked STOP"] call _check;
    ''')


def test_deterioration_before_inventory_ack_keeps_device_stopped_and_recoverable():
    execute(custody_setup()+'''
        ["attach",_medic,_patient,"MASK"] call ACME_fnc_ventCustodyRequest;
        private _id=_patient getVariable ["ACME_vent_custodyId",""];
        _patient setVariable ["ACE_isUnconscious",true];
        ["take",_id,_medic,true,[]] call ACME_fnc_ventCustodyAck;
        [_patient getVariable ["ACME_vent_onPatient",false],"acknowledged device was lost"] call _check;
        [!(_patient getVariable ["ACME_vent_connected",true]),"late ACK started ventilation"] call _check;
        [!([_patient] call ACME_fnc_ventNivEligible),"late ACK made patient eligible"] call _check;
        ["return",_medic,_patient] call ACME_fnc_ventCustodyRequest;
        private _record=(missionNamespace getVariable ["ACME_vent_custody",createHashMap]) get _id;
        [(_record get "phase")=="returning","deteriorated patient lost recovery path"] call _check;
    ''')


def test_nrb_and_physical_cp_ap_mask_cannot_be_stacked():
    execute(setup()+func('nrbAirwayCompatible')+'''
        [[_patient] call ACME_fnc_nrbAirwayCompatible,"fixture should accept NRB without mask"] call _check;
        _patient setVariable ["ACME_vent_nivMask",true];
        [!([_patient] call ACME_fnc_nrbAirwayCompatible),"NRB stacked over physical CPAP mask"] call _check;
    ''')


@pytest.mark.parametrize('mask',[False,True])
def test_real_live_edit_simple_guard_applies_to_invasive_but_not_mask(mask):
    s=production('ventPanelLiveEdit')
    execute(setup()+'ACME_fnc_ventPanelLiveEdit={'+s+'};'+'''
        ACME_fnc_procedureAllowed={true};ACME_fnc_ventPanelRefresh={};
        missionNamespace setVariable ["ACME_vent_simpleMode",true];
        uiNamespace setVariable ["ACME_vent_selIdx",1];
        uiNamespace setVariable ["ACME_vent_editing",true];
        uiNamespace setVariable ["ACME_vent_vt",500];
        _patient setVariable ["ACME_vent_vt",500];
    '''+f'_patient setVariable ["ACME_vent_nivMask",{str(mask).lower()}];'+'''
        [1] call ACME_fnc_ventPanelLiveEdit;
    '''+f'[(_patient getVariable ["ACME_vent_vt",0])=={510 if mask else 500},"wrong Simple editing guard"] call _check;')


def test_debug_renderer_and_geometry_are_byte_identical_to_b221():
    original=__import__('subprocess').check_output(['git','show','7e6a66401e66e881a009b2bf3f56e33ae9084abf:addons/acm_extended/functions/fn_debugMenuClinical.sqf'],cwd=ROOT)
    assert (ROOT/'addons/acm_extended/functions/fn_debugMenuClinical.sqf').read_bytes()==original


def test_build_helper_packages_only_and_never_installs_or_publishes():
    script=(ROOT/'tools/Build-ACME-B222.ps1').read_text()
    assert 'hemtt check' in script and 'hemtt release' in script
    for forbidden in ['Copy-Item','Move-Item','Remove-Item','hemtt publish','git push','ServerKeysPath','ModPath']:
        assert forbidden not in script
    assert 'NA8-B222-1.2.4.1-candidate' in script
