"""Execute physical tubing attachment and tray rendering with native UI boundaries mocked."""
import json
import re

import pytest

from source_scan import lex, matching
from test_b232_iv_finish import SETUP, START_SETUP, rules
from test_b234_field_iv import ui_source
from test_b289_iv_supplies import fixture
from test_bounded_selector_lifetime import ui_commands
from test_menu_death_lifecycle import ROOT, execute, read


ASSEMBLIES = [
    [False, False, False, False],
    [True, False, False, False],
    [True, True, True, False],
    [False, False, False, False, True, 0],
    [False, False, False, False, True, 14, True],
    [True, False, False, False, True, 16, True],
]


def sqf(value):
    return json.dumps(value).lower()


@pytest.mark.parametrize("state", ASSEMBLIES)
@pytest.mark.parametrize("compromised", [False, True])
def test_real_tubing_transaction_accepts_all_ports_without_certifying_patency_or_opening_flow(state, compromised):
    execute(fixture("line") + f'''
        _row set [15,{sqf(state)}];_patient setVariable ["ACME_IV_Marks",[_row]];
        _patient setVariable ["ACME_ivCompromised_leftarm_1",{sqf(compromised)}];
        private _bags=createHashMapFromArray [["leftarm",[["Saline",500,0,1,true,16,false,0,"closed-primary"]]]];
        _patient setVariable ["ACM_circulation_IV_Bags",_bags];
        private _before=str _bags;
        _medic setVariable ["fixtureStock",[_item]];
        call _start;call _beginRequest;call _ack;
        _serverTime=102;call _finishRequest;call _finishRequest;call _ack;
        private _expected={sqf(state)};_expected set [3,true];
        [(call _getState) isEqualTo _expected,"tubing changed aspiration, dressing or upstream hardware"] call _check;
        [count _debits==1 && {{count _refunds==0}},"one physical administration line was not consumed"] call _check;
        [(_patient getVariable ["ACME_ivCompromised_leftarm_1",false])=={sqf(compromised)},"attachment repaired a compromised site"] call _check;
        [str (_patient getVariable "ACM_circulation_IV_Bags")==_before,"attachment changed existing bag or clamp state"] call _check;
        [count (call _credits)==0,"attachment fabricated a saline flush"] call _check;
        [((call _getRow) param [17,""])!="","installed line has no stable identity"] call _check;
    ''')


@pytest.mark.parametrize("state", ASSEMBLIES)
@pytest.mark.parametrize("angle", [-15, 0, 15, 165])
@pytest.mark.parametrize("aspect", [0.5625, 0.28125])
def test_click_preview_and_direct_tube_art_share_the_actual_port(state, angle, aspect):
    execute(SETUP + rules() + START_SETUP + f'''
        _testPixelW={aspect};_testPixelH=1;_row set [13,{angle}];_row set [15,{sqf(state)}];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        private _state=_row select 15;private _lock=_state param [4,false];
        private _extension=_state select 0;
        private _point=if (_lock) then {{[_row,[_row] call ACME_fnc_ivFieldPort] call ACME_fnc_ivFieldPoint}} else {{
            if (_extension) then {{[_row,[1033.02/2048,1386.52/2048],[1006.5/2048,1052/2048]] call ACME_fnc_ivFinishPoint}}
            else {{private _g=[_row] call ACME_fnc_ivFinishGeometry;[_g select 0,_g select 1]}}
        }};
        private _hit=[_point select 0,_point select 1,"line",false,true] call ACME_fnc_ivFinishTarget;
        [count _hit==3 && {{((_hit select 0) select 14)==(_row select 14)}},"real socket is not clickable"] call _check;
        [(_hit select 2) isEqualTo _point,"magnet target differs from the active port"] call _check;
        private _paintRow=[_row,!_extension] call ACME_fnc_ivFieldAccessoryRow;
        private _shown=[_paintRow,[1033.02/2048,1386.52/2048],[1006.5/2048,1052/2048]] call ACME_fnc_ivFinishPoint;
        [abs ((_shown select 0)-(_point select 0))<0.00001 && {{abs ((_shown select 1)-(_point select 1))<0.00001}},"tube sprite is not seated at clicked port"] call _check;
    ''')


