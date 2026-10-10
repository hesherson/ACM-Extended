"""B228 owner/request invariants and transfusion input isolation.

Production SQF is executed in SQF-VM; object locality, UI drawing/audio, network
transport and fluid admission are explicitly simulated engine boundaries. These
checks do not establish native Arma rendering or dedicated-server reliability.
"""
import re
import subprocess
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b227_line_service_and_assessments import basic, service_setup, pump_setup, fn, src
from test_b211_direct_pressure_inputs import setup as pressure_setup
from test_b156_procedure_supplies import primitives


def local_fn(name):
    # Preserve locality as an independent input rather than the older always-local fixture.
    text=src(name).replace('!true', '!_local')
    return 'ACME_fnc_'+name+'={'+text+'};'


@pytest.mark.parametrize('mode,total',[('prime',25),('flush',50)])
@pytest.mark.parametrize('fraction',[0,0.25,0.8,1])
def test_priming_and_flushing_credit_exact_admitted_volume(mode,total,fraction):
    execute(service_setup()+f'''
      [100,false,{str(mode=='flush').lower()}] call _init;
      _fraction={fraction};["{mode}","once"] call _request;[7] call _advance;
      [abs (call _stock-(100-{total}))<.001,"incorrect reserve debit"] call _check;
      [abs (_credited-{total*fraction})<.001,"priming/flush systemic fluid not admission-based"] call _check;
      [abs ((_patient getVariable "ACM_circulation_Saline_Volume")-{total*fraction/1000})<.00001,"compartment differs from ledger"] call _check;
    ''')


@pytest.mark.parametrize('mode',['prime','flush'])
@pytest.mark.parametrize('blocker',['stop','occlusion','arrest','zero-co'])
def test_both_service_modes_pause_without_debit_and_resume_without_catchup(mode,blocker):
    blocked={
      'stop':'_patient setVariable ["ACM_circulation_FluidBagsFlow_IO",[1,0,1,1,1,1]];',
      'occlusion':'_admissionRate=0;',
      'arrest':'_patient setVariable ["ace_medical_inCardiacArrest",true];',
      'zero-co':'_co=0;'
    }[blocker]
    execute(service_setup()+f'''
      [100,false,{str(mode=='flush').lower()}] call _init;["{mode}","one"] call _request;
      {blocked}[20] call _advance;
      [call _stock==100 && {{_credited==0}},"blocked access delivered fluid"] call _check;
      _patient setVariable ["ACM_circulation_FluidBagsFlow_IO",[1,1,1,1,1,1]];
      _patient setVariable ["ace_medical_inCardiacArrest",false];_co=5;_admissionRate=1;
      [1] call _advance;[_credited=={5 if mode=='prime' else 10},"blocked time caused catch-up bolus"] call _check;
      [8] call _advance;[_credited=={25 if mode=='prime' else 50},"service did not resume exactly"] call _check;
    ''')


@pytest.mark.parametrize('mode',['prime','flush'])
def test_cpr_perfusion_path_is_preserved_for_service(mode):
    execute(service_setup()+f'''
      [100,false,{str(mode=='flush').lower()}] call _init;
      _co=0;_cpr=true;_patient setVariable ["ace_medical_inCardiacArrest",true];
      ["{mode}","cpr"] call _request;[7] call _advance;
      [_credited=={25 if mode=='prime' else 50},"CPR perfusion rejected"] call _check;
    ''')


@pytest.mark.parametrize('bad',['empty-id','future','expired','wrong-reserve','wrong-site','wrong-epoch','medicated','replay'])
def test_service_request_identity_deadline_and_carrier_validation(bad):
    modify={
      'empty-id':'_id="";', 'future':'_at=103;', 'expired':'_at=89;',
      'wrong-reserve':'_uid="replacement";', 'wrong-site':'_site=2;',
      'wrong-epoch':'_epoch=0;',
      'medicated':'private _drug=[];_drug set [23,"reserve"];_patient setVariable ["ACME_infusion_BagMedications",[_drug]];',
      'replay':'["flush","one"] call _request;'
    }[bad]
    execute(service_setup()+f'''
      [100] call _init;private _id="one";private _at=_serverTime;private _uid="reserve";private _site=0;private _epoch=_liveEpoch;
      {modify}
      [_patient,_medic,"body",false,_site,_epoch,"flush",_id,_at,_uid,""] call ACME_fnc_yFlushStart;
      [8] call _advance;[_credited=={50 if bad=='replay' else 0},"rejected/replayed service changed fluid"] call _check;
    ''')


