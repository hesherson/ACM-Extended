"""Single readable overlay, with SQF layout and explicit engine UI metric fixtures."""
import re

import pytest

from test_menu_death_lifecycle import ROOT, execute, read
from test_historical_core_boundaries import block_at


def definition(name):
    text = read("debugMenuClinical")
    start = text.index(f"private {name} = {{")
    opening = text.index("{", start)
    return text[start:opening] + block_at(text, opening) + ";"


def test_one_overlay_toggle_and_no_page_registration():
    pre = (ROOT / "addons/acm_extended/XEH_preInit.sqf").read_text()
    names = re.findall(r'"(ACME_debug_\w+)"\s*,\s*"(?:CHECKBOX|SLIDER|LIST)"', pre)
    assert names == ["ACME_debug_enabled"]
    assert 'if (!isNil "ACME_fnc_debugMenu") then {call ACME_fnc_debugMenu};' in pre
    assert "registerDebugPageKeybindRuntime" not in read("postInit")
    assert "CBA_fnc_addKeybind" not in read("registerDebugPageKeybindRuntime")
    for name in ("debugMenu", "debugMenuClinical", "debugMenuCore", "debugMenuNetwork"):
        assert "ACME_debug_page" not in read(name)


def test_all_legacy_entrypoints_reach_the_same_overlay_once():
    setup = 'private _draws=0;ACME_fnc_debugMenuClinical={_draws=_draws+1;};'
    for name in ("debugMenu", "debugMenuCore", "debugMenuNetwork"):
        setup += "call {" + read(name) + "};"
    execute(setup + '[_draws==3,"legacy entrypoint opened another renderer or duplicated draw"] call _check;')


@pytest.mark.parametrize("metric_height", [0.04, 0.22, 0.77])
def test_measurement_uses_wrapped_content_height_without_changing_font(metric_height):
    source = definition("_measureRows")
    source = source.replace('_ctrlM ctrlSetPosition [_x, _y, _width, safeZoneH * 4];', '_positions pushBack _width;')
    source = source.replace('_ctrlM ctrlCommit 0;', '')
    source = source.replace('ctrlTextHeight _ctrlM', '_metricH')
    execute(f'private _metricH={metric_height};private _fontH=0.018;private _ctrlM="measure";private _positions=[];private _draws=[];' +
        'private _renderBlock={_draws pushBack _this;};' + source + '''
        private _height=[["Patient: Long Complete Patient Name"],0.34] call _measureRows;
        [_positions isEqualTo [0.34],"measurement did not use actual wrapping width"] call _check;
        [abs (_height-_metricH-0.0045)<0.00001,"content height replaced by fixed allocation"] call _check;
        [_fontH==0.018 && {count (_draws select 0)==2},"measurement reduced readable font"] call _check;
        [((_draws select 0) select 1) isEqualTo ["Patient: Long Complete Patient Name"],"measurement lost text"] call _check;
    ''')


def test_common_base_font_is_safezone_relative_and_uniform_across_resolutions():
    source = read("debugMenuClinical")
    assert 'private _fontH = safeZoneH * 0.0096;' in source
    assert 'pixelH' not in source
    assert '{_x ctrlSetFontHeight _fontH;} forEach [_ctrlH, _ctrlT, _ctrlL, _ctrlR, _ctrlS, _ctrlM];' in source
    assert 'safeZoneWAbs * 0.235' in source
    assert "size='" not in source
    assert '_measureBlock' not in source and '_fit' not in source


def test_section_color_spacing_and_values_survive_shared_formatting():
    source = ''.join(definition(n) for n in ("_safe", "_padRight", "_alignValue", "_pair", "_wrapValue", "_formatRow", "_sect"))
    execute('private _cTitle="#D9A441";private _cSect=_cTitle;private _cLabel="label";' + source + '''
        private _section=["PERFUSION / BLEEDING"] call _sect;
        [(_section find "<br/>")==-1,"compact section inserted a blank spacer"] call _check;
        [(_section find _cTitle)>0,"section title color differs from main title"] call _check;
        private _row=[["HR",103,"good","BP","120/80","good"] call _pair,12] call _formatRow;
        [(_row find "103")>=0 && {(_row find "120/80")>=0},"paired value changed"] call _check;
        private _safeName=["Patient <One> & Two"] call _safe;
        [_safeName=="Patient &lt;One&gt; &amp; Two","patient name broke structured text"] call _check;
    ''')


