"""Whole transfusion controller/layout checks against explicit native UI boundaries.

The complete production controller, layout and change-only writer execute. Native
control creation, events, list transport and drawing are fixture primitives;
these checks do not certify Arma pointer dispatch, rendering or sound. Each IDC
has separate state, and right-inventory selection has a unique fixture name so
the controller's legitimate private active-bag `_selection` cannot shadow it.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from source_scan import lex, matching
from test_menu_death_lifecycle import read, adapt, execute
from test_b156_procedure_supplies import primitives
from test_b274_transfusion_preparation import stage_setup, gui


@pytest.fixture(autouse=True)
def ui_boundary_warnings_are_failures(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert '[WRN]' not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, 'run', checked)


def selection_boundary(source):
    """Rename only fixture right-list selection before adding production UI."""
    return re.sub(r"\b_selection\b", "_fixtureRightSelection", source)


def ui_source(name):
 s=read(name).replace(']) != _display', ']) isNotEqualTo _display').replace('findDisplay 86000','missionNamespace').replace('findDisplay 86200','objNull').replace('findDisplay 84000','objNull')
 s=re.sub(r'ctrlParent (\([^\n;]+?\)|_\w+)', 'missionNamespace',s)
 # Native constructors/lookup return distinct numeric/child control handles.
 s=re.sub(r'_display displayCtrl (\([^;\n]+?\)|_\w+|\d+)',r'\1',s)
 s=re.sub(r'_display ctrlCreate (\[[^;]+?\])',r'(\1 call _createControl)',s)
 s=re.sub(r'_group controlsGroupCtrl (\([^;\n]+?\)|_\w+|\d+)',r'[_group,\1]',s)
 # Strip actual engine registration as a boundary, retaining event order.
 ts=lex(s); ps=matching(ts); edits=[]
 for i,t in enumerate(ts):
  if t.value not in ('ctrlAddEventHandler','displayAddEventHandler'):continue
  end=ps[i+1]; event=ts[i+2].value
  edits.append((ts[i-1].offset,ts[end].offset+1,f'[{ts[i-1].value},"{event}"] call _registerEvent'))
 for a,b,v in reversed(edits):s=s[:a]+v+s[b:]
 # UI metadata lives separately from native unit namespaces.
 control_names={'_x','_c','_ctrl','_button','_frame','_group','_list','_rule','_tab','_warmer','_warmerYes','_warmerNo','_bloodType','_accessKind','_accessIcon','_warming','_piggyback','_spikeDropdown','_inventoryTab','_parent','_ctrlY','_ctrlSpike','_ctrlSetsBtn','_ctrlSetsList','_ctrlRightList','_ctrlLeftList','_ctrlActiveInfList','_ctrlPreparedList','_ctrlGivePrep','_ctrlRateText','_ctrlTransfusionList'}
 ts=lex(s);ps=matching(ts);edits=[]
 for i,t in enumerate(ts):
  if t.value not in ('getVariable','setVariable') or i<1 or ts[i-1].value not in control_names:continue
  if ts[i+1].value!='[':continue
  end=ps[i+1];a=s[ts[i+1].offset:ts[end].offset+1]
  edits.append((ts[i-1].offset,ts[end].offset+1,f'([{ts[i-1].value},{a}] call '+('_controlRead' if t.value=='getVariable' else '_controlSet')+')'))
 for a,b,v in reversed(edits):s=s[:a]+v+s[b:]
 # UI unary read primitives; each consumes one variable (all actual source operands here do).
 for cmd,fn in {'ctrlPosition':'_uiNativePosition','ctrlShown':'_uiNativeShown','ctrlEnabled':'_uiNativeEnabled','ctrlText':'_uiNativeText','ctrlTextColor':'_uiNativeColor','ctrlIDC':'_uiNativeIDC','ctrlTextWidth':'_uiNativeWidth','lbCurSel':'_uiNativeSel','lbSize':'_uiNativeSize','ctrlTextHeight':'_uiNativeHeight'}.items():
  s=re.sub(r'\b'+cmd+r' (_\w+)',lambda m:f'([{m[1]}] call {fn})',s)
 # List reads consume one native index atom.
 for cmd,prop in {'lbData':'data','lbValue':'value','lbText':'text','lbColor':'color','lbTooltip':'tooltip'}.items():
  s=re.sub(r'(_\w+) '+cmd+r' (_\w+|\d+)',lambda m:f'([{m[1]},"{prop}",{m[2]}] call _listGet)',s)
 s=re.sub(r'lbClear (_\w+)',r'[\1] call _listClear',s)
 # Commands used as expressions must preserve their result.
 s=re.sub(r'(_\w+) lbAdd ([^;\n]+)',r'[\1,\2] call _listAdd',s)
 # The remaining native binary mutations run to their semicolon boundary.
 cmds={'ctrlEnable':'enable','ctrlShow':'show','ctrlSetText':'text','ctrlSetFont':'font','ctrlSetFontHeight':'fontH','ctrlSetTextColor':'color','ctrlSetBackgroundColor':'background','ctrlSetTooltip':'tooltip','ctrlSetFade':'fade','ctrlCommit':'commit','ctrlSetPosition':'position'}
 for cmd,prop in cmds.items():
  s=re.sub(r'(\([^;\n]+?\)|_\w+) '+cmd+r' ([^;\n]+);',lambda m:f'[{m[1]},"{prop}",{m[2]}] call _setUI;',s)
 for cmd,prop in {'lbSetData':'data','lbSetValue':'value','lbSetText':'text','lbSetColor':'color','lbSetPicture':'picture','lbSetPictureRight':'pictureRight','lbSetTooltip':'tooltip'}.items():
  s=re.sub(r'(_\w+) '+cmd+r' ([^;\n]+);',lambda m:f'[{m[1]},"{prop}",{m[2]}] call _listSet;',s)
 s=re.sub(r'(_\w+) lbSetCurSel ([^;\n]+);',r'[\1,\2] call _listSelect;',s)
 s=re.sub(r'(_\w+) lbDelete ([^;\n]+);',r'[\1,\2] call _listDelete;',s)
 s=s.replace('safeZoneX','0').replace('safeZoneY','0').replace('safeZoneW','1.7777778').replace('safeZoneH','1').replace('pixelW','(1/1920)').replace('pixelH','(1/1080)')
 # Config picture lookup is deliberately an engine boundary.
 s=re.sub(r'getText \([^;\n]*? >> "picture"\)','"picture.paa"',s)
 s=s.replace('netId _targetPatient','"casualty"')
 return primitives(adapt(s))


UI_BOUNDARY = r'''
 // Native getOrDefault must return its fallback without first manufacturing
 // a nil local (the older supply fixture does that and emits VM warnings).
 private _mapDefault={params["_map","_args"];_args params["_key","_default"];if(_key in _map)then{_map get _key}else{_default}};
 private _controlProps=createHashMap;private _controlValues=createHashMap;private _events=[];private _writes=[];
 private _controlRead={params["_c","_a"];_a params["_k","_d"];private _key=format["%1:%2",_c,_k];if(_key in _controlProps)then{_controlProps get _key}else{_d}};
 private _controlSet={params["_c","_a"];_a params["_k","_v"];_controlProps set[format["%1:%2",_c,_k],_v];};
 private _prop={params["_c","_p","_d"];private _key=format["%1:%2",_c,_p];if(_key in _controlValues)then{_controlValues get _key}else{_d}};
 private _setUI={params["_c","_p","_v"];_controlValues set[format["%1:%2",_c,_p],_v];_writes pushBack _this;};
 private _uiInitialPositions=createHashMapFromArray[[86004,[.125,.228,.212,.210]],[86005,[.673,.279,.202,.235]],[86006,[.125,.188,.212,.029]],[86007,[.141,.233,.180,.024]],[86008,[.141,.261,.180,.024]]];
 private _uiNativePosition={private _c=_this select 0;private _fallback=if(_c in _uiInitialPositions)then{_uiInitialPositions get _c}else{[.1,.1,.1,.03]};[_c,"position",_fallback]call _prop};
 private _uiNativeShown={[_this select 0,"show",true]call _prop};private _uiNativeEnabled={[_this select 0,"enable",true]call _prop};
 private _uiNativeText={[_this select 0,"text",""]call _prop};private _uiNativeColor={[_this select 0,"color",[1,1,1,1]]call _prop};
 private _uiNativeIDC={_this select 0};private _uiNativeWidth={.1};private _uiNativeHeight={.03};
 private _listRows=createHashMap;private _selected=createHashMap;
 private _getRows={params["_c"];if(_c==86005)exitWith{
     private _old=if(_c in _listRows)then{_listRows get _c}else{[]};
     private _rows=[];{private _r=_old param[_forEachIndex,[]];
         _rows pushBack(if((_r param[0,""])==_x)then{+_r}else{[_x,_x,0,[1,1,1,1],""]});
     }forEach _rowData;_rows
 };if(_c in _listRows)then{_listRows get _c}else{[]}};
 private _uiNativeSize={count(_this call _getRows)};private _uiNativeSel={params["_c"];if(_c==86005)exitWith{_fixtureRightSelection};if(_c in _selected)then{_selected get _c}else{-1}};
 private _listGet={params["_c","_p","_i"];private _r=([_c]call _getRows)param[_i,[]];private _k=["data","text","value","color","tooltip"]find _p;_r param[_k,if(_p=="value")then{-1}else{if(_p=="color")then{[1,1,1,1]}else{""}}]};
 private _listClear={params["_c"];_listRows set[_c,[]];_selected set[_c,-1];if(_c==86005)then{_rowData=[];_fixtureRightSelection=-1;};};
 private _listAdd={params["_c","_txt"];private _rows=[_c]call _getRows;private _i=count _rows;_rows pushBack["",_txt,0,[1,1,1,1],""];_listRows set[_c,_rows];if(_c==86005)then{_rowData pushBack "";};_i};
 private _listSet={params["_c","_p","_a"];_a params["_i","_v"];private _rows=[_c]call _getRows;private _k=["data","text","value","color","tooltip"]find _p;if(_k>=0&&{_i>=0}&&{_i<count _rows})then{(_rows select _i)set[_k,_v];_listRows set[_c,_rows];if(_c==86005&&{_p=="data"})then{_rowData set[_i,_v];};};};
 private _listSelect={params["_c","_i"];_selected set[_c,_i];if(_c==86005)then{_fixtureRightSelection=_i;};};
 private _listDelete={params["_c","_i"];private _rows=[_c]call _getRows;if(_i>=0&&{_i<count _rows})then{_rows deleteAt _i;_listRows set[_c,_rows];if(_c==86005)then{_rowData deleteAt _i;if(_fixtureRightSelection==_i)then{_fixtureRightSelection=-1;};if(_fixtureRightSelection>_i)then{_fixtureRightSelection=_fixtureRightSelection-1;};};};};
 private _createControl={_this select 1};private _registerEvent={_events pushBack _this;};
 uiNamespace setVariable["ACME_infusion_LayoutDisplay",objNull];
 {uiNamespace setVariable[_x,[.125,.228,.212,.21]];}forEach["ACME_infusion_BaseLeftListPos","ACME_infusion_BaseRightListPos","ACME_infusion_BaseMovePos","ACME_infusion_BaseRemovePos","ACME_infusion_BaseStopPos"];
 
 ACME_fnc_updateTransfusionAccessHotspots={};ACME_fnc_getSelectedActiveBagContext={[]};ACME_fnc_transfusionAccessValid={false};ACME_fnc_bagInfusionEntry={[]};
 ACME_fnc_isYLineAccess={false};ACME_fnc_pressureInfuserCan={false};ACME_fnc_transfusionServicePaint={};
 ACME_fnc_transfusionRoundedFrame={};ACME_fnc_knownBloodType={"???"};ACME_fnc_lineWarmerActionState={[false,false,0,false,false]};
 ACME_fnc_updateTransfusionLineDetails={};ACME_fnc_updateTransfusionCards={};ACME_fnc_paintTransfusionYBracket={};ACME_fnc_pressureInfuserPaint={};
 missionNamespace setVariable["ACME_coolerAutoUse",false];
 ACM_circulation_TransfusionMenu_Selection_IVBags=[];

'''


def ui_setup():
    """Append to a native inventory fixture defining _rowData/right selection."""
    return UI_BOUNDARY + ''.join(
        'ACME_fnc_' + name + '={' + ui_source(name) + '};'
        for name in ('transfusionUiSet', 'layoutTransfusionMenu', 'updateTransfusionControls')
    )


def workflow_setup():
    return selection_boundary(stage_setup()) + "ACME_fnc_coolerYDrawDone={" + gui(read("coolerYDrawDone")) + "};" + ui_setup() + r"""
        _rowData=["ACM_BloodBag_ON_500|BloodIV_ON_500","ACM_SalineBag_500|SalineIV_500"];
        _medic setVariable["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
        private _pair={_fixtureRightSelection=0;[]call ACME_fnc_transfusionYTubing;
            _fixtureRightSelection=1;[]call ACME_fnc_transfusionYTubing;};
        private _finish={(_waits select 0 select 1)call(_waits select 0 select 0);};
    """


def test_complete_controller_repaints_every_y_step_and_opens_prepared_sets():
    execute(workflow_setup() + r"""
        []call ACME_fnc_updateTransfusionControls;
        _fixtureRightSelection=0;[]call ACME_fnc_transfusionYTubing;
        [_controlValues get "86142:text"=="Select Flush Saline","whole controller missed saline step"]call _check;
        _fixtureRightSelection=1;[]call ACME_fnc_transfusionYTubing;
        [_controlValues get "86142:text"=="Build Y Tubing","whole controller missed build step"]call _check;
        []call ACME_fnc_transfusionYTubing;
        [count _waits==1&&{_controlValues get "86142:text"=="Building..."},"whole controller did not schedule/show build"]call _check;
        [(_controlValues get "86142:enable")isEqualTo false,"building action remained enabled"]call _check;
        call _finish;
        [uiNamespace getVariable["ACME_preparedListMode",false],"completion did not open prepared mode"]call _check;
        [count(_medic getVariable["ACME_preparedIVSets",[]])==1,"completion did not deliver prepared set"]call _check;
        [([86142]call _uiNativeShown)isEqualTo false,"prepared mode leaked Y button"]call _check;
        [([86145]call _uiNativeSize)==1&&{([86145,"data",0]call _listGet)!=""},"whole controller did not populate prepared rows"]call _check;
    """)


def test_pending_build_remains_busy_when_wall_clock_advances_while_mission_clock_is_paused():
    execute(workflow_setup() + r"""
        call _pair;[]call ACME_fnc_transfusionYTubing;
        private _pending=missionNamespace getVariable["ACME_yBuildPending",[]];
        private _missionAt=CBA_missionTime;
        _nowTime=_nowTime+20;
        []call ACME_fnc_updateTransfusionControls;
        [CBA_missionTime==_missionAt&&{(missionNamespace getVariable["ACME_yBuildPending",[]])isEqualTo _pending},"paused build was retired by the UI clock"]call _check;
        [_controlValues get "86142:text"=="Building..."&&{(_controlValues get "86142:enable")isEqualTo false}&&{([86142]call _uiNativeShown)isEqualTo true},"wall clock hid or re-enabled a live build"]call _check;
        []call ACME_fnc_transfusionYTubing;
        [count _waits==1,"paused build accepted a duplicate native action"]call _check;
        CBA_missionTime=CBA_missionTime+2.5;call _finish;
        [count(_medic getVariable["ACME_preparedIVSets",[]])==1&&{([86142]call _uiNativeShown)isEqualTo false},"mission-clock completion did not publish one prepared set"]call _check;
    """)


def test_whole_controller_shows_waiting_for_the_actual_pending_cooler_draw():
    execute(workflow_setup() + r"""
        private _coolerRequests=[];
        ACME_fnc_coolerDraw={_coolerRequests pushBack _this;true};
        _rowData set[0,"ACM_BloodBag_ON_500|BloodIV_ON_500|COOLER"];
        call _pair;[]call ACME_fnc_transfusionYTubing;
        [count _coolerRequests==1&&{count _waits==0},"cooler recipe did not await its canonical source draw"]call _check;
        _nowTime=_nowTime+20;
        []call ACME_fnc_updateTransfusionControls;
        [_controlValues get "86142:text"=="Withdrawing blood..."&&{(_controlValues get "86142:enable")isEqualTo false}&&{([86142]call _uiNativeShown)isEqualTo true},"pending cooler transfer has no waiting indication"]call _check;
        []call ACME_fnc_transfusionYTubing;
        [count _coolerRequests==1&&{count _waits==0},"waiting cooler recipe duplicated its draw or scheduled an unfunded build"]call _check;
    """)


@pytest.mark.parametrize('ending', ('cancel', 'complete'))
def test_completed_or_canceled_workflow_restores_nonblood_spike_action(ending):
    change = 'missionNamespace setVariable["ACME_yPending",""];' if ending == 'cancel' else ''
    expected = 0 if ending == 'cancel' else 1
    execute(workflow_setup() + 'call _pair;[]call ACME_fnc_transfusionYTubing;' + change + r"""
        call _finish;
        [false]call ACME_fnc_togglePreparedSets;
        _fixtureRightSelection=1;
        []call ACME_fnc_updateTransfusionControls;
        [([86142]call _uiNativeShown)isEqualTo false&&{([86141]call _uiNativeShown)isEqualTo true},"nonblood selection inherited the Y action after retirement"]call _check;
        [_controlValues get "86141:text"=="Spike Bag","ordinary saline inherited a Y-build label"]call _check;
    """ + f'[count(_medic getVariable["ACME_preparedIVSets",[]])=={expected},"retired workflow changed prepared custody"]call _check;')


@pytest.mark.parametrize('mutation', (
    '_context set[0,profileNamespace];',
    '_context set[6,1];',
    '_context set[7,1];',
))
@pytest.mark.parametrize('pending_key', ('ACME_yBuildPending', 'ACME_yCoolerDrawPending'))
def test_foreign_or_old_epoch_intents_do_not_paint_current_nonblood_selection_busy(mutation, pending_key):
    execute(workflow_setup() + r"""
        _fixtureRightSelection=1;
        private _context=[_medic,_patient,"leftarm",true,0,0,0,0,"","","","","","",1];
    """ + mutation + f'missionNamespace setVariable["{pending_key}",[1,_context]];' + r"""
        missionNamespace setVariable["ACME_yBuildingActive",_nowTime+100];
        []call ACME_fnc_updateTransfusionControls;
        [([86142]call _uiNativeShown)isEqualTo false,"foreign/old intent exposed a current nonblood Y action"]call _check;
        [_controlValues get "86142:text"=="Spike Y tubing","foreign/old intent claimed the current waiting label"]call _check;
    """)


@pytest.mark.parametrize('pending', ('"stale"', '[]', '[1,[]]', '["bad",_context]', '[-1,_context]', '[1,_context select[0,8]]'))
def test_malformed_intents_never_abort_the_full_refresh_or_claim_busy_state(pending):
    execute(workflow_setup() + r"""
        _fixtureRightSelection=1;
        private _context=[_medic,_patient,"leftarm",true,0,0,0,0,"","","","","","",1];
    """ + f'missionNamespace setVariable["ACME_yBuildPending",{pending}];missionNamespace setVariable["ACME_yCoolerDrawPending",{pending}];' + r"""
        []call ACME_fnc_updateTransfusionControls;
        [([86142]call _uiNativeShown)isEqualTo false&&{_controlValues get "86142:text"=="Spike Y tubing"},"malformed intent claimed the current nonblood action"]call _check;
        [missionNamespace getVariable["ACME_txLayoutManaged",false],"malformed intent aborted before final layout"]call _check;
    """)
