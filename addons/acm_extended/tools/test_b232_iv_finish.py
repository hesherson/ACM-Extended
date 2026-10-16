"""B232 physical IV finish: actual SQF rules/transactions; engine/UI boundaries mocked.

No test claims native blood-return rendering or real multiplayer packet execution.
"""
import hashlib
import json
import re
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_historical_vial_execution import map_defaults

ASSETS = ROOT / 'addons/acm_extended/ui/iv/finish'
FUNCTIONS = ['ivSupplyBind','ivSupplyScopeCheck','ivSupplyRelease','ivFieldTransition','ivFieldClear','ivFieldAccessoryRow','ivFinishPlan','ivFinishFrame','ivFinishPatency','ivFinishCommit',
             'ivMarkCommit','ivFinishReply','ivFinishAbort','ivFinishRetry']

def source(name):
    s=adapt(read(name)).replace('serverTime','_serverTime')
    # Native clock finiteness and UI handles use explicit scalar/namespace stand-ins.
    s=s.replace('finite _deadline','(_deadline isEqualType 0)').replace('finite _epoch','(_epoch isEqualType 0)')
    # Only the native OBJECT type boundary is adapted: namespace stand-ins
    # represent donor/provider objects; objNull remains the vehicle sentinel.
    for idx in (0,2):
        native=f'(_receipt select {idx}) isEqualType objNull'
        s=s.replace(native, '('+native+f' || {{(_receipt select {idx}) isEqualType missionNamespace}})')
    s=map_defaults(s)
    return s

def rules():
    return ''.join(f'ACME_fnc_{n}={{'+source(n)+'};\n' for n in FUNCTIONS)

SETUP = r'''
private _serverTime=100;
private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
missionNamespace setVariable ["ACME_supplyReceipts",createHashMap];
missionNamespace setVariable ["ACME_IV_SupplyScopes",createHashMap];
_medic setVariable ["ACME_IV_SupplyBindings",[]];
private _fixtureIssued=[];

private _testClinicalEpoch=7;
private _hasIV=true;
private _viewValid=true;
private _refunds=[];
private _renders=0;private _refreshes=0;
private _messages=[];
private _d=missionNamespace;
ACME_fnc_clinicalEpoch={_testClinicalEpoch};
ACME_fnc_patientInteractionDistance={_distance};
ACM_circulation_fnc_hasIV={_hasIV};
ACME_fnc_ivSiteIndex={switch (_this select 0) do {case "upper":{0};case "middle":{1};case "lower":{2};case "left":{0};case "right":{1};default{-1}}};
ACME_fnc_treatmentSupplyRefund={_refunds pushBack _this;};
ACME_fnc_ivMinigameViewValid={_viewValid};
ACME_fnc_ivMinigameRenderMarks={_renders=_renders+1;};
ACME_fnc_ivMinigameRefreshBandSlot={_refreshes=_refreshes+1;};
ace_common_fnc_displayTextStructured={_messages pushBack (_this select 0);};
private _receipt=[_medic,"ACM_SalineFlush_10",objNull,"stock1"];
private _row=["leftarm","front",0.5,0.5,"hub","","",16,-1,1,"middle",0,1,0,"ivhub:7:1",[false,false,false,false],[]];
_patient setVariable ["ACME_IV_Marks",[+_row]];
_patient setVariable ["ACME_IV_FinishReceipts",[]];
_patient setVariable ["ACME_IV_MarkVer",0];
_patient setVariable ["ACME_ivCompromised_leftarm_1",false];
uiNamespace setVariable ["ACME_IV_DLG",_d];
uiNamespace setVariable ["ACME_IV_Medic",_medic];
private _invoke={
    params ["_phase","_action",["_token","token"],["_receiptArg",[]],["_uid","ivhub:7:1"],["_ep",7],["_deadline",130]];
    // Native inventory is a fixture boundary. Mint each fixture receipt once;
    // production binding/scope checks execute unchanged. Never rebind a replay.
    if (_phase=="begin" && {count _receiptArg==4} && {!((_receiptArg select 3) in _fixtureIssued)}) then {
        _fixtureIssued pushBack (_receiptArg select 3);
        (missionNamespace getVariable "ACME_supplyReceipts") set [_receiptArg select 3,+_receiptArg];
        [_medic,_patient,_uid,_action,_token,_ep,_deadline,_receiptArg] call ACME_fnc_ivSupplyBind;
    };
    [_patient,_medic,_phase,_uid,_action,_token,_ep,_deadline,_receiptArg] call ACME_fnc_ivFinishCommit;
};
private _getRow={(_patient getVariable ["ACME_IV_Marks",[]]) select 0};
private _getState={(call _getRow) select 15};
private _lastReply={(_events select (count _events-1)) select 2};
private _credits={_events select {(_x select 1)=="crystalloidCredit"}};
'''

