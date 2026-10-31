"""Appearance-only scope, native decorator geometry and owned blur lifetimes.

The tests execute actual SQF decisions with native controls/PP calls as explicit
engine boundaries. They do not certify native rendering or pointer delivery.
"""
from pathlib import Path
import re
import subprocess
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute, read

BASE = 'd7949abaed921628b670b41dae988025dca02837'


def config_properties(source):
    tokens=lex(source); pairs=matching(tokens); result={}
    def walk(start,end,path=()):
        i=start
        while i<end:
            if tokens[i].value=='class':
                name=tokens[i+1].value;j=i+2
                while j<end and tokens[j].value not in ('{',';'):j+=1
                if j<end and tokens[j].value=='{':
                    walk(j+1,pairs[j],path+(name,));i=pairs[j]+1;continue
            j=i+1
            if tokens[i].kind=='ident':
                if j+1<end and tokens[j].value=='[' and tokens[j+1].value==']':j+=2
                if j<end and tokens[j].value=='=':
                    k=j+1
                    while k<end and tokens[k].value!=';':
                        k=pairs[k]+1 if tokens[k].value in ('{','[','(') and k in pairs else k+1
                    result[path+(tokens[i].value,)]=(tuple(t.value for t in tokens[j+1:k]),tokens[j+1].offset,tokens[k].offset)
                    i=k+1;continue
            i=pairs[i]+1 if tokens[i].value in ('{','[','(') and i in pairs else i+1
    walk(0,len(tokens));return result


def test_existing_config_geometry_ids_text_and_actions_are_unchanged():
    before=subprocess.check_output(['git','show',BASE+':addons/acm_extended/config.cpp'],cwd=ROOT,text=True)
    after=(ROOT/'addons/acm_extended/config.cpp').read_text()
    old=config_properties(before);new=config_properties(after)
    appearance={'colorBackground','colorBackgroundActive','colorBackgroundDisabled','colorFocused','colorBorder','colorShadow','borderSize'}
    changed=[]
    for key,(value,_,_) in old.items():
        assert key in new, key
        actual=new[key][0]
        if key[-1] in appearance:continue
        if key[-1]=='onLoad':
            strip=lambda v:re.sub(r"\s*\[_this select 0,'[^']+'\] call ACME_fnc_uiGlassInstall;?",'',v[0]).strip().rstrip(';')
            assert strip(actual)==strip(value),key
        elif actual!=value:changed.append(key)
    assert not changed,changed


def test_dynamic_factories_preserve_original_native_constructor_arguments_and_code():
    for name in ['skInject','skListRefresh','skEpinephrineDose','skPendingTagEnsure','ivFinishTray','thoraInit','skBodyActionRender']:
        original=subprocess.check_output(['git','show',BASE+f':addons/acm_extended/functions/fn_{name}.sqf'],cwd=ROOT,text=True)
        current=read(name)
        # Inverse only the added rendering factory at the native constructor boundary.
        current=re.sub(r'\[(_\w+),"([^"]+)",([^\]\n]+)\] call ACME_fnc_uiGlassControl',
            lambda m:m[1]+' ctrlCreate ["'+m[2]+'",'+re.sub(r',controlNull,"(?:panel|button)"$','',re.sub(r',(_group),"panel"$',r',\1',m[3]))+']',current)
        assert [t.value for t in lex(current)]==[t.value for t in lex(original)],name


def test_decorators_do_not_take_over_input_or_treatment():
    sources='\n'.join(read(n) for n in ['uiGlassInstall','uiGlassTrack','uiGlassTick','uiGlassControl','uiGlassBlur','uiGlassClose'])
    assert all(command not in sources for command in ['ButtonClick','ButtonDown','ctrlSetEventHandler','ctrlSetFocus','lbSetCurSel','remoteExec','ownerDispatch','closeDialog','createDialog','setUnitLoadout'])
    painter=read('uiGlassTick')
    assert '_target ctrlSetPosition' not in painter and '_target ctrlShow' not in painter and '_target ctrlEnable' not in painter
    assert 'ctrlDelete _target' not in painter
    assert 'ctrlDelete _frame' in painter


