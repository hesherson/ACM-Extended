"""Current click-only selectors and their recorded UI-boundary requests.

Handler bodies and layout arithmetic run from checked-out SQF. Controls, focus
and event order are fixtures; this does not render lists or certify live clicks.
"""
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import execute, adapt
from test_historical_syringe_identity import source
from test_bounded_tag_contracts import require


def handlers(text, control):
    ts=lex(text); pairs=matching(ts); found={}
    for i,t in enumerate(ts):
        if t.value!='ctrlAddEventHandler' or i<1 or ts[i-1].value!=control:
            continue
        assert ts[i+1].value=='[' and ts[i+2].kind=='string' and ts[i+4].value=='{'
        event=ts[i+2].value; opening=i+4
        assert event not in found
        found[event]=text[ts[opening].offset+1:ts[pairs[opening]].offset]
    return found


def dropdown_contract(inject=None, ensure=None):
    inject=source('skInject') if inject is None else inject
    ensure=source('skPendingTagEnsure') if ensure is None else ensure
    for text, control, fn in [(inject,'_colorList','skTagColor'),(ensure,'_list','skPendingTagColor')]:
        h=handlers(text,control)
        require(h['LBSelChanged'],'_this call ACME_fnc_'+fn)
        require(h['MouseButtonUp'],'private _row = lbCurSel _ctrl;')
        require(h['MouseButtonUp'],'if (_row >= 0) then {[_ctrl,_row] call ACME_fnc_'+fn+';}')
        require(text,'["none","None - No syringe tag"]')
    main=handlers(ensure,'_button')
    assert set(main)=={'ButtonClick'}, 'main selector must not open from hover'
    for text,control in [(ensure,'_button'),(inject,'_colorBtn')]:
        body=handlers(text,control)['ButtonClick']
        require(body,'if (ctrlShown _l) then')
        require(body,'_l lbSetCurSel -1;')
        require(body,'_l ctrlShow true;')
        require(body,'_l ctrlShow false;')
    # Current pending selector follows artwork, then its list is created last.
    seq=[next(t.offset for i,t in enumerate(lex(ensure)) if t.value=='ctrlCreate'
              and lex(ensure)[i+2].value==cls and lex(ensure)[i+4].value==str(idc))
         for cls,idc in [('RscPicture',84600),('ACME_SK_StyledButton',84610),('ACME_SK_TagList',84611)]]
    assert seq==sorted(seq) and len(set(seq))==3


def captions_contract(render=None):
    render=source('skCarouselRender') if render is None else render
    require(render,'_colorBtn ctrlSetText (if (_editMode) then {"Select Syringe Tag"} else {"Edit Syringe Tag"});')
    require(source('skPendingTagEnsure'),'_button ctrlSetText "Select Syringe Tag";')


def geometry(name):
    text=source(name); ts=lex(text)
    start=next(i for i in range(len(ts)-2) if ts[i].value=='private' and ts[i+1].value=='_menuW')
    finish=next(i for i in range(start,len(ts)-2) if ts[i].value=='private' and ts[i+1].value=='_menuH')
    end=next(i for i in range(finish,len(ts)) if ts[i].value==';')
    return text[ts[start].offset:ts[end].offset+1]


def geometry_contract(pending=None, stored=None):
    pending=source('skPendingTagRender') if pending is None else pending
    stored=source('skCarouselRender') if stored is None else stored
    for text,target in [(pending,'_list'),(stored,'_colorList')]:
        for fragment in ['private _menuW = (_uiW * 0.24) min (safeZoneH * 0.78);',
                         'private _menuY = _btnY + _btnH + 2*pixelH;',
                         'private _menuH = (safeZoneH * 0.58) min _maxBelow;',
                         target+' ctrlSetPosition [_menuX,_menuY,_menuW,_menuH];',
                         target+' ctrlSetBackgroundColor [0.04,0.04,0.04,0.96];']:
            require(text,fragment)
    require(pending,'_list ctrlEnable true;')


def setup_handler(kind, event):
    text=source('skPendingTagEnsure' if kind=='pending' else 'skInject')
    control=('_button' if kind=='pending' else '_colorBtn') if event=='ButtonClick' else ('_list' if kind=='pending' else '_colorList')
    body=handlers(text,control)[event]
    for old,new in [
        ('findDisplay 84000','_drawDisplay'), ('_d displayCtrl 84611','84611'),
        ('_d displayCtrl 84471','84471'), ('_d displayCtrl 84460','84460'),
        ('ctrlShown _l','_shown'), ('_l lbSetCurSel -1;','_resets=_resets+1;'),
        ('_l ctrlShow true;','_shown=true;'),('_l ctrlShow false;','_shown=false;'),
        ('ctrlSetFocus _l;','_focus pushBack _l;'),
        ('ctrlSetFocus (84460);','_focus pushBack 84460;'),('lbCurSel _ctrl','_rowSelected'),
    ]: body=body.replace(old,new)
    return '''
        private _drawDisplay=missionNamespace; private _shown=false;
        private _focus=[]; private _resets=0; private _ensures=0; private _opened=0;
        private _selected=[]; private _rowSelected=2;
        ACME_fnc_skPendingTagEnsure={_ensures=_ensures+1;};
        ACME_fnc_skTagEditOpen={_opened=_opened+1;};
        ACME_fnc_skTagColor={_selected pushBack _this;_rowSelected=-1;};
        ACME_fnc_skPendingTagColor={_selected pushBack _this;_rowSelected=-1;};
        uiNamespace setVariable ["ACME_SK_TagEditMode",true];
        uiNamespace setVariable ["ACME_SK_View","syringe"];
    '''+'private _handler={'+adapt(body)+'};\n'