def test_old_cancel_cannot_remove_new_jobs_queue_on_same_reserve():
    execute(service_setup()+'''
      [500] call _init;["flush","old"] call _request;[6] call _advance;
      ["flush","new"] call _request;["flush","new-tail"] call _request;
      [_patient,_medic,"body",false,0,_liveEpoch,"cancel","old-cancel",_serverTime,"reserve","old"] call ACME_fnc_yFlushStart;
      [count (((_patient getVariable "ACME_yFlushJobs") get _key) select 9)==1,"stale cancel modified new job"] call _check;
      [12] call _advance;[_credited==150,"stale cancel changed fluid quantity"] call _check;
    ''')


def test_swapped_saline_uid_retires_job_without_debiting_replacement():
    execute(service_setup()+'''
      [500] call _init;["flush","one"] call _request;[2] call _advance;
      private _map=_patient getVariable "ACM_circulation_IV_Bags";private _rows=_map get "body";
      private _fresh=+(_rows select 0);_fresh set [8,"replacement"];_fresh set [1,500];_rows set [0,_fresh];
      _map set ["body",_rows];_patient setVariable ["ACM_circulation_IV_Bags",_map];
      [8] call _advance;[call _stock==500 && {_credited==20},"old job drained new reserve"] call _check;
      [count (_patient getVariable "ACME_yFlushJobs")==0,"stale job was not retired"] call _check;
    ''')


@pytest.mark.parametrize('field,value',[(4,-1),(4,100),(5,0),(5,501),(8,-1),(9,'[25]'),(10,'"bogus"'),(11,500),(12,-5),(12,20),(13,'123')])
def test_corrupt_job_arithmetic_is_rejected_before_any_debit(field,value):
    execute(service_setup()+f'''
      [500] call _init;["flush","one"] call _request;
      private _jobs=_patient getVariable "ACME_yFlushJobs";private _job=_jobs get _key;_job set [{field},{value}];_jobs set [_key,_job];
      [8] call _advance;[_credited==0 && {{call _stock==500}},"corrupt job admitted fluid"] call _check;
      [count (_patient getVariable "ACME_yFlushJobs")==0,"corrupt job remains active"] call _check;
    ''')


def test_wrong_job_map_key_cannot_service_another_site():
    execute(service_setup()+'''
      [500] call _init;["flush","one"] call _request;
      private _jobs=_patient getVariable "ACME_yFlushJobs";private _job=_jobs get _key;
      _jobs deleteAt _key;_jobs set ["leftarm#true#1",_job];[5] call _advance;
      [_credited==0,"job key allowed site redirection"] call _check;
    ''')


def test_receipt_capacity_does_not_evict_a_still_valid_request():
    execute(service_setup()+'''
      [500] call _init;["flush","first"] call _request;
      private _r=_patient getVariable "ACME_yServiceReceipts";
      for "_n" from 1 to 511 do {_r set [str _n,_serverTime];};
      ["flush","overflow"] call _request;["flush","first"] call _request;[8] call _advance;
      [_credited==50 && {count _r==512},"capacity/replay added fluid or evicted receipt"] call _check;
      _serverTime=_serverTime+13;["flush","fresh"] call _request;[8] call _advance;
      [_credited==100,"expired receipts did not free bounded capacity"] call _check;
    ''')


def test_actual_job_remainder_is_published_for_each_fractional_debit():
    execute(service_setup()+'''
      private _published=[];
      ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];
        if (_key=="ACME_yFlushJobs" && {"body#false#0" in _value}) then {_published pushBack +(_value get "body#false#0");};
      };
      [500] call _init;["flush","one"] call _request;
      _serverTime=_serverTime+.05;[_patient] call ACME_fnc_yFlushTick;
      _serverTime=_serverTime+.05;[_patient] call ACME_fnc_yFlushTick;
      [count _published==3,"subsecond debits missing job publication"] call _check;
      [abs ((_published select 2 select 4)-49)<.001,"published remainder differs from debit"] call _check;
      [abs ((_published select 2 select 12)-1)<.001,"published delivered amount differs from debit"] call _check;
    ''')