def run(body):
    execute(SETUP+rules()+body)

@pytest.mark.parametrize('action,state,patent,allowed,sequence',[
 ('extension',[False]*4,True,True,'extension_attach'),
 ('extension',[True,False,False,False],True,False,''),
 ('flush',[False]*4,True,False,''),
 ('flush',[True,False,False,False],True,True,'blood_return_flush'),
 ('flush',[True,False,False,False],False,True,'resisted_no_return'),
 ('flush',[True]*4,True,False,''),
 ('dressing',[True,False,False,False],True,False,''),
 ('dressing',[True,True,False,False],True,True,'tegaderm_apply'),
 ('dressing',[True,True,False,False],False,False,''),
 ('dressing',[True,True,True,False],True,False,''),
 ('line',[True,True,False,False],True,False,''),
 ('line',[True,True,True,False],True,True,'iv_line_attach'),
 ('line',[True,True,True,False],False,False,''),
 ('line',[True]*4,True,False,''),
 ('unknown',[False]*4,True,False,''),
])
def test_procedure_rules(action,state,patent,allowed,sequence):
    b=lambda v:'true' if v else 'false'
    st='['+','.join(map(b,state))+']'
    run(f'private _p=[{st},"{action}",{b(patent)}] call ACME_fnc_ivFinishPlan;'
        f'[(_p select 0)=={b(allowed)},"permission"] call _check;'
        f'[(_p select 2)=="{sequence}","authored branch"] call _check;')

@pytest.mark.parametrize('seq,time,expected',[
 ('extension_attach',0,'extension_attach_0000'),('extension_attach',500,'extension_attach_0023'),
 ('iv_line_attach',500,'iv_line_attach_0029'),('tegaderm_apply',500,'tegaderm_apply_0035'),
 ('blood_return_flush',0,'blood_return_flush_0000'),('blood_return_flush',5.99,'blood_return_flush_0179'),
 ('blood_return_flush',6,'post_flush_secure_0000'),('blood_return_flush',100,'post_flush_secure_0041'),
 ('resisted_no_return',3.99,'resisted_no_return_0119'),('resisted_no_return',4,'resisted_no_return_0047'),
 ('resisted_no_return',100,'resisted_no_return_0000'),('blood_return_flush',-10,'blood_return_flush_0000'),
])
def test_frames_are_bounded_and_failed_syringe_never_uses_empty_branch(seq,time,expected):
    run(f'private _f=["{seq}",{time/1.25 if seq in ["blood_return_flush","resisted_no_return"] else time}] call ACME_fnc_ivFinishFrame;'
        f'[(_f find "{expected}_ca.paa")>=0,"frame"] call _check;')

@pytest.mark.parametrize('bp,site,key', [('leftarm','upper','leftarm_0'),('rightarm','middle','rightarm_1'),
 ('leftleg','lower','leftleg_2'),('ej','left','head_0'),('ej','right','head_1')])
def test_actual_site_compromise_drives_aspiration(bp,site,key):
    run(f'_row set [0,"{bp}"];_row set [10,"{site}"];'
        f'_patient setVariable ["ACME_ivCompromised_{key}",false];'
        '[[_patient,_row] call ACME_fnc_ivFinishPatency,"good"] call _check;'
        f'_patient setVariable ["ACME_ivCompromised_{key}",true];'
        '[!([_patient,_row] call ACME_fnc_ivFinishPatency),"missed"] call _check;'
        f'_patient setVariable ["ACME_ivCompromised_{key}",false];_hasIV=false;'
        '[!([_patient,_row] call ACME_fnc_ivFinishPatency),"removed"] call _check;')

