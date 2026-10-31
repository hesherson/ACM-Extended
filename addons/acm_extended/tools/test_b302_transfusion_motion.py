"""Compact layout and bounded read-only flow/pulse/measurement decoration."""
import re, subprocess
import pytest
from test_menu_death_lifecycle import ROOT,read,execute,adapt
from test_b278_transfusion_geometry import renderer_setup,renderer_source
from test_b301_transfusion_alignment import topology_setup
from test_b273_transfusion_layout import fixed_layout
BASE='de71fb771a30ae4e3cc25e1c115b65e7753a47d2'

@pytest.mark.parametrize('count',[3,6,11])
@pytest.mark.parametrize('delta',[-1,-.7,-.35,0,.35,.7,1])
def test_tick_zoom_is_bounded_symmetric_and_tapers_at_both_sides(count,delta):
    radius=.7/(count-1);distance=delta*radius
    expected=1+.35*max(0,1-abs(delta))**2*(3-2*max(0,1-abs(delta)))
    execute('ACME_fnc_transfusionMarkScale={'+adapt(read('transfusionMarkScale'))+'};'+f'''
      private _s=[.5+{distance},.5,{count}] call ACME_fnc_transfusionMarkScale;
      [abs (_s-{expected})<.00001,"tick scale is not the bounded symmetric proximity curve"] call _check;
    ''')


def visual_setup():
    source=renderer_source('transfusionVisualTick').replace('diag_tickTime','_visualTime').replace('_nowTime','_visualTime')
    source=source.replace('isNull _display','false').replace('isNull _frame','false')
    source=source.replace('ctrlShown _group','(_controlValues get format["%1:show",_group])')
    source=source.replace('ctrlShown _mask','(_controlValues get format["%1:show",_mask])')
    source=source.replace('ctrlShown _frame','true')
    source=source.replace('_frame ctrlSetFade _fade','[_frame,"fade",_fade] call ACME_fnc_transfusionUiSet').replace('_frame ctrlCommit 0;','')
    return renderer_setup()+r'''
      private _visualTime=.1;
      ACME_fnc_transfusionCardData={params ["_l","_r"];["Carrier","50 / 100 mL","Piggyback Secondary","",[1,1,1,1],"bag.paa","",.5,100,_l==86129]};
    '''+'ACME_fnc_transfusionVisualTick={'+source+'};'


def test_animation_moves_only_the_clipped_flow_texture_and_ready_frame_without_rebinding():
    execute(visual_setup()+r'''
      [missionNamespace] call ACME_fnc_updateTransfusionCards;
      missionNamespace setVariable ["ACME_txVisualRefresh",0];
      missionNamespace setVariable ["ACME_txPulseFrames",[86414]];
      private _pool=_creationCount;private _callbacks=count _events;
      private _rect=+(_controlValues get "86510:position");
      [missionNamespace] call ACME_fnc_transfusionVisualTick;
      private _old=+(_controlValues get "[[86510,40],41]:position");
      private _fade=_controlValues get "86414:fade";
      _visualTime=.2;[missionNamespace] call ACME_fnc_transfusionVisualTick;
      [(_controlValues get "[[86510,40],41]:position") isNotEqualTo _old,"flow stripes did not advance"] call _check;
      [(_controlValues get "86414:fade")!=_fade,"ready action did not pulse"] call _check;
      [!(_controlValues get "[86500,40]:show"),"held primary claims flow"] call _check;
      [_pool==_creationCount && {_callbacks==count _events} && {_rect isEqualTo (_controlValues get "86510:position")},"decoration reallocated or resized its card/hit area"] call _check;
      _visualTime=.8;[missionNamespace] call ACME_fnc_transfusionVisualTick;
      [!(_controlValues get "[86510,40]:show"),"stale data kept claiming flow"] call _check;
    ''')


