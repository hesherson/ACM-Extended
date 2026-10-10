"""B234 field-IV owner transactions, native insertion and coordinate contracts.

SQF-VM executes production rules and controllers. Native rendering, physical
mouse input, inventory engine behavior and networking are explicit boundaries.
"""
import json, math, re, hashlib
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b232_iv_finish import SETUP, rules, START_SETUP, geometry_source, start_source, source
from test_b233_iv_interactions import FAMILIES
from test_historical_vial_execution import map_defaults


def run(body):
    execute(SETUP+rules()+body)


def field_state(sec=0, ext=False, tested=False, dressed=False, line=False):
    return json.dumps([ext,tested,dressed,line,True,sec]).lower()


@pytest.mark.parametrize('base',[14,16,18,20])
@pytest.mark.parametrize('second',[14,16])
def test_field_gauges_and_base_access(base,second):
    run(f'''private _p=[{field_state(dressed=True)},"field{second}",false,{base}] call ACME_fnc_ivFinishPlan;
    [(_p select 0)=={str(base in [14,16]).lower()},"large bore rule"] call _check;''')


@pytest.mark.parametrize('state',[
    [False]*4,[False,False,False,False,True,14],
    [True,False,True,False,True,0],[False,False,False,False,True,0],
    [False,False,False,True,True,0]])
def test_field_requires_exposed_empty_lock(state):
    # B235: exposed port now means a covered primary lock without downstream hardware.
    # Keep this case identity while rejecting an UNDRESSED primary, not the required film.
    run(f'[!(([{json.dumps(state).lower()},"field16",true,16] call ACME_fnc_ivFinishPlan) select 0),"exposed port"] call _check;')


@pytest.mark.parametrize('action,wanted,disconnect',[
    ('removeLock',[False]*4,1),
    ('removeSecondary',[False,False,False,False,True,0],1),
    ('removeExtension',[False,False,True,False,True,16],1),
    ('removeLine',[True,True,True,False,True,16],1),
    ('removeDressing',[True,True,False,True,True,16],0)])
def test_component_removal_cascade_never_removes_primary(action,wanted,disconnect):
    run(f'''
    private _unplugs=0;ACME_fnc_ivAccessoryUnplug={{_unplugs=_unplugs+1;}};
    _row set [15,{field_state(16,True,True,True,True)}];
    private _other=+_row;_other set [14,"other"];_other set [10,"upper"];
    _patient setVariable ["ACME_IV_Marks",[_row,_other]];
    ["begin","{action}","pull"] call _invoke;
    _serverTime=101;["finish","{action}","pull"] call _invoke;
    ["finish","{action}","pull"] call _invoke;
    [(call _getState) isEqualTo {json.dumps(wanted).lower()},"dependency graph"] call _check;
    [_unplugs=={disconnect},"one disconnect"] call _check;
    [((call _getRow) select 4)=="hub" && {{_hasIV}},"primary remains"] call _check;
    [(((_patient getVariable "ACME_IV_Marks") select 1) select 15) isEqualTo {field_state(16,True,True,True,True)},"other site unchanged"] call _check;
    ''')


@pytest.mark.parametrize('second',[14,16])
@pytest.mark.parametrize('missed',[False,True])
def test_real_owner_field_insertion_has_one_access_and_inherits_patency(second,missed):
    run(f'''
    _row set [15,{field_state(dressed=True)}];_patient setVariable ["ACME_IV_Marks",[_row]];
    _patient setVariable ["ACME_ivCompromised_leftarm_1",{str(missed).lower()}];
    private _needle=[_medic,"ACM_IV_{second}g",objNull,"needle1"];
    ["begin","field{second}","f",_needle,"ivhub:7:1",7,190] call _invoke;
    _serverTime=101;
    ["finish","field{second}","f",[],"ivhub:7:1",7,190] call _invoke;
    [((call _getState) param [5,0])==0,"no timer-based completion"] call _check;
    {{[_x,"field{second}","f",[],"ivhub:7:1",7,190] call _invoke;}} forEach ["advance","thread","retract","finish","finish"];
    [((call _getState) param [5,0])=={second},"secondary seated"] call _check;
    [count (_patient getVariable "ACME_IV_Marks")==1,"not another venous access"] call _check;
    [count (call _credits)==0,"no saline from needle"] call _check;
    ["begin","flush","saline",_receipt] call _invoke;
    _serverTime=109;["finish","flush","saline"] call _invoke;
    [count (call _credits)=={0 if missed else 1},"actual base patency"] call _check;
    [((call _getState) select 1)=={str(not missed).lower()},"tested state"] call _check;
    [(_patient getVariable ["ACME_ivCompromised_leftarm_1",false])=={str(missed).lower()},"no repair roll"] call _check;
    ''')


