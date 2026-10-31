"""Six-row inventory and direct Body Map initialization; engine/UI boundaries are explicit."""
import pytest
from test_menu_death_lifecycle import execute,read,adapt,ROOT
from test_b278_transfusion_geometry import renderer_setup
from test_b288_ui_launch import setup as launch_setup
from test_bounded_page_navigation import setup as nav_setup
from test_historical_carousel_input import block_at

@pytest.mark.parametrize('offset',[0,1,2,99])
def test_inventory_has_six_compact_rows_with_exact_scroll_binding_and_no_refresh_resize(offset):
    execute(renderer_setup()+f'''
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        missionNamespace setVariable ["ACME_txCardOffset_86005",{offset}];
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        private _window=[8,6,{offset}] call ACME_fnc_transfusionCardWindow;
        private _last=0;
        for "_slot" from 0 to 5 do {{
            private _group=86520+_slot;private _rect=_controlValues get format["%1:position",_group];
            private _id=[[_group,9],["ACME_txIdentity",[]]] call _controlRead;
            [_controlValues get format["%1:show",_group],"sixth inventory row missing"] call _check;
            [(_id select 2)==((_window select 1) select _slot),"compact inventory selected wrong source row"] call _check;
            [(_rect select 1)>=_last && {{(_rect select 3)<.04}},"inventory entries still tall or overlap"] call _check;
            _last=(_rect select 1)+(_rect select 3);
        }};
        private _p=_positions get 86005;
        [_last<=(_p select 1)+(_p select 3)+.00001,"sixth item outside viewport"] call _check;
        private _before=count _writes;
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        [count _writes==_before && {{_creationCount==38}} && {{count _events==161}},"refresh resized or duplicated inventory"] call _check;
    ''')

@pytest.mark.parametrize('change,accepted',[
    ('',True),('_epoch=8;',False),('_draw=objNull;',False),('_mouse=[-.1,.3];',False),
    ('_mouse=[.2,1.1];',False),('_mouse=["bad",.3];',False),('_mouse=[.2];',False)])
def test_cursor_restore_is_one_shot_owned_by_current_navigation_and_display(change,accepted):
    s=read('restorePageCursor').replace('findDisplay 84000','_draw').replace('findDisplay 86000','objNull').replace('!finite _x','false').replace('setMousePosition _mouse;','_cursorWrites pushBack _mouse;')
    execute('private _draw=missionNamespace;private _epoch=7;private _mouse=[.2,.3];private _cursorWrites=[];uiNamespace setVariable ["ACME_pageTransitionEpoch",7];ACME_fnc_restorePageCursor={'+adapt(s)+'};'+change+f'''
        private _restored=[missionNamespace,[_epoch,_mouse]] call ACME_fnc_restorePageCursor;
        [_restored isEqualTo {str(accepted).lower()} && {{count _cursorWrites=={int(accepted)}}},"stale navigation moved pointer"] call _check;
        [missionNamespace,[_epoch,_mouse]] call ACME_fnc_restorePageCursor;
        [count _cursorWrites=={int(accepted)},"later callback pulled pointer back again"] call _check;
    ''')

@pytest.mark.parametrize('body',[False,True])
def test_inline_constructor_selects_body_before_deferred_setup_and_never_prepares_hidden_syringe(body):
    fixture=launch_setup().replace('ACME_fnc_skCompoundBegin={};','ACME_fnc_skCompoundBegin={_compounds=_compounds+1;};')
    old='ACM_circulation_fnc_Syringe_Draw={if (_createSuccess) then {_nativeDisplay=missionNamespace;};};'
    new='''ACM_circulation_fnc_Syringe_Draw={params ["_m","_p","_part","_size","_ready"];
        if (_createSuccess) then {_nativeDisplay=missionNamespace;[_ready select 0,_nativeDisplay] call (_ready select 1);};};'''
    assert old in fixture
    fixture=fixture.replace(old,new)
    execute(fixture+f'''
        private _compounds=0;private _cursorSettles=0;_createSuccess=true;uiNamespace setVariable ["ACME_pageTransitionEpoch",7];
        ACME_infusion_pendingPausedFlow=[];ACME_infusion_pendingContext=[];
        uiNamespace setVariable ["ACME_SK_View","{'body' if body else 'syringe'}"];
        ACME_fnc_restorePageCursor={{_cursorSettles=_cursorSettles+1;}};
        [10,_patient,"leftarm","",[7,[.2,.3]]] call ACME_fnc_skOpenDraw;
        [_injected==1 && {{_cursorSettles==1}},"requested page waited a frame for injection"] call _check;
        [0] call _run;
        [_injected==1 && {{_cursorSettles==1}} && {{_compounds=={int(not body)}}},"Body Map started hidden preparation or reloaded controls"] call _check;
    ''')