def test_complete_good_workflow_credits_exactly_ten_ml_once():
    run(r'''
["begin","extension","ext"] call _invoke;
[_patient getVariable ["ACME_IV_MarkVer",0]==1,"started"] call _check;
["finish","extension","ext"] call _invoke;
[!(call _getState select 0),"cannot fast-forward"] call _check;
_serverTime=101;["finish","extension","ext"] call _invoke;
[(call _getState select 0),"extension committed"] call _check;
["begin","flush","flush",_receipt] call _invoke;
[((call _getRow select 16) select 5)=="blood_return_flush","native patency"] call _check;
[count (call _credits)==0,"no early credit"] call _check;
_serverTime=109;["finish","flush","flush"] call _invoke;
["finish","flush","flush"] call _invoke;
[count (call _credits)==1,"one credit"] call _check;
[(((call _credits) select 0) select 2) isEqualTo [0.010],"ten ml litres"] call _check;
[(call _getState select 1),"tested"] call _check;
["begin","dressing","dress"] call _invoke;_serverTime=111;["finish","dressing","dress"] call _invoke;
["begin","line","line"] call _invoke;_serverTime=112;["finish","line","line"] call _invoke;
[(call _getState) isEqualTo [true,true,true,true],"finished"] call _check;
''')

def test_missed_placement_uses_resisted_branch_without_fluid_or_repair():
    run(r'''
_row set [15,[true,false,false,false]];_patient setVariable ["ACME_IV_Marks",[_row]];
_patient setVariable ["ACME_ivCompromised_leftarm_1",true];
["begin","flush","f",_receipt] call _invoke;
[((call _getRow select 16) select 5)=="resisted_no_return","correct branch"] call _check;
_serverTime=106;["finish","flush","f"] call _invoke;
[count (call _credits)==0,"no injected fluid"] call _check;
[!(call _getState select 1),"not marked good"] call _check;
[_patient getVariable ["ACME_ivCompromised_leftarm_1",false],"not repaired"] call _check;
["begin","dressing","d"] call _invoke;
[!((call _lastReply) select 4),"cannot secure as checked"] call _check;
''')

@pytest.mark.parametrize('change',[
 '_hasIV=false;', '_testClinicalEpoch=8;', '_distance=4;', '_alive=false;',
 '_medic setVariable ["ACE_isUnconscious",true];',
 '_patient setVariable ["ACME_ivCompromised_leftarm_1",true];',
 '_row set [14,"newhub"];_patient setVariable ["ACME_IV_Marks",[_row]];',
 '_row set [4,"removed"];_patient setVariable ["ACME_IV_Marks",[_row]];'
])
def test_invalidation_never_credits_fluid(change):
    run(r'''_row set [15,[true,false,false,false]];_patient setVariable ["ACME_IV_Marks",[_row]];
["begin","flush","f",_receipt] call _invoke;'''+change+r'''
_serverTime=108;["finish","flush","f"] call _invoke;
[count (call _credits)==0,"no credit after invalidation"] call _check;
''')

@pytest.mark.parametrize('phase', ['cancel_before','cancel_after','duplicate_begin','other_token','changed_deadline','missing_receipt','wrong_receipt'])
def test_reservation_and_replay_boundaries(phase):
    body=r'''_row set [15,[true,false,false,false]];_patient setVariable ["ACME_IV_Marks",[_row]];'''
    if phase=='cancel_before':
        body+='["cancel","flush","f"] call _invoke;["begin","flush","f",_receipt] call _invoke;[(call _getRow select 16) isEqualTo [],"tombstone"] call _check;'
    elif phase=='cancel_after':
        body+='["begin","flush","f",_receipt] call _invoke;["cancel","flush","f"] call _invoke;_serverTime=108;["finish","flush","f"] call _invoke;[(call _getRow select 16) isEqualTo [],"cancelled"] call _check;'
    elif phase=='duplicate_begin':
        body+='["begin","flush","f",_receipt] call _invoke;_serverTime=101;["begin","flush","f",_receipt] call _invoke;[((call _getRow select 16) select 3)==100,"not restarted"] call _check;'
    elif phase=='other_token':
        body+='["begin","flush","f",_receipt] call _invoke;["begin","flush","g",_receipt] call _invoke;[!((call _lastReply) select 4),"locked"] call _check;[((call _getRow select 16) select 0)=="f","original preserved"] call _check;'
    elif phase=='changed_deadline':
        body+='["begin","flush","f",_receipt] call _invoke;private _n=count _events;["finish","flush","f",[],"ivhub:7:1",7,200] call _invoke;[count _events==_n,"fingerprint"] call _check;'
    else:
        if phase=='wrong_receipt':body+='_receipt set [1,"ACM_Syringe_10"];'
        else:body+='_receipt=[];'
        body+='["begin","flush","f",_receipt] call _invoke;[!((call _lastReply) select 4),"missing sterile flush"] call _check;'
    run(body+'[count (call _credits)==0,"no stray saline"] call _check;')