def test_stale_owner_cannot_start_or_tick_services():
    execute(service_setup()+local_fn('yFlushStart')+local_fn('yFlushTick')+'''
      private _local=false;[500] call _init;["flush","one"] call _request;
      [count (_patient getVariable "ACME_yFlushJobs")==0,"non-owner started service"] call _check;
      _local=true;["flush","two"] call _request;[2] call _advance;
      _local=false;[8] call _advance;[_credited==20,"retired owner still drains"] call _check;
      _local=true;[8] call _advance;[_credited==50,"resumed owner duplicated/lost remainder"] call _check;
    ''')


def refill_setup():
    return basic()+fn('yRefillCommit').replace('alive _owner','_alive')+'''
      private _acks=[];ace_common_fnc_isAwake={!_unconscious};
      CBA_fnc_targetEvent={_acks pushBack _this;};
      _patient setVariable ["ACME_YLines",["body#false#0"]];
      _patient setVariable ["ACME_yRefillClaims",createHashMap];
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[]]]];
      private _claim={params ["_mode",["_id","one"]];[_patient,_medic,"claim",_id,_mode,"body",false,0,_liveEpoch] call ACME_fnc_yRefillCommit;};
    '''


@pytest.mark.parametrize('denial',['blood','dirty','saline','claim','service','access','epoch','down'])
def test_y_refill_rejections_exit_outer_case_and_never_send_later_success(denial):
    changes={
      'blood':'_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["Blood",1,0,0,false]]]]];',
      'dirty':'_patient setVariable ["ACME_YLineDirty",createHashMapFromArray [["body#false#0",true]]];',
      'saline':'_mode="saline";_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["ACME_SalineY",1,0,0,false]]]]];',
      'claim':'_patient setVariable ["ACME_yRefillClaims",createHashMapFromArray [["body#false#0",[_medic,"other","blood",_serverTime,_liveEpoch]]]];',
      'service':'_patient setVariable ["ACME_yFlushJobs",createHashMapFromArray [["body#false#0",[1]]]];',
      'access':'_accessValid=false;', 'epoch':'_sendEpoch=0;', 'down':'_unconscious=true;'
    }[denial]
    execute(refill_setup()+f'''
      private _mode="blood";private _sendEpoch=_liveEpoch;{changes}
      [_patient,_medic,"claim","one",_mode,"body",false,0,_sendEpoch] call ACME_fnc_yRefillCommit;
      [count _acks==1 && {{!(_acks select 0 select 1 select 3)}},"rejection fell through and sent success"] call _check;
      private _claims=_patient getVariable "ACME_yRefillClaims";
      [(count _claims)=={1 if denial=='claim' else 0},"rejected request reserved/overwrote site"] call _check;
    ''')


def test_duplicate_y_claim_keeps_original_shared_clock_and_is_idempotent():
    execute(refill_setup()+'''
      ["blood","one"] call _claim;_serverTime=105;CBA_missionTime=5000;
      ["blood","one"] call _claim;
      private _entry=(_patient getVariable "ACME_yRefillClaims") get "body#false#0";
      [count _acks==2 && {(_acks select 0 select 1 select 3)} && {(_acks select 1 select 1 select 3)},"duplicate ack wrong"] call _check;
      [(_entry select 3)==100,"duplicate changed lease/used machine-local clock"] call _check;
    ''')


@pytest.mark.parametrize('local',[False,True])
def test_slot_repair_is_owner_only_and_does_not_replace_live_volumes(local):
    execute(basic()+local_fn('yEnsureSlots')+f'''
      private _local={str(local).lower()};private _commits=0;
      ACME_fnc_ivBagsCommit={{params ["_p","_map"];_p setVariable ["ACM_circulation_IV_Bags",_map];_commits=_commits+1;}};
      _patient setVariable ["ACME_YLines",["body#false#0"]];
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["Blood",123,0,0,false,-1,500,-1,"live"]]]]];
      [_patient] call ACME_fnc_yEnsureSlots;
      private _rows=(_patient getVariable "ACM_circulation_IV_Bags") get "body";
      [(_rows select 0 select 1)==123,"repair overwrote current fluid"] call _check;
      [count _rows=={2 if local else 1} && {{_commits=={int(local)}}},"repair ownership/empty slot incorrect"] call _check;
      _nowTime=_nowTime+2;[_patient] call ACME_fnc_yEnsureSlots;
      [_commits=={int(local)},"already complete line was republished"] call _check;
    ''')


