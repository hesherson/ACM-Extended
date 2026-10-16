"""B235 production SQF behavior. UI, transport and engine inventory remain mocked.

Actual asset metadata and control order are checked offline, not native Arma rendering.
B234's undressed-field fixtures are updated separately to the requested covered-lock contract.
"""
import hashlib
import json
import math
import re
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b232_iv_finish import SETUP, rules, START_SETUP, source, start_source
from test_b234_field_iv import ui_source
from test_bounded_selector_lifetime import ui_commands
from test_historical_vial_execution import map_defaults
from source_scan import lex, matching


def run(body):
    execute(SETUP+rules()+body)


def js(value):
    return json.dumps(value).lower()


@pytest.mark.parametrize('second',[14,16])
@pytest.mark.parametrize('patent',[False,True])
def test_full_cover_then_insert_workflow_retains_primary_film_without_fluid_credit(second,patent):
    # Execute provider settlement as well as the owner transaction: a rejected
    # reservation is refunded, and the next Take issues a NEW receipt ID.
    refund=source('treatmentSupplyRefund').replace('_vehicle addItemCargoGlobal [_item, 1];','_returns=_returns+1;')
    run('ACME_fnc_treatmentSupplyRefund={'+refund+'};'+f'''
    private _returns=0;ace_common_fnc_addToInventory={{_returns=_returns+1;}};
    _patient setVariable ["ACME_ivCompromised_leftarm_1",{js(not patent)}];
    ["begin","lock","lock"] call _invoke;_serverTime=101;["finish","lock","lock"] call _invoke;
    private _needle=[_medic,"ACM_IV_{second}g",objNull,"needle1"];
    _medic setVariable ["ACME_IV_FinishPending",[_patient,"early","ivhub:7:1","field{second}",7,190,_needle,[_d,[],0,"leftarm","front"],false]];
    ["begin","field{second}","early",_needle,"ivhub:7:1",7,190] call _invoke;
    [((call _getRow) select 16) isEqualTo [],"uncovered lock rejected before insertion"] call _check;
    [!((call _lastReply) select 4),"explicit negative acknowledgement"] call _check;
    _viewValid=false;(call _lastReply) call ACME_fnc_ivFinishReply;_viewValid=true;
    [_returns==1 && {{!("needle1" in (missionNamespace getVariable "ACME_supplyReceipts"))}},"rejected needle returned exactly once"] call _check;
    [(_medic getVariable "ACME_IV_SupplyBindings") isEqualTo [],"rejected scope retired"] call _check;
    // Inventory itself is a fixture boundary, as in _invoke. Model a new Take,
    // never transfer the rejected receipt to a different operation token.
    _needle=[_medic,"ACM_IV_{second}g",objNull,"needle2"];
    ["begin","dressing","base"] call _invoke;_serverTime=103;["finish","dressing","base"] call _invoke;
    [((call _getState) select 2) && {{!((call _getState) select 1)}},"primary film does not require or fabricate aspiration"] call _check;
    ["begin","field{second}","field",_needle,"ivhub:7:1",7,190] call _invoke;
    _serverTime=104;
    {{[_x,"field{second}","field",[],"ivhub:7:1",7,190] call _invoke;}} forEach ["advance","thread","retract","finish","finish"];
    [(call _getState) isEqualTo [false,false,false,false,true,{second},true],"short base film retained under secondary"] call _check;
    [count (call _credits)==0 && {{count (_patient getVariable "ACME_IV_Marks")==1}},"no fluid or extra access from hardware"] call _check;
    ["begin","extension","ext"] call _invoke;_serverTime=106;["finish","extension","ext"] call _invoke;
    ["begin","flush","flush",_receipt] call _invoke;_serverTime=114;["finish","flush","flush"] call _invoke;
    ["begin","dressing","outer"] call _invoke;_serverTime=116;["finish","dressing","outer"] call _invoke;
    ["begin","line","line"] call _invoke;_serverTime=118;["finish","line","line"] call _invoke;
    [((call _getState) select 3)=={js(patent)},"line still requires proven primary patency and final dressing"] call _check;
    [((call _getState) param [6,false]),"short film remains after remaining apparatus"] call _check;
    [count (call _credits)=={1 if patent else 0},"only actual successful flush credits saline"] call _check;
    ''')