def pp_setup():
    source=read('uiGlassBlur').replace('uiNamespace','parsingNamespace')
    source=re.sub(r'ppEffectCreate \[[^\n]+\]', 'call _allocate',source)
    source=source.replace('ppEffectDestroy _handle;','_destroyed pushBack _handle;')
    source=re.sub(r'_handle (ppEffect\w+) ([^;]+);',r'_effects pushBack ["\1",\2];',source)
    return r'''
    private _one=missionNamespace;private _two=profileNamespace;
    private _created=0;private _destroyed=[];private _effects=[];private _fail=false;
    private _allocate={_created=_created+1;if (_fail) then {-1} else {40+_created}};
    '''+'ACME_fnc_uiGlassBlur={'+adapt(source)+'};'


def test_owned_blur_is_shared_across_nested_menus_and_released_once():
    execute(pp_setup()+r'''
        [_one,true] call ACME_fnc_uiGlassBlur;[_one,true] call ACME_fnc_uiGlassBlur;
        [_two,true] call ACME_fnc_uiGlassBlur;
        [_created==1,"nested/repeated acquisition stacked blur"]call _check;
        [_one,false]call ACME_fnc_uiGlassBlur;
        [count _destroyed==0,"closing old menu destroyed newer menu blur"]call _check;
        [_two,false]call ACME_fnc_uiGlassBlur;[_two,false]call ACME_fnc_uiGlassBlur;
        [_destroyed isEqualTo [41],"final close leaked or destroyed twice"]call _check;
    ''')


def test_existing_nv_effect_is_never_reused_or_destroyed():
    execute(pp_setup()+r'''
        [_one,true]call ACME_fnc_uiGlassBlur;
        parsingNamespace setVariable ["ACME_NV_FocusHandle",900];
        [_one,true]call ACME_fnc_uiGlassBlur;
        [_destroyed isEqualTo [41] && {_created==1},"glass stacked NV focus or destroyed another mod effect"]call _check;
        parsingNamespace setVariable ["ACME_NV_FocusHandle",-1];_nowTime=12;
        [_one,true]call ACME_fnc_uiGlassBlur;
        [_created==2,"glass failed to resume after NV focus ended"]call _check;
        [_one,false]call ACME_fnc_uiGlassBlur;
        [_destroyed isEqualTo [41,42],"cleanup touched a non-owned handle"]call _check;
    ''')


def test_blur_allocation_failure_is_bounded_and_throttled():
    execute(pp_setup()+r'''
        _fail=true;[_one,true]call ACME_fnc_uiGlassBlur;
        [_created==8,"allocation retries unbounded"]call _check;
        [_one,true]call ACME_fnc_uiGlassBlur;
        [_created==8 && {count _destroyed==0},"failed allocation retried every frame or destroyed foreign effect"]call _check;
        _nowTime=12;[_one,true]call ACME_fnc_uiGlassBlur;
        [_created==16,"bounded retry did not resume"]call _check;
    ''')


def test_factory_paints_before_the_original_native_hit_control():
    source=adapt(read('uiGlassControl')).replace('_display ctrlCreate _frameArgs','(_frameArgs call _create)').replace('_display ctrlCreate _targetArgs','(_targetArgs call _create)')
    execute(r'''
        private _view=missionNamespace;private _frame=uiNamespace;private _target=profileNamespace;
        private _made=[];private _tracked=[];
        private _create={_made pushBack +_this;if(count _made==1)then{_frame}else{_target}};
        ACME_fnc_uiGlassTrack={_tracked pushBack _this;};
    '''+'ACME_fnc_uiGlassControl={'+source+'};'+r'''
        private _result=[_view,"ACME_SK_StyledButton",84470,_view]call ACME_fnc_uiGlassControl;
        [_made isEqualTo [["ACME_TransfusionRoundedFrame",-1,_view],["ACME_SK_StyledButton",84470,_view]],"factory changed native class/IDC/parent or painted over target"]call _check;
        [_result isEqualTo _target && {count _tracked==1},"factory returned decorator instead of original input"]call _check;
    ''')


