"""B223 executes actual interaction state machines with explicit native engine boundaries.
These are not a rendered Arma, mouse driver, dedicated server or medical validation.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b222_niv import setup as vent_setup, func as vent_func, drive_setup
from test_b213_respiration_observation import setup as observation_setup
from test_b219_revision import motor_setup, motor_code


def function(name):
    s=read(name).replace('serverTime','_nowTime')
    s=re.sub(r'finite (_\w+)',r'(\1 isEqualType 0)',s)
    return 'ACME_fnc_'+name+'={'+adapt(s)+'};\n'


@pytest.mark.parametrize('direction',[-1,1])
def test_actual_scroll_step_latches_direction_stops_at_last_frame_and_never_repeats(direction):
    execute(function('chestSealScrollStep')+f'''
      private _state=[0,0,false];private _completed=0;
      for "_i" from 1 to 50 do {{
          private _result=(_state+[{direction}]) call ACME_fnc_chestSealScrollStep;
          _state=_result select [0,3];if (_result select 3) then {{_completed=_completed+1;}};
      }};
      [_state isEqualTo [5,{direction},true],"peel did not stop at final frame"] call _check;
      [_completed==1,"repeated wheel triggered multiple burps"] call _check;
      private _reverse=(_state+[{direction*-1}]) call ACME_fnc_chestSealScrollStep;
      [(_reverse select [0,3]) isEqualTo [4,{direction},true],"reverse did not reseal the selected corner"] call _check;
      private _fresh=[0,0,false,{direction*-1}] call ACME_fnc_chestSealScrollStep;
      [_fresh isEqualTo [1,{direction*-1},false,false],"new hover did not rearm direction"] call _check;
    ''')


@pytest.mark.parametrize('frame',range(1,5))
@pytest.mark.parametrize('direction',[-1,1])
def test_opposite_scroll_reseals_without_changing_corner_until_hover_exit(frame,direction):
    execute(function('chestSealScrollStep')+f'''
      private _result=[{frame},{direction},false,{direction*-1}] call ACME_fnc_chestSealScrollStep;
      [_result isEqualTo [{frame-1},{direction},false,false],"reverse wheel did not reseal fixed corner"] call _check;
    ''')


def test_both_scroll_handlers_use_shared_step_and_hover_exit_resets_state():
    for name in ('chestSealScroll','thoraSealScroll'):
        s=read(name)
        assert 'call ACME_fnc_chestSealScrollStep' in s
        assert 'if (_complete' in s
        assert '% 6' not in s
    assert 'ACME_CS_BurpFrame' in read('chestSealTick') and 'ACME_CS_BurpDir' in read('chestSealTick')
    assert 'setVariable ["ACME_Thora_Burp", ["", 0, 0, false]]' in read('thoraTick')
    assert '_medic,10] call ACME_fnc_chestSealLogOnce' in read('thoraAftercareLocal')


@pytest.mark.parametrize('age', [20,30,60,120,200,500])
@pytest.mark.parametrize('sample',[0,0.5,1])
def test_actual_arrest_jerk_taper_is_brief_and_progressively_sparser(age,sample):
    t=min(1,max(0,(age-20)/180))
    duration=(.08+.04*sample)*(1-.5*t);gap=(4+4*sample)*(1+4*t)
    execute(function('seizureJerkTiming')+f'''
      private _timing=[{age},{sample},{sample}] call ACME_fnc_seizureJerkTiming;
      [abs ((_timing select 0)-{duration})<0.00001,"incorrect jerk duration taper"] call _check;
      [abs ((_timing select 1)-{gap})<0.0001,"incorrect jerk quiet taper"] call _check;
    ''')


@pytest.mark.parametrize('complete',[True,False])
def test_native_watch_is_created_with_popup_and_deleted_once_on_stop(complete):
    execute(observation_setup()+f'''
      [_medic,_patient] call ACME_fnc_respirationStart;
      [_watchCreates==1 && {{_watchShows==1}},"watch not visible with observation popup"] call _check;
      [count ((uiNamespace getVariable "ACME_RespirationSession") select 5)==0,"watch consumed prep time"] call _check;
      [{str(complete).lower()},false,1] call ACME_fnc_respirationStop;
      [false,false,1] call ACME_fnc_respirationStop;
      [_watchDeletes==1,"watch leaked or was deleted twice"] call _check;
    ''')


@pytest.mark.parametrize('order',[0,1])
@pytest.mark.parametrize('simple',[False,True])
@pytest.mark.parametrize('running',[False,True])
def test_selecting_niv_and_cpap_in_either_order_fits_mask_on_existing_device(order,simple,running):
    keys=[('ACME_vent_mode','CPAP PS HF'),('ACME_vent_iface','NON INVASIVE')]
    if order:keys.reverse()
    execute(vent_setup()+f'''
      missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];
      _patient setVariable ["ACME_vent_onPatient",true];_patient setVariable ["ACME_vent_custodyId","existing"];
      _patient setVariable ["ACME_vent_circuit",true];_patient setVariable ["ACME_vent_connected",{str(running).lower()}];
      _patient setVariable ["{keys[0][0]}","{keys[0][1]}"];
      [!([_patient] call ACME_fnc_ventSyncMask),"partial selection fitted mask"] call _check;
      _patient setVariable ["{keys[1][0]}","{keys[1][1]}"];
      // Effective settings cannot sneak in a mandatory breath before flag reconciliation.
      [!(([_patient] call ACME_fnc_ventEffectiveSettings) select 0),"Simple overrode explicit mask selection"] call _check;
      [[_patient] call ACME_fnc_ventSyncMask,"completed pair did not fit mask"] call _check;
      [_patient getVariable ["ACME_vent_nivMask",false],"mask flag missing"] call _check;
      [(_patient getVariable ["ACME_vent_connected",false]) isEqualTo {str(running).lower()},"mask selection started/stopped machine"] call _check;
      [(_patient getVariable ["ACME_vent_custodyId",""])=="existing","mask re-acquired device"] call _check;
      _patient setVariable ["ACME_vent_iface","INVASIVE"];
      [!([_patient] call ACME_fnc_ventSyncMask),"invasive selection kept physical mask"] call _check;
    ''')


@pytest.mark.parametrize('change', ['_patient setVariable ["ACME_vent_onPatient",false];',
 '_patient setVariable ["ACME_vent_circuit",false];','_patient setVariable ["ACME_vent_custodyId",""];',
 '_patient setVariable ["ACME_vent_recovering",true];','_patientLocal=false;'])
def test_mask_reconciliation_does_not_create_device_from_preset_or_retired_custody(change):
    execute(vent_setup()+'''
      _patient setVariable ["ACME_vent_onPatient",true];_patient setVariable ["ACME_vent_custodyId","existing"];
      _patient setVariable ["ACME_vent_circuit",true];_patient setVariable ["ACME_vent_mode","CPAP PS HF"];
      _patient setVariable ["ACME_vent_iface","NON INVASIVE"];
    '''+change+'''[!([_patient] call ACME_fnc_ventSyncMask),"mask created without local physical custody"] call _check;''')


def mask_button_setup():
    return vent_setup()+vent_func('ventSetMaskCPAP')+'''
      private _allowed=true;private _near=true;
      ACME_fnc_procedureAllowed={_allowed};ACME_fnc_ventRecoveryNear={_near};
      _patient setVariable ["ACME_vent_custodyId","existing"];_patient setVariable ["ACME_vent_onPatient",true];
      _patient setVariable ["ACME_vent_circuit",true];
      private _request=[_patient,_medic,"existing",1,103];
    '''


@pytest.mark.parametrize('running',[False,True])
def test_attached_cpap_button_is_idempotent_preserves_power_and_inventory(running):
    execute(mask_button_setup()+f'''
      _patient setVariable ["ACME_vent_connected",{str(running).lower()}];
      [_request call ACME_fnc_ventSetMaskCPAP,"button rejected existing device"] call _check;
      _patient setVariable ["ACME_vent_psup",8];
      [_request call ACME_fnc_ventSetMaskCPAP,"repeat rejected"] call _check;
      [(_patient getVariable ["ACME_vent_psup",-1])==8,"repeated button reset tuned pressure support"] call _check;
      [!(_patient getVariable ["ACME_vent_powerOn",false]),"button switched power on"] call _check;
      [count _events==0,"mask switch requested inventory/network custody"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['_near=false;','_allowed=false;','_alive=false;',
 '_medic setVariable ["ACE_isUnconscious",true];','_patient setVariable ["ACME_clinicalEpoch",2];',
 '_patient setVariable ["ACME_vent_custodyId","successor"];','_patient setVariable ["ACME_vent_onPatient",false];',
 '_patient setVariable ["ACME_vent_circuit",false];','_patient setVariable ["ACME_vent_recovering",true];',
 '_serverTime=104;', '_request set [4,200];'])
def test_stale_or_unauthorized_mask_button_cannot_change_new_device(invalid):
    execute(mask_button_setup()+invalid+'''
      [!(_request call ACME_fnc_ventSetMaskCPAP),"invalid mask command accepted"] call _check;
      [!(_patient getVariable ["ACME_vent_nivMask",false]),"invalid command fitted mask"] call _check;
    ''')


def capillary_setup():
    return '''
      private _poses=[];private _stops=[];private _results=[];private _nextPose=0;
      ace_common_fnc_isAwake={true};
      ACME_fnc_treatmentPoseStart={_poses pushBack _this;_nextPose=_nextPose+1;_nextPose};
      ACME_fnc_treatmentPoseStop={_stops pushBack _this;};
      ACM_circulation_fnc_checkCapillaryRefill={_results pushBack _this;};
    '''+function('capillaryStart')+function('capillaryStop')


@pytest.mark.parametrize('success',[True,False])
def test_capillary_finishes_exact_pulse_pose_once_and_reports_only_success(success):
    execute(capillary_setup()+f'''
      [_medic,_patient] call ACME_fnc_capillaryStart;
      [(_poses select 0) isEqualTo [_medic,"pulse",-1,_patient],"not pulse-family pose"] call _check;
      private _args=[_medic,_patient,"LeftArm","CheckCapillaryRefill",objNull,"",false,1];
      [_args,{str(success).lower()}] call ACME_fnc_capillaryStop;
      [_args,{str(success).lower()}] call ACME_fnc_capillaryStop;
      [count _stops==1 && {{(_stops select 0) isEqualTo [_medic,"pulse",1]}},"pose exit duplicated or wrong episode"] call _check;
      [count _results=={int(success)},"canceled or duplicate capillary result"] call _check;
    ''')


def test_capillary_old_callback_never_stops_successor_or_reports_old_assessment():
    execute(capillary_setup()+'''
      [_medic,_patient] call ACME_fnc_capillaryStart;
      [_medic,_patient] call ACME_fnc_capillaryStart;
      [[_medic,_patient,"LeftArm","CheckCapillaryRefill",objNull,"",false,1],true] call ACME_fnc_capillaryStop;
      [count _stops==0 && {count _results==0},"old callback touched successor"] call _check;
      [((_medic getVariable "ACME_capillaryPose") select 0)==2,"successor record lost"] call _check;
    ''')


def cpr_setup():
    return '''
      private _canTreat=true;private _canInteract=true;private _nativeAccept=true;private _begins=0;
      ace_medical_treatment_fnc_canTreatCached={_canTreat};ace_common_fnc_canInteractWith={_canInteract};
      ace_common_fnc_isAwake={!((_this select 0) getVariable ["ACE_isUnconscious",false])};
      ACME_fnc_patientInteractionDistance={_distance};CBA_fnc_localEvent={_events pushBack _this;};
      ACM_circulation_fnc_beginCPR={_begins=_begins+1;if (_nativeAccept) then {
          _medic setVariable ["ACM_circulation_CPR_Patient",_patient];
          _medic setVariable ["ACM_circulation_isPerformingCPR",true];
      };};
    '''+function('cprAfterChestPrep')


def test_prepared_cpr_directly_hands_off_without_a_second_progress_dialog():
    execute(cpr_setup()+'''
      [[_medic,_patient,"Body","CPR"] call ACME_fnc_cprAfterChestPrep,"prepared CPR did not start"] call _check;
      [_begins==1 && {!ace_medical_gui_pendingReopen},"wrong startup/menu handoff"] call _check;
      [(_events apply {_x select 0}) isEqualTo ["ace_treatmentStarted","ace_treatmentSucceded"],"lease did not hand off to native CPR"] call _check;
    ''')


@pytest.mark.parametrize('invalid',['_canTreat=false;','_canInteract=false;','_alive=false;',
 '_medic setVariable ["ACE_isUnconscious",true];','_distance=20;',
 '_medic setVariable ["ACME_chestAccessPreflightActive",true];'])
def test_prepared_cpr_still_rechecks_provider_patient_distance_and_finished_preparation(invalid):
    execute(cpr_setup()+invalid+'''
      [!([_medic,_patient,"Body","CPR"] call ACME_fnc_cprAfterChestPrep),"invalid prepared CPR started"] call _check;
      [_begins==0 && {count _events==0},"invalid prepared CPR touched native session"] call _check;
    ''')


def test_refused_native_cpr_reports_failure_not_false_success():
    execute(cpr_setup()+'''
      _nativeAccept=false;
      [!([_medic,_patient,"Body","CPR"] call ACME_fnc_cprAfterChestPrep),"native refusal reported success"] call _check;
      [(_events select 1 select 0)=="ace_treatmentFailed","refusal left carrier lease stranded"] call _check;
    ''')


@pytest.mark.parametrize('handler',['chestSealScroll','thoraSealScroll'])
@pytest.mark.parametrize('direction',[-1,1])
def test_actual_wheel_handler_dispatches_once_at_open_and_allows_resealing(handler,direction):
    setup='''
      private _lifts=0;private _renders=0;private _sounds=0;
      ACME_fnc_chestSealSealAt={0};ACME_fnc_thoraSealAt={true};
      ACME_fnc_chestSealBurpReady={true};ACME_fnc_chestSealBurp={_lifts=_lifts+1;};
      ACME_fnc_thoraAftercareRequest={_lifts=_lifts+1;};
      ACME_fnc_chestSealSnd={_sounds=_sounds+1;};
      ACME_fnc_chestSealRender={_renders=_renders+1;};ACME_fnc_thoraRenderTube=ACME_fnc_chestSealRender;
      uiNamespace setVariable ["ACME_CS_Patient",_patient];uiNamespace setVariable ["ACME_CS_Medic",_medic];
      uiNamespace setVariable ["ACME_Thora_Patient",_patient];uiNamespace setVariable ["ACME_Thora_Medic",_medic];
    '''+function('chestSealScrollStep')+function(handler)
    reset='''uiNamespace setVariable ["ACME_CS_BurpIdx",-1];uiNamespace setVariable ["ACME_CS_BurpFrame",0];
        uiNamespace setVariable ["ACME_CS_BurpDir",0];uiNamespace setVariable ["ACME_CS_BurpFired",false];''' if handler=='chestSealScroll' else 'uiNamespace setVariable ["ACME_Thora_Burp",["",0,0,false]];'
    execute(setup+f'''
      for "_i" from 1 to 100 do {{[objNull,{direction}] call ACME_fnc_{handler};}};
      [_lifts==1 && {{_renders==5}},"full peel repeated or re-rendered after end"] call _check;
      [objNull,{direction*-1}] call ACME_fnc_{handler};
      [_lifts==1 && {{_renders==6}},"reverse scroll did not reseal completed hover"] call _check;
    '''+reset+f'''
      for "_i" from 1 to 5 do {{[objNull,{direction*-1}] call ACME_fnc_{handler};}};
      [_lifts==2 && {{_renders==11}},"hover exit did not permit next burp"] call _check;
    ''')


def test_thoracostomy_log_dedupes_per_provider_and_side_without_blocking_treatment():
    s=read('chestSealLogOnce').replace('netId _medic','"medic"')
    s=s.replace('serverTime','_nowTime')
    # SQF-VM lacks getOrDefault; preserve the actual lookup and fallback semantics.
    s=s.replace('_times getOrDefault [_key, -1e6]', '(if (_key in _times) then {_times get _key} else {-1e6})')
    execute('ACME_fnc_chestSealLogOnce={'+adapt(s)+'};'+'''
      private _logs=[];ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
      private _args=[_patient,"thoraBurp:left","%1 burped left",["M. Harlow"],_medic,10];
      [_args call ACME_fnc_chestSealLogOnce,"first completed burp not logged"] call _check;
      for "_i" from 1 to 20 do {[_args call ACME_fnc_chestSealLogOnce isEqualTo false,"rapid duplicate log"] call _check;};
      [count _logs==1,"same hover burst flooded log"] call _check;
      _args set [1,"thoraBurp:right"];[_args call ACME_fnc_chestSealLogOnce,"other side wrongly suppressed"] call _check;
      _args set [1,"thoraBurp:left"];_nowTime=20;
      [_args call ACME_fnc_chestSealLogOnce,"valid later burp did not log"] call _check;
      [count _logs==3,"side/time dedupe wrong"] call _check;
    ''')


@pytest.mark.parametrize('awake',[True,False])
def test_removing_previous_tube_after_selecting_mask_keeps_same_ventilator_custody(awake):
    execute(drive_setup()+vent_func('ventAirwayLoss')+f'''
      private _clearCount=0;ACME_fnc_ventPatientClear={{_clearCount=_clearCount+1;}};
      _patient setVariable ["ACME_ETT_Inserted",false];
      _patient setVariable ["ACE_isUnconscious",{str(not awake).lower()}];
      [_patient,_medic,"tube removed"] call ACME_fnc_ventAirwayLoss;
      [_clearCount==0 && {{count _events==0}},"NIV tube removal returned the entire device"] call _check;
      [_patient getVariable ["ACME_vent_onPatient",false],"mask device detached"] call _check;
      [(_patient getVariable ["ACME_vent_driving",false]) isEqualTo {str(awake).lower()},"mask patient support eligibility wrong"] call _check;
    ''')


def test_prepared_chest_launch_enters_actual_native_cpr_and_keeps_lease_until_cancel():
    from test_cpr_lifecycle import execute as cpr_execute
    bridge=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    block=bridge[bridge.index('        private _launch = {'):]
    block=block[:block.index('\n\n        [{')]
    block=block.replace('objectParent _m','_medicVehicle').replace('objectParent _p','_patientVehicle')
    block=adapt(block)
    watchers=adapt(read('registerChestAccessVestRuntime').replace('serverTime','CBA_missionTime').replace('!= _patient','isNotEqualTo _patient'))
    cpr_execute('''
      private _events=[];private _listeners=[];private _leaseRequests=[];private _watches=[];
      private _prepStops=0;private _finishes=0;private _aborts=0;
      CBA_fnc_addEventHandler={_listeners pushBack _this;};
      CBA_fnc_localEvent={params ["_event","_args"];_events pushBack _event;
          {if ((_x select 0)==_event) then {_args call (_x select 1);};} forEach _listeners;
      };
      CBA_fnc_waitUntilAndExecute={_watches pushBack _this;};
      ACME_fnc_chestAccessVestEvent={_leaseRequests pushBack _this;};
      ACME_fnc_chestAccessVestProvider={
          [(_this select 2)=="stop" && {_this select 3},"carrier pose not handed off"] call _check;
          _prepStops=_prepStops+1;_medic setVariable ["ACME_chestAccessProvider",[]];
      };
      ACME_fnc_patientInteractionDistance={_distance};
      ace_medical_treatment_fnc_canTreatCached={true};ace_common_fnc_canInteractWith={true};
      ACME_fnc_chestAccessManeuverActive={[_medic,_patient] call ACM_circulation_fnc_cprSessionValid};
      _medic setVariable ["ACME_chestAccess_treatment",[_patient,"cpr","lease1"]];
      _medic setVariable ["ACME_chestAccessPreflightActive",true];
      _medic setVariable ["ACME_chestAccessPreflightToken","prep1"];
      _medic setVariable ["ACME_chestAccessProvider",[_patient,1,"pose1"]];
    '''+watchers+function('cprAfterChestPrep')+block+'''
      [_medic,_patient,[_medic,_patient,"Body","CPR"],"prep1","lease1","cpr",false,
          {_finishes=_finishes+1;},{_aborts=_aborts+1;}] call _launch;
      [_prepStops==1 && {_finishes==1} && {_aborts==0},"automatic carrier prep did not hand off once"] call _check;
      [_medic getVariable ["ACM_circulation_isPerformingCPR",false],"real native CPR never acquired provider"] call _check;
      [count _watches==1 && {count _leaseRequests==0},"carrier restored or re-acquired during handoff"] call _check;
      call _enter;
      ["ACM_CPR" in _moves,"real CPR did not enter compressions"] call _check;
      private _watch=_watches select 0;
      [!((_watch select 2) call (_watch select 0)),"carrier watcher released active CPR"] call _check;
      call _cancel;call _freed;
      [(_watch select 2) call (_watch select 0),"canceled CPR left carrier lease alive"] call _check;
      (_watch select 2) call (_watch select 1);
      [count _leaseRequests==1 && {!((_leaseRequests select 0) select 3)},"final carrier release was not exactly once"] call _check;
    ''')


def test_deploy_script_preserves_normal_source_and_both_launcher_paths():
    s=(ROOT/'tools/Deploy-ACME-B223.ps1').read_text()
    assert 'hemtt check' in s and 'hemtt release' in s
    assert "Join-Path $Repo '.hemttout\\build'" in s
    assert 'Copy-Item -LiteralPath $File.FullName' in s
    assert 'Get-FileHash -LiteralPath $Destination' in s
    assert 'Remove-Item' not in s and '/MIR' not in s and 'git clean' not in s
    assert 'ACME-B222-Test' not in s