@pytest.mark.parametrize('mutation',['uncovered','extension','secondary','primary_gauge'])
def test_owner_rechecks_covered_empty_lock_at_manual_completion(mutation):
    change={'uncovered':'_state set [2,false];', 'extension':'_state set [0,true];',
            'secondary':'_state set [5,14];','primary_gauge':'_current set [7,18];'}[mutation]
    run('''
    _row set [15,[false,false,true,false,true,0]];_patient setVariable ["ACME_IV_Marks",[_row]];
    private _needle=[_medic,"ACM_IV_16g",objNull,"needle1"];
    ["begin","field16","f",_needle,"ivhub:7:1",7,190] call _invoke;
    _serverTime=101;
    {[_x,"field16","f",[],"ivhub:7:1",7,190] call _invoke;} forEach ["advance","thread","retract"];
    private _current=+(call _getRow);private _state=+(_current select 15);
    '''+change+'''
    _current set [15,_state];_patient setVariable ["ACME_IV_Marks",[_current]];
    ["finish","field16","f",[],"ivhub:7:1",7,190] call _invoke;
    [((call _getState) param [5,0])!=16,"mutated assembly cannot accept stale completion"] call _check;
    [((call _getRow) select 16) isEqualTo [],"invalid job retires"] call _check;
    [count (call _credits)==0,"no credit"] call _check;
    ''')


@pytest.mark.parametrize('action,wanted',[
    ('removeSecondary',[False,False,False,False,True,0,True]),
    ('removeExtension',[False,False,True,False,True,16,True]),
    ('removeLock',[False]*4),
    ('removeDressing',[True,True,False,True,True,16,True]),
    ('removeLine',[True,True,True,False,True,16,True]),
])
def test_primary_film_survives_only_correct_dependency_removals(action,wanted):
    run(f'''
    private _next=[[true,true,true,true,true,16,true],"{action}"] call ACME_fnc_ivFieldTransition;
    [_next isEqualTo {js(wanted)},"explicit hierarchy"] call _check;
    ''')


def test_peel_outer_then_primary_film_and_reinsert_after_secondary_removal():
    run('''
    private _state=[[true,true,true,true,true,16,true],"removeDressing"] call ACME_fnc_ivFieldTransition;
    [(_state select 6) && {!(_state select 2)},"first peel preserves base"] call _check;
    _state=[_state,"removeDressing"] call ACME_fnc_ivFieldTransition;
    [!(_state select 6),"second peel removes base"] call _check;
    _state=[[true,true,true,true,true,16,true],"removeSecondary"] call ACME_fnc_ivFieldTransition;
    [([_state,"field14",true,16] call ACME_fnc_ivFinishPlan) select 0,"retained short film permits replacement"] call _check;
    [!(([[false,false,false,false,true,0],"line",true,16] call ACME_fnc_ivFinishPlan) select 0),"a lock alone is not a connected line"] call _check;
    ''')