@pytest.mark.parametrize('accepted', [True,False])
def test_ack_settles_only_matching_reservation_once(accepted):
    a=str(accepted).lower()
    run(r'''
private _context=[_d,[],0,"leftarm","front"];
_medic setVariable ["ACME_IV_FinishPending",[_patient,"f","ivhub:7:1","flush",7,130,_receipt,_context,false]];
[_medic,_patient,"wrong","done",false,"",_row] call ACME_fnc_ivFinishReply;
[count _refunds==0,"unsolicited"] call _check;
'''+f'[_medic,_patient,"f","done",{a},"",_row] call ACME_fnc_ivFinishReply;'
      f'[_medic,_patient,"f","done",{a},"",_row] call ACME_fnc_ivFinishReply;'
      f'[count _refunds==1 && {{((_refunds select 0) select 1)=={str(not accepted).lower()}}},"settled once"] call _check;')

def test_stale_view_ack_commits_used_syringe_but_never_restarts_ui():
    run(r'''
_viewValid=false;
_medic setVariable ["ACME_IV_FinishPending",[_patient,"f","ivhub:7:1","flush",7,130,_receipt,[_d,[],0,"leftarm","front"],false]];
[_medic,_patient,"f","begin",true,"",_row] call ACME_fnc_ivFinishReply;
[count _refunds==1 && {!((_refunds select 0) select 1)},"used not refunded"] call _check;
[_renders==0,"no stale rendering"] call _check;
[(((_events select 0) select 2) select 1)=="cancel","retired on owner"] call _check;
''')

def test_lost_ack_timeout_does_not_duplicate_consumable():
    run(r'''
_medic setVariable ["ACME_IV_FinishPending",[_patient,"f","ivhub:7:1","flush",7,130,_receipt,[_d,[],0,"leftarm","front"],false]];
_serverTime=133;[_medic,"f"] call ACME_fnc_ivFinishRetry;
[count _refunds==1 && {!((_refunds select 0) select 1)},"no speculative refund"] call _check;
[(_medic getVariable ["ACME_IV_FinishPending",[]]) isEqualTo [],"unlocked"] call _check;
[count _waits==0,"bounded"] call _check;
''')

def test_saved_hub_ids_cannot_collide_with_reset_serial():
    run(r'''
_patient setVariable ["ACME_IV_HubSerial",0];
private _new=+_row;_new set [10,"upper"];
[_patient,"add",[_new],7] call ACME_fnc_ivMarkCommit;
private _marks=_patient getVariable ["ACME_IV_Marks",[]];
[count _marks==2 && {((_marks select 0) select 14)!=((_marks select 1) select 14)},"unique after reload"] call _check;
''')

def test_legacy_connected_marks_migrate_only_once():
    run(r'''
_row resize 14;_row set [5,"iv_line_connected_16g.paa"];_patient setVariable ["ACME_IV_Marks",[_row]];
[_patient,"finishmigrate",[],7] call ACME_fnc_ivMarkCommit;
private _old=+(call _getRow);
[_patient,"finishmigrate",[],7] call ACME_fnc_ivMarkCommit;
[(call _getState) isEqualTo [true,true,true,true],"grandfathered"] call _check;
[(call _getRow) isEqualTo _old,"idempotent"] call _check;
''')

def test_no_new_permanent_frame_worker_and_native_site_result_retained():
    assert 'addPerFrameHandler' not in read('ivFinishTick')
    assert 'ivFinishTick' in read('ivMinigameTick')
    assert 'setVariable' not in read('ivFinishPatency')
    assert 'ACME_ivCompromised_' in read('ivFinishPatency')
    assert read('ivMinigameResetView').index('ivFinishAbort') < read('ivMinigameResetView').index('ACME_IV_ViewGeneration')
    assert 'ACM_SalineFlush_10' in read('ivFinishStart')
    assert 'ACM_Syringe_10' not in read('ivFinishStart')

