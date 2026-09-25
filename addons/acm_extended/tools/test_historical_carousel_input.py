"""Batch 10: actual carousel selection, keyboard and repeat/collapse logic.

Engine display/control primitives and presentation delegates are explicit fixtures.
The real store identity functions, navigation and input-handler/first-tick bodies
execute. Callbacks are captured and replayed in controlled order, not live CBA/UI
scheduling. Geometry/fill arithmetic uses a fixed viewport; no live control rendering,
fonts, medication delivery or engine player switching is simulated.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import execute
from test_historical_syringe_identity import setup as identity_setup, source
from test_historical_procedure_trays import controls, ui_code


def block_at(text, marker):
    assert text.count(marker) == 1, marker
    opening = text.index('{', text.index(marker))
    tokens = lex(text); pairs = matching(tokens)
    index = next(i for i,t in enumerate(tokens) if t.offset == opening)
    return text[opening:tokens[pairs[index]].offset+1]


def code(text):
    text = text.replace('findDisplay 84000', '_drawDisplay')
    text = text.replace('focusedCtrl _d', '_focused')
    text = re.sub(r"\bsafeZoneH\b", "_screenHeight", text)
    text = re.sub(r"\bctrlType (_\w+)", r"([\1] call _controlType)", text)
    text = text.replace('ctrlIDC _focus', '_focus')
    text = text.replace('ctrlShown (_d displayCtrl 84471)', '_colorOpen')
    text = text.replace('ctrlText (_d displayCtrl _x)', '([_x] call _readText)')
    text = text.replace('_colorList lbSetCurSel -1;', '_listReset = -1;')
    return ui_code(text)


def tick_body():
    text = source('skUiTick')
    # This complete initial tick section owns repeat, editor hold and collapse.
    # Subsequent stock/plunger/NV work is a distinct scope, not replaced or tested here.
    start = 'disableSerialization;'
    end = 'private _navPulse = '
    assert text.count(start) == text.count(end) == 1
    return text[text.index(start):text.index(end)]


def setup():
    return identity_setup() + controls() + '''
        private _focused = objNull; private _screenHeight = 1;
        private _colorOpen = false;
        private _layouts = []; private _renderCalls = []; private _viewCalls = 0;
        private _controlType = {if ((_this select 0) == 84470) then {1} else {2}};
        ACME_fnc_uiCanvas = {[0,0,1,1]};
        ACME_fnc_skDynamicLayout = {_layouts pushBack _this;};
        ACME_fnc_skCarouselRender = {_renders = _renders+1; _renderCalls pushBack _this;};
        ACME_fnc_skSetView = {_viewCalls = _viewCalls+1;};
        ACME_fnc_skBodyActionRender = {};
        ACME_fnc_skPendingTagRender = {};
        ACME_fnc_a11yColor = {[0.1,0.2,0.3,0.4]};
        CBA_fnc_waitAndExecute = {_waits pushBack _this;};
        private _drain = {private _pending = +_waits; _waits=[];
            {(_x select 1) call (_x select 0);} forEach _pending;};
        uiNamespace setVariable ["ACME_SK_View","body"];
        uiNamespace setVariable ["ACME_SK_CarouselHeldDir",0];
        uiNamespace setVariable ["ACME_SK_CarouselRepeatAt",0];
        uiNamespace setVariable ["ACME_SK_CarouselExpanded",false];
        ["id-a",_rows] call ACME_fnc_skSelectStored;
    ''' + ''.join('ACME_fnc_'+name+'={'+code(source(name))+'};\n' for name in (
        'skCarouselMove','skCarouselPick','skCarouselToggle','skCarouselHover')) + \
        'private _down='+code(block_at(source('skInject'),'_display displayAddEventHandler ["KeyDown",'))+';\n' + \
        'private _up='+code(block_at(source('skInject'),'_display displayAddEventHandler ["KeyUp",'))+';\n' + \
        'private _uiTick={'+code(tick_body())+'};\n' + \
        'private _repeat={[[ _drawDisplay ],0] call _uiTick;};\n'


@pytest.mark.parametrize('offset,expected',[(-2,'id-b'),(-1,'id-c'),(1,'id-b'),(2,'id-c')])
def test_click_selects_its_final_visible_record_once_without_a_deferred_second_step(offset,expected):
    execute(setup()+f'[{offset}] call ACME_fnc_skCarouselPick;'+
        f'[(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="{expected}","click stopped on an intermediate medication"] call _check;'+'''
        [count _waits==0,"click left a delayed navigation callback"] call _check;
        [count _layouts==1 && {_renders==1} && {_hotspots==1},"click repainted intermediate selections"] call _check;
        [uiNamespace getVariable ["ACME_SK_CarouselExpanded",false],"click did not promote"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _rows,"navigation changed medication payload"] call _check;
    ''')


@pytest.mark.parametrize('replacement',[
    '_drawDisplay=profileNamespace;',
    'ACE_player=_patient; _patient setVariable ["ACME_narcStore",+_rows];',
    'uiNamespace setVariable ["ACME_SK_View","syringe"];uiNamespace setVariable ["ACME_SK_View","body"];',
    'uiNamespace setVariable ["ACME_SK_TagEditMode",true];uiNamespace setVariable ["ACME_SK_TagEditMode",false];',
    '[_medic,[_c,_a,_b]] call ACME_fnc_narcStoreCommit;',
    '[-1] call ACME_fnc_skCarouselMove;',
])
def test_old_far_click_cannot_move_a_reopened_or_changed_session(replacement):
    execute(setup()+'''[2] call ACME_fnc_skCarouselPick;'''+replacement+'''
        ["id-a",_rows] call ACME_fnc_skSelectStored;
        call _drain;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a","old click changed newer selection"] call _check;
    ''')


@pytest.mark.parametrize('blocker',[
    '_drawDisplay=objNull;',
    'uiNamespace setVariable ["ACME_SK_View","syringe"];',
    'uiNamespace setVariable ["ACME_SK_TagEditMode",true];',
    'uiNamespace setVariable ["ACME_SK_InjectionBusy",true];',
    '[_medic,[]] call ACME_fnc_narcStoreCommit;',
])
def test_rejected_far_click_does_not_schedule_later_navigation(blocker):
    execute(setup()+blocker+'''[2] call ACME_fnc_skCarouselPick;
        [count _waits==0 && {count _layouts==0} && {_renders==0},"rejected click scheduled/repainted navigation"] call _check;
        _drawDisplay=missionNamespace;ACE_player=_medic;
        uiNamespace setVariable ["ACME_SK_View","body"];
        uiNamespace setVariable ["ACME_SK_TagEditMode",false];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
        [_medic,+_rows] call ACME_fnc_narcStoreCommit;
        ["id-a",_rows] call ACME_fnc_skSelectStored;
        call _drain;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a","rejected click later executed"] call _check;
    ''')


@pytest.mark.parametrize('count', [0,1,2,3])
@pytest.mark.parametrize('direction', [-1,1])
def test_keyboard_steps_keep_wraparound_and_never_mutate_the_store(count,direction):
    execute(setup()+f'private _store=_rows select [0,{count}]; [_medic,+_store] call ACME_fnc_narcStoreCommit;'+
        f'for "_i" from 1 to 7 do {{[{direction}] call ACME_fnc_skCarouselMove;}};'+
        f'private _expected={-1 if count==0 else (7*direction)%count};'+'''
        private _actual=if (count _store==0) then {-1} else {[_store,false] call ACME_fnc_skSelectedIndex};
        [_actual==_expected,"keyboard wrap changed"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _store,"keyboard changed drug/tag data"] call _check;
        [count _waits==0,"keyboard added a timer"] call _check;
    ''')


@pytest.mark.parametrize('key,expected',[(30,'id-c'),(32,'id-b')])
def test_keydown_hold_and_keyup_preserve_existing_repeat_cadence(key,expected):
    execute(setup()+f'private _handled=[_drawDisplay,{key}] call _down;'+
        f'[_handled && {{(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="{expected}"}},"A/D did not navigate"] call _check;'+'''
        [(uiNamespace getVariable ["ACME_SK_CarouselRepeatAt",0])==10.22,"initial repeat delay changed"] call _check;
    '''+f'[_drawDisplay,{key}] call _down;'+'''
        [_renders==1,"engine duplicate keydown repeated immediately"] call _check;
        _nowTime=10.21;call _repeat;[_renders==1,"repeat fired early"] call _check;
        _nowTime=10.22;call _repeat;[_renders==2,"held key did not repeat"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CarouselRepeatAt",0])==10.31,"repeat interval changed"] call _check;
    '''+f'[_drawDisplay,{key}] call _up;'+'''
        _nowTime=11;call _repeat;
        [_renders==2,"keyup left repeat active"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CarouselHeldDir",9])==0,"held direction not released"] call _check;
    ''')


@pytest.mark.parametrize('focus',[84460,84461,84462,84601,84602,84603,84830,99999])
@pytest.mark.parametrize('key',[30,32])
def test_any_edit_control_keeps_ad_typing_and_cancels_an_existing_hold(focus,key):
    execute(setup()+f'[_drawDisplay,{key}] call _down; _focused={focus};'+'''
        private _chosen=uiNamespace getVariable "ACME_SK_SelectedSyringeId";
        _nowTime=11;call _repeat;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")==_chosen,"repeat changed medication while an editor held focus"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CarouselHeldDir",9])==0,"editor left stale held direction"] call _check;
    '''+f'[!([_drawDisplay,{key}] call _down),"editor keydown swallowed text"] call _check;'+
        f'[!([_drawDisplay,{key}] call _up),"editor keyup swallowed text"] call _check;'+'''
        _focused=objNull;_nowTime=12;call _repeat;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")==_chosen,"editor exit resurrected old hold"] call _check;
    ''')


@pytest.mark.parametrize('key',[30,32])
def test_keyup_in_tag_mode_cancels_hold_even_without_an_intervening_tick(key):
    execute(setup()+f'[_drawDisplay,{key}] call _down;'+'''
        private _chosen=uiNamespace getVariable "ACME_SK_SelectedSyringeId";
        uiNamespace setVariable ["ACME_SK_TagEditMode",true];_focused=84470;
    '''+f'[_drawDisplay,{key}] call _up;'+'''
        uiNamespace setVariable ["ACME_SK_TagEditMode",false];_focused=objNull;
        _nowTime=11;call _repeat;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")==_chosen,"Done resurrected a key released in tag mode"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CarouselHeldDir",9])==0,"tag-mode keyup ignored"] call _check;
    ''')


@pytest.mark.parametrize('exclusive', ['tag','push','other-view'])
def test_exclusive_workflow_cancels_held_input_without_resuming_it_afterward(exclusive):
    change={'tag':'uiNamespace setVariable ["ACME_SK_TagEditMode",true];',
            'push':'uiNamespace setVariable ["ACME_SK_InjectionBusy",true];',
            'other-view':'uiNamespace setVariable ["ACME_SK_View","syringe"];'}[exclusive]
    execute(setup()+'''[_drawDisplay,32] call _down;private _chosen=uiNamespace getVariable "ACME_SK_SelectedSyringeId";'''+change+'''
        _nowTime=11;call _repeat;
        uiNamespace setVariable ["ACME_SK_TagEditMode",false];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
        uiNamespace setVariable ["ACME_SK_View","body"];
        _nowTime=12;call _repeat;
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")==_chosen,"exclusive workflow retained stale A/D hold"] call _check;
    ''')


@pytest.mark.parametrize('key', [1,16,18,31,57])
def test_unrelated_keys_are_not_consumed_or_used_for_navigation(key):
    execute(setup()+f'[!([_drawDisplay,{key}] call _down) && {{!([_drawDisplay,{key}] call _up)}},"unrelated key swallowed"] call _check;'+'''
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a" && {_renders==0},"unrelated key navigated"] call _check;
    ''')


@pytest.mark.parametrize('expanded', [True,False])
@pytest.mark.parametrize('hover', [True,False])
def test_hover_is_presentation_only_and_keeps_selection_and_expansion(expanded,hover):
    execute(setup()+f'uiNamespace setVariable ["ACME_SK_CarouselExpanded",{str(expanded).lower()}];[{str(hover).lower()}] call ACME_fnc_skCarouselHover;'+
        f'[(uiNamespace getVariable "ACME_SK_CarouselExpanded") isEqualTo {str(expanded).lower()},"hover changed expansion"] call _check;'+'''
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a","hover changed medication"] call _check;
        [count _layouts==0 && {_renders==0} && {_hotspots==0} && {count _waits==0},"hover repainted layout or queued navigation"] call _check;
    ''')


@pytest.mark.parametrize('guard',['pointer','zone','tag-focus','color','held','pending','editor','busy','none'])
def test_expanded_view_collapse_respects_existing_retention_conditions(guard):
    changes={
        'pointer':'uiNamespace setVariable ["ACME_SK_CarouselHover",true];',
        'zone':'uiNamespace setVariable ["ACME_SK_CarouselZoneHover",true];',
        'tag-focus':'_focused=84460;', 'color':'_colorOpen=true;',
        'held':'uiNamespace setVariable ["ACME_SK_CarouselHeldDir",1];uiNamespace setVariable ["ACME_SK_CarouselRepeatAt",100];',
        'pending':'uiNamespace setVariable ["ACME_SK_PendingInjection",["patient","part",1]];',
        'editor':'uiNamespace setVariable ["ACME_SK_TagEditMode",true];',
        'busy':'uiNamespace setVariable ["ACME_SK_CarouselBusy",true];', 'none':''}
    execute(setup()+'''uiNamespace setVariable ["ACME_SK_CarouselExpanded",true];uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",9];'''+changes[guard]+'''
        call _repeat;
    '''+f'[(uiNamespace getVariable "ACME_SK_CarouselExpanded") isEqualTo {str(guard!="none").lower()},"collapse retention failed"] call _check;'+'''
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a","collapse changed medication"] call _check;
    ''')


@pytest.mark.parametrize('pending',[False,True])
def test_center_click_toggles_browsing_but_keeps_a_staged_target_promoted(pending):
    execute(setup()+('uiNamespace setVariable ["ACME_SK_PendingInjection",["patient","part",1]];' if pending else '')+'''
        [0] call ACME_fnc_skCarouselPick;
        [uiNamespace getVariable ["ACME_SK_CarouselExpanded",false],"center failed to promote"] call _check;
        [0] call ACME_fnc_skCarouselPick;
    '''+f'[(uiNamespace getVariable "ACME_SK_CarouselExpanded") isEqualTo {str(pending).lower()},"center lost pending target or failed to toggle"] call _check;'+'''
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a" && {count _waits==0},"center navigated"] call _check;
    ''')


@pytest.mark.parametrize('key',[30,32])
def test_new_dialog_does_not_inherit_a_hold_whose_keyup_went_to_the_closed_display(key):
    text=source('skInject')
    start='private _afterSaveId = '
    end='uiNamespace setVariable ["ACME_SK_Route", "vascular"];'
    assert text.count(start)==1
    tail=text[text.index(start):]
    assert tail.count(end)==1
    initialize=tail[:tail.index(end)+len(end)]
    execute(setup()+f'[_drawDisplay,{key}] call _down;'+'''
        // Simulate reopening straight to a stored syringe before a preparation-page tick.
        // Execute the real display initializer, not a mock resetting the input state.
        _drawDisplay=profileNamespace;
        uiNamespace setVariable ["ACME_SK_OpenCarouselId","id-a"];
        private _job=createHashMapFromArray [["flowing",true],["syringeId","id-c"]];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
    '''+'call {'+code(initialize)+'}; _nowTime=11;call _repeat;'+'''
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a","old held key changed reopened selection"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CarouselHeldDir",9])==0,"new display inherited key hold"] call _check;
        [(missionNamespace getVariable "ACME_HCMedPushJob") isEqualTo _job,"input reset changed ongoing push job"] call _check;
    ''')


@pytest.mark.parametrize('view',['syringe','body'])
def test_current_keyboard_route_is_body_only_and_legacy_bridge_uses_the_same_move(view):
    execute(setup()+f'uiNamespace setVariable ["ACME_SK_View","{view}"];'+
        f'private _handled=[_drawDisplay,32] call _down; [_handled isEqualTo {str(view=="body").lower()},"wrong view consumed navigation"] call _check;'+
        'private _bridge={'+code(source('skBodySyringeMove'))+'}; [-1] call _bridge;'+'''
        [(uiNamespace getVariable "ACME_SK_SelectedSyringeId")=="id-a","legacy bridge used a different selection engine"] call _check;
    ''')


@pytest.mark.parametrize('expanded',[False,True])
@pytest.mark.parametrize('slot',[0,1,2,3,4])
def test_actual_slot_hover_alpha_changes_without_changing_its_geometry(expanded,slot):
    text=source('skCarouselRender')
    a='private _fullH = safeZoneH * '
    b='// Hitboxes are bounded '
    c='        private _scale = if (_editMode) '
    d='        private _bar = '
    assert all(text.count(x)==1 for x in (a,b,c,d))
    dimensions=text[text.index(a):text.index(b)]
    presentation=text[text.index(c):text.index(d)]
    execute(setup()+f'private _expanded={str(expanded).lower()};private _slot={slot};'+'''
        private _editMode=false;private _ratio=0.3;private _rw=0.8;private _centerX=0.5;private _centerY=0.7;
        private _off=_slot-2;private _hoverOffset=99;
    '''+code(dimensions)+'private _paint={'+code(presentation)+'[_alpha,_scale,_x,_y,_w,_h]};'+'''
        private _base=call _paint;
        _hoverOffset=_off;private _hovered=call _paint;
        [_hovered isEqualTo _base,"hover changed slot opacity or geometry"] call _check;
        _hoverOffset=_off+1;
        [(call _paint) isEqualTo _base,"another slot hover changed this slot"] call _check;
    ''')


@pytest.mark.parametrize('size',[1,3,5,10])
@pytest.mark.parametrize('fraction',[0,0.5,1,1.2])
def test_actual_plunger_fraction_uses_total_solution_and_clamps_to_the_barrel(size,fraction):
    text=source('skCarouselRender')
    a='        private _frac = '
    b='        // During an ordinary display-bound push'
    assert text.count(a)==text.count(b)==1
    body=text[text.index(a):text.index(b)]
    ratio={1:10.2/10.5,3:9.83/10.5,5:10.3/10.5,10:1}[size]
    expected=0.3+0.2*ratio*min(fraction,1)*0.5
    execute(setup()+f'private _size={size};private _amt={size*fraction*0.4};private _nsMl={size*fraction*0.6};'+'''
        private _native=[0,0,0.3,1];private _h=0.5;private _y=0.3;private _travel10=0.2;
    '''+code(body)+f'[abs (_py-{expected})<0.000001,"stored plunger ignores carrier volume or leaves barrel"] call _check;')


def test_navigation_clears_existing_site_dose_and_discard_transients_without_touching_contents():
    execute(setup()+'''
        uiNamespace setVariable ["ACME_SK_EpiDoseChoice",7];
        uiNamespace setVariable ["ACME_SK_SelFlush","flush"];
        uiNamespace setVariable ["ACME_SK_SiteIdx",3];
        uiNamespace setVariable ["ACME_SK_DiscardArmedId","id-a"];
        [2] call ACME_fnc_skCarouselPick;
        [(uiNamespace getVariable "ACME_SK_EpiDoseChoice")==0 && {(uiNamespace getVariable "ACME_SK_SiteIdx")== -1},"navigation retained old dose/site"] call _check;
        [(uiNamespace getVariable "ACME_SK_SelFlush")=="" && {(uiNamespace getVariable "ACME_SK_DiscardArmedId")==""},"navigation retained flush/discard authorization"] call _check;
        [(_medic getVariable "ACME_narcStore") isEqualTo _rows,"navigation mutated syringe contents"] call _check;
    ''')