def test_legacy_saline_retag_does_not_steal_other_site_reserve():
    execute(basic()+fn('ySalineSetup')+'''
      private _seen=[];
      ACME_fnc_yLinesCommit={params ["_p","_lines"];_p setVariable ["ACME_YLines",_lines];};
      ACME_fnc_ivBagsCommit={params ["_p","_map"];_p setVariable ["ACM_circulation_IV_Bags",_map];_seen pushBack _map;};
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[
        ["Saline",100,0,0,true,-1,100,-1,"other"], ["Saline",200,0,1,true,-1,200,-1,"selected"]
      ]]]];
      [_patient,"leftarm#true#1",true,_liveEpoch] call ACME_fnc_ySalineSetup;
      private _a=(_patient getVariable "ACM_circulation_IV_Bags") get "leftarm";
      [(_a select 0 select 0)=="Saline" && {(_a select 1 select 0)=="ACME_SalineY"},"retag changed wrong access"] call _check;
      [(_a select 0 select 1)==100 && {(_a select 1 select 1)==200},"retag altered volume"] call _check;
    ''')


@pytest.mark.parametrize('invalid',['protocol','no-id','no-access','no-supply','bad-bag','old-time'])
def test_pressure_pump_cannot_use_legacy_deadline_bypass_or_absent_access(invalid):
    changes={'protocol':'_protocol="";','no-id':'_id="";','no-access':'_accessValid=false;',
             'no-supply':'_supply=0;','bad-bag':'_uid="other";','old-time':'_at=0;'}[invalid]
    execute(pump_setup()+f'''
      private _protocol="pump-b227";private _id="one";private _uid="bag";private _at=_serverTime;{changes}
      [_patient,_medic,_uid,1,_id,_at,true,false,_protocol] call ACME_fnc_pressureInfuserCommit;
      [call _level==0,"invalid pump changed pressure"] call _check;
    ''')


@pytest.mark.parametrize('button',[1,2])
def test_transfusion_input_does_not_cancel_direct_pressure(button):
    execute(pressure_setup()+f'''
      private _uiOpen=true;ACME_fnc_transfusionInputOwned={{_uiOpen}};
      ["body",false] call _start;[_display] call ACME_fnc_installRmbCancelGuard;
      [_display,{button}] call _mouse;
      [count _cancelQueue==0 && {{_medic getVariable ["ACME_DP_Active",false]}},"child click cancelled DP"] call _check;
      _uiOpen=false;[_display,{button}] call _mouse;
      [count _cancelQueue==1,"outside click no longer releases hold"] call _check;
      call _runCancel;[!(_medic getVariable ["ACME_DP_Active",true]),"outside cancellation failed"] call _check;
    ''')


def test_opening_child_before_deferred_background_cancel_preserves_pressure():
    execute(pressure_setup()+'''
      private _uiOpen=false;ACME_fnc_transfusionInputOwned={_uiOpen};
      ["body",false] call _start;[_display] call ACME_fnc_installRmbCancelGuard;
      [_display,1] call _mouse;_uiOpen=true;call _runCancel;
      [_medic getVariable ["ACME_DP_Active",false],"deferred cancel leaked into child dialog"] call _check;
    ''')


@pytest.mark.parametrize('transfusion,clamp',[(False,False),(True,False),(False,True),(True,True)])
def test_input_owner_predicate_checks_both_native_displays(transfusion,clamp):
    text=read('transfusionInputOwned').replace('findDisplay 86000','_tf').replace('findDisplay 86200','_rc')
    text=text.replace('isNull (_tf)','((_tf) isEqualTo objNull)').replace('isNull (_rc)','((_rc) isEqualTo objNull)')
    execute(f'private _tf={"missionNamespace" if transfusion else "objNull"};private _rc={"parsingNamespace" if clamp else "objNull"};private _owns={{'+text+f'''}};
      [(call _owns) isEqualTo {str(transfusion or clamp).lower()},"wrong input owner"] call _check;
    ''')