@pytest.mark.parametrize('name', FUNCTIONS+['ivFinishStart','ivFinishTick','ivFinishTray','ivFinishGrab','ivFinishPose'])
def test_registration(name):
    assert re.search(r'\bclass\s+'+name+r'\s*\{', (ROOT/'addons/acm_extended/config.cpp').read_text())


def test_all_shipped_asset_hashes_and_count():
    data=json.loads((ASSETS/'manifest.json').read_text())
    paths=list(ASSETS.glob('*.paa'))
    assert len(paths)==443
    # Digest validation reads the actual converted game files, not the preview sources.
    digests=data['files']
    for p in paths:
        expected=digests[p.name] if isinstance(digests,dict) else None
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,p.name

@pytest.mark.parametrize('stem,last', [('extension_attach',23),('iv_line_attach',29),('blood_return_flush',179),('resisted_no_return',119),('post_flush_secure',41),('tegaderm_apply',35)])
def test_each_authored_sequence_is_contiguous(stem,last):
    for i in range(last+1):assert (ASSETS/f'{stem}_{i:04d}_ca.paa').is_file()


def start_source():
    s=source('ivFinishStart')
    s=re.sub(r'private _axis=\(uiNamespace getVariable \["ACME_IV_FrameAxis",createHashMap\]\) getOrDefault \[[^;]+;',
             'private _axis=_testAxis;',s)
    s=s.replace('pixelW','_testPixelW').replace('pixelH','_testPixelH')
    s=s.replace('netId _medic','"provider"')
    s=re.sub(r'\(uiNamespace getVariable \["ACME_IV_HeldCursorCtrl",objNull\]\) ctrlShow false;', '_cursorHidden=true;', s)
    s=s.replace('playSound "ACE_Sound_Click";','_clicks=_clicks+1;')
    return s

def geometry_source(name):
    s=source(name).replace('pixelW','_testPixelW').replace('pixelH','_testPixelH')
    if name=='ivFinishGeometry':
        s=re.sub(r'private _axis=.+?;', 'private _axis=_testAxis;',s)
    return map_defaults(s)

START_SETUP=r'''
private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
private _testAxis=[0,-1];private _testPixelW=1/1920;private _testPixelH=1/1080;
private _clicks=0;private _cursorHidden=false;private _takes=0;private _stock=true;private _testSupplyReceipt=+_receipt;
ACME_fnc_ivUiValid={true};
ACME_fnc_treatmentSupplyTake={_takes=_takes+1;if (_stock) then {
    (missionNamespace getVariable "ACME_supplyReceipts") set [_testSupplyReceipt select 3,+_testSupplyReceipt];
    _testSupplyReceipt
} else {[]}};
uiNamespace setVariable ["ACME_IV_Patient",_patient];
uiNamespace setVariable ["ACME_IV_BodyPart","leftarm"];
uiNamespace setVariable ["ACME_IV_View","front"];
uiNamespace setVariable ["ACME_IV_AspectFix",0.5625];
uiNamespace setVariable ["ACME_IV_CathScale",0.62];
uiNamespace setVariable ["ACME_IV_BodyRect",[0,0,1,1]];
uiNamespace setVariable ["ACME_IV_Session",[_patient,7,5]];
_d setVariable ["ACME_IV_ViewGeneration",2];
uiNamespace setVariable ["ACME_IV_Held","flush"];
_row set [15,[true,false,false,false]];_patient setVariable ["ACME_IV_Marks",[_row]];
'''+''.join('ACME_fnc_'+n+'={'+geometry_source(n)+'};' for n in ['ivFinishGeometry','ivFinishPoint','ivFieldPoint','ivFieldPort','ivFieldSecondaryRow','ivFieldAccessoryRow','ivFinishTarget'])

