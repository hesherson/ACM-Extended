"""Execute native-tag selector arithmetic, not live layout or font fitting.

The three paths share tag-face anchoring and width caps, but the stored
editor deliberately retains its different canvas-edge gap. Do not erase it.
"""
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import execute
from test_bounded_tag_contracts import source, require
from test_bounded_tag_dropdowns import geometry, geometry_contract, dropdown_contract
from test_bounded_selector_lifetime import setup, ui_commands, slice_to


def geometry_source_contract(pending=None, ensure=None, stored=None):
    pending=source('skPendingTagRender') if pending is None else pending
    ensure=source('skPendingTagEnsure') if ensure is None else ensure
    stored=source('skCarouselRender') if stored is None else stored
    for text,fragments in [
        (pending,['private _textW = ctrlTextWidth _button;',
            'private _btnW = ((_textW + 12*pixelW) max (safeZoneH*0.090)) min (safeZoneH*0.145);',
            'private _tagCenterX = _x + _w*0.36;','private _btnX = _tagCenterX - _btnW/2;',
            'private _btnY = _y + _h*0.575;',
            '_btnX = (_btnX max (_uiX + 2*pixelW)) min (_uiX + _uiW - _btnW - 2*pixelW);',
            '_button ctrlSetPosition [_btnX,_btnY,_btnW,_btnH];']),
        (ensure,['private _textW0 = ctrlTextWidth _button;',
            'private _bw0 = ((_textW0 + 12*pixelW) max (safeZoneH*0.090)) min (safeZoneH*0.145);',
            'private _tagCenterX0 = (_r0 select 0) + (_r0 select 2)*0.36;',
            'private _bx0 = _tagCenterX0 - _bw0/2;',
            '_bx0 = (_bx0 max (_uiX + 2*pixelW)) min (_uiX + _uiW - _bw0 - 2*pixelW);',
            'private _by0 = (_r0 select 1) + (_r0 select 3)*0.575;',
            '_button ctrlSetPosition [_bx0,_by0,_bw0,_bh0];']),
        (stored,['private _textW = ctrlTextWidth _colorBtn;',
            '_btnW = ((_textW + 12*pixelW) max (safeZoneH*0.090)) min (safeZoneH*0.145);',
            'private _tagCenterX = _ax + _aw*0.36;','_btnX = _tagCenterX - _btnW/2;',
            '_btnY = _ay + _ah*0.575;',
            '_btnX = (_btnX max (_uiX + _gap)) min (_uiX + _uiW - _btnW - _gap);',
            '_colorBtn ctrlSetPosition [_btnX,_btnY,_btnW,_btnH];']),
    ]:
        for f in fragments: require(text,f)
    geometry_contract(pending=pending,stored=stored)


def snippet(kind):
    if kind=='pending':
        return slice_to(source('skPendingTagRender'),'private _size =','_button ctrlSetFade 0;')
    text=source('skCarouselRender')
    prefix=slice_to(text,'private _btnH =','_colorBtn ctrlSetText')
    # Select the actual edit-mode geometry block, not another if(_editMode).
    ts=lex(text);pairs=matching(ts)
    i=next(i for i in range(len(ts)-5) if ts[i].value=='private' and ts[i+1].value=='_textW')
    openings=[j for j in range(i) if ts[j].value=='{' and pairs.get(j,-1)>i]
    op=max(openings); start=op-5
    assert [t.value for t in ts[start:op]]==['if','(','_editMode',')','then']
    end=next(j for j in range(i,len(ts)-2) if [t.value for t in ts[j:j+3]]==['_colorBtn','ctrlShow','true'])
    return prefix+text[ts[start].offset:ts[end].offset]