@pytest.mark.parametrize('angle',[-195,-180,-165,-15,0,15,165,180,195])
@pytest.mark.parametrize('aspect',[.5625,.28125,1])
def test_magnet_executes_smooth_monotone_distance_curve_and_exact_contact(angle,aspect):
    # A distal logical port, not the rotation pivot: attraction must not rotate around the wrong socket.
    short=(angle+180)%360-180
    body='ACME_fnc_ivMagnetGeometry={'+source('ivMagnetGeometry')+'};'
    body+=f'private _aspect={aspect};private _angle={angle};'
    body+='''
    private _rect=[0.2,0.1,0.62*_aspect,0.62];private _pivot=[0.49,0.504];
    private _du=0.015;private _dv=0.17;
    private _target=[0.2+0.62*_aspect*(_pivot select 0)+0.62*_aspect*(_du*cos _angle-_dv*sin _angle),
        0.1+0.62*(_pivot select 1)+0.62*(_du*sin _angle+_dv*cos _angle)];
    private _previous=-1;
    {
        private _cursor=[(_target select 0)+_x*_aspect,_target select 1];
        private _g=[_cursor,_target,_rect,_angle,_pivot,_aspect,1] call ACME_fnc_ivMagnetGeometry;
        _g params ["_r","_turn","_blend"];
        [_blend>=_previous && {_blend>=0} && {_blend<=1},"smooth monotone attraction"] call _check;
        if (_x>0.004 && {_x<0.052}) then {[_blend>0 && {_blend<1},"no broad-radius snap"] call _check;};
        private _cx=(_r select 0)+(_r select 2)*(_pivot select 0)+(_r select 2)*(_du*cos _turn-_dv*sin _turn);
        private _cy=(_r select 1)+(_r select 3)*(_pivot select 1)+(_r select 3)*(_du*sin _turn+_dv*cos _turn);
        [abs (_cx-((_cursor select 0)+((_target select 0)-(_cursor select 0))*_blend))<0.00001,"contact follows attraction x"] call _check;
        [abs (_cy-(_target select 1))<0.00001,"contact follows attraction y"] call _check;
        if (_x<=0.004) then {
            [_blend==1,"very close locks"] call _check;
            [abs ((_r select 0)-(_rect select 0))<0.00001 && {abs ((_r select 1)-(_rect select 1))<0.00001},"installed final rectangle"] call _check;
        };
        if (_x>=0.052) then {[abs _blend<0.000001 && {abs _turn<0.00001},"no attraction outside field"] call _check;};
        _previous=_blend;
    } forEach [0.06,0.052,0.048,0.035,0.02,0.008,0.003,0];
    '''
    run(body)


@pytest.mark.parametrize('tool',['lock','extension','flush','dressing','line','field'])
@pytest.mark.parametrize('aspect',[.5625,.28125])
def test_click_radius_is_distinct_from_attraction_radius(tool,aspect):
    run(START_SETUP+f'''
    _testPixelW={aspect};_testPixelH=1;
    _row set [15,[true,true,true,false,true,0]];_patient setVariable ["ACME_IV_Marks",[_row]];
    private _logical=switch ("{tool}") do {{
        case "field":{{[1006.5,1088]}};case "extension":{{[1006.5,1088]}};
        case "lock";case "dressing":{{[1006.5,1037]}};default{{[_row] call ACME_fnc_ivFieldPort}};
    }};
    private _point=[_row,_logical] call ACME_fnc_ivFieldPoint;
    private _far=[(_point select 0)+0.025*{aspect},_point select 1];
    private _comfortable=[(_point select 0)+0.012*{aspect},_point select 1];
    [([_far select 0,_far select 1,"{tool}"] call ACME_fnc_ivFinishTarget) isNotEqualTo [],"wide magnetic search"] call _check;
    [([_far select 0,_far select 1,"{tool}",false,true] call ACME_fnc_ivFinishTarget) isEqualTo [],"click still rejects well outside component"] call _check;
    [([_comfortable select 0,_comfortable select 1,"{tool}",false,true] call ACME_fnc_ivFinishTarget) isNotEqualTo [],"comfortable click capture"] call _check;
    [([(_point select 0)+0.003*{aspect},_point select 1,"{tool}",false,true] call ACME_fnc_ivFinishTarget) isNotEqualTo [],"near seating"] call _check;
    ''')