def test_enabled_overlay_reuses_controls_and_restores_transparency():
    source = definition("_control")
    # Namespace-backed fake controls retain the original lifetime branch logic. Arma UI calls are boundaries.
    source = source.replace("controlNull", '"NONE"')
    source = source.replace("isNull _c", '(_c isEqualTo "NONE")')
    source = source.replace("ctrlParent _c", '(_parents getVariable _c)')
    source = source.replace("ctrlDelete _c;", "_deleted pushBack _c;")
    source = source.replace('_display ctrlCreate ["RscStructuredText", -1]',
                            'call {_created=_created+1;private _id=format ["control%1",_created];_parents setVariable [_id,_display];_id}')
    source = source.replace('_c ctrlSetBackgroundColor [0, 0, 0, 0];', '_backgrounds pushBack [_c,[0,0,0,0]];')
    source = source.replace('_c ctrlShow _visible;', '_visibility pushBack [_c,_visible];')
    execute('private _display="mission";private _parents=profileNamespace;private _created=0;private _deleted=[];private _backgrounds=[];private _visibility=[];' +
        source + '''
        private _first=["testControl"] call _control;
        private _again=["testControl"] call _control;
        [_first==_again && {_created==1},"repeated tick duplicated overlay"] call _check;
        [count _backgrounds==2 && {(_backgrounds select 1) select 1 isEqualTo [0,0,0,0]},"existing dark panel was not made transparent"] call _check;
        _display="replacement";
        private _next=["testControl",false] call _control;
        [_next!=_first && {_created==2} && {_deleted isEqualTo [_first]},"display switch leaked old control"] call _check;
        [(_visibility select 2) isEqualTo [_next,false],"measurement control became visible"] call _check;
    ''')


def test_disabling_cleans_up_backing_header_all_sections_and_hidden_measurement():
    source = definition("_cleanup").replace("controlNull", '"NONE"')
    source = source.replace("isNull _c", '(_c isEqualTo "NONE")').replace("ctrlDelete _c;", "_deleted pushBack _c;")
    execute('private _deleted=[];' + source + '''
        private _names=["ACME_DebugMenuBackdrop","ACME_DebugMenuCtrl","ACME_DebugMenuCtrlTop","ACME_DebugMenuCtrlL","ACME_DebugMenuCtrlR","ACME_DebugMenuCtrlS","ACME_DebugMenuCtrlMeasure"];
        {uiNamespace setVariable [_x,_x];} forEach _names;
        call _cleanup;
        [_deleted isEqualTo _names,"disabled overlay left visible or hidden controls"] call _check;
        {[(uiNamespace getVariable _x)=="NONE","control handle survived cleanup"] call _check;} forEach _names;
    ''')


@pytest.mark.parametrize("header,body", [
    (0.025,0.38),
    (0.035,0.62),
    (0.020,0.24),
])
def test_layout_is_content_driven_single_column_without_screen_filling_gap(header, body):
    source=definition("_layout")
    source=re.sub(r'(_ctrl\\w+) ctrlSetPosition (\\[[^;]+\\]);', r'_positions pushBack [\\1,\\2];',source)
    source=source.replace('{_x ctrlShow false;} forEach [_ctrlT, _ctrlR, _ctrlS];','_hidden append [_ctrlT,_ctrlR,_ctrlS];')
    source=source.replace('{_x ctrlCommit 0;} forEach [_ctrlB, _ctrlH, _ctrlL, _ctrlT, _ctrlR, _ctrlS];','')
    execute('''
        private _ctrlB="back";private _ctrlH="head";private _ctrlT="top";private _ctrlL="body";private _ctrlR="right";private _ctrlS="net";
        private _positions=[];private _hidden=[];private _x=-1;private _y=-0.16;
        private _totalW=0.21;private _gap=0.0025;private _fontH=0.0096;
    '''+source+f'[{header},{body}] call _layout;'+'''
        [count _positions==3,"compact layout created extra visible regions"] call _check;
        private _back=(_positions select 0) select 1;
        private _head=(_positions select 1) select 1;
        private _body=(_positions select 2) select 1;
        [abs ((_body select 0)-(_back select 0))<0.00001 && {abs ((_body select 2)-(_back select 2))<0.00001},"body is not one full-width column"] call _check;
        [abs ((_body select 1)-(_head select 1)-(_head select 3)-0.0025)<0.00001,"body is not directly beneath header"] call _check;
        [abs ((_back select 3)-(_head select 3)-0.0025-(_body select 3)-0.00192)<0.00001,"backing contains unused vertical space"] call _check;
        [_hidden isEqualTo ["top","right","net"],"B162 secondary columns were not retired"] call _check;
    ''')


def test_original_navy_backing_is_created_below_all_text_and_ignores_mouse_input():
    source = read("debugMenuClinical")
    assert source.index('private _ctrlB =') < source.index('private _ctrlH =')
    assert '_ctrlB ctrlSetBackgroundColor [0.043, 0.082, 0.188, 0.74];' in source
    assert '_ctrlB ctrlEnable false;' in source
    # Introducing the backing to a running old overlay must first remove its existing text controls.
    before = source[:source.index('private _control =')]
    assert 'if (isNull _backdrop || {!((ctrlParent _backdrop) isEqualTo _display)}) then {call _cleanup;};' in before