@pytest.mark.parametrize('mode',['out_of_order','duplicate','early','cancel','expired','removed','owner_change','wrong_provider','wrong_uid','no_needle','reused_receipt'])
def test_insertion_protocol_boundaries(mode):
    begin='["begin","field16","f",_needle,"ivhub:7:1",7,190] call _invoke;'
    body=f'''
    _row set [15,{field_state(dressed=True)}];_patient setVariable ["ACME_IV_Marks",[_row]];
    private _needle=[_medic,"ACM_IV_16g",objNull,"needle1"];
    '''
    if mode=='no_needle':body+='_needle=[];'
    if mode=='reused_receipt':body+='_patient setVariable ["ACME_IV_FinishReceipts",[["old",_medic,"oldhub","field16",7,190,true,"field_insert","done","needle1"]]];'
    body+=begin
    if mode=='out_of_order':
        body+='_serverTime=101;["retract","field16","f",[],"ivhub:7:1",7,190] call _invoke;["thread","field16","f",[],"ivhub:7:1",7,190] call _invoke;'
    elif mode=='early':body+='{[_x,"field16","f",[],"ivhub:7:1",7,190] call _invoke;} forEach ["advance","thread","retract"];'
    elif mode=='cancel':body+='["cancel","field16","f",[],"ivhub:7:1",7,190] call _invoke;'
    else:
        body+='_serverTime=101;'
        if mode=='expired':body+='_serverTime=191;'
        if mode=='removed':body+='_hasIV=false;'
        if mode=='owner_change':body+='_testClinicalEpoch=8;'
        if mode=='wrong_provider':
            body+='{[_patient,missionNamespace,_x,"ivhub:7:1","field16","f",7,190] call ACME_fnc_ivFinishCommit;} forEach ["advance","thread","retract"];'
        elif mode=='wrong_uid':
            body+='{[_x,"field16","f",[],"otherhub",7,190] call _invoke;} forEach ["advance","thread","retract"];'
        else:body+='{[_x,"field16","f",[],"ivhub:7:1",7,190] call _invoke;} forEach ["advance","thread","thread","retract"];'
    body+='["finish","field16","f",[],"ivhub:7:1",7,190] call _invoke;'
    body+=f'[((call _getState) param [5,0])=={16 if mode=="duplicate" else 0},"protocol {mode}"] call _check;'
    run(body)


@pytest.mark.parametrize('second',[0,14,16])
@pytest.mark.parametrize('ext',[False,True])
def test_lock_and_field_direct_extension_routes(second,ext):
    run(f'''
    _row set [15,{field_state(second,ext)}];_patient setVariable ["ACME_IV_Marks",[_row]];
    ["begin","flush","flush",_receipt] call _invoke;
    _serverTime=108;["finish","flush","flush"] call _invoke;
    ["begin","dressing","film"] call _invoke;_serverTime=110;["finish","dressing","film"] call _invoke;
    ["begin","line","line"] call _invoke;_serverTime=112;["finish","line","line"] call _invoke;
    [((call _getState) select 3),"route connects"] call _check;
    [count (call _credits)==1,"single full-flush credit"] call _check;
    ''')


