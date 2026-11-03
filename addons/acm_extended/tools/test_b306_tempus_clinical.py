"""Execute production Tempus transactions; native objects/networking are explicit boundaries."""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute, adapt


def pacing_setup():
    source=(ROOT/'addons/acme_tempusls/functions/fn_tempusLsPacingRate.sqf').read_text()
    source=source.replace('_device distance _patient','_deviceDistance')
    return '''
    private _device=missionNamespace;private _deviceDistance=1;private _fixtureEpoch=4;
    _device setVariable ["acme_tempusls_pat",_patient];
    _device setVariable ["acme_tempusls_pw",[true]];
    _patient setVariable ["acme_tempusls_capture",false];
    _patient setVariable ["ace_medical_inCardiacArrest",false];
    _patient setVariable ["acme_tempusls_thr",60];
    private _settings=[_device,true,70,80,true,4,_medic];
    ACME_fnc_clinicalEpoch={_fixtureEpoch};
    ACM_circulation_fnc_hasPulse={true};
    ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
    ACME_fnc_tempusLsPacingRate={'''+adapt(source)+'''};
    '''


@pytest.mark.parametrize('intrinsic,change,expected,capture',[
    (40,'',70,True),(80,'',80,False),(70,'',70,False),
    (80,'_settings set [4,false];',70,True),
    (40,'_settings set [3,20];',40,False),
    (40,'_settings set [1,false];',40,False),
    (40,'_device setVariable ["acme_tempusls_pw",[false]];',40,False),
    (40,'_device setVariable ["acme_tempusls_pat",objNull];',40,False),
    (40,'_deviceDistance=6.01;',40,False),
    (40,'_patient setVariable ["ace_medical_inCardiacArrest",true];',40,False),
    (40,'ACM_circulation_fnc_hasPulse={false};',40,False),
    (40,'_patientAlive=false;',40,False),
    (40,'_fixtureEpoch=5;',40,False),
    (40,'_settings=[];_patient setVariable ["acme_tempusls_capture",true];',40,False),
])
def test_pacing_respects_intrinsic_rate_and_retires_invalid_capture(intrinsic,change,expected,capture):
    execute(pacing_setup()+change+f'''
      _patient setVariable ["acme_tempusls_paceSet",_settings];
      private _result=[_patient,{intrinsic}] call ACME_fnc_tempusLsPacingRate;
      [_result=={expected},"incorrect effective pacing rate"] call _check;
      [(_patient getVariable ["acme_tempusls_capture",false]) isEqualTo {str(capture).lower()},"incorrect capture state"] call _check;
    ''')


def shock_setup():
    source=(ROOT/'addons/acme_tempusls/functions/fn_tempusLsShock.sqf').read_text()
    source=source.replace('_medic distance _o','_deviceReach').replace('_o distance _patient','_cableReach')
    source=source.replace('_o isKindOf "ACME_TempusLS"','true')
    source=source.replace('isRemoteExecuted','_remote').replace('remoteExecutedOwner','_caller')
    source=source.replace('serverTime','_nowTime')
    source=source.replace('!finite _energy','false')
    source=re.sub(r'playSound3D \[[^;]+;', '_jolts=_jolts+1;', source)
    return '''
      private _o=missionNamespace;private _remote=true;private _caller=7;
      private _fixtureEpoch=4;private _deviceReach=1;private _cableReach=1;
      private _calls=[];private _notices=[];private _jolts=0;private _rh=0;
      ace_medical_gui_maxDistance=3;
      _o setVariable ["acme_tempusls_pat",_patient];
      _o setVariable ["acme_tempusls_pw",[true]];
      _o setVariable ["acme_tempusls_armed",true];
      _o setVariable ["acme_tempusls_shocks",[]];
      _patient setVariable ["ACM_circulation_AED_Placement_Pads",false];
      _patient setVariable ["ACM_circulation_AED_InUse",false];
      _patient setVariable ["ACM_circulation_AED_Charged",false];
      ace_common_fnc_isAwake={true};ACME_fnc_clinicalEpoch={_fixtureEpoch};
      ACME_fnc_patientInteractionDistance={_distance};ACME_fnc_rhythmGet={_rh};
      ACME_fnc_clinicalNotice={_notices pushBack _this};
      ace_medical_treatment_fnc_addToLog={};
      ACME_fnc_shockLocal={_calls pushBack _this;};
      ACME_fnc_tempusLsShock={'''+adapt(source)+'''};
      private _request=[_o,_medic,_patient,150,false,"Adult","tx:7:1",4,10];
    '''