@pytest.mark.parametrize('scenario',['normal','repeat_click','other_view','no_stock','no_hub','needs_extension','missed_site'])
def test_real_click_launch_and_exact_supply_reservation(scenario):
    body=START_SETUP+'ACME_fnc_ivFinishStart={'+start_source()+'};'
    if scenario=='other_view':body+='uiNamespace setVariable ["ACME_IV_View","back"];'
    if scenario=='no_stock':body+='_stock=false;'
    if scenario=='no_hub':body+='_patient setVariable ["ACME_IV_Marks",[]];'
    if scenario=='needs_extension':body+='_row set [15,[false,false,false,false]];_patient setVariable ["ACME_IV_Marks",[_row]];'
    if scenario=='missed_site':body+='_patient setVariable ["ACME_ivCompromised_leftarm_1",true];'
    body+='([_row,[1033.02/2048,1386.52/2048]] call ACME_fnc_ivFinishPoint) call ACME_fnc_ivFinishStart;'
    if scenario=='repeat_click':body+='([_row,[1033.02/2048,1386.52/2048]] call ACME_fnc_ivFinishPoint) call ACME_fnc_ivFinishStart;'
    allowed=scenario in ['normal','repeat_click','missed_site']
    body+=f'[count _events=={1 if allowed else 0},"one request or local rejection"] call _check;'
    body+=f'[_takes=={1 if allowed or scenario=="no_stock" else 0},"supply reservation count"] call _check;'
    if allowed:
        body+='[(_d getVariable ["ACME_IV_FinishBusy",false]) && {_cursorHidden},"pending visible state"] call _check;'
        body+='[(((_events select 0) select 2) select 2)=="ivhub:7:1","exact UID"] call _check;'
    run(body)

@pytest.mark.parametrize('angle',[0,15,-15,165,-165])
def test_distal_port_target_matches_square_pixel_asset_transform(angle):
    # The port uses the same physical square canvas, including non-square body panel.
    import math
    t=math.radians(angle)
    dx=(1033.02-1006.5)/2048*.62;dy=(1386.52-1032)/2048*.62
    ratio=(1/1920)/(1/1080)
    hu=(.49246-.49166)*.62;hv=(.50391-.44434)*.62
    u=.5+((hu+dx)*math.cos(t)-(hv+dy)*math.sin(t))*ratio
    v=.5+(hu+dx)*math.sin(t)+(hv+dy)*math.cos(t)
    run(START_SETUP+f'_row set [13,{angle}];_patient setVariable ["ACME_IV_Marks",[_row]];'+
        'ACME_fnc_ivFinishStart={'+start_source()+'};'+
        f'[{u},{v}] call ACME_fnc_ivFinishStart;'+
        '[count _events==1,"actual distal port hit"] call _check;')


def test_successful_end_frame_contains_only_extension_not_floating_piston():
    import numpy as np
    from paa import read_paa
    rgb,alpha=read_paa(ASSETS/'post_flush_secure_0041_ca.paa',want=512)
    rgb2,alpha2=read_paa(ASSETS/'extension_ca.paa',want=512)
    # Verify shipped (decoded) PAA, not just source PNG. DXT rounding permits minor edge noise.
    assert abs(alpha.astype(float)-alpha2.astype(float)).mean()<0.5
    assert int(alpha[370:].max())==0


def test_migration_is_requested_on_open_and_owner_only_mutates_marks():
    assert '"ivMarks",["finishmigrate",[],[_patient] call ACME_fnc_clinicalEpoch]' in read('ivMinigameInit')
    assert 'setVariable ["ACME_IV_Marks"' not in read('ivFinishStart')
    assert 'setVariable ["ACME_IV_Marks"' not in read('ivFinishTick')
    assert '"ivFinish": {([_patient]+_args) call ACME_fnc_ivFinishCommit;}' in read('ownerDispatch')