@pytest.mark.parametrize('gauge',[14,16])
def test_field_click_guard_accepts_large_bore_near_lock_without_skin_fallthrough(gauge):
    s=read('ivMinigameClick');a=s.index('private _fieldTarget=');b=s.index('// for a held needle',a)
    block=s[a:b]
    prefix=f'''
    private _held="needle";private _starts=[];private _skin=0;
    ACME_fnc_ivFinishStart={{_starts pushBack _this;true}};
    uiNamespace setVariable ["ACME_IV_Gauge",{gauge}];
    _row set [15,[false,false,true,false,true,0,true]];_patient setVariable ["ACME_IV_Marks",[_row]];
    private _p=[_row,[1006.5,1088]] call ACME_fnc_ivFieldPoint;
    private _ux=(_p select 0)+.025*.5625;private _uy=_p select 1;
    private _click={{'''
    suffix=f'''_skin=_skin+1;false}};
    [call _click,"lock vicinity handled"] call _check;
    [count _starts==0 && {{_skin==0}},"distant preview is neither insertion nor skin puncture"] call _check;
    _ux=(_p select 0)+.012*.5625;[call _click,"comfortable lock click handled"] call _check;
    [count _starts==1 && {{_skin==0}},"near lock begins field catheter"] call _check;
    [((_starts select 0) select 2)=="field{gauge}","selected large bore gauge retained"] call _check;
    uiNamespace setVariable ["ACME_IV_Gauge",20];call _click;
    [count _starts==1 && {{_skin==0}},"small gauge never punctures skin under lock"] call _check;
    '''
    run(START_SETUP+prefix+map_defaults(adapt(block))+suffix)

def hub_block():
    s=read('ivMinigameRenderMarks');ts=lex(s);pairs=matching(ts)
    a=s.index('if (_mkind == "hub") then {');i=next(i for i,t in enumerate(ts) if t.offset>=a and t.value=='{')
    return s[ts[i].offset+1:ts[pairs[i]].offset]


def test_field_click_guard_cannot_fall_through_to_skin_when_not_close():
    """Retain the audited B235 case identity against B242's wider click contract."""
    for gauge in (14, 16):
        test_field_click_guard_accepts_large_bore_near_lock_without_skin_fallthrough(gauge)


def test_actual_mark_creation_order_puts_lock_and_extension_under_hub():
    s=hub_block().replace('_dlg','_d')
    s=re.sub(r'_d ctrlCreate (\[[^;\n]+?\])',r'(\1 call _create)',s)
    s=map_defaults(ui_commands(s))
    run('''
    private _created=[];private _writes=[];private _ctrls=[];private _hubCtrls=[];private _finishCtrls=[];
    private _create={_created pushBack _this;count _created};private _write={_writes pushBack _this;};
    private _x=+_row;private _forEachIndex=0;private _mgauge=16;private _mtex="";private _mframe="";
    private _anchors=createHashMap;private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    private _bx=0;private _by=0;private _bw=1;private _bh=1;private _mu=.5;private _mv=.5;
    ACME_fnc_ivCathTex={"native_hub"};ACME_fnc_ivCathPose={};
    '''+s+'''
    [_ctrls isEqualTo [1,2,3,4,5,6],"flat cleanup retains every layer"] call _check;
    [_hubCtrls isEqualTo [[0,3]],"native hub above lock and extension"] call _check;
    [_finishCtrls isEqualTo [["ivhub:7:1",2,6,1,5,4]],"base film below secondary, final film above"] call _check;
    ''')


@pytest.mark.parametrize('during',[False,True])
def test_live_renderer_keeps_short_primary_film_beneath_secondary(during):
    state=[False,False,during,False,True,0 if during else 16,not during]
    job='["field",_medic,"field16",100,0.5,"field_insert",190,6]' if during else '[]'
    run(START_SETUP+'ACME_fnc_ivFieldRender={'+ui_source('ivFieldRender')+'};'+f'''
    private _writes=[];private _write={{_writes pushBack _this;}};
    ACME_fnc_ivFieldPose={{}};ACME_fnc_ivFinishPose={{}};ACME_fnc_ivCathPose={{}};ACME_fnc_ivCathTex={{"needle"}};
    _row set [15,{js(state)}];
    [_row,{job},0,[objNull,objNull,objNull,objNull,_d]] call ACME_fnc_ivFieldRender;
    private _texts=_writes select {{(_x select 1)=="ctrlSetText"}};
    [count _texts==1 && {{(((_texts select 0) select 2) find "dressing_lock_ca.paa")>=0}},"short film independent of final dressing"] call _check;
    ''')