@pytest.mark.parametrize('change',[
    '_caller=8;','_alive=false;','ace_common_fnc_isAwake={false};',
    '_deviceReach=3.1;','_cableReach=6.1;','_distance=3.1;',
    '_fixtureEpoch=5;','_request set [8,-6];','_request set [8,13];',
    '_o setVariable ["acme_tempusls_pat",objNull];',
    '_o setVariable ["acme_tempusls_pw",[false]];',
    '_o setVariable ["acme_tempusls_armed",false];',
    '_request set [3,0];','_request set [3,201];',
])
def test_invalid_shock_request_never_reaches_clinical_backend(change):
    execute(shock_setup()+change+'''_request call ACME_fnc_tempusLsShock;
      [count _calls==0,"invalid request shocked a patient"] call _check;
    ''')


def test_charge_is_spent_once_and_native_pad_state_is_restored():
    execute(shock_setup()+'''
      _request call ACME_fnc_tempusLsShock;
      _request call ACME_fnc_tempusLsShock;
      [count _calls==1,"charge replay produced multiple clinical shocks"] call _check;
      [!(_o getVariable ["acme_tempusls_armed",true]),"charge was not retired"] call _check;
      [{_patient getVariable [_x,false]} count ["ACM_circulation_AED_Placement_Pads","ACM_circulation_AED_InUse","ACM_circulation_AED_Charged"]==0,"LS leaked its temporary native charge/pads"] call _check;
    ''')


def test_sync_without_organized_r_wave_does_not_shock():
    execute(shock_setup()+'''
      _rh=2;_request set [4,true];_request call ACME_fnc_tempusLsShock;
      [count _calls==0 && {count _notices==1},"SYNC request bypassed missing R wave"] call _check;
    ''')


def test_physical_power_requires_hold_and_old_callbacks_cannot_toggle_again():
    source=(ROOT/'addons/acme_tempus/functions/fn_tempusPowerKey.sqf').read_text()
    source=source.replace('_provider distance _device','_deviceReach')
    execute('''
      private _key=missionNamespace;private _device=profileNamespace;
      private _deviceReach=1;private _powerCalls=[];
      _key setVariable ["ACME_power_device",_device];
      _device setVariable ["acme_tempus_pw",[false]];
      ace_common_fnc_isAwake={true};
      CBA_fnc_waitAndExecute={_waits pushBack _this};
      ACME_fnc_tempusPower={_powerCalls pushBack _this;};
      ACME_fnc_tempusPowerKey={'''+adapt(source)+'''};
      [_key,0,true] call ACME_fnc_tempusPowerKey;
      [_key,0,false] call ACME_fnc_tempusPowerKey;
      ((_waits select 0) select 1) call ((_waits select 0) select 0);
      [count _powerCalls==0,"short click toggled physical power"] call _check;
      [_key,0,true] call ACME_fnc_tempusPowerKey;
      [((_waits select 1) select 2)==2.5,"incorrect membrane hold duration"] call _check;
      ((_waits select 1) select 1) call ((_waits select 1) select 0);
      ((_waits select 1) select 1) call ((_waits select 1) select 0);
      [count _powerCalls==1 && {((_powerCalls select 0) select 1)},"hold did not power once"] call _check;
    ''')


def test_forced_browser_refresh_reseeds_waveforms_even_with_unchanged_vitals():
    source=(ROOT/'addons/acme_tempus/functions/fn_tempusWaveforms.sqf').read_text()
    source=source.replace('_control ctrlWebBrowserAction [','_js pushBack [')
    # SQF-VM lacks Arma's resize [count,fill] overload; retain its exact zero-fill behavior.
    source=source.replace('_ecg resize [176, 0];','_ecg resize 176; _ecg=_ecg apply {0};')
    execute('''
      private _control=uiNamespace;private _device=missionNamespace;private _js=[];
      _device setVariable ["acme_tempus_pat",objNull];
      _device setVariable ["acme_tempus_pw",[false]];
      _device setVariable ["acme_tempus_v",[]];
      ACME_fnc_tempusWaveforms={'''+adapt(source)+'''};
      [_control,_device,false,false] call ACME_fnc_tempusWaveforms;
      [_control,_device,false,false] call ACME_fnc_tempusWaveforms;
      [count _js==1,"unchanged waveform flooded browser"] call _check;
      [_control,_device,false,true] call ACME_fnc_tempusWaveforms;
      [count _js==2,"fresh browser received no host waveform"] call _check;
      _nowTime=16;
      [_control,_device,false,false] call ACME_fnc_tempusWaveforms;
      [count _js==3,"expired waveform window was not replenished"] call _check;
    ''')
