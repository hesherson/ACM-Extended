"""Check safe control defaults and execute per-display optional font selection.

Only file probing and UI commands are fixtures. No font files are bundled here.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, execute
from test_bounded_tag_contracts import source, require, tokens
from test_bounded_selector_lifetime import slice_to
from test_bounded_tag_line_layout import snippet

FONT = 'ACME_QEDaveMergens'
ASSET = r'\acm_extended\ui\fonts\QEDaveMergens\QEDaveMergens96.fxy'


def config_class(text, name):
    ts=lex(text); pairs=matching(ts)
    hits=[i for i in range(len(ts)-2) if ts[i].value=='class' and ts[i+1].value==name and ts[i+2].value!=';']
    assert len(hits)==1, (name,hits)
    start=hits[0]; op=next(i for i in range(start,len(ts)) if ts[i].value=='{')
    return text[ts[start].offset:ts[pairs[op]].offset+1]


def font_block(kind, text=None):
    text=source('skPendingTagRender' if kind=='pending' else 'skCarouselRender') if text is None else text
    return slice_to(text,'private _tagFont =','private _lines =' if kind=='pending' else 'private _fnc_medName =')


def static_loop(text=None):
    text=source('skCarouselRender') if text is None else text; ts=lex(text); pairs=matching(ts)
    hits=[]
    for i in range(len(ts)-1):
        if ts[i].value!='for' or ts[i+1].value!='_ln': continue
        op=next(j for j in range(i,len(ts)) if ts[j].value=='{')
        block=text[ts[i].offset:ts[pairs[op]].offset+1]+';'
        if tokens('_tc ctrlSetFont _tagFont;') in tokens(block): hits.append(block)
    assert len(hits)==1
    return hits[0]


def font_contract(config=None, pending=None, stored=None):
    config=(ROOT/'addons/acm_extended/config.cpp').read_text() if config is None else config
    family=config_class(config,FONT)
    require(family,'fonts[] = {"'+ASSET[:-4]+'"};')
    for cls in ('ACME_SK_TagEdit','ACME_SK_TagText'):
        # The engine resolves this font when ctrlCreate runs, before the render
        # function can probe optional assets or apply its cached font choice.
        require(config_class(config,cls),'font = "Caveat";')
    for kind,text in [('pending',pending),('stored',stored)]:
        block=font_block(kind,text)
        for f in ('private _tagFont = _d getVariable ["ACME_SK_TagFont", ""];',
                  'if (_tagFont == "") then',
                  'fileExists "'+ASSET+'"',
                  'then {"'+FONT+'"} else {"Caveat"}',
                  '_d setVariable ["ACME_SK_TagFont", _tagFont];'):
            require(block,f)
        require(snippet(kind,text),'ctrlSetFont _tagFont;')
    require(static_loop(stored),'_tc ctrlSetFont _tagFont;')
    for text in (config,source('skPendingTagRender') if pending is None else pending,
                 source('skCarouselRender') if stored is None else stored):
        assert 'ACME_QEPhillips' not in tokens(text)
        assert r'\ui\fonts\QEPhillips' not in tokens(text)


def no_outline_fonts():
    addon=ROOT/'addons/acm_extended'
    assert not [p for p in addon.rglob('*') if p.is_file() and p.suffix.lower() in ('.ttf','.otf','.woff','.woff2')]


def setup():
    out='''
        private _d=missionNamespace; private _present=false; private _probes=[];
        private _probe={_probes pushBack _this; _present};
    '''
    for kind in ('pending','stored'):
        text=font_block(kind)
        needle='fileExists "'+ASSET+'"'
        assert text.count(needle)==1
        text=text.replace(needle,'("'+ASSET+'" call _probe)')
        out+='private _'+kind+'={'+text+' _tagFont};\n'
    return out


@pytest.mark.parametrize('kind',['pending','stored'])
@pytest.mark.parametrize('available',[False,True])
def test_cold_font_probe_and_warm_cache_preserve_text_payload(kind,available):
    expected=FONT if available else 'Caveat'
    execute(setup()+f'''
        _present={str(available).lower()};
        private _payload=["Mixed Case","Dose 3","<tag>"];
        uiNamespace setVariable ["ACME_SK_PendingTagText",+_payload];
        _medic setVariable ["ACME_narcStore",[+_payload]];
        [call _{kind} == "{expected}","wrong cold font choice"] call _check;
        _present=!_present;
        [call _{kind} == "{expected}","cache changed on repaint"] call _check;
        [_probes isEqualTo ["{ASSET}"],"wrong or repeated asset probe"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingTagText",[]]) isEqualTo _payload,"font choice changed pending text"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo [_payload],"font choice changed stored text"] call _check;
    ''')


@pytest.mark.parametrize('first,second',[('pending','stored'),('stored','pending')])
@pytest.mark.parametrize('available',[False,True])
def test_render_paths_share_only_the_same_display_cache(first,second,available):
    expected=FONT if available else 'Caveat'; other='Caveat' if available else FONT
    execute(setup()+f'''
        _present={str(available).lower()};
        [call _{first} == "{expected}","first path font"] call _check;
        _present=!_present;
        [call _{second} == "{expected}","same display cache not shared"] call _check;
        [count _probes==1,"second path probed unnecessarily"] call _check;
        _d=profileNamespace;
        [call _{second} == "{other}","new display inherited stale cache"] call _check;
        [count _probes==2,"new display did not probe"] call _check;
    ''')


@pytest.mark.parametrize('kind',['pending','stored','static'])
@pytest.mark.parametrize('available',[False,True])
def test_selected_font_reaches_all_three_actual_text_controls(kind,available):
    block=static_loop() if kind=='static' else snippet(kind)
    block=re.sub(r'_d displayCtrl \(([^;]+?)\)',r'(\1)',block)
    block=re.sub(r'(_e|_edit|_tc) (ctrlSet\w+|ctrlShow|ctrlEnable|ctrlCommit)\s*([^;]+);',
                 lambda m:'_writes pushBack ['+m[1]+',"'+m[2]+'",'+m[3]+'];',block)
    prefix=setup()+f'''
        _present={str(available).lower()};private _tagFont=call _{'pending' if kind=='pending' else 'stored'};
        private _writes=[]; private _lines=["A","B","C"];
        private _cur=["","","","","","","",""]+_lines;private _e=+_cur;
        private _x=0;private _y=0;private _w=0.2;private _h=0.8;
        private _ax=_x;private _ay=_y;private _aw=_w;private _ah=_h;
        private _focusIDC=-1;private _hasTag=true;private _curHasTag=true;
        private _editMode=true;private _duration=0;private _slot=1;private _bid=84410;
        private _alpha=0.7;private _lineY=[0.443,0.480,0.517];private _lineH=0.038;private _lineFontH=0.031;
    '''
    base={'pending':84601,'stored':84460,'static':84414}[kind]
    execute(prefix+block+f'''
        private _fonts=_writes select {{(_x select 1)=="ctrlSetFont"}};
        [count _fonts==3,"missing font assignment"] call _check;
        for "_n" from 0 to 2 do {{
            [(_fonts select _n) isEqualTo [{base}+_n,"ctrlSetFont","{FONT if available else 'Caveat'}"],"font applied to wrong control"] call _check;
        }};
    ''')


def test_font_wiring_and_no_outline_font_distribution():
    font_contract();no_outline_fonts()


@pytest.mark.parametrize('mutation',['unavailable-control-font','wrong-probe','empty-fallback','no-cache','wrong-static-target'])
def test_font_contract_rejects_mutations_despite_comment_decoys(mutation):
    pending=source('skPendingTagRender');stored=source('skCarouselRender');config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    if mutation=='unavailable-control-font':
        old='font = "Caveat";';config=config.replace(old,'font = "'+FONT+'"; /* '+old+' */')
    elif mutation=='wrong-probe':
        old='fileExists "'+ASSET+'"';pending=pending.replace(old,'fileExists "wrong.fxy" /* '+old+' */')
    elif mutation=='empty-fallback':
        pending=pending.replace('else {"Caveat"}','else {""} /* else {"Caveat"} */')
    elif mutation=='no-cache':
        old='_d setVariable ["ACME_SK_TagFont", _tagFont];';pending=pending.replace(old,'/* '+old+' */')
    else:
        old='_tc ctrlSetFont _tagFont;';stored=stored.replace(old,'_other ctrlSetFont _tagFont; /* '+old+' */')
    with pytest.raises(AssertionError):font_contract(config,pending,stored)