def geometry_setup(kind,rect,canvas,height,pixel,text_width,native=True,size=10):
    ui_x,ui_w=canvas; gap=max(4*pixel,rect[2]*.01)
    target=84470 if kind=='stored' else 84610
    code=setup()+f'''
        _rect={list(rect)};_zoneH={height};_pixelW={pixel};_pixelH={pixel};_textWidth={text_width};
        private _uiX={ui_x};private _uiY=-0.1;private _uiW={ui_w};private _uiH=_zoneH;
        ACME_fnc_uiCanvas={{[_uiX,_uiY,_uiW,_uiH]}};
        _display setVariable ["ACME_SK_CarouselNativeRect",_rect];
        uiNamespace setVariable ["ACME_SK_CurSize",{size}];
    '''
    barrel=84012+3*[10,5,3,1].index(size)
    if native: code+=f'_controls setVariable ["{barrel}",{barrel}];'
    if kind=='initial': code+='call ACME_fnc_skPendingTagEnsure;'
    else:
        block=snippet(kind).replace('ctrlPosition _barrel','_rect').replace('ctrlTextWidth _colorBtn','_textWidth')
        code+='''
            private _d=_display;private _button=84610;private _colorBtn=84470;
            private _editMode=true;private _duration=0.12;
            _rect params ["_ax","_ay","_aw","_ah"];
        '''+ui_commands(block)
        code+=ui_commands(geometry('skPendingTagRender' if kind=='pending' else 'skCarouselRender'))
    width=min(max(text_width+12*pixel,height*.09),height*.145)
    margin=gap if kind=='stored' else 2*pixel
    bx=min(max(rect[0]+rect[2]*.36-width/2,ui_x+margin),ui_x+ui_w-width-margin)
    expected=[bx,rect[1]+rect[3]*.575,width,height/32]
    code+=f'''
        private _matches=_writes select {{(_x select 0)=={target} && {{(_x select 1)=="ctrlSetPosition"}}}};
        [count _matches==1,"wrong geometry write count"] call _check;
        private _actual=(_matches select 0) select 2;private _expected={expected};
        for "_i" from 0 to 3 do {{[abs ((_actual select _i)-(_expected select _i))<0.00001,"wrong selector geometry"] call _check;}};
    '''
    if kind!='initial':
        menu_w=min(ui_w*.24,height*.78)
        menu_x=min(max(bx,ui_x+gap),ui_x+ui_w-menu_w-gap)
        menu_y=expected[1]+expected[3]+2*pixel
        menu_h=min(height*.58,max(-.1+height-gap-menu_y,height*.12))
        code+=f'''
            private _expectedMenu={[menu_x,menu_y,menu_w,menu_h]};private _actualMenu=[_menuX,_menuY,_menuW,_menuH];
            for "_i" from 0 to 3 do {{[abs ((_actualMenu select _i)-(_expectedMenu select _i))<0.00001,"wrong below-selector menu"] call _check;}};
        '''
    return code


CASES=[
 ((.3,.2,.1,.8),(-.2,1.5),1.2,.001),
 ((-.4,.1,.12,.7),(-.2,1.5),1.2,.001),
 ((1.4,.1,.12,.7),(-.2,1.5),1.2,.001),
 ((.35,-.05,.13,.9),(-.8,2.6),1.2,.0005),
 ((.1,.2,.2,1.1),(-.5,2),1.6,.002),
]


@pytest.mark.parametrize('kind',['initial','pending','stored'])
@pytest.mark.parametrize('case',CASES)
@pytest.mark.parametrize('text_width',[0,.09,2])
def test_actual_selector_paths_keep_width_caps_tag_face_and_existing_edge_rules(kind,case,text_width):
    execute(geometry_setup(kind,*case,text_width))


@pytest.mark.parametrize('size',[10,5,3,1])
@pytest.mark.parametrize('native',[False,True])
def test_initial_and_repaint_paths_use_native_or_captured_barrel_rectangles(size,native):
    for kind in ('initial','pending'):
        execute(geometry_setup(kind,*CASES[0],.09,native=native,size=size))


def test_all_current_geometry_paths_and_click_wiring_match():
    geometry_source_contract();dropdown_contract()


@pytest.mark.parametrize('field,name,old,new',[
 ('pending','skPendingTagRender','_w*0.36','_w*0.254'),
 ('ensure','skPendingTagEnsure','(_r0 select 3)*0.575','(_r0 select 3)*0.425'),
 ('stored','skCarouselRender','_aw*0.36','_aw*0.20'),
 ('pending','skPendingTagRender','safeZoneH*0.145','safeZoneH*0.165'),
 ('pending','skPendingTagRender','_uiX + 2*pixelW','_uiX - 2*pixelW'),
 ('stored','skCarouselRender','_btnY + _btnH + 2*pixelH','_btnY - _btnH - 2*pixelH'),
])
def test_geometry_contract_rejects_old_positions_or_wrong_bounds_despite_comments(field,name,old,new):
    text=source(name);assert old in text
    with pytest.raises(AssertionError):geometry_source_contract(**{field:text.replace(old,new)+'\n// '+old})