@pytest.mark.parametrize('family',list(FAMILIES))
@pytest.mark.parametrize('angle',[-15,0,15])
@pytest.mark.parametrize('aspect',[.5625,.28125])
def test_secondary_socket_exact_for_primary_orientation_and_screen(family,angle,aspect):
    anchor,hub,axis=FAMILIES[family];t=math.atan2(axis[0],-axis[1])+math.radians(angle)
    dx=-math.sin(t)*152/2048*.62*aspect;dy=math.cos(t)*152/2048*.62
    run(START_SETUP+f'''
    _testPixelW={aspect};_testPixelH=1;_testAxis={json.dumps(axis)};
    _row set [6,"{family}"];_row set [13,{angle}];_row set [15,{field_state()}];
    uiNamespace setVariable ["ACME_IV_FrameAnchors",createHashMapFromArray [["{family}",{json.dumps(anchor)}]]];
    uiNamespace setVariable ["ACME_IV_LineAnchors",createHashMapFromArray [["{family}",{json.dumps(hub)}]]];
    private _parent=[_row] call ACME_fnc_ivFinishGeometry;
    private _child=[_row,14] call ACME_fnc_ivFieldSecondaryRow;
    private _placed=[_child] call ACME_fnc_ivFinishGeometry;
    [abs (((_placed select 0)-(_parent select 0))-{dx})<0.00001,"secondary socket x"] call _check;
    [abs (((_placed select 1)-(_parent select 1))-{dy})<0.00001,"secondary socket y"] call _check;
    [(_placed select 4)==(_parent select 4),"one axis"] call _check;
    [(_child select 7)==14 && {{(_row select 7)==16}},"gauge-specific native child"] call _check;
    ''')


@pytest.mark.parametrize('second',[0,16])
@pytest.mark.parametrize('ext',[False,True])
def test_active_port_and_direct_flush_transform(second,ext):
    run(START_SETUP+f'''
    _row set [15,{field_state(second,ext)}];
    private _port=[_row,[_row] call ACME_fnc_ivFieldPort] call ACME_fnc_ivFieldPoint;
    private _virtual=[_row,{str(not ext).lower()}] call ACME_fnc_ivFieldAccessoryRow;
    private _shown=[_virtual,[1033.02/2048,1386.52/2048],[1006.5/2048,1052/2048]] call ACME_fnc_ivFinishPoint;
    [abs ((_port select 0)-(_shown select 0))<0.00001 && {{abs ((_port select 1)-(_shown select 1))<0.00001}},"flush meets active port"] call _check;
    ''')


def test_local_click_reserves_second_catheter_once():
    run(START_SETUP+'ACME_fnc_ivFinishStart={'+start_source()+r'''};
    _row set [15,[false,false,true,false,true,0]];_patient setVariable ["ACME_IV_Marks",[_row]];
    _testSupplyReceipt=[_medic,"ACM_IV_14g",objNull,"second"];
    [0,0,"field14","ivhub:7:1"] call ACME_fnc_ivFinishStart;
    [0,0,"field14","ivhub:7:1"] call ACME_fnc_ivFinishStart;
    [_takes==1 && {count _events==1},"one reservation"] call _check;
    [(((_events select 0) select 2) select 7) isEqualTo _testSupplyReceipt,"actual catheter receipt"] call _check;
    ''')


def test_code_reuses_real_insertion_controls_and_cannot_register_a_second_skin_iv():
    assert 'call ACME_fnc_ivMinigameInsertStart' in read('ivFieldInsertStart')
    assert 'ACME_IV_FieldInserting' in read('ivMinigameClick')
    assert read('ivMinigameStickSuccess').index('call ACME_fnc_ivFieldInsertEnd') < read('ivMinigameStickSuccess').index('call ACME_fnc_ivMinigameRegister')
    assert 'ACME_fnc_ivMinigameRegister' not in read('ivFieldInsertEnd')
    assert 'ACME_fnc_ivInfiltrated' not in read('ivFieldInsertEnd')
    assert 'ACME_IV_FieldInserting' in read('ivMinigameSaveState')
    assert 'field14' in read('ivFinishTick') and 'call ACME_fnc_ivFieldClear' in read('ivFinishAbort')