@pytest.mark.parametrize("extension", [False, True])
@pytest.mark.parametrize("active", [False, True])
def test_regular_tubing_renderer_does_not_invent_an_extension(extension, active):
    execute(SETUP + rules() + START_SETUP + 'ACME_fnc_ivFinishTick={' + ui_source('ivFinishTick') + '};' + f'''
        private _writes=[];private _write={{_writes pushBack _this;}};private _poses=[];
        ACME_fnc_ivFinishPose={{_poses pushBack _this;}};
        _row set [15,[{sqf(extension)},false,false,{sqf(not active)}]];
        _row set [16,{ '["job",_medic,"line",99.5,1,"iv_line_attach",130]' if active else '[]' }];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        _d setVariable ["ACME_IV_FinishCtrls",[["ivhub:7:1",_d,objNull]]];
        [] call ACME_fnc_ivFinishTick;
        private _texts=_writes select {{(_x select 1)=="ctrlSetText" && {{(_x select 0) isEqualTo _d}}}};
        [count _texts==1,"accessory renderer did not paint one layer"] call _check;
        private _texture=(_texts select 0) select 2;
    ''' + (
        '[(_texture find "cursor_line_ca.paa")>=0,"bare catheter was painted with a phantom extension"] call _check;'
        if not extension else
        '[(_texture find "cursor_line_ca.paa")<0,"existing extension was lost from connected or animated tubing"] call _check;'
    ))


@pytest.mark.parametrize("extension", [False, True])
@pytest.mark.parametrize("angle", [-15, 0, 15])
def test_tube_removal_target_follows_the_tube_after_direct_attachment(extension, angle):
    execute(SETUP + rules() + START_SETUP + f'''
        _row set [13,{angle}];_row set [15,[{sqf(extension)},false,false,true]];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        private _paintRow=[_row,{sqf(not extension)}] call ACME_fnc_ivFieldAccessoryRow;
        private _point=[_paintRow,[1100/2048,1720/2048],[1006.5/2048,1052/2048]] call ACME_fnc_ivFinishPoint;
        private _hit=[_point select 0,_point select 1,"",true] call ACME_fnc_ivFinishTarget;
        [count _hit==3 && {{(_hit select 1)=="removeLine"}},"tube pull target drifted away from visible tubing"] call _check;
    ''')


def test_all_iv_tray_labels_share_one_native_typography_and_no_runtime_size_override():
    cpp=(ROOT/'addons/acm_extended/config.cpp').read_text()
    tokens=lex(cpp);pairs=matching(tokens)
    def native_class(name):
        start=next(i for i,t in enumerate(tokens[:-1]) if t.value=='class' and tokens[i+1].value==name)
        brace=next(i for i in range(start,len(tokens)) if tokens[i].value=='{')
        return cpp[tokens[brace].offset:tokens[pairs[brace]].offset+1]
    label=native_class('ACME_IV_ToolLabel')
    assert 'font="RobotoCondensed"' in label
    assert 'sizeEx="0.018 * safezoneH"' in label
    assert 'style=2' in label
    for name in ('IV_BandLbl','IV_PadLbl','IV_G14Lbl'):
        assert f'class {name}: ACME_IV_ToolLabel' in cpp
    assert 'ctrlSetFontHeight' not in read('ivFinishTray')
    assert 'ctrlCreate ["ACME_IV_ToolLabel"' in read('ivFinishTray')
    for name in ('ACME_IV_ToolButton','IV_BandSlotClick','IV_PadClick','IV_G14Click'):
        button=native_class(name)
        assert 'soundClick[]={"",0,1}' in button
        assert 'soundPush[]={"",0,1}' in button


def test_finishing_labels_read_real_stock_and_match_existing_count_spacing_and_empty_alpha():
    source=read('ivMinigameRefreshBandSlot')
    block=source[source.rindex('{\n    _x params ["_tool","_pic","_label","_button"];'):]
    execute(ui_commands('''
        private _dlg=missionNamespace;private _writes=[];private _write={_writes pushBack _this;};
        private _slots=[];ACME_fnc_traySlotState={_slots pushBack _this;};
        private _held="none";
        private _stock=createHashMapFromArray [["ACME_IVExtension",2],["ACME_Tegaderm",0],["ACME_IVLine",3],["ACME_SalineLock",4],["ACM_SalineFlush_10",5]];
        private _count={_stock get (_this select 0)};
        _dlg setVariable ["ACME_IV_FinishTray",[["extension",10,11,12],["dressing",20,21,22],["line",30,31,32],["lock",40,41,42],["flush",50,51,52]]];
    ''' + block) + '''
        private _texts=(_writes select {(_x select 1)=="ctrlSetText"}) apply {_x select 2};
        [_texts isEqualTo ["EXTENSION  x2","TEGADERM  x0","IV TUBING  x3","SALINE LOCK  x4","10 mL FLUSH  x5"],"labels do not match stock or existing tray formatting"] call _check;
        private _colors=(_writes select {(_x select 1)=="ctrlSetTextColor"}) apply {(_x select 2) select 3};
        [_colors isEqualTo [1,0.3,1,1,1],"empty stock labels are not dimmed consistently"] call _check;
        [(_slots apply {_x select 2}) isEqualTo [2,0,3,4,5],"tool silhouettes have fictional stock"] call _check;
    ''')