def test_single_service_button_and_diagnostic_free_stop_label_source_contract():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    native=(ROOT/'addons/circulation/functions/fnc_openTransfusionMenu.sqf').read_text()
    assert 'class ACME_PrimeLineButton' not in config
    assert 'class ACME_FlushLineButton' in config
    assert "action = \"['auto'] call ACME_fnc_transfusionFlushLine\"" in config
    assert 'Flow physically blocked' not in native and '_physicalBlock' not in native
    assert 'inCardiacArrest' not in native
    assert 'STOP_IV_TRANSFUSION' in native or 'Stop' in native
    paint=read('transfusionServicePaint')
    assert '"Prime Line (25 mL)", "Flush Line"' in paint
    assert '_primed && {_dirty} && {!_blood}' in paint
    assert 'ctrlSetBackgroundColor' in paint and 'sin (360' in paint
    assert 'playSoundUI' in paint and '"soundClick"' in paint
    assert '"MouseButtonUp"' not in paint  # no second queue cancel or click sound
    assert 'LifeWarmer Quantum inline: %1 mL remaining.' in read('updateTransfusionControls')


def test_renderer_never_publishes_viewer_bag_map_and_slot_repair_is_bounded():
    ui=read('updateTransfusionControls')
    assert '"yEnsureSlots", []' in ui and '_needsSlots' in ui
    assert 'setVariable ["ACM_circulation_IV_Bags"' not in ui
    assert 'diag_tickTime + 1' in ui
    assert 'ACME_ySlotsNextCheckLocal' in read('yEnsureSlots')


def used_setup():
    text=src('rehangUsedBagCommit').replace('netId _medic','"provider"')
    return basic()+'''ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
      ace_common_fnc_isAwake={true};ACM_circulation_fnc_hasIV={true};ACM_circulation_fnc_hasIO={true};
      ACM_circulation_fnc_getAccessType={4};ACM_circulation_fnc_updateActiveFluidBags={};
      ACME_fnc_resumeSiteFlow={};ACME_fnc_lineWarmer={false};
      private _acks=[];CBA_fnc_targetEvent={_acks pushBack _this;};
      ACME_fnc_ivBagsCommit={params ["_p","_map"];_p setVariable ["ACM_circulation_IV_Bags",_map];};
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[]]]];
      private _record=["used","Blood",100,4,-1,500,"Blood"];
      private _send={[_patient,_medic,"body",false,0,"used",_record,1,"one",false,_serverTime] call ACME_fnc_rehangUsedBagCommit;};
    '''+'ACME_fnc_rehangUsedBagCommit={'+text+'};'


@pytest.mark.parametrize('bad',['overflow','negative','identity','occupied','dirty','service','late','none'])
def test_used_bag_cannot_overfill_bypass_y_gates_or_replay(bad):
    change={
      'overflow':'_record set [2,501];', 'negative':'_record set [2,-1];', 'identity':'_record set [0,"other"];',
      'occupied':'_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["Blood",200,0,0,false,-1,500,-1,"existing"]]]]];',
      'dirty':'_patient setVariable ["ACME_YLineDirty",createHashMapFromArray [["body#false#0",true]]];',
      'service':'_patient setVariable ["ACME_yFlushJobs",createHashMapFromArray [["body#false#0",[1]]]];',
      'late':'_send={[_patient,_medic,"body",false,0,"used",_record,1,"one",false,80] call ACME_fnc_rehangUsedBagCommit;};',
      'none':''
    }[bad]
    execute(used_setup()+change+f'''
      call _send;call _send;
      private _rows=(_patient getVariable "ACM_circulation_IV_Bags") get "body";
      [count _rows=={1 if bad in ('none','occupied') else 0},"used bag rejection/duplicate placement failed"] call _check;
    ''')