@pytest.mark.parametrize('kind',['pending','stored'])
def test_click_opens_then_closes_the_same_list_and_resets_selection(kind):
    list_id=84611 if kind=='pending' else 84471
    execute(setup_handler(kind,'ButtonClick')+'''
        [100] call _handler;
        [_shown && {_resets==1},"click did not open/reset list"] call _check;
    '''+f'[_focus isEqualTo [{list_id}],"opened wrong list"] call _check;'+'''
        [100] call _handler;
        [!_shown && {_resets==2} && {_opened==0},"second click did not close/reset list"] call _check;
    '''+f'[_focus isEqualTo {f"[{list_id}]" if kind=="pending" else f"[{list_id},84460]"},"close focus behavior changed"] call _check;')


@pytest.mark.parametrize('kind',['pending','stored'])
def test_missing_display_prevents_toggle(kind):
    execute(setup_handler(kind,'ButtonClick')+'''
        _drawDisplay=objNull; [100] call _handler;
        [!_shown && {count _focus==0} && {_resets==0} && {_opened==0},"missing display still toggled"] call _check;
    ''')


def test_pending_selector_does_not_toggle_on_body_page():
    execute(setup_handler('pending','ButtonClick')+'''
        uiNamespace setVariable ["ACME_SK_View","body"]; [100] call _handler;
        [!_shown && {count _focus==0} && {_ensures==0},"pending list opened on body map"] call _check;
    ''')


def test_stored_button_opens_editor_before_it_can_toggle_the_list():
    execute(setup_handler('stored','ButtonClick')+'''
        uiNamespace setVariable ["ACME_SK_TagEditMode",false]; [100] call _handler;
        [_opened==1 && {!_shown} && {_resets==0},"ordinary edit button bypassed editor"] call _check;
    ''')


@pytest.mark.parametrize('kind',['pending','stored'])
@pytest.mark.parametrize('row',[-1,0,12])
def test_mouse_release_fallback_commits_only_a_valid_row_once(kind,row):
    execute(setup_handler(kind,'MouseButtonUp')+f'_rowSelected={row};'+'''
        [100] call _handler; [100] call _handler;
    '''+f'[_selected isEqualTo {f"[[100,{row}]]" if row>=0 else "[]"},"release fallback committed twice or accepted deselection"] call _check;')


@pytest.mark.parametrize('kind',['pending','stored'])
def test_native_selection_then_release_does_not_commit_the_row_twice(kind):
    text=source('skPendingTagEnsure' if kind=='pending' else 'skInject')
    body=handlers(text,'_list' if kind=='pending' else '_colorList')['LBSelChanged']
    execute(setup_handler(kind,'MouseButtonUp')+'private _changed={'+adapt(body)+'};'+'''
        [100,2] call _changed; [100] call _handler;
        [_selected isEqualTo [[100,2]],"selection plus release produced a duplicate commit"] call _check;
    ''')


@pytest.mark.parametrize('width,height,x',[ (0.9,1.0,0.0),(1.5,1.2,-0.3),(2.4,1.0,-0.7)])
@pytest.mark.parametrize('name',['skPendingTagRender','skCarouselRender'])
def test_actual_menu_geometry_stays_below_selector_with_shared_width_formula(width,height,x,name):
    execute(f'''
        private _uiW={width}; private _uiX={x}; private _zoneH={height}; private _zoneY=-0.1;
        private _pixelH=0.001; private _gap=0.01; private _btnX={x}+0.05;
        private _btnY=0.25; private _btnH=0.04;
    '''+adapt(geometry(name).replace('safeZoneH','_zoneH').replace('safeZoneY','_zoneY').replace('pixelH','_pixelH'))+f'''
        [abs (_menuW-{min(width*.24,height*.78)})<0.00001,"wrong dropdown width"] call _check;
        [abs (_menuY-0.292)<0.00001,"dropdown moved above selector"] call _check;
        [_menuX>=_uiX && {{_menuX+_menuW<=_uiX+_uiW}},"horizontal bounds escaped canvas"] call _check;
        [_menuH>0,"dropdown height vanished"] call _check;
    ''')


def test_current_wiring_captions_and_geometry_match():
    dropdown_contract();captions_contract();geometry_contract()


@pytest.mark.parametrize('mutation',['wrong_callback','no_none','hover','caption','width'])
def test_contracts_reject_wrong_targets_and_retired_behavior_despite_comment_decoys(mutation):
    if mutation in ['wrong_callback','no_none','hover']:
        text=source('skPendingTagEnsure')
        old,new={
            'wrong_callback':('call ACME_fnc_skPendingTagColor','call ACME_fnc_skTagColor'),
            'no_none':('["none","None - No syringe tag"]','["removed","None - No syringe tag"]'),
            'hover':('_button ctrlAddEventHandler ["ButtonClick"','_button ctrlAddEventHandler ["MouseEnter"'),
        }[mutation]
        with pytest.raises((AssertionError,KeyError)):
            dropdown_contract(ensure=text.replace(old,new)+'\n// '+old)
    elif mutation=='caption':
        text=source('skCarouselRender');old='then {"Select Syringe Tag"} else {"Edit Syringe Tag"}'
        with pytest.raises(AssertionError):captions_contract(text.replace(old,'then {"Edit Tag"} else {"Select Tag"}')+'\n// '+old)
    else:
        text=source('skPendingTagRender');old='(_uiW * 0.24) min (safeZoneH * 0.78)'
        with pytest.raises(AssertionError):geometry_contract(pending=text.replace(old,'_uiW * 0.05')+'\n// '+old)