@pytest.mark.parametrize('boundary',['complete','duplicate_frame','cancel','view_changed','range','compromised'])
def test_real_active_tick_completes_once_or_aborts(boundary):
    body=r'''
ACME_fnc_ivFinishTick={'''+source('ivFinishTick')+r'''};
_row set [15,[true,false,false,false]];
_row set [16,["f",_medic,"flush",100,7.4,"blood_return_flush",130]];
_patient setVariable ["ACME_IV_Marks",[_row]];
uiNamespace setVariable ["ACME_IV_Patient",_patient];
_medic setVariable ["ACME_IV_FinishPending",[_patient,"f","ivhub:7:1","flush",7,130,[],[_d,[],0,"leftarm","front"],false]];
_d setVariable ["ACME_IV_FinishActive",[_row,10,false]];
_d setVariable ["ACME_IV_FinishBusy",true];
_d setVariable ["ACME_IV_FinishCtrls",[]];
[] call ACME_fnc_ivFinishTick;
[count _events==0,"not completed early"] call _check;
'''
    if boundary=='view_changed':body+='_viewValid=false;'
    if boundary=='range':body+='_distance=4;'
    if boundary=='compromised':body+='_patient setVariable ["ACME_ivCompromised_leftarm_1",true];'
    if boundary=='cancel':body+='[] call ACME_fnc_ivFinishAbort;'
    body+='_nowTime=18;_serverTime=108;[] call ACME_fnc_ivFinishTick;'
    if boundary=='duplicate_frame':body+='[] call ACME_fnc_ivFinishTick;'
    wanted='finish' if boundary in ['complete','duplicate_frame'] else 'cancel'
    body+=f'[count _events==1 && {{(((_events select 0) select 2) select 1)=="{wanted}"}},"exact completion or cancel"] call _check;'
    run(body)

@pytest.mark.parametrize('width,height,scale',[(1680,1050,1),(1920,1080,1),(2560,1440,1),(3440,1440,1),(5120,1440,1.5),(1280,720,1.5)])
def test_extra_tool_column_stays_in_canvas_and_does_not_overlap_native_column(width,height,scale):
    # Evaluate production tray dimensions in a normalized safe-zone view.
    aspect=height/width
    slot_w=.066*scale;slot_h=slot_w*aspect*.92;label=.024;gap=.012;y=.115
    need=(slot_h+label+gap)*6;avail=.97-y
    if need>avail:
        fit=avail/need;slot_w*=fit;slot_h*=fit;label*=fit;gap*=fit
    native_x=.961-slot_w;left=native_x-slot_w-.012
    assert left>0 and left+slot_w<native_x
    assert y+4*(slot_h+label+gap)<=.97
    assert '[_display,_colX-_slotW-(_szW*0.012),_colY,_slotW,_slotH,_lblH,_step]' in read('ivMinigameInit')


def test_sampler_paths_resolve_for_every_frame_of_all_branches():
    # Exact production sampler is executed through SQF tests above. Check the full set it can address.
    for seq in ['extension_attach','iv_line_attach','tegaderm_apply','blood_return_flush','resisted_no_return']:
        for frame in range(301):
            stem=seq;idx=frame
            if seq=='extension_attach':idx=min(frame,23)
            elif seq=='iv_line_attach':idx=min(frame,29)
            elif seq=='tegaderm_apply':idx=min(frame,35)
            elif seq=='blood_return_flush' and frame>=180:stem='post_flush_secure';idx=min(frame-180,41)
            elif seq=='resisted_no_return' and frame>=120:idx=max(47-(frame-120),0)
            assert (ASSETS/f'{stem}_{idx:04d}_ca.paa').is_file()

@pytest.mark.parametrize('limb,site,idx,site_idx',[('leftarm','middle',2,1),('rightarm','upper',3,0),('ej','left',0,0),('ej','right',0,1)])
def test_native_hasiv_lookup_uses_requested_access_not_neighbor(limb,site,idx,site_idx):
    native=adapt((ROOT/'addons/circulation/functions/fnc_hasIV.sqf').read_text(),component='circulation')
    native=native.replace('GET_IV(_patient)','(_patient getVariable ["ACM_circulation_IV_Placement",[]])')
    native=native.replace('ALL_BODY_PARTS','["head","body","leftarm","rightarm","leftleg","rightleg"]')
    native=native.replace('ACM_IV_PLACEMENT_DEFAULT_0','[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]')
    run('ACM_circulation_fnc_hasIV={'+native+'};'+f'''
_row set [0,"{limb}"];_row set [10,"{site}"];
private _placement=[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]];
(_placement select {idx}) set [{site_idx},1];
_patient setVariable ["ACM_circulation_IV_Placement",_placement];
[[_patient,_row] call ACME_fnc_ivFinishPatency,"native access found"] call _check;
(_placement select {idx}) set [{site_idx},0];
(_placement select {idx}) set [{(site_idx+1)%3},1];
_patient setVariable ["ACM_circulation_IV_Placement",_placement];
[!([_patient,_row] call ACME_fnc_ivFinishPatency),"neighbor cannot establish patency"] call _check;
''')