@pytest.mark.parametrize('pending,match,accepted',[(False,True,False),(True,False,False),(True,True,False),(True,True,True)])
def test_used_bag_results_require_owned_pending_record_and_settle_only_once(pending,match,accepted):
    text=src('rehangUsedBagResult').replace('!local _provider','!true').replace('isNull ACE_player','(ACE_player isEqualTo objNull)')
    execute(basic()+'ACME_fnc_rehangUsedBagResult={'+text+'};'+f'''
      ACME_fnc_updateTransfusionControls={{}};
      private _rec=["used","Blood",100,4,-1,500,"Blood"];
      _medic setVariable ["ACME_usedBags",[]];
      uiNamespace setVariable ["ACME_usedRehangPending",createHashMap];
      uiNamespace setVariable ["ACME_usedRehangContext",createHashMap];
      if ({str(pending).lower()}) then {{
        uiNamespace setVariable ["ACME_usedRehangPending",createHashMapFromArray [["one",_rec]]];
        uiNamespace setVariable ["ACME_usedRehangContext",createHashMapFromArray [["one",[_medic,{"_patient" if match else "missionNamespace"},"used"]]]];
      }};
      private _payload=[_patient,"one",{str(accepted).lower()},"used",_rec,"body","",""];
      _payload call ACME_fnc_rehangUsedBagResult;_payload call ACME_fnc_rehangUsedBagResult;
      [count (_medic getVariable "ACME_usedBags")=={int(pending and match and not accepted)},"unsolicited/replayed result minted a bag"] call _check;
    ''')


def test_debug_renderer_is_byte_identical_to_b227():
    path='addons/acm_extended/functions/fn_debugMenuClinical.sqf'
    before=subprocess.check_output(['git','show','6135b2758ff1c8a772da2cef40939642ab1b174e:'+path],cwd=ROOT)
    assert (ROOT/path).read_bytes()==before


def test_y_claim_id_cannot_be_reused_for_the_other_limb():
    execute(refill_setup()+'''
      ["blood","one"] call _claim;["saline","one"] call _claim;
      [count _acks==2 && {!(_acks select 1 select 1 select 3)},"same ID authorized different limb"] call _check;
      [((_patient getVariable "ACME_yRefillClaims") get "body#false#0" select 2)=="blood","existing claim changed type"] call _check;
    ''')


@pytest.mark.parametrize('mode',['prime','flush'])
@pytest.mark.parametrize('flow',[0,1])
def test_service_io_effects_require_actual_admitted_fluid(mode,flow):
    execute(service_setup()+f'''
      [100,false,{str(mode=='flush').lower()}] call _init;_fraction={flow};
      ["{mode}","one"] call _request;[7] call _advance;
      [(_ioCalls>0) isEqualTo {str(flow>0).lower()},"service bypassed IO effects or caused effects without admission"] call _check;
    ''')


def service_paint_setup():
    # Execute the full paint and native RMB callback with only UI command adapters.
    from test_b222_suction_input import block
    text=read('transfusionServicePaint')
    i=text.index('if !(_flush getVariable');body=text[:i]
    body=body.replace('private _flush = _display displayCtrl 86143;', 'private _flush = missionNamespace;')
    body=body.replace('_flush ctrlShow _isY;', '_visible=_isY;')
    body=body.replace('_flush ctrlEnable ', '_enabled=')
    body=body.replace('ctrlText _flush', '_textValue').replace('_flush ctrlSetText _text;', '_textValue=_text;')
    body=body.replace('_flush ctrlSetTooltip _tip;', '_tooltip=_tip;')
    body=body.replace('_flush ctrlSetTextColor ', '_textColor=').replace('_flush ctrlSetBackgroundColor ', '_background=')
    callback=block(text,'_flush ctrlAddEventHandler ["MouseButtonDown",')
    callback=callback.replace('ctrlEnabled _control','_enabled').replace('ctrlShown _control','_visible')
    callback=re.sub(r'getArray \(configFile[^;]+;', '_nativeSound;',callback)
    callback=callback.replace('playSoundUI [_sound select 0,_sound select 1,_sound select 2];', '_sounds pushBack [_sound select 0,_sound select 1,_sound select 2];')
    return basic()+fn('yServicePlan')+'''
      private _state=[];private _visible=false;private _enabled=false;private _textValue="";private _tooltip="";
      private _textColor=[];private _background=[];private _sounds=[];private _clicks=0;private _cancelAllowed=true;
      private _nativeSound=["native-click.ogg",.09,1.15];
      ACME_fnc_yServiceState={_state};
      ACME_fnc_transfusionFlushLine={_clicks=_clicks+1;_cancelAllowed};
    '''+'private _paint={'+adapt(body)+'};'+'private _right={'+adapt(callback)+'};'


