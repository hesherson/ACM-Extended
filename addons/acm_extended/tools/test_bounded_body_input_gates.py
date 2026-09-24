"""Current editor input gates: actual expressions and full guarded navigation.

Numeric/control stand-ins record visibility decisions, not rendered controls or
live mouse/keyboard propagation. No presentation or navigation runtime is changed.
"""
from itertools import product
import pytest
from source_scan import lex
from test_menu_death_lifecycle import F, adapt, execute
from test_bounded_normal_push_lifetime import setup as push_setup, source
from test_bounded_staged_push_contracts import contains


def declaration(text, variable, occurrence=0):
    ts=lex(text)
    found=[]
    for i in range(len(ts)-2):
        if [t.value for t in ts[i:i+3]]==['private',variable,'=']:
            end=next(t for t in ts[i+3:] if t.value==';')
            found.append(text[ts[i].offset:end.offset+1])
    assert len(found)>occurrence, variable
    return found[occurrence]


def editor_input_contract(render=None, build=None, move=None, pick=None):
    render = (F/'fn_skCarouselRender.sqf').read_text() if render is None else render
    build = (F/'fn_skBuildHotspots.sqf').read_text() if build is None else build
    move = (F/'fn_skCarouselMove.sqf').read_text() if move is None else move
    pick = (F/'fn_skCarouselPick.sqf').read_text() if pick is None else pick
    assert contains(render, 'private _hitUsable = (_slot != 2) && {!_editMode} && {!_injectBusy} && {!_carouselBusy} && {_hitH > 4*pixelH};')
    assert contains(render, '_hit ctrlShow _hitUsable; _hit ctrlEnable _hitUsable;')
    assert contains(render, 'private _activeUsable = !_editMode && {!_injectBusy} && {!_carouselBusy} && {_activeH > 4*pixelH};')
    assert contains(render, '_activeHit ctrlShow _activeUsable; _activeHit ctrlEnable _activeUsable;')
    for fragment in [
        '_body && {!_tagEditMode} && {!_carouselBusy} && {_layoutReady} && {_deliveryReady} && {_route == "vascular"}',
        '_body && {!_tagEditMode} && {!_carouselBusy} && {_layoutReady} && {_route == "im"}',
        '_input ctrlShow _show;', '_input ctrlEnable _show;',
    ]:
        assert contains(build, fragment)
    for text in (move,pick):
        assert contains(text, 'if (uiNamespace getVariable ["ACME_SK_TagEditMode",false]) exitWith {};')
        ts=lex(text)
        gate=next(i for i,t in enumerate(ts) if t.kind=='string' and t.value=='ACME_SK_TagEditMode')
        ensure=next(i for i,t in enumerate(ts) if t.kind=='ident' and t.value=='ACME_fnc_skStoreEnsureIds')
        assert gate<ensure


@pytest.mark.parametrize('editing,injecting,carousel_busy',list(product([False,True],repeat=3)))
def test_active_and_neighbor_hit_regions_obey_all_three_locks(editing,injecting,carousel_busy):
    text=(F/'fn_skCarouselRender.sqf').read_text()
    neighbor=declaration(text,'_hitUsable').replace('pixelH','0.001')
    active=declaration(text,'_activeUsable').replace('pixelH','0.001')
    allowed=not (editing or injecting or carousel_busy)
    execute(f'''
        private _slot=1; private _editMode={str(editing).lower()};
        private _injectBusy={str(injecting).lower()}; private _carouselBusy={str(carousel_busy).lower()};
        private _hitH=0.05; private _activeH=0.05;
    '''+neighbor+active+f'''
        [_hitUsable isEqualTo {str(allowed).lower()},"neighbor input gate"] call _check;
        [_activeUsable isEqualTo {str(allowed).lower()},"active input gate"] call _check;
        _slot=2;
    '''+neighbor+'''
        [!_hitUsable,"generic center competes with dedicated input"] call _check;
    ''')


@pytest.mark.parametrize('editing,carousel_busy,layout_ready',list(product([False,True],repeat=3)))
def test_both_routes_disable_hotspots_while_editing_or_relaying_layout(editing,carousel_busy,layout_ready):
    text=(F/'fn_skBuildHotspots.sqf').read_text()
    vascular=declaration(text,'_show',0).replace('ctrlShown _image','_imageShown')
    im=declaration(text,'_show',1)
    allowed=not editing and not carousel_busy and layout_ready
    execute(f'''
        private _body=true; private _tagEditMode={str(editing).lower()};
        private _carouselBusy={str(carousel_busy).lower()}; private _layoutReady={str(layout_ready).lower()};
        private _deliveryReady=true; private _have=true; private _image=missionNamespace;
        private _imageShown=true; private _route="vascular";
    '''+adapt(vascular)+f'''
        [_show isEqualTo {str(allowed).lower()},"vascular editor/layout gate"] call _check;
        _route="im";
    '''+im+f'''
        [_show isEqualTo {str(allowed).lower()},"IM editor/layout gate"] call _check;
    ''')


@pytest.mark.parametrize('name,arg',[('skCarouselMove',-1),('skCarouselMove',1),('skCarouselPick',-2),('skCarouselPick',0),('skCarouselPick',2)])
def test_editing_navigation_rejects_before_store_or_selection_work(name,arg):
    execute(push_setup()+r'''
        uiNamespace setVariable ["ACME_SK_TagEditMode",true];
        private _storeReads=0; private _movesRequested=0;
        ACME_fnc_skStoreEnsureIds={_storeReads=_storeReads+1;[]};
        ACME_fnc_skCarouselMove={_movesRequested=_movesRequested+1;};
        private _saved=+(_medic getVariable ["ACME_narcStore",[]]);
    '''+'private _navigate={'+source(name)+'};'+f'[{arg}] call _navigate;'+r'''
        [_storeReads==0 && {_movesRequested==0} && {_refreshes==0},"editor navigated"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SelectedSyringeId",""])=="id-one","editor changed selection"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo _saved,"editor altered store"] call _check;
    ''')


@pytest.mark.parametrize('target,old,new',[
    ('render','&& {!_editMode}','&& {true}'),
    ('render','_activeHit ctrlEnable _activeUsable;','_activeHit ctrlEnable true;'),
    ('build','&& {!_tagEditMode}','&& {true}'),
    ('build','_input ctrlEnable _show;','_input ctrlEnable true;'),
    ('move','if (uiNamespace getVariable ["ACME_SK_TagEditMode", false]) exitWith {};',''),
    ('pick','if (uiNamespace getVariable ["ACME_SK_TagEditMode",false]) exitWith {};',''),
])
def test_contract_rejects_removed_gates_even_with_comment_decoys(target,old,new):
    texts={k:(F/f'fn_{n}.sqf').read_text() for k,n in [('render','skCarouselRender'),('build','skBuildHotspots'),('move','skCarouselMove'),('pick','skCarouselPick')]}
    assert old in texts[target]
    texts[target]=texts[target].replace(old,new)+'\n/* '+old+' */\n'
    with pytest.raises(AssertionError):editor_input_contract(**texts)