def test_field_textures_match_archive_layers_and_have_no_gauge_baked_in():
    path=ROOT/'addons/acm_extended/ui/iv/field'
    manifest=json.loads((path/'manifest.json').read_text())
    assert len(manifest['files'])==371
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((path/name).read_bytes()).hexdigest()==digest,name
    assert manifest['secondary_socket']==[1006.5,1189]
    assert 'ctrlSetAngle [_angle,0.5,0.5,false]' in read('ivFieldPose')
    from paa import read_paa
    for k in ('lock','field'):
        rgb,alpha=read_paa(path/f'dressing_{k}_ca.paa',want=256)
        assert alpha.max()>0
        assert alpha[:5].max()==0 and alpha[-5:].max()==0
    _,last=read_paa(path/'direct_post_flush_secure_0041_ca.paa',want=256)
    assert last.max()==0


def test_new_functions_registered_and_debug_unchanged():
    cpp=(ROOT/'addons/acm_extended/config.cpp').read_text()
    for p in (ROOT/'addons/acm_extended/functions').glob('fn_ivField*.sqf'):
        assert 'class '+p.stem[3:]+' {};' in cpp
    import subprocess
    base=subprocess.check_output(['git','show','43b63622b28766869c4ef1d2597eee43674fcb53:addons/acm_extended/functions/fn_debugMenuClinical.sqf'],cwd=ROOT)
    assert (ROOT/'addons/acm_extended/functions/fn_debugMenuClinical.sqf').read_bytes()==base


def ui_source(name):
    """Record controls/mouse only; preserve complete production branching and calls."""
    from test_bounded_selector_lifetime import ui_commands
    s=read(name)
    s=re.sub(r'\(_\w+ displayCtrl \d+\)', '_d',s)
    s=re.sub(r'\b_\w+ ctrlCreate \[[^;\n]+?\]', '_d',s)
    s=s.replace('getMousePosition','_mouse')
    s=re.sub(r'setMousePosition (\[[^;]+\]);',r'_mouse=\1;',s)
    s=s.replace('safeZoneWAbs','_zoneW').replace('safeZoneH','_zoneH')
    s=s.replace('diag_deltaTime','_delta')
    s=re.sub(r'ctrlDelete (_\w+);',r'_deleted pushBack \1;',s)
    s=s.replace('playSound "ACE_Sound_Click";','_clicks=_clicks+1;')
    s=s.replace('serverTime','_serverTime')
    return map_defaults(ui_commands(s))