@pytest.mark.parametrize('primed,kind,expected',[(False,'','Prime Line (25 mL)'),(False,'prime','Priming...'),(True,'','Flush Line'),(True,'flush','Flush In Progress... (2)')])
def test_one_control_changes_prime_flush_label_without_recreation(primed,kind,expected):
    job='["body",false,0,"reserve",50,10,100,_medic,1,[50],"flush",50,0,"one"]' if kind=='flush' else ('["body",false,0,"reserve",25,5,100,_medic,1,[],"prime",25,0,"one"]' if kind else '[]')
    execute(service_paint_setup()+f'''
      _state=[500,0,false,false,{str(primed).lower()},"{kind}","reserve",{job}];
      [missionNamespace,_patient,"body",false,0,true] call _paint;
      [_visible && {{_textValue=="{expected}"}},"shared service button wrong label"] call _check;
    ''')


def test_required_flush_red_flash_stops_when_service_begins():
    execute(service_paint_setup()+'''
      _state=[500,0,false,true,true,"","reserve",[]];
      [missionNamespace,_patient,"body",false,0,true] call _paint;private _first=+_background;
      _nowTime=_nowTime+.25;[missionNamespace,_patient,"body",false,0,true] call _paint;
      [!(_background isEqualTo _first) && {(_background select 1)==0},"required flush did not pulse red"] call _check;
      _state set [5,"flush"];_state set [7,["body",false,0,"reserve",50,10,100,_medic,1,[],"flush",50,0,"one"]];
      [missionNamespace,_patient,"body",false,0,true] call _paint;
      [_background isEqualTo [0,0,0,1],"in-progress flush still flashes"] call _check;
    ''')


@pytest.mark.parametrize('button,enabled,allowed,sounds',[(1,True,True,1),(1,True,False,1),(1,False,True,0),(0,True,True,0),(2,True,True,0)])
def test_right_click_uses_native_click_sound_once_without_synthetic_left_action(button,enabled,allowed,sounds):
    execute(service_paint_setup()+f'''
      _enabled={str(enabled).lower()};_visible=true;_cancelAllowed={str(allowed).lower()};
      [missionNamespace,{button}] call _right;
      [count _sounds=={sounds},"wrong right-click sound count"] call _check;
      if (count _sounds>0) then {{[(_sounds select 0) isEqualTo _nativeSound,"not inherited native button sound"] call _check;}};
      [_clicks=={int(button==1 and enabled)},"click submitted twice or wrong button submitted"] call _check;
    ''')


def salvage_setup(name):
    text=src(name)
    return basic()+fn('yLinesCommit').replace('["ACME_YLines", _lines, _public]', '["ACME_YLines", _lines]')+'ACME_fnc_'+name+'={'+text+'};'+'''
      ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
      ace_common_fnc_isAwake={true};ACM_circulation_fnc_updateActiveFluidBags={};
      ACME_fnc_ivBagsCommit={params ["_p","_map"];_p setVariable ["ACM_circulation_IV_Bags",_map];};
      ACME_fnc_infusionMedicationStateCommit={params ["_p","_entries"];_p setVariable ["ACME_infusion_BagMedications",_entries];};
      _patient setVariable ["ACME_YLines",["body#false#0"]];
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[
        ["Blood",101,0,0,false,-1,500,-1,"blood"], ["ACME_SalineY",203,0,0,false,-1,500,-1,"reserve"]
      ]]]];
    '''