@pytest.mark.parametrize('peel_final',[False,True])
def test_pull_targets_only_selected_dressing_layer(peel_final):
    run('ACME_fnc_ivFieldPullLayers={'+ui_source('ivFieldPullLayers')+'};'+f'''
    _row set [15,[true,true,{js(peel_final)},true,true,16,true]];
    _d setVariable ["ACME_IV_FinishCtrls",[["ivhub:7:1",objNull,_patient,objNull,objNull,_medic]]];
    private _r=[_d,_row,"removeDressing",objNull] call ACME_fnc_ivFieldPullLayers;
    [(_r select 0) isEqualTo [{'_patient' if peel_final else '_medic'}],"one exact film layer"] call _check;
    ''')


HUBS=json.loads((ROOT/'tools/b235-hub-sockets.json').read_text())['families']
@pytest.mark.parametrize('family',HUBS,ids=lambda d:d['suffix'] or 'base')
@pytest.mark.parametrize('angle',[-15,0,15])
def test_production_socket_maps_drive_actual_seated_axis_and_all_downstream_points(family,angle):
    from test_b233_iv_interactions import FAMILIES
    anchor=FAMILIES[family['suffix']][0];hub=family['socket_uv'];axis=family['axis'];t=math.radians(angle)
    x=.5+.62*.5625*((hub[0]-anchor[0])*math.cos(t)-(hub[1]-anchor[1])*math.sin(t))
    y=.5+.62*((hub[0]-anchor[0])*math.sin(t)+(hub[1]-anchor[1])*math.cos(t))
    theta=family['angle_deg']+angle
    init=read('ivMinigameInit');start=init.index('uiNamespace setVariable ["ACME_IV_HubSockets"');end=init.index('uiNamespace setVariable ["ACME_IV_LineAnchors"',start)
    geometry=map_defaults(source('ivFinishGeometry').replace('pixelW','_testPixelW').replace('pixelH','_testPixelH'))
    run(START_SETUP+map_defaults(adapt(init[start:end]))+'ACME_fnc_ivFinishGeometry={'+geometry+'};'+f'''
    _row set [6,"{family['suffix']}"];_row set [13,{angle}];
    uiNamespace setVariable ["ACME_IV_FrameAnchors",createHashMapFromArray [["{family['suffix']}",{js(anchor)}]]];
    private _g=[_row] call ACME_fnc_ivFinishGeometry;
    [abs ((_g select 0)-{x})<0.00001 && {{abs ((_g select 1)-{y})<0.00001}},"measured socket, not floating line anchor"] call _check;
    [abs ((_g select 4)-{theta})<0.0001,"seated art axis"] call _check;
    _row set [15,[true,true,false,false,true,16,true]];
    private _child=[_row,14] call ACME_fnc_ivFieldSecondaryRow;
    private _childHub=[_child] call ACME_fnc_ivFinishGeometry;
    private _expected=[_row,[1006.5,1189]] call ACME_fnc_ivFieldPoint;
    [abs ((_childHub select 0)-(_expected select 0))<0.00001 && {{abs ((_childHub select 1)-(_expected select 1))<0.00001}},"downstream child seated"] call _check;
    private _port=[_row,[_row] call ACME_fnc_ivFieldPort] call ACME_fnc_ivFieldPoint;
    private _acc=[_row,false] call ACME_fnc_ivFieldAccessoryRow;
    private _shown=[_acc,[1033.02/2048,1386.52/2048],[1006.5/2048,1052/2048]] call ACME_fnc_ivFinishPoint;
    [abs ((_port select 0)-(_shown select 0))<0.00001 && {{abs ((_port select 1)-(_shown select 1))<0.00001}},"extension/syringe share measured axis"] call _check;
    ''')