def test_distinct_hubs_and_providers_do_not_cross_complete():
    run(r'''
_row set [15,[true,false,false,false]];
private _other=+_row;_other set [10,"upper"];_other set [14,"ivhub:7:2"];
_patient setVariable ["ACME_IV_Marks",[_row,_other]];
["begin","flush","f",_receipt] call _invoke;
_serverTime=108;
[_patient,missionNamespace,"finish","ivhub:7:1","flush","f",7,130] call ACME_fnc_ivFinishCommit;
["finish","flush","f",[],"ivhub:7:2"] call _invoke;
[count (call _credits)==0,"wrong hub/provider rejected"] call _check;
["finish","flush","f"] call _invoke;
[count (call _credits)==1,"actual provider completed"] call _check;
private _marks=_patient getVariable ["ACME_IV_Marks",[]];
[((_marks select 1) select 15) isEqualTo [true,false,false,false],"neighbor unaffected"] call _check;
''')


def test_tool_button_click_is_not_swallowed_by_body_router():
    text=read('ivMinigameClick')
    assert 'if (_onFinishTray) exitWith {false};' in text
    assert text.index('if (_onFinishTray)') < text.index('if (_held in ["extension","flush","dressing","line","lock"])')
    assert 'ctrlAddEventHandler ["ButtonClick"' in read('ivFinishTray')


def test_complete_provider_owner_ack_animation_owner_ack_loop():
    # Networking transport and engine UI are simulated, but every production
    # callback in the transaction executes synchronously in its actual order.
    body=START_SETUP+'ACME_fnc_ivFinishStart={'+start_source()+'};ACME_fnc_ivFinishTick={'+source('ivFinishTick')+r'''};
ACME_fnc_ownerDispatch={
 _events pushBack +_this;
 params ["_target","_op","_args"];
 switch (_op) do {
  case "ivFinish": {([_target]+_args) call ACME_fnc_ivFinishCommit;};
  case "ivFinishReply": {_args call ACME_fnc_ivFinishReply;};
 };
};
_d setVariable ["ACME_IV_FinishCtrls",[]];
([_row,[1033.02/2048,1386.52/2048]] call ACME_fnc_ivFinishPoint) call ACME_fnc_ivFinishStart;
[(_d getVariable ["ACME_IV_FinishBusy",false]),"awaiting sequence"] call _check;
[count (_d getVariable ["ACME_IV_FinishActive",[]])==3,"ACK enabled animation"] call _check;
[count _refunds==1 && {!((_refunds select 0) select 1)},"ACK commits one syringe"] call _check;
_nowTime=18;_serverTime=108;[] call ACME_fnc_ivFinishTick;
[count (_medic getVariable ["ACME_IV_FinishPending",[]])==0,"finish ACK released pending"] call _check;
[!(_d getVariable ["ACME_IV_FinishBusy",false]),"UI unlocked"] call _check;
[count (call _credits)==1,"one saline credit"] call _check;
[(call _getState select 1),"test completed"] call _check;
[] call ACME_fnc_ivFinishTick;
[count (call _credits)==1 && {count _refunds==1},"no extra delivery or supply mutation"] call _check;
'''
    run(body)


def test_native_seeded_access_also_gets_unique_finishing_identity():
    run('ACME_fnc_ivSeedHub={'+source('ivSeedHub')+r'''};
_patient setVariable ["ACME_IV_Marks",[]];
_patient setVariable ["ACM_circulation_IV_Placement",[[0,0,0],[0,0,0],[0,1,0],[0,0,0],[0,0,0],[0,0,0]]];
ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
ACME_fnc_ivSiteData={["front","band",0.5,0.5,0.5,0.5]};
[_medic,_patient,"leftarm",1,true,1] call ACME_fnc_ivSeedHub;
[(_waits select 0) select 1] call {(_this select 0) call ((_waits select 0) select 0);};
private _marks=_patient getVariable ["ACME_IV_Marks",[]];
[count _marks==1 && {((_marks select 0) param [14,""])!=""},"native UID assigned"] call _check;
[(_waits select 0) select 1] call {(_this select 0) call ((_waits select 0) select 0);};
[count (_patient getVariable ["ACME_IV_Marks",[]])==1,"no repeated seed"] call _check;
''')