@pytest.mark.parametrize('bad',['none','identity','deadline','epoch','distant'])
def test_discard_is_bound_to_current_bags_and_salvages_exactly_once(bad):
    change={'none':'','identity':'_identity=["blood","old-reserve"];','deadline':'_at=80;','epoch':'_epoch=0;','distant':'_distance=10;'}[bad]
    execute(salvage_setup('discardYTubingCommit')+f'''
      private _identity=["blood","reserve"];private _at=_serverTime;private _epoch=_liveEpoch;{change}
      private _request=[_patient,_medic,"body",false,0,_epoch,"discard",_at,_identity];
      _request call ACME_fnc_discardYTubingCommit;_request call ACME_fnc_discardYTubingCommit;
      private _rows=(_patient getVariable "ACM_circulation_IV_Bags") get "body";
      [count _rows=={0 if bad=='none' else 2},"discard affected wrong/new bags"] call _check;
      if ({str(bad=='none').lower()}) then {{
        [count _events==2 && {{(_events select 0 select 1 select 3) isEqualTo (_events select 1 select 1 select 3)}},"duplicate discard response changed salvage"] call _check;
        [(_events select 0 select 1 select 3 select 0 select 1)==203,"wrong live salvage volume"] call _check;
      }};
    ''')


def test_discard_does_not_launder_medicated_carrier_into_plain_saline():
    execute(salvage_setup('discardYTubingCommit')+'''
      private _drug=[];_drug set [1,"body"];_drug set [4,0];_drug set [5,false];_drug set [23,"reserve"];
      _patient setVariable ["ACME_infusion_BagMedications",[_drug]];
      [_patient,_medic,"body",false,0,_liveEpoch,"discard",_serverTime,["blood","reserve"]] call ACME_fnc_discardYTubingCommit;
      private _salvage=_events select 0 select 1 select 3;
      [count _salvage==1 && {(_salvage select 0 select 0)=="Blood"},"drug carrier became plain used saline"] call _check;
      [count (_patient getVariable "ACME_infusion_BagMedications")==0,"discarded medication record remains"] call _check;
    ''')


@pytest.mark.parametrize('name,var',[('transfusionPullResult','ACME_txPullPending'),('discardYTubingResult','ACME_yDiscardPending')])
@pytest.mark.parametrize('pending',[False,True])
def test_salvage_result_mints_only_once_and_only_for_pending_request(name,var,pending):
    text=src(name).replace('isNull ACE_player','(ACE_player isEqualTo objNull)').replace('!local _provider','!true')
    payload='[_patient,"one",true,_bag,"body","used",true,""]' if name=='transfusionPullResult' else '[_patient,"one",true,[_bag],"body",false,0,""]'
    execute(basic()+'ACME_fnc_'+name+'={'+text+'};'+f'''
      ACME_fnc_updateTransfusionControls={{}};
      private _bag=["Saline",100,0,0,false,-1,500,-1,"bag"];
      _medic setVariable ["ACME_usedBags",[]];
      uiNamespace setVariable ["{var}",createHashMap];
      if ({str(pending).lower()}) then {{uiNamespace setVariable ["{var}",createHashMapFromArray [["one",[_medic,_patient]]]];}};
      {payload} call ACME_fnc_{name};{payload} call ACME_fnc_{name};
      [count (_medic getVariable "ACME_usedBags")=={int(pending)},"unsolicited/replayed salvage duplicated stock"] call _check;
    ''')


@pytest.mark.parametrize('case',['normal','expired','wrong-uid','distant'])
def test_pull_uses_current_owner_volume_and_stable_identity(case):
    modify={'normal':'','expired':'_at=80;','wrong-uid':'_uid="old";','distant':'_distance=9;'}[case]
    execute(salvage_setup('transfusionPullCommit')+f'''
      private _at=_serverTime;private _uid="blood";{modify}
      private _req=[_patient,_medic,"body",_uid,0,[],_liveEpoch,"pull",_at];
      _req call ACME_fnc_transfusionPullCommit;_req call ACME_fnc_transfusionPullCommit;
      private _row=(_patient getVariable "ACM_circulation_IV_Bags") get "body" select 0;
      [(_row select 1)=={0 if case=='normal' else 101},"pull changed wrong row"] call _check;
      if ({str(case=='normal').lower()}) then {{
        [(_events select 0 select 1 select 3 select 1)==101,"pull returned stale/default bag volume"] call _check;
        [(_events select 0 select 1) isEqualTo (_events select 1 select 1),"duplicate pull changed receipt"] call _check;
      }};
    ''')