def test_hub_measurements_bound_to_unchanged_native_art_and_no_duplicate_lock_shell():
    for d in HUBS:
        assert hashlib.sha256((ROOT/d['source']).read_bytes()).hexdigest()==d['sha256']
    assert 'class ivMagnetGeometry {};' in (ROOT/'addons/acm_extended/config.cpp').read_text()
    assert '"lock"]' in read('ivHeldRaise')
    assert 'ctrlCreate ["ACME_IV_HubMark"' not in read('ivFieldInsertStart')
    assert 'call ACME_fnc_ivMagnetGeometry' in read('ivFinishPreview')
    assert 'call ACME_fnc_ivMagnetGeometry' in read('ivFieldPreview')


def test_upright_flush_tray_uses_dedicated_existing_image():
    s=read('ivFinishTray');assert 'if (_tool=="flush") then {"\\acm_extended\\ui\\items\\salineFlush_ca.paa"}' in s
    assert (ROOT/'addons/acm_extended/ui/items/salineFlush_ca.paa').is_file()


@pytest.mark.parametrize('size',[1,3,5,10])
def test_real_in_place_flush_texture_switch_restores_each_normal_barrel(size):
    # Execute the full control-independent selection and texture path. Native pixel bounds are stand-ins.
    s=read('skApplySize')
    s=re.sub(r'^#include.*$', '',s,flags=re.M)
    s=re.sub(r'\(_d displayCtrl \([^()]*\)\)', '_d', s)
    s=re.sub(r'\(_d displayCtrl \w+\)', '_d', s)
    s=re.sub(r'_d displayCtrl \([^()]*\)', '_d', s)
    s=re.sub(r'_d displayCtrl \w+','_d',s)
    s=s.replace('ctrlPosition _hit','[.2,.1,.2,.5]').replace('ctrlPosition _vis','[.2,.1,.2,.5]').replace('ctrlPosition _barrel','[.2,.1,.2,.5]')
    # Only engine/UI coordinate macros are mocked, not the selection, existing compound or texture branches.
    s=re.sub(r'\bSYRINGEDRAW_\w+', '0.2', s)
    s=map_defaults(ui_commands(s))
    execute('''
    private _display=missionNamespace;private _writes=[];private _write={_writes pushBack _this;};
    ACME_fnc_treatmentSupplyCount={1};ACME_fnc_skWasteEnd={uiNamespace setVariable ["ACME_SK_WasteStage",""];};
    ACME_fnc_skCompoundBegin={};ACME_fnc_skPendingTagRender={};ACME_fnc_skListRefresh={};
    ACME_fnc_skCompoundCommit={true};ACME_fnc_skPendingTagReset={};ACME_fnc_skRefreshDrawn={};
    '''+'ACME_fnc_skApplySize={'+s+'};'+f'''
    [10,"ACM_SalineFlush_10"] call ACME_fnc_skApplySize;
    private _texts=_writes select {{(_x select 1)=="ctrlSetText"}};
    [count _texts==1 && {{(((_texts select 0) select 2) find "syringe_flush_10_barrel_ca.paa")>=0}},"dedicated flush selected without reopening"] call _check;
    uiNamespace setVariable ["ACME_SK_WasteStage","ready"];
    _writes=[];[{size},""] call ACME_fnc_skApplySize;
    _texts=_writes select {{(_x select 1)=="ctrlSetText"}};
    [count _texts==1 && {{(((_texts select 0) select 2) find "syringe_{size}_barrel_ca.paa")>=0}} && {{(((_texts select 0) select 2) find "flush")<0}},"normal barrel restored"] call _check;
    ''')