@pytest.mark.parametrize('abort_at',['none','advance','thread','retract','view_change'])
def test_real_manual_push_thread_retract_commits_only_hardware(abort_at):
    names=['ivFieldInsertStart','ivFieldProgress','ivFieldInsertEnd','ivFieldClear',
           'ivMinigameInsertStart','ivMinigameInsertAdvance','ivMinigameScroll',
           'ivMinigameRetract','ivMinigameStickSuccess']
    body=START_SETUP+''.join('ACME_fnc_'+n+'={'+ui_source(n)+'};' for n in names)
    body+='ACME_fnc_ivFinishStart={'+start_source()+'};'
    body+=r'''
    private _writes=[];private _deleted=[];private _frames=[];private _labels=[];
    private _write={_writes pushBack _this;};private _mouse=[0.5,0.5];
    private _zoneW=1;private _zoneH=1;private _delta=0.016;
    private _pixelW=0.5625;private _pixelH=1;
    private _nativeRegistrations=0;ACME_fnc_ivMinigameRegister={_nativeRegistrations=_nativeRegistrations+1;};
    ACME_fnc_ivCathGeometry={[0.62*0.5625,0.62,[.49166,.44434],[0,-1]]};
    ACME_fnc_ivCathPose={_poses pushBack _this;[0.4,0.4,0.4,0.6]};
    private _poses=[];
    ACME_fnc_ivCathTex={_this select 2};
    ACME_fnc_ivCathSetFrame={_frames pushBack (_this select 1);};
    ACME_fnc_ivFieldPose={};ACME_fnc_ivMinigameHookCtrl={};
    ACME_fnc_ownerDispatch={
        _events pushBack +_this;params ["_target","_op","_args"];
        switch (_op) do {
            case "ivFinish": {([_target]+_args) call ACME_fnc_ivFinishCommit;};
            case "ivFinishReply": {_args call ACME_fnc_ivFinishReply;};
        };
    };
    uiNamespace setVariable ["ACME_IV_CathCtrl",_d];
    _d setVariable ["ACME_IV_FinishCtrls",[]];
    _row set [15,[false,false,true,false,true,0]];_patient setVariable ["ACME_IV_Marks",[_row]];
    _testSupplyReceipt=[_medic,"ACM_IV_16g",objNull,"needle1"];
    [0,0,"field16","ivhub:7:1"] call ACME_fnc_ivFinishStart;
    [(uiNamespace getVariable ["ACME_IV_InsStage",""])=="advance","native advance started after owner ACK"] call _check;
    [count _refunds==1 && {!((_refunds select 0) select 1)},"one catheter consumed"] call _check;
    [false] call ACME_fnc_ivMinigameInsertAdvance;
    [(uiNamespace getVariable ["ACME_IV_InsFrame",0])==1,"release pauses insertion"] call _check;
    [!([] call ACME_fnc_ivMinigameRetract),"early safety does not finish"] call _check;
    '''
    if abort_at=='advance':body+='[] call ACME_fnc_ivFinishAbort;'
    elif abort_at=='view_change':body+='_viewValid=false;[] call ACME_fnc_ivFinishAbort;'
    else:
        body+=r'''
        _serverTime=101;_mouse=[0.5,0.44];
        [true] call ACME_fnc_ivMinigameInsertAdvance;
        [(uiNamespace getVariable ["ACME_IV_InsStage",""])=="thread","native threading phase"] call _check;
        [!([] call ACME_fnc_ivMinigameRetract),"cannot skip thread"] call _check;
        { [1] call ACME_fnc_ivMinigameScroll; } forEach [1,2,3,4,5];
        [(uiNamespace getVariable ["ACME_IV_InsFrame",0])==11,"all threading steps"] call _check;
        '''
        if abort_at=='thread':body+='[] call ACME_fnc_ivFinishAbort;'
        else:
            body+='[[] call ACME_fnc_ivMinigameRetract,"normal safety button"] call _check;'
            if abort_at=='retract':body+='[] call ACME_fnc_ivFinishAbort;'
            body+=r'''
            private _id=count _handlers-1;
            private _h=_handlers select _id;
            // Run even a late scheduled callback once; its view/stage guards must reject.
            [_h select 1,_id] call (_h select 0);
            if (_h select 2) then {[_h select 1,_id] call (_h select 0);};
            '''
    expected=16 if abort_at=='none' else 0
    body+=f'''
    [_nativeRegistrations==0,"no second skin IV or wound created"] call _check;
    [((call _getState) param [5,0])=={expected},"seating or cancellation"] call _check;
    [(uiNamespace getVariable ["ACME_IV_InsStage",""])=="","input released"] call _check;
    [count (_patient getVariable "ACME_IV_Marks")==1,"same primary mark"] call _check;
    '''
    if abort_at=='none':body+='[_frames isEqualTo [6,7,8,9,10,11,12,13,14],"native frame sequence, no fake placement"] call _check;'
    run(body)


