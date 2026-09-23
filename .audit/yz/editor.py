"""Current editor presentation: source contracts and recorded engine requests.

No live glyph fitting, input, pixels, control creation or child-overlay rendering.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute, adapt
from test_bounded_tag_contracts import source, require, tokens
from test_bounded_tag_font_fallback import config_class
from test_bounded_selector_lifetime import slice_to
from test_bounded_tag_line_layout import layout_contract
from test_bounded_selector_geometry import geometry_source_contract


def frame_contract(config=None):
    config=(ROOT/'addons/acm_extended/config.cpp').read_text() if config is None else config
    editor=config_class(config,'ACME_SK_TagEdit')
    for f in ('style = 0x200;','colorBackground[] = {0,0,0,0};',
              'colorBorder[] = {0,0,0,0};','borderSize = 0;','shadow = 0;',
              'forceDrawCaret = 0;','maxChars = 25;'):
        require(editor,f)
    label=config_class(config,'ACME_SK_TagText')
    require(label,'colorBackground[] = {0,0,0,0};')
    require(label,'shadow = 0;')
    for name in ('skPendingTagRender','skCarouselRender'):
        require(source(name),'ctrlSetBackgroundColor [0,0,0,0];')
    layout_contract()


def native_block(text=None):
    return slice_to(source('skCarouselRender') if text is None else text,'private _editNative =','private _lineY =')


def body_block(text=None):
    return slice_to(source('skDynamicLayout') if text is None else text,'private _group =','private _patientHeader =')


def native_editor_contract(stored=None, layout=None):
    stored=source('skCarouselRender') if stored is None else stored
    layout=source('skDynamicLayout') if layout is None else layout
    block=native_block(stored)
    for f in ('private _editSize = (_store select _idx) param [1,10,[0]];',
              '84010 + 3 * (([10,5,3,1] find _editSize) max 0) + 2',
              'count _nr == 4','(_nr select 2) > 0','(_nr select 3) > 0',
              'private _editX = _editNative select 0;','private _editY = _editNative select 1;',
              '_fullW = _editNative select 2;','_fullH = _editNative select 3;'):
        require(block,f)
    require(stored,'_colorBtn ctrlSetText (if (_editMode) then {"Select Syringe Tag"} else {"Edit Syringe Tag"});')
    require(body_block(layout),'if (_editMode) then {_group ctrlShow false;};')
    assert 'ctrlShow true' not in tokens(body_block(layout))
    require(layout,'_patientHeader ctrlShow (!_editMode);')
    geometry_source_contract(stored=stored)
    layout_contract(stored=stored)


def native_setup(size=10, rectangle='[0.3,0.2,0.12,0.7]', exists=True, editing=True):
    text=native_block()
    text=re.sub(r'_d displayCtrl \(([^\n;]+)\)',r'([\1] call _lookup)',text)
    text=text.replace('ctrlPosition _editNativeCtrl','_rect')
    return f'''
        private _requested=[];
        private _lookup={{_requested pushBack (_this select 0); {'profileNamespace' if exists else 'objNull'}}};
        private _rect={rectangle};private _native=[0.1,0.1,0.05,0.4];
        private _store=[["drug",{size}]];private _before=+_store;private _idx=0;
        private _editMode={str(editing).lower()};private _fullW=0.09;private _fullH=0.3;
        private _centerX=0.4;private _centerY=0.5;
    '''+adapt(text)


@pytest.mark.parametrize('size,idc',[(10,84012),(5,84015),(3,84018),(1,84021)])
@pytest.mark.parametrize('editing',[False,True])
def test_stored_own_size_native_rectangle_is_used_only_in_editor(size,idc,editing):
    execute(native_setup(size,editing=editing)+f'''
        [_requested isEqualTo [{idc}],"wrong stored-size control"] call _check;
        [_editNative isEqualTo [0.3,0.2,0.12,0.7],"native rectangle lost"] call _check;
        [abs (_fullW-{0.12 if editing else 0.09})<0.00001 && {{abs (_fullH-{0.7 if editing else 0.3})<0.00001}},"wrong editing dimensions"] call _check;
        [abs (_centerX-{0.36 if editing else 0.4})<0.00001 && {{abs (_centerY-{0.55 if editing else 0.5})<0.00001}},"wrong editor anchor"] call _check;
        [_store isEqualTo _before,"editor layout changed stored syringe"] call _check;
    ''')


@pytest.mark.parametrize('rectangle,exists',[
    ('[]',True),('[0,0,0,1]',True),('[0,0,1,-1]',True),
    ('[0,0,1]',True),('[0,0,1,1,1]',True),('[0.2,0.3,0.2,0.7]',False)])
def test_missing_or_invalid_native_control_retains_existing_rectangle(rectangle,exists):
    execute(native_setup(rectangle=rectangle,exists=exists)+'''
        [_editNative isEqualTo _native,"invalid native rectangle accepted"] call _check;
        [abs (_fullW-0.05)<0.00001 && {abs (_fullH-0.4)<0.00001},"fallback rectangle lost"] call _check;
    ''')


@pytest.mark.parametrize('editing',[False,True])
@pytest.mark.parametrize('exists',[False,True])
def test_layout_can_hide_body_group_but_never_reshow_its_child_overlays(editing,exists):
    text=body_block().replace('_d displayCtrl 84140','_groupFixture')
    text=text.replace('allControls _group','[]').replace('ctrlParentControlsGroup _x','_groupFixture')
    text=re.sub(r'(_group|_x) (ctrlShow|ctrlSetPosition|ctrlCommit) ([^;]+);',
                lambda m:'_writes pushBack ["'+m[2]+'",'+m[3]+'];',text)
    execute(f'''
        private _groupFixture={'profileNamespace' if exists else 'objNull'};
        private _editMode={str(editing).lower()};private _bodyRect=[0,0,0.2,0.4];private _duration=0;
        private _writes=[];
    '''+adapt(text)+f'''
        private _visibility=_writes select {{(_x select 0)=="ctrlShow"}};
        [_visibility isEqualTo {('[['+chr(34)+'ctrlShow'+chr(34)+',false]]') if editing and exists else '[]'},"body layout changed overlay visibility ownership"] call _check;
        [count _writes=={(3 if editing else 2) if exists else 0},"wrong body-group requests"] call _check;
    ''')


def test_current_frames_native_editor_and_shared_layout():
    frame_contract();native_editor_contract()


@pytest.mark.parametrize('old,new',[
    ('style = 0x200;','style = 0;'),('colorBackground[] = {0,0,0,0};','colorBackground[] = {0,0,0,1};'),
    ('colorBorder[] = {0,0,0,0};','colorBorder[] = {0,0,0,1};'),('borderSize = 0;','borderSize = 1;')])
def test_frame_contract_rejects_visible_frames_despite_comment_decoys(old,new):
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    block=config_class(config,'ACME_SK_TagEdit');assert old in block
    altered=config.replace(block,block.replace(old,new+' /* '+old+' */'))
    with pytest.raises(AssertionError):frame_contract(altered)


@pytest.mark.parametrize('mutation',['wrong-size','show-body','old-caption'])
def test_native_contract_rejects_regressions_despite_comment_decoys(mutation):
    stored=source('skCarouselRender');layout=source('skDynamicLayout')
    if mutation=='wrong-size':
        old='private _editSize = (_store select _idx) param [1,10,[0]];'
        stored=stored.replace(old,'private _editSize = 10; /* '+old+' */')
    elif mutation=='show-body':
        old='if (_editMode) then {_group ctrlShow false;};'
        layout=layout.replace(old,'_group ctrlShow true; /* '+old+' */')
    else:
        stored=stored.replace('"Select Syringe Tag"','"Select Tag" /* "Select Syringe Tag" */')
    with pytest.raises(AssertionError):native_editor_contract(stored,layout)