@pytest.mark.parametrize('view,dir,target',[('transfuse','left','body'),('transfuse','right','syringe'),('body','right','transfuse')])
def test_cross_display_navigation_carries_click_position_and_epoch(view,dir,target):
    configure='''_drawDisplay=objNull;_txDisplay=missionNamespace;
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","rightarm"];''' if view=='transfuse' else 'uiNamespace setVariable ["ACME_SK_View","body"];'
    execute(nav_setup()+configure+f'["{dir}"] call _navigate;'+'''
        call _drain;
        private _args=if (count _opens>0) then {_opens select 0} else {_transfuse select 0};
        [(_args select 4) isEqualTo [uiNamespace getVariable "ACME_pageTransitionEpoch",[.2,.3]],"navigation lost click cursor or epoch"] call _check;
    ''')

def test_native_ready_hook_runs_after_geometry_and_body_view_has_no_native_drag():
    native=(ROOT/'addons/circulation/functions/fnc_Syringe_Draw.sqf').read_text()
    assert native.index('GVAR(SyringeDraw_Moving) = false;')<native.index('call (_ready select 1)')<native.index('}, { // On cancel')
    assert 'if (GVAR(SyringeDraw_Moving) && {(uiNamespace getVariable ["ACME_SK_View","syringe"]) != "body"})' in native
    assert 'call ACME_fnc_skOpenDraw' not in block_at(read('skPageNavigate'),'if (!isNull _draw && {_target in ["syringe","body"]}) exitWith')


def test_navigation_captures_cursor_before_tearing_down_source():
    source=read("skPageNavigate")
    assert source.index("private _navigation = [_transitionEpoch,getMousePosition];") < source.index("closeDialog 0;")

@pytest.mark.parametrize('width,height',[(1280,960),(1920,1080),(3440,1440),(5120,1440)])
def test_single_line_inventory_name_and_icon_share_row_center(width,height):
    fixture=renderer_setup().replace('(1/1920)',f'(1/{width})').replace('(1/1080)',f'(1/{height})')
    fixture=fixture.replace('"125 mL remaining","Running",""','"","",""')
    execute(fixture+'''
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        private _row=_controlValues get "86520:position";
        private _name=_controlValues get "[86520,10]:position";
        private _icon=_controlValues get "[86520,14]:position";
        [abs ((_name select 1)+(_name select 3)/2-(_row select 3)/2)<.00001,"single-line inventory title not centered"] call _check;
        [abs ((_icon select 1)+(_icon select 3)/2-(_row select 3)/2)<.00001,"compact icon not centered with title"] call _check;
        [(_icon select 2)>0 && {(_icon select 3)>.025},"compact icon became illegible"] call _check;
    ''')

@pytest.mark.parametrize('change',[
    '_providerLocal=false;','_controlled=missionNamespace;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    'uiNamespace setVariable ["ACME_pageTransitionEpoch",8];',
    'uiNamespace setVariable ["ACME_SK_DrawLaunch",[999,_medic,_flow,_context,[]]];'])
def test_delayed_ready_callback_cannot_inject_or_move_cursor_after_ownership_changes(change):
    fixture=launch_setup()
    old='ACM_circulation_fnc_Syringe_Draw={if (_createSuccess) then {_nativeDisplay=missionNamespace;};};'
    fixture=fixture.replace(old,'ACM_circulation_fnc_Syringe_Draw={_capturedReady=_this select 4;};')
    execute(fixture+'''
        private _capturedReady=[];private _cursorSettles=0;
        uiNamespace setVariable ["ACME_pageTransitionEpoch",7];
        ACME_fnc_restorePageCursor={_cursorSettles=_cursorSettles+1;};
        [10,_patient,"leftarm","",[7,[.2,.3]]] call ACME_fnc_skOpenDraw;
        _nativeDisplay=missionNamespace;
    '''+change+'''
        [_capturedReady select 0,_nativeDisplay] call (_capturedReady select 1);
        [_injected==0 && {_cursorSettles==0},"stale constructor changed page/cursor"] call _check;
    ''')