def test_close_retires_only_its_own_visual_worker():
    execute('ACME_fnc_uiGlassClose={'+adapt(read('uiGlassClose'))+'};'+r'''
        private _view=missionNamespace;private _removedVisual=[];private _released=[];
        CBA_fnc_removePerFrameHandler={_removedVisual pushBack (_this select 0);};
        ACME_fnc_uiGlassBlur={_released pushBack _this;};
        _view setVariable ["ACME_glassPFH",17];
        [_view]call ACME_fnc_uiGlassClose;[_view]call ACME_fnc_uiGlassClose;
        [_removedVisual isEqualTo [17],"close changed native workers or retired twice"]call _check;
        [(_view getVariable "ACME_glassEntries") isEqualTo [],"closed display retained decorators"]call _check;
    ''')


def test_main_menu_and_transfusion_native_callbacks_stay_byte_equivalent():
    paths=['addons/gui/overrides/fnc_updateActions.sqf','addons/circulation/functions/fnc_openTransfusionMenu.sqf',
           'addons/acm_extended/functions/fn_registerMedicalMenuOpenRuntime.sqf']
    for path in paths:
        original=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
        current=(ROOT/path).read_text()
        current=current.replace('[_display,_buttonClass,-1,_group] call ACME_fnc_uiGlassControl',
                                '_display ctrlCreate [_buttonClass, -1, _group]')
        current=re.sub(r'\[(_\w+),"([^"]+)",(\d+),controlNull,"button"\] call ACME_fnc_uiGlassControl',
                       lambda m:m[1]+' ctrlCreate ["'+m[2]+'",'+m[3]+']',current)
        current=current.replace('[_display,"ACE_Medical_Menu"] call ACME_fnc_uiGlassInstall;','')
        assert [t.value for t in lex(current)]==[t.value for t in lex(original)],path


@pytest.mark.parametrize('shown,enabled',[(True,True),(False,True),(True,False),(False,False)])
def test_painter_follows_native_bounds_visibility_and_enabled_state(shown,enabled):
    source=read('uiGlassTick')
    for old,new in {'ctrlBackgroundColor _target':'_nativeColor',
                    '_target ctrlSetBackgroundColor [0,0,0,0];':'_nativeColor=[0,0,0,0];',
                    'ctrlShown _target':'_nativeShown','ctrlPosition _target':'_nativeRect',
                    'ctrlEnabled _target':'_nativeEnabled','ctrlFade _target':'_nativeFade',
                    '_frame ctrlSetFade _fade;':'_paintedFade=_fade;',
                    '_frame ctrlCommit 0;':'','ctrlDelete _frame;':'_deleted=_deleted+1;'} .items():source=source.replace(old,new)
    execute(r'''
        private _view=profileNamespace;private _target=missionNamespace;private _frame=uiNamespace;
        private _nativeColor=[0.2,0.4,0.6,0.8];private _nativeRect=[0.2,0.3,0.4,0.1];private _nativeFade=0;
        private _painted=[];private _paintedFade=-1;private _deleted=0;
        ACME_fnc_transfusionRoundedFrame={_painted pushBack _this;};ACME_fnc_uiGlassBlur={};
        _view setVariable ["ACME_glassEntries",[[_target,_frame,"button"]]];
    '''+f'private _nativeShown={str(shown).lower()};private _nativeEnabled={str(enabled).lower()};'+
    'ACME_fnc_uiGlassTick={'+adapt(source)+'};'+r'''
        [_view]call ACME_fnc_uiGlassTick;
        [count _painted==1 && {((_painted select 0) select 1) isEqualTo _nativeRect},"decorator moved the native rectangle"]call _check;
        [((_painted select 0) select 3)==0.007 && {((_painted select 0) select 4) isEqualTo _nativeShown},"decorator changed corner/visibility rule"]call _check;
        [_paintedFade==(if(_nativeEnabled)then{0}else{0.45}),"disabled native control lost its visual state"]call _check;
        _view setVariable ["ACME_glassEntries",[[objNull,_frame,"button"]]];
        [_view]call ACME_fnc_uiGlassTick;
        [_deleted==1 && {count (_view getVariable "ACME_glassEntries")==0},"deleted dynamic row leaked a surface"]call _check;
    ''')