def test_equal_fluid_and_infusion_widths_include_identical_progress_and_connector_arms():
    execute(topology_setup()+r'''
      _positions set [86004,[.125*1.7777778,.228,.212*1.7777778,.187]];
      _positions set [86129,[.125*1.7777778,.575,.212*1.7777778,.187]];
      [missionNamespace] call ACME_fnc_updateTransfusionCards;
      [missionNamespace] call ACME_fnc_paintTransfusionYBracket;
      private _a=_controlValues get "[86500,16]:position";private _b=_controlValues get "[86510,16]:position";
      [abs ((_a select 2)-(_b select 2))<.000001,"fluid/infusion measurement bars differ"] call _check;
      private _pa=_controlValues get "86226:position";private _pb=_controlValues get "86227:position";
      [abs ((_pa select 2)-(_pb select 2))<.000001,"piggyback arms differ across sections"] call _check;
      private _ya=_controlValues get "86185:position";
      [abs ((_ya select 2)-(_pa select 2))<.000001,"Y and piggyback arm lengths differ"] call _check;
    ''')


def test_compact_rows_gaps_log_and_source_tooltip_stay_in_existing_menu():
    rects=fixed_layout()
    for idc in [86004,86005,86145]:assert rects[idc][3]==.244
    for idc in [86129,86127]:assert rects[idc][3]==.187
    for a,b in [(86006,86170),(86131,86172),(86214,86144)]:
        left,right=(rects[x] for x in [a,b]);assert left[2]==right[2]==.104
        assert right[0]-left[0]-left[2]==pytest.approx(.004)
    assert rects[86171]==(.125,.822,.212,.068)
    assert 'Click to switch between Self and Patient inventory.' in read('layoutTransfusionMenu')
    assert '* 0.004' in read('updateTransfusionLineDetails')


def test_new_motion_is_read_only_cached_and_keeps_native_pause_action():
    motion=read('transfusionVisualTick');runtime=read('registerTransfusionUiRuntime')
    for forbidden in ['ownerDispatch','IV_Bags','lbSetCurSel','ctrlCreate','createDialog','addPerFrameHandler']:
        assert forbidden not in motion
    assert runtime.count('call CBA_fnc_addPerFrameHandler')==2
    assert 'diag_tickTime + 0.25' in runtime and '}, 0.05, []]' in runtime
    native='addons/circulation/functions/fnc_openTransfusionMenu.sqf'
    current=(ROOT/native).read_text();old=subprocess.check_output(['git','show',BASE+':'+native],cwd=ROOT,text=True)
    normalized=current.replace('format ["Pause %1 Transfusion", _typeString]','format [LLSTRING(TransfusionMenu_StopTransfusion_Display), _typeString]').replace('format ["Pause fluid flow through the selected %1 access.", _typeString]','format [LLSTRING(TransfusionMenu_StopTransfusion_ToolTip), _typeString]')
    # B305 adds only a navigation cursor packet and one constructor-time restore.
    normalized=normalized.replace(', ["_navigation", [], [[]]]];','];').replace('\n[_display,_navigation] call ACME_fnc_restorePageCursor;\n','')
    assert normalized==old
    for path in ['addons/gui','addons/acm_extended/ui/iv','addons/circulation/functions/fnc_TransfusionMenu_ToggleIVFlow.sqf']:
        assert not subprocess.check_output(['git','diff','--name-only',BASE,'--',path],cwd=ROOT).strip()


def test_shared_ui_worker_keeps_expensive_refresh_at_four_hz_and_registration_idempotent():
    from test_b156_procedure_supplies import primitives
    source=read('registerTransfusionUiRuntime').replace('hasInterface','true')
    source=source.replace('findDisplay 86000','missionNamespace').replace('findDisplay 86200','objNull')
    source=source.replace('!isNull _display','_display isNotEqualTo objNull')
    source=primitives(adapt(source))
    execute(r'''
      private _registered=[];private _refreshCount=0;private _visualCount=0;
      missionNamespace setVariable ["ACME_transfusionUiRuntimeRegistered",false];
      missionNamespace setVariable ["ACME_txNextRefresh",0];
      CBA_fnc_addPerFrameHandler={_registered pushBack _this;count _registered};
      ACME_fnc_updateTransfusionControls={_refreshCount=_refreshCount+1;};
      ACME_fnc_transfusionVisualTick={_visualCount=_visualCount+1;};
    '''+'private _register={'+source+'};'+r'''
      call _register;call _register;
      [count _registered==2,"UI reinitialization duplicated its workers"] call _check;
      private _run=(_registered select 0) select 0;
      for "_i" from 0 to 10 do {_nowTime=_i*.05;call _run;};
      [_refreshCount==3 && {_visualCount==11},"animation increased expensive refresh frequency"] call _check;
    ''')
