"""Execute stock-column/header blocks with explicit display and vial boundaries.

No rendered pixels, real font metrics, inventory debits or network scheduling are
claimed. Existing row/source and physical-vial execution suites cover those inputs.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, execute
from test_historical_medication_rows import ui_setup, config_code, listbox_code
from test_historical_procedure_trays import controls, ui_code
from test_bounded_medication_presentation import require, renderer_contract, source


def body_after(text, marker, unique=True):
    assert (text.count(marker) == 1 if unique else marker in text), marker
    at = text.index('{', text.index(marker) + len(marker))
    ts = lex(text); pairs = matching(ts)
    start = next(i for i,t in enumerate(ts) if t.offset == at)
    return text[at:ts[pairs[start]].offset + 1]


def presentation_code(text):
    text = re.sub(r'\bsafeZoneH\b', '_screenH', text)
    text = re.sub(r'\bpixelW\b', '_pixelW', text)
    text = re.sub(r'\bctrlPosition (_\w+)', r'([\1] call _position)', text)
    text = re.sub(r'\bctrlTextWidth (_\w+)', '_measuredWidth', text)
    # Font operations are recorded, not measured by an Arma renderer.
    text = re.sub(r'(_\w+) ctrlSetFontHeight ([^;]+);', r'[_dummyFont, "font", \2] call _controlWrite;', text)
    text = re.sub(r'(_\w+) ctrlSetFont "[^"]+";', '', text)
    text = re.sub(r'_d ctrlCreate (\[[^;]+\])', r'(\1 call _create)', text)
    return ui_code(text)


def presentation_setup():
    return controls() + '''
        private _screenH=1; private _uiW=1; private _pixelW=0.001;
        private _dummyFont=999; private _measuredWidth=0.3;
        private _d=missionNamespace; private _group=uiNamespace;
        private _created=[];
        private _create={_created pushBack _this; 9000 + count _created};
        private _position={
            params ["_c"];
            private _key=(str _c)+":ctrlSetPosition";
            if (_key in _controlValues) exitWith {+(_controlValues get _key)};
            if (_c isEqualTo _group) exitWith {[0.2,0.4,0.4,0.5]};
            [0.2,0.3,0.2,0.1]
        };
    '''


def header_code():
    text = source('skListRefresh')
    marker = 'private _header = _group getVariable'
    start = text.rfind('if (_kind == "medication") then', 0, text.index(marker))
    return body_after(text[start:], 'if (_kind == "medication") then', unique=False)


def header_contract(text=None):
    text = source('skListRefresh') if text is None else text
    for fragment in ('private _header = _group getVariable ["ACME_SK_ColumnHeader", []];',
                     'if (_header isEqualTo []) then',
                     '_group setVariable ["ACME_SK_ColumnHeader", _header];',
                     'forEach [84007,84008]',
                     '[1,"Medication",_uiW / 420,_stockX - _uiW / 210]',
                     '[2,"Contents",_stockX,_contentsW]', '[3,"Vials",_countX,_countW]',
                     '{_x ctrlShow _visible; _x ctrlCommit 0;} forEach _header;'):
        require(text, fragment)


def split_column_contract(text=None):
    text = source('skListRefresh') if text is None else text
    for fragment in ('_stock ctrlSetText _stockLabel;', '_countText ctrlSetText _countLabel;',
                     '_stock ctrlSetPosition [_stockX, _cursorY, _contentsW, _rowH];',
                     '_countText ctrlSetPosition [_countX, _cursorY, _countW, _rowH];',
                     '_d ctrlCreate ["ACME_SK_RightText", -1, _group]',
                     '[_kind, _nativeID, _data, _value, _back, _visible, _text1, _text2, _stock, _countText]'):
        require(text, fragment)


def tick_contract(text=None):
    text = source('skUiTick') if text is None else text
    for fragment in ('if (_kind == "medication" && {_selected} && {!isNull _stock}) then',
                     '["preview", _data, _reserved, _d] call ACME_fnc_vialSession;',
                     '_stock ctrlSetText format ["%1 mL", _curMl toFixed 2];',
                     'if (!isNull _countText) then {_countText ctrlSetText ("x" + _cnt);};',
                     '[_d] call ACME_fnc_skMedicationStockRefresh;'):
        require(text, fragment)


@pytest.mark.parametrize('height', [0.8, 1, 1.4])
@pytest.mark.parametrize('visible', [False, True])
def test_headers_are_created_once_and_source_captions_only_move_once(height, visible):
    execute(presentation_setup() + f'''_screenH={height}; private _visible={str(visible).lower()};
        private _innerW=0.4; private _stockX=0.28; private _contentsW=0.06;
        private _countX=0.35; private _countW=0.04;
        private _headerPass=''' + presentation_code(header_code()) + ''';
        for "_pass" from 1 to 3 do {call _headerPass;};
        [count _created==4,"header duplicated on refresh"] call _check;
        private _shifts=_uiWrites select {(_x select 0) in [84007,84008] && {(_x select 1)=="ctrlSetPosition"}};
        [count _shifts==2,"inventory captions shifted repeatedly"] call _check;
        { [abs (((_x select 2) select 1) - (0.3 - _screenH/32)) < 0.00001,"caption shift amount changed"] call _check; } forEach _shifts;
        [(_controlValues get "9002:ctrlSetText")=="Medication","name header missing"] call _check;
        [(_controlValues get "9003:ctrlSetText")=="Contents","contents header missing"] call _check;
        [(_controlValues get "9004:ctrlSetText")=="Vials","count header missing"] call _check;
        { [(_controlValues get ((str _x)+":ctrlShow")) isEqualTo _visible,"header visibility disagrees"] call _check; } forEach [9001,9002,9003,9004];
        [(_uiWrites findIf {(_x select 0) isEqualTo _group && {(_x select 1)=="ctrlSetPosition"}})<0,"header resized scrolling group"] call _check;
    ''')


@pytest.mark.parametrize('stage,reserved', [('',1.5), ('compound',3.5), ('draw',3.5), ('waste',0)])
@pytest.mark.parametrize('selected,count_control', [(True,True),(False,True),(True,False)])
def test_selected_row_refresh_keeps_contents_count_and_reserved_amount_separate(stage,reserved,selected,count_control):
    text=source('skUiTick')
    marker='if (_kind == "medication" && {_selected} && {!isNull _stock}) then'
    block=marker+body_after(text, marker)+';'
    execute(presentation_setup() + f'''
        private _kind="medication"; private _selected={str(selected).lower()};
        private _stock=601; private _countText={602 if count_control else 'objNull'};
        private _data="Ketamine"; private _stage="{stage}"; private _calls=[];
        ACM_circulation_SyringeDraw_DrawnAmount=1.5;
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        uiNamespace setVariable ["ACME_SK_CompoundComponents",[["Ketamine",1],["Other",9],["Ketamine",1.5]]];
        uiNamespace setVariable ["ACME_SK_WasteFill",6];
        uiNamespace setVariable ["ACME_SK_WasteFloorMl",5];
        ACME_fnc_vialHolder={{_medic}};
        ACME_fnc_vialSession={{_calls pushBack _this; [1.25,2,11.25,0]}};
    '''+presentation_code(block)+f'''
        [count _calls=={int(selected)},"nonselected row refreshed as selected"] call _check;
        [ACM_circulation_SyringeDraw_DrawnAmount==1.5 && {{ACM_circulation_SyringeDraw_Medication=="Ketamine"}},"refresh changed solution"] call _check;
    ''' + (f'''
        [_calls isEqualTo [["preview","Ketamine",{reserved},_d]],"reservation or physical preview route changed"] call _check;
        [(_controlValues get "601:ctrlSetText")=="1.25 mL","contents not independent"] call _check;
    ''' + ('[(_controlValues get "602:ctrlSetText")=="x02","count not independent"] call _check;' if count_control else '[!("602:ctrlSetText" in _controlValues),"missing count control used"] call _check;') if selected else '[count _uiWrites==0,"unselected row repainted"] call _check;'))


@pytest.mark.parametrize('bound', [False,True])
@pytest.mark.parametrize('amount,vials', [(0,0),(0.25,1),(4,2),(4,12)])
def test_stock_info_formats_two_columns_without_mutating_bound_or_open_stock(bound,amount,vials):
    body=body_after(source('skListRefresh'),'private _fnStockInfo = ')
    total=amount if vials<2 else amount+10*(vials-1)
    execute(ui_setup()+f'''
        private _holder=_medic; private _calls=[];
        private _preview=[{vials},{amount},0,{total}];
        ACME_fnc_vialPreview={{_calls pushBack ["open",_this]; _preview}};
        ACME_fnc_vialSession={{_calls pushBack ["bound",_this]; [{amount},{vials},{total},0]}};
        ACME_fnc_vialItemCount={{0}}; ACME_fnc_vialCapacity={{10}};
        _d setVariable ["ACME_SK_VialSessions",createHashMapFromArray {('[['+chr(34)+'Ketamine'+chr(34)+',[1]]]') if bound else '[]'}];
        private _before=+(_d getVariable "ACME_SK_VialSessions");
        private _stock='''+config_code(body)+f''';
        private _result=["Ketamine",1.5,"ACM_Vial_Ketamine"] call _stock;
        [_result isEqualTo ["{amount:.2f} mL",{vials},{amount},{total},"x{vials:02d}"],"stock column formatting changed"] call _check;
        [(_calls select 0) select 0=="{'bound' if bound else 'open'}","wrong stock source"] call _check;
        [(_d getVariable "ACME_SK_VialSessions") isEqualTo _before,"preview mutated bound source"] call _check;
    ''')


def test_missing_holder_has_zero_stock_not_a_stale_count():
    body=body_after(source('skListRefresh'),'private _fnStockInfo = ')
    execute(ui_setup()+'private _holder=objNull; private _stock='+config_code(body)+''';
        [(["Ketamine",1,"ACM_Vial_Ketamine"] call _stock) isEqualTo ["0.00 mL",0,0,0,"x00"],"missing holder inherited stock"] call _check;
    ''')


def test_preparation_hides_only_existing_flush_sources_and_keeps_tally_wiring():
    text=source('patchDrawDialog')
    start=text.index('// Flushes cannot be used while preparing a bag;')
    end=text.index('private _sizeRect',start)
    execute(controls()+'private _display=missionNamespace;'+ui_code(text[start:end])+'''
        [(_uiWrites select {(_x select 1)=="ctrlShow"}) isEqualTo [[84131,"ctrlShow",false],[84132,"ctrlShow",false],[84301,"ctrlShow",false]],"wrong prep sources hidden"] call _check;
        [(_uiWrites select {(_x select 1)=="ctrlEnable"}) isEqualTo [[84131,"ctrlEnable",false],[84132,"ctrlEnable",false],[84301,"ctrlEnable",false]],"hidden source still enabled"] call _check;
    ''')
    for fragment in ('["RscControlsGroup",84362]', '["RscStructuredText",84361,_tallyGroup]',
                     '_tallyHdr ctrlSetText "Pushed into bag";', '[] call ACME_fnc_infusionRefreshTally;'):
        require(text,fragment)


@pytest.mark.parametrize('contract,name,old,new',[
    (header_contract,'skListRefresh','if (_header isEqualTo []) then','if (true) then'),
    (split_column_contract,'skListRefresh','_countText ctrlSetText _countLabel;','_stock ctrlSetText _countLabel;'),
    (tick_contract,'skUiTick','_countText ctrlSetText ("x" + _cnt);','_stock ctrlSetText ("x" + _cnt);'),
    (tick_contract,'skUiTick','["preview", _data, _reserved, _d]','["select", _data, _reserved, _d]'),
])
def test_contracts_reject_duplicate_headers_wrong_column_and_mutating_preview(contract,name,old,new):
    text=source(name); assert old in text
    with pytest.raises(AssertionError): contract(text.replace(old,new+' /* '+old+' */'))
