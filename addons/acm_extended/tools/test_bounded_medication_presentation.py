"""Execute current medication visibility and prep-stock controller boundaries.

Uses actual SQF blocks/functions with engine UI commands represented explicitly.
No controls are rendered, and a passed visibility request is not a pixel test.
"""
import pytest
from source_scan import lex, render
from test_menu_death_lifecycle import ROOT, adapt, execute

F=ROOT/'addons/acm_extended/functions'


def source(name): return (F/('fn_'+name+'.sqf')).read_text()


def require(text,fragment):
    assert render(lex(fragment)) in render(lex(text)), fragment


def renderer_contract(text=None):
    text=source('skListRefresh') if text is None else text
    for fragment in ('[84006,84303,"medication"]', '[_d] call ACME_fnc_skMedicationSync;',
                     '_nativeMedB50 ctrlShow false;', '_list ctrlShow false;',
                     '_d ctrlCreate ["ACME_SK_RowGroup", _groupID]',
                     'private _metaRows = _d getVariable ["ACME_SK_MedicationRows", []];',
                     '(_x param [1, ""]) == _data', '_list lbText _i', '_list lbPicture _i',
                     '_group setVariable ["ACME_SK_ColumnHeader",_header]',
                     '_stock ctrlSetText _stockLabel;', '_countText ctrlSetText _countLabel;',
                     '_button setVariable ["ACME_SK_Row", [_kind, _nativeID, _data, _value, _item, _back, _label]]'):
        require(text,fragment)
    for caption in ('Medication','Contents','Vials'): require(text,'"'+caption+'"')
    # A hidden native selector still drives labels and selection, never two visible medication lists.
    assert render(lex(text)).index(render(lex('call ACME_fnc_skMedicationSync'))) < render(lex(text)).index(render(lex('private _metaRows')))


def view_prefix():
    text=source('skSetView')
    start=text.index('private _view = ')
    end=text.index('private _size = ',start)
    return text[start:end]


def visibility_block():
    text=source('skListRefresh')
    start=text.index('    private _visible = ')
    end=text.index('    private _backdropB54',start)
    block=text[start:end]
    block=block.replace('_list ctrlShow false;','_nativeShown=false;')
    block=block.replace('_group ctrlShow _visible;','_groupShown=_visible;')
    return block


@pytest.mark.parametrize('view',['syringe','body','carousel'])
@pytest.mark.parametrize('infusion',[False,True])
@pytest.mark.parametrize('kind',['size','flush','medication'])
def test_actual_view_and_refresh_keep_preparation_sources_off_body_map(view, infusion, kind):
    expected_view='syringe' if infusion else ('body' if view=='carousel' else view)
    expected=expected_view=='syringe' and not (infusion and kind=='flush')
    execute('''private _display=missionNamespace;
        private _groupShown=true; private _nativeShown=true;
    '''+f'uiNamespace setVariable ["ACME_SK_View","{view}"]; _display setVariable ["ACME_SK_Return",{("[1]" if infusion else "[]")}];'+
        adapt(view_prefix())+'private _carousel=_view=="carousel";'+f'private _kind="{kind}";'+adapt(visibility_block())+f'''
        [_view=="{expected_view}","view normalization mismatch"] call _check;
        [_groupShown isEqualTo {str(expected).lower()},"wrong source-group visibility"] call _check;
        [!_nativeShown,"native backing became a second visible list"] call _check;
    ''')


def prep_function():
    text=source('infusionDrawStock')
    substitutions={
        'findDisplay 84000':'_drawDisplay',
        '_display displayCtrl 84006':'_nativeList',
        '_list ctrlShow false;':'_nativeShown=false;',
        'finite _drawn':'(_drawn isEqualType 0)',
        '(_display displayCtrl 84003) ctrlEnable (':'_injectEnabled = (',
    }
    for old,new in substitutions.items():
        assert old in text,old
        text=text.replace(old,new)
    return adapt(text)


@pytest.mark.parametrize('drawn,moving,busy,allowed,enabled,sync',[
    (0,False,False,True,False,True),
    (0.0005,False,False,True,False,True),
    (0.0006,False,False,True,True,False),
    (2,False,False,True,True,False),
    (2,True,False,True,False,False),
    (0,True,False,True,False,False),
    (2,False,True,True,False,False),
    (2,False,False,False,False,False),
    (-1,False,False,True,False,True),
])
def test_prep_stock_refresh_preserves_partial_draw_identity_and_button_gate(drawn,moving,busy,allowed,enabled,sync):
    execute('''
        private _drawDisplay=missionNamespace; private _nativeList=uiNamespace;
        private _nativeShown=true; private _injectEnabled=true;
        private _syncs=0; private _stocks=0; private _tallies=0;
        ACME_fnc_skMedicationSync={_syncs=_syncs+1;};
        ACME_fnc_skMedicationStockRefresh={_stocks=_stocks+1;};
        ACME_fnc_infusionRefreshTally={_tallies=_tallies+1;};
        ACME_infusion_pendingContext=["prepared"];
    '''+f'''
        ACM_circulation_SyringeDraw_DrawnAmount={drawn};
        ACM_circulation_SyringeDraw_Moving={str(moving).lower()};
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        ACME_infusion_allowedMedications={('["Ketamine"]' if allowed else '[]')};
        ACME_infusion_pendingInject="{('pending' if busy else '')}";
    '''+'call {'+prep_function()+'};'+f'''
        [_injectEnabled isEqualTo {str(enabled).lower()},"incorrect inject gate"] call _check;
        [_syncs=={int(sync)},"partial draw selector was rebuilt"] call _check;
        [!_nativeShown && {{_stocks==1}} && {{_tallies==1}},"presentation refresh missing"] call _check;
        [ACM_circulation_SyringeDraw_DrawnAmount=={drawn} && {{ACM_circulation_SyringeDraw_Medication=="Ketamine"}},"refresh changed draw identity/volume"] call _check;
    ''')


def test_rendering_remains_one_custom_group_with_a_hidden_native_selector():
    renderer_contract()
    require(source('infusionDrawStock'),'_list ctrlShow false;')
    require(source('infusionDrawStock'),'[_display] call ACME_fnc_skMedicationStockRefresh;')
    require(source('skUiTick'),'(_d displayCtrl 84006) ctrlShow false;')
    require(source('skSetView'),'(_display displayCtrl 84006) ctrlShow false;')


@pytest.mark.parametrize('old,new',[
    ('[84006,84303,"medication"]','[84006,84304,"medication"]'),
    ('_list ctrlShow false;','_list ctrlShow true;'),
    ('(_x param [1, ""]) == _data','(_x param [0, ""]) == _data'),
])
def test_renderer_contract_rejects_second_selector_or_wrong_identity_with_comment_decoys(old,new):
    text=source('skListRefresh');assert old in text
    with pytest.raises(AssertionError): renderer_contract(text.replace(old,new+' /* '+old+' */'))
