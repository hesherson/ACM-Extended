"""Actual pending-selector creation and page gating, with explicit UI fixtures.

Controls and text metrics are stand-ins; no real pixels, event propagation,
modal ownership, or complete open/close lifetime is certified here.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import execute, adapt
from test_bounded_tag_contracts import source, require, tokens
from test_bounded_tag_dropdowns import dropdown_contract


def slice_to(text, first, last):
    ts=lex(text); a=lex(first); b=lex(last)
    def at(pattern):
        found=[i for i in range(len(ts)-len(pattern)+1)
               if [(t.kind,t.value) for t in ts[i:i+len(pattern)]]==[(t.kind,t.value) for t in pattern]]
        assert len(found)==1, (pattern,found)
        return found[0]
    start=at(a); end=at(b)
    assert start<end
    return text[ts[start].offset:ts[end].offset]


def selector_contract(ensure=None, inject=None, opener=None, render=None, tick=None):
    ensure=source('skPendingTagEnsure') if ensure is None else ensure
    inject=source('skInject') if inject is None else inject
    opener=source('skOpenDraw') if opener is None else opener
    render=source('skPendingTagRender') if render is None else render
    tick=source('skUiTick') if tick is None else tick
    dropdown_contract(ensure=ensure,inject=inject)
    require(inject,'_display setVariable ["ACME_SK_PendingTagReady", false];')
    ordered=['call ACME_fnc_skInject;', '_tagDisplayEarly setVariable ["ACME_SK_PendingTagReady", true];',
             'call ACME_fnc_skPendingTagEnsure;', 'call ACME_fnc_skPendingTagRender;']
    position=-1; stream=tokens(opener)
    for fragment in ordered:
        position=stream.index(tokens(fragment),position+1)
    for cls,idc in [('RscPicture',84600),('ACME_SK_StyledButton',84610),('ACME_SK_TagList',84611)]:
        assert tokens(ensure).count(tokens(f'ctrlCreate ["{cls}", {idc}]'))==1
        assert tokens(f'ctrlCreate ["{cls}", {idc}]') not in tokens(inject)
    require(ensure,'if (isNull _d || {!(_d getVariable ["ACME_SK_PendingTagReady", false])}) exitWith {false};')
    require(ensure,'if (isNull _button) then')
    require(ensure,'_button ctrlSetText "Select Syringe Tag";')
    require(render,'_button ctrlSetText "Select Syringe Tag";')
    require(render,'_button ctrlSetTooltip format ["Select or change this syringe tag. Current: %1. None removes the tag.", _short];')
    require(render,'private _showSetup = (_view == "syringe");')
    require(render,'_button ctrlShow _showSetup;')
    require(render,'_button ctrlEnable _showSetup;')
    require(render,'if (!_showSetup) exitWith')
    require(tick,'if (_now >= (_d getVariable ["ACME_SK_NextPendingTag",0])) then')
    require(tick,'_d setVariable ["ACME_SK_NextPendingTag", _now + 0.10];')
    require(tick,'call ACME_fnc_skPendingTagRender;')
    require(inject,'[{if (!isNull (findDisplay 84000)) then {call ACME_fnc_skPendingTagRender;};}, [], 0.03] call CBA_fnc_waitAndExecute;')


def ui_commands(text):
    """Record outer statement-form UI writes; balanced handler payloads stay code."""
    ts=lex(text);pairs=matching(ts); edits=[];i=0
    while i<len(ts):
        t=ts[i]
        if t.kind=='ident' and (t.value.startswith('ctrlSet') or t.value in ['ctrlShow','ctrlEnable','ctrlCommit','ctrlAddEventHandler','lbSetCurSel','lbSetData']):
            # Unary focus is only inside registered, unexecuted handlers.
            if t.value=='ctrlSetFocus':i+=1;continue
            assert i>0 and ts[i-1].kind=='ident'
            end=i+1
            while end<len(ts) and ts[end].value!=';':
                end=pairs[end]+1 if ts[end].value in ['[','{','('] and end in pairs else end+1
            rhs=text[ts[i+1].offset:ts[end].offset]
            edits.append((ts[i-1].offset,ts[end].offset+1, f'[{ts[i-1].value},"{t.value}",{rhs}] call _write;'))
            i=end+1;continue
        i+=1
    for a,b,s in reversed(edits): text=text[:a]+s+text[b:]
    text=text.replace('!isNull (_d displayCtrl 84610)','!((_d displayCtrl 84610) isEqualTo objNull)')
    text=re.sub(r'_d ctrlCreate (\[[^\n;]+\])',r'(\1 call _create)',text)
    text=re.sub(r'_d displayCtrl \(([^\n;]+?)\)',r'([\1] call _lookup)',text)
    text=re.sub(r'_d displayCtrl (\d+|_x)',r'([\1] call _lookup)',text)
    text=text.replace('_list lbAdd _label','([_list,_label] call _addRow)')
    text=text.replace('ctrlPosition _barrel0','_rect').replace('ctrlTextWidth _button','_textWidth')
    text=text.replace('findDisplay 84000','_display')
    for old,new in [('safeZoneY','_zoneY'),('safeZoneH','_zoneH'),('pixelW','_pixelW'),('pixelH','_pixelH')]:text=text.replace(old,new)
    return adapt(text)


def setup():
    ensure=ui_commands(source('skPendingTagEnsure'))
    prefix=ui_commands(slice_to(source('skPendingTagRender'),'disableSerialization;', 'private _color ='))
    return r'''
        private _display=missionNamespace;
        private _controls=profileNamespace;private _created=[];private _writes=[];private _rows=[];
        private _fail=-1;private _textWidth=0.09;private _rect=[0.3,0.2,0.1,0.8];
        private _zoneY=-0.1;private _zoneH=1.2;private _pixelW=0.001;private _pixelH=0.001;
        private _lookup={_controls getVariable [str (_this select 0),objNull]};
        private _create={params ["_cls","_id"];if (_id==_fail) exitWith {objNull};
            _created pushBack [_cls,_id];_controls setVariable [str _id,_id];_id};
        private _write={_writes pushBack _this;};
        private _addRow={_rows pushBack _this;(count _rows)-1};
        ACME_fnc_uiCanvas={[-0.2,-0.1,1.5,1.2]};
        _display setVariable ["ACME_SK_PendingTagReady",true];
        _display setVariable ["ACME_SK_CarouselNativeRect",_rect];
        uiNamespace setVariable ["ACME_SK_View","syringe"];
        uiNamespace setVariable ["ACME_SK_CurSize",10];
    '''+'ACME_fnc_skPendingTagEnsure={'+ensure+'}; private _renderPrefix={'+prefix+'};\n'


@pytest.mark.parametrize('size',[10,5,3,1])
@pytest.mark.parametrize('native',[False,True])
def test_complete_ensure_creates_each_control_once_and_keeps_art_button_list_order(size,native):
    idc=84012+3*[10,5,3,1].index(size)
    execute(setup()+f'''
        uiNamespace setVariable ["ACME_SK_CurSize",{size}];
    '''+(f'_controls setVariable ["{idc}",{idc}];' if native else '')+'''
        [call ACME_fnc_skPendingTagEnsure,"selector not created"] call _check;
        private _expected=[84600,84601,84602,84603,84610,84611];
        [(_created apply {_x select 1}) isEqualTo _expected,"wrong creation order"] call _check;
        [count _rows==13,"tag purposes/None lost"] call _check;
        private _before=+_writes;
        [call ACME_fnc_skPendingTagEnsure,"second ensure rejected"] call _check;
        [(_created apply {_x select 1}) isEqualTo _expected && {_writes isEqualTo _before},"duplicate controls/handlers/writes"] call _check;
        private _events=_writes select {(_x select 1)=="ctrlAddEventHandler"};
        [count _events==9,"registration count changed"] call _check;
        [(_events apply {[_x select 0,((_x select 2) select 0)]}) isEqualTo [[84601,"KillFocus"],[84601,"KeyUp"],[84602,"KillFocus"],[84602,"KeyUp"],[84603,"KillFocus"],[84603,"KeyUp"],[84610,"ButtonClick"],[84611,"LBSelChanged"],[84611,"MouseButtonUp"]],"wrong event targets"] call _check;
    ''')


@pytest.mark.parametrize('missing',[False,True])
def test_unready_or_missing_display_creates_nothing(missing):
    execute(setup()+('_display=objNull;' if missing else '_display setVariable ["ACME_SK_PendingTagReady",false];')+'''
        [!(call ACME_fnc_skPendingTagEnsure),"invalid display accepted"] call _check;
        call _renderPrefix;
        [count _created==0 && {count _writes==0},"unready display modified"] call _check;
    ''')


@pytest.mark.parametrize('view',['syringe','body','other'])
@pytest.mark.parametrize('infusion',[False,True])
def test_actual_render_prefix_controls_visibility_without_inferring_pixels(view,infusion):
    execute(setup()+f'uiNamespace setVariable ["ACME_SK_View","{view}"];'+
            ('_display setVariable ["ACME_SK_Return",["bag"]];' if infusion else '')+'''
        call ACME_fnc_skPendingTagEnsure;_writes=[];
        call _renderPrefix;
    '''+f'''
        [([84610,"ctrlShow",{str(view=='syringe').lower()}] in _writes),"wrong selector visibility"] call _check;
        [([84610,"ctrlEnable",{str(view=='syringe').lower()}] in _writes),"wrong selector availability"] call _check;
    '''+('''
        {[[_x,"ctrlShow",false] in _writes,"pending artwork not hidden"] call _check;} forEach [84600,84601,84602,84603,84611];
        [[84611,"lbSetCurSel",-1] in _writes,"hidden list selection not reset"] call _check;
    ''' if view!='syringe' else '[count _writes==2,"preparation prefix unexpectedly hid artwork"] call _check;'))


def test_current_creation_and_refresh_source_contract():
    selector_contract()


@pytest.mark.parametrize('kind',['ready','caption','repaint','order'])
def test_selector_contract_rejects_regressions_even_with_comment_decoys(kind):
    field,name,old,new={
        'ready':('ensure','skPendingTagEnsure','!(_d getVariable ["ACME_SK_PendingTagReady", false])','false'),
        'caption':('ensure','skPendingTagEnsure','_button ctrlSetText "Select Syringe Tag";','_button ctrlSetText "Select Tag";'),
        'repaint':('tick','skUiTick','_now + 0.10','_now + 10'),
        'order':('opener','skOpenDraw','_tagDisplayEarly setVariable ["ACME_SK_PendingTagReady", true];','_tagDisplayEarly setVariable ["ACME_SK_PendingTagReady", false];'),
    }[kind]
    text=source(name);assert old in text
    with pytest.raises((AssertionError,ValueError)):
        selector_contract(**{field:text.replace(old,new)+'\n// '+old})