@pytest.mark.parametrize('ending',['replication_arrives','replacement','expires'])
def test_owner_ack_before_mark_replication_does_not_cancel_new_field_insert(ending):
    run(START_SETUP+'ACME_fnc_ivFinishTick={'+source('ivFinishTick')+r'''};
    _row set [15,[false,false,false,false,true,0]];
    _patient setVariable ["ACME_IV_Marks",[+_row]];
    private _accepted=+_row;
    _accepted set [16,["field",_medic,"field16",100,0.5,"field_insert",190,1]];
    private _context=[_d,_patient,_medic,"leftarm","front"];
    _medic setVariable ["ACME_IV_FinishPending",[_patient,"field","ivhub:7:1","field16",7,190,[],_context,false]];
    _d setVariable ["ACME_IV_FinishActive",[_accepted,10,false]];
    _d setVariable ["ACME_IV_FinishCtrls",[]];
    _d setVariable ["ACME_IV_FieldInserting",true];
    _d setVariable ["ACME_IV_FieldJobSeen",false];
    _d setVariable ["ACME_IV_FieldShell",objNull];
    [] call ACME_fnc_ivFinishTick;
    [_d getVariable ["ACME_IV_FieldInserting",false],"ACK is authoritative before replicated job arrives"] call _check;
    '''+('''_serverTime=191;[] call ACME_fnc_ivFinishTick;
    [!(_d getVariable ["ACME_IV_FieldInserting",false]),"unreplicated job bounded by deadline"] call _check;
    ''' if ending=='expires' else r'''
    _patient setVariable ["ACME_IV_Marks",[_accepted]];
    [] call ACME_fnc_ivFinishTick;
    [_d getVariable ["ACME_IV_FieldJobSeen",false],"replication acknowledged"] call _check;
    [_d getVariable ["ACME_IV_FieldInserting",false],"live job retained"] call _check;
    '''+(r'''_patient setVariable ["ACME_IV_Marks",[_row]];[] call ACME_fnc_ivFinishTick;
    [!(_d getVariable ["ACME_IV_FieldInserting",false]),"observed job removal retires presentation"] call _check;
    ''' if ending=='replacement' else '')))


@pytest.mark.parametrize('layer',['accessory','film','lock','secondary'])
@pytest.mark.parametrize('route',['lock','direct','extension'])
def test_real_layer_renderer_selects_matching_hardware_and_dressing(layer,route):
    second=0 if route=='lock' else 16
    ext=route=='extension'
    ctrls=['_d' if layer==x else 'objNull' for x in ['accessory','film','lock','secondary']]
    run(START_SETUP+'ACME_fnc_ivFieldRender={'+ui_source('ivFieldRender')+r'''};
    private _writes=[];private _write={_writes pushBack _this;};
    private _poses=[];
    ACME_fnc_ivFinishPose={_poses pushBack ["accessory",_this select 1];};
    ACME_fnc_ivFieldPose={_poses pushBack ["field",_this select 1];};
    ACME_fnc_ivCathPose={_poses pushBack ["secondary",_this];};
    ACME_fnc_ivCathTex={format ["native_%1_%2",_this select 0,_this select 2]};
    '''+f'''
    _row set [15,{field_state(second,ext,True,True,route!='lock')}];
    [_row,[],0,[{','.join(ctrls)}]] call ACME_fnc_ivFieldRender;
    private _texts=_writes select {{(_x select 1)=="ctrlSetText"}};
    private _shown=if (_texts isEqualTo []) then {{""}} else {{(_texts select 0) select 2}};
    '''+{
        'film':f'[(_shown find "dressing_{"lock" if second==0 else "field"}_ca.paa")>=0,"assembly-specific dressing"] call _check;',
        'lock':'[(_shown find "field\\lock_ca.paa")>=0,"supplied lock layer"] call _check;',
        'secondary':f'[_shown=="{"native_16_14" if second else ""}","native gauge-specific secondary"] call _check;',
        'accessory':('[(_shown find "finish\\line_ca.paa")>=0,"extension line"] call _check;' if ext else
                     '[(_shown find "cursor_line_ca.paa")>=0,"direct line"] call _check;' if second else
                     '[_shown=="","lock only has no extra extension"] call _check;')
    }[layer])