def test_original_number_and_state_anchors_preserve_digits_decimals_units_and_full_text():
    source = definition('_padRight') + definition('_alignValue')
    execute(source + '''
        private _hr=[103] call _alignValue;
        private _map=[75] call _alignValue;
        private _temp=["37.5 C"] call _alignValue;
        private _negative=["-0.42"] call _alignValue;
        private _bleed=["1200 mL/min"] call _alignValue;
        [(_hr find "3")==7 && {(_map find "5")==7},"original integer ones anchor changed"] call _check;
        [(_temp find ".")==8 && {(_negative find ".")==8},"original decimal anchor changed"] call _check;
        [count _hr==12 && {count _temp==12} && {count _bleed==12},"original minimum value width changed"] call _check;
        {
            private _aligned=[_x] call _alignValue;
            [(_aligned find _x)+(count _x)==8,"text state does not end at original value anchor"] call _check;
        } forEach ["yes","no","none","OPEN","awake","client","host","n/a","120/80","99%"];
        [(_temp find "37.5 C")>=0 && {(_bleed find "1200 mL/min")>=0},"units or numbers were truncated"] call _check;
        private _long=["CONDITION VALUE LONGER THAN TWELVE"] call _alignValue;
        [_long=="CONDITION VALUE LONGER THAN TWELVE","long state text lost data"] call _check;
    ''')


@pytest.mark.parametrize("value", [
    "7.3 L/min", "0 mL/min", "1200 mL/min", "37.0 C", "6.00L",
    "0 / 0.00L", "1.00 / 0.00", "1.00 / -1.00", "-0.42",
    "BVM:- V:-", "BVM:Y V:Y", "OBSTRUCTED", "ETT+cuff", "OPA+NPA",
    "postictal", "C0 V0 B0", "Z3+Ing-left+AxL+AxR",
])
def test_normal_readings_stay_complete_on_one_row_with_fixed_label_positions(value):
    source=''.join(definition(n) for n in ('_safe','_padRight','_alignValue','_wrapValue','_formatRow'))
    # Use the actual renderer's width, not an independently chosen test width.
    width=re.search(r'private _valueW = (\d+);',read('debugMenuClinical'))[1]
    execute('private _cLabel="label";' + source + f'private _value="{value}";private _valueW={width};' + '''
        private _row=[["Reading",_value,"good","Other",0,"good"],_valueW] call _formatRow;
        private _baseline=[["Reading",0,"good","Other",0,"good"],_valueW] call _formatRow;
        [(_row find "<br/>")==-1,"ordinary reading split onto another line"] call _check;
        [(_row find _value)>=0,"reading or unit was split/truncated"] call _check;
        [(_row find "Other")==(_baseline find "Other"),"reading moved the next label"] call _check;
    ''')


def test_extended_device_lists_wrap_without_reintroducing_a_second_major_column():
    source=''.join(definition(n) for n in ('_safe','_padRight','_alignValue','_wrapValue','_pair','_one','_formatRow','_renderAll'))
    execute('''
        private _cLabel="label";private _valueW=14;private _fontH=0.018;
        private _totalW=0.21;
        private _ctrlH="head";private _ctrlL="body";
        private _renders=[];private _sizes=[];private _heights=[];
        private _measureRows={_heights pushBack _this;[0.025,0.58] select ((count _heights)-1)};
        private _layout={_sizes=+_this;};
        private _renderBlock={_renders pushBack _this;};
    '''+source+'''
        private _header=["ACME DEBUG B163 | Patient: Complete Long Name"];
        private _top=[["Role","client","good","MP","yes","good"] call _pair];
        private _left=[["HR",103,"good","BP","120/80","good"] call _pair];
        private _right=[["AAJT","Z3+Ing-left+AxL+AxR+additional device","good","XStat","no","good"] call _pair];
        private _network=[["Chest/Own","S1/E1","good","Revision","NA2-1.2.3-stable","good"] call _pair];
        call _renderAll;
        [count _renders==2 && {count _heights==2},"compact renderer still painted multiple major columns"] call _check;
        [_sizes isEqualTo [0.025,0.58],"content-driven layout did not receive one combined body height"] call _check;
        private _rows=(_renders select 1) select 1;
        [count _rows==4,"logical sections were lost while serializing the single column"] call _check;
        private _long=_rows select 2;
        [(_long find "<br/>")>=0,"long device list did not wrap inside narrow panel"] call _check;
        private _parts=["Z3+Ing-left+AxL+AxR+additional device",14] call _wrapValue;
        [(_parts joinString "")=="Z3+Ing-left+AxL+AxR+additional device","wrapping dropped device text"] call _check;
        {[(count _x)<=14,"continuation overruns compact field"] call _check;} forEach _parts;
    ''')

