"""Execute checked-out tag editor loops with explicit control-command fixtures.

Numeric rectangles and text requests are checked, not font fitting, pixels,
Unicode graphemes, native input or complete dialog lifetimes.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, execute
from test_bounded_tag_contracts import source, require, tag_limits
from test_bounded_tag_dropdowns import dropdown_contract


def snippet(kind, text=None):
    text=source('skPendingTagRender' if kind=='pending' else 'skCarouselRender') if text is None else text
    ts=lex(text);pairs=matching(ts);pieces=[]
    for name in ('_lineY','_lineH','_lineFontH'):
        starts=[i for i in range(len(ts)-1) if ts[i].value=='private' and ts[i+1].value==name]
        assert len(starts)==1
        start=starts[0];end=next(i for i in range(start,len(ts)) if ts[i].value==';')
        pieces.append(text[ts[start].offset:ts[end].offset+1])
    starts=[i for i in range(len(ts)-1) if ts[i].value=='for' and ts[i+1].value=='_ln']
    candidates=[]
    for start in starts:
        op=next(i for i in range(start,len(ts)) if ts[i].value=='{')
        values=[t.value for t in ts[op:pairs[op]+1]]
        if ('84601' if kind=='pending' else '84460') in values:
            candidates.append((start,op))
    assert len(candidates)==1
    start,op=candidates[0]
    pieces.append(text[ts[start].offset:ts[pairs[op]].offset+1]+';')
    return '\n'.join(pieces)


def layout_contract(pending=None, stored=None):
    for kind,text in [('pending',pending),('stored',stored)]:
        block=snippet(kind,text)
        for fragment in ('private _lineY = [0.443,0.480,0.517];','private _lineH = 0.038;',
                         'private _lineFontH = 0.031;','for "_ln" from 0 to 2 do','select [0,25]'):
            require(block,fragment)
        if kind=='pending':
            require(block,'_e ctrlSetPosition [_x + _w*0.247, _y + _h*(_lineY select _ln), _w*0.245, _h*_lineH];')
            require(block,'_e ctrlSetFontHeight (_h*_lineFontH);')
            require(block,'if (_focusIDC != (84601 + _ln)) then {_e ctrlSetText _lineText;};')
        else:
            require(block,'_edit ctrlSetPosition [_ax+_aw*0.247,_ay+_ah*(_lineY select _ln),_aw*0.245,_ah*_lineH];')
            require(block,'_edit ctrlSetFontHeight (_ah*_lineFontH);')
    # Navigation delegates layout to the render path; it does not retain a separate old line geometry.
    require(source('skCarouselMove'),'[0] call ACME_fnc_skCarouselRender;')


def pending_contract(ensure=None):
    ensure=source('skPendingTagEnsure') if ensure is None else ensure
    dropdown_contract(ensure=ensure)
    require(ensure,'for "_line" from 0 to 2 do')
    require(ensure,'_e = _d ctrlCreate ["ACME_SK_TagEdit", 84601 + _line];')
    require(ensure,'_e ctrlAddEventHandler ["KeyUp", {call ACME_fnc_skPendingTagCommit;}];')
    require(ensure,'_e ctrlAddEventHandler ["KillFocus", {call ACME_fnc_skPendingTagCommit;}];')
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    ts=lex(config);pairs=matching(ts)
    start=next(i for i in range(len(ts)-1) if ts[i].value=='class' and ts[i+1].value=='ACME_SK_TagEdit')
    op=next(i for i in range(start,len(ts)) if ts[i].value=='{')
    block=config[ts[op].offset:ts[pairs[op]].offset+1]
    for fragment in ('style = 0x200;','colorBackground[] = {0,0,0,0};','colorBorder[] = {0,0,0,0};','maxChars = 25;'):
        require(block,fragment)
    render=source('skPendingTagRender')
    for fragment in ('private _hasTag = !(_color in ["", "none"]);','_e ctrlShow _hasTag;',
                     '_e ctrlEnable _hasTag;','tag_overlay_%1mL_%2.paa'):
        if fragment.startswith('tag_'): assert fragment in render
        else: require(render,fragment)


def setup(kind, rect, shown=True, focus=-1, edit=True):
    block=snippet(kind)
    block=re.sub(r'_d displayCtrl \(([^;]+?)\)',r'(\1)',block)
    block=re.sub(r'(_e|_edit) (ctrlSet\w+|ctrlShow|ctrlEnable|ctrlCommit) ([^;]+);',
                 lambda m:'_writes pushBack ['+m[1]+',"'+m[2]+'",'+m[3]+'];',block)
    x,y,w,h=rect
    return f'''
        private _writes=[];private _tagFont="fixture";private _duration=0.12;
        private _x={x};private _y={y};private _w={w};private _h={h};
        private _ax=_x;private _ay=_y;private _aw=_w;private _ah=_h;
        private _hasTag={str(shown).lower()};private _curHasTag=_hasTag;
        private _editMode={str(edit).lower()};private _focusIDC={focus};
        private _lines=["abcdefghijklmnopqrstuvwxyz1234","Mixed Case","Dose 3"];
        private _cur=["","","","","","","",""]+_lines;
    '''+block+'''
        private _value={
            params ["_id","_op"];
            private _idx=_writes findIf {(_x select 0)==_id && {(_x select 1)==_op}};
            if (_idx<0) exitWith {[]};
            (_writes select _idx) select 2
        };
    '''


@pytest.mark.parametrize('kind',['pending','stored'])
@pytest.mark.parametrize('rect',[(0.1,0.2,0.15,0.8),(0,0,0.04,0.2),(-0.2,0.1,0.23,1.1)])
@pytest.mark.parametrize('shown',[False,True])
def test_actual_three_line_geometry_and_text_are_scaled_consistently(kind,rect,shown):
    base=84601 if kind=='pending' else 84460
    execute(setup(kind,rect,shown)+f'''
        for "_n" from 0 to 2 do {{
            private _id={base}+_n;
            private _r=[_id,"ctrlSetPosition"] call _value;
            private _expected=[_x+_w*0.247,_y+_h*([0.443,0.480,0.517] select _n),_w*0.245,_h*0.038];
            for "_i" from 0 to 3 do {{[abs ((_r select _i)-(_expected select _i))<0.00001,"wrong scaled tag rectangle"] call _check;}};
            [abs (([_id,"ctrlSetFontHeight"] call _value)-_h*0.031)<0.00001,"wrong tag font scale"] call _check;
            [([_id,"ctrlSetText"] call _value)==(["abcdefghijklmnopqrstuvwxy","Mixed Case","Dose 3"] select _n),"wrong tag text/truncation"] call _check;
            [([_id,"ctrlShow"] call _value) isEqualTo {str(shown).lower()},"wrong editor visibility"] call _check;
            [([_id,"ctrlEnable"] call _value) isEqualTo {str(shown).lower()},"wrong editor input state"] call _check;
            [([_id,"ctrlSetBackgroundColor"] call _value) isEqualTo [0,0,0,0],"tag editor background became opaque"] call _check;
        }};
    ''')


@pytest.mark.parametrize('line',[0,1,2])
def test_pending_render_does_not_replace_the_active_text_field(line):
    execute(setup('pending',(0.1,0.2,0.15,0.8),focus=84601+line)+f'''
        [(_writes findIf {{(_x select 0)=={84601+line} && {{(_x select 1)=="ctrlSetText"}}}})==-1,"focused pending text replaced"] call _check;
        [count (_writes select {{(_x select 1)=="ctrlSetText"}})==2,"other pending fields did not refresh"] call _check;
    ''')


def test_stored_fields_are_hidden_outside_edit_mode_even_with_a_tag():
    execute(setup('stored',(0.1,0.2,0.15,0.8),edit=False)+'''
        for "_n" from 0 to 2 do {
            [!([84460+_n,"ctrlShow"] call _value) && {!([84460+_n,"ctrlEnable"] call _value)},"stored fields active outside editor"] call _check;
        };
    ''')


def test_current_pending_wiring_and_both_layout_contracts():
    pending_contract();layout_contract();tag_limits()


@pytest.mark.parametrize('kind',['pending','stored'])
@pytest.mark.parametrize('old,new',[("_lineH = 0.038","_lineH = 0.030"),("_lineFontH = 0.031","_lineFontH = 0.0185"),("select [0,25]","select [0,17]")])
def test_contract_rejects_obsolete_geometry_or_text_limit_with_comment_decoys(kind,old,new):
    text=source('skPendingTagRender' if kind=='pending' else 'skCarouselRender')
    assert old in text
    text=text.replace(old,new+' /* '+old+' */')
    with pytest.raises(AssertionError):layout_contract(**{('pending' if kind=='pending' else 'stored'):text})


def test_pending_contract_rejects_removing_third_editor():
    text=source('skPendingTagEnsure').replace('for "_line" from 0 to 2 do','for "_line" from 0 to 1 do /* for "_line" from 0 to 2 do */')
    with pytest.raises(AssertionError):pending_contract(text)
