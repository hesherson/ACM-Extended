"""Single narrow overlay, with SQF fitting and explicit engine UI metric fixtures."""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read
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


@pytest.mark.parametrize("width,height", [(0.2, 0.3), (1.8, 0.3), (0.2, 2.0), (1.8, 2.0)])
def test_actual_text_fit_preserves_rows_and_respects_both_available_dimensions(width, height):
    source = definition("_measureBlock")
    source = source.replace('_ctrlM ctrlSetStructuredText parseText format [_template, _size, _body];',
                            '_measured pushBack (format [_template, _size, _body]);')
    source = source.replace('_ctrlM ctrlSetStructuredText parseText format [_template, _size, _x];',
                            '_measured pushBack (format [_template, _size, _x]);')
    source = source.replace("ctrlTextWidth _ctrlM", "_metricW").replace("ctrlTextHeight _ctrlM", "_metricH")
    execute(f'private _metricW={width};private _metricH={height};private _measured=[];private _rendered=[];' +
        source + '''
        private _fit=[["ACME DEBUG v1.2.3 | B154", "Patient: Long Complete Patient Name"], 0.62, 0.34, 1] call _measureBlock;
        [count _measured==3,"each row and full height were not measured before render"] call _check;
        private _body=_measured select 2;
        [_fit>0 && {_fit<=0.62},"fit grew or invalidated font size"] call _check;
        [(_metricW*_fit/0.62)<=0.320001,"width fit would wrap"] call _check;
        [(_metricH*_fit/0.62)<=0.980001,"height fit would clip"] call _check;
        [(_body find "ACME DEBUG v1.2.3 | B154")>=0,"title/build was truncated"] call _check;
        [(_body find "Patient: Long Complete Patient Name")>=0,"patient name was truncated"] call _check;
    ''')


def test_section_color_spacing_and_values_survive_shared_formatting():
    source = ''.join(definition(n) for n in ("_safe", "_padRight", "_alignValue", "_pair", "_formatRow", "_sect"))
    execute('private _cTitle="#D9A441";private _cSect=_cTitle;private _cLabel="label";' + source + '''
        private _section=["PERFUSION / BLEEDING"] call _sect;
        [(_section find "<br/>")==0,"missing space before section"] call _check;
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
        private _names=["ACME_DebugMenuBackdrop","ACME_DebugMenuCtrl","ACME_DebugMenuCtrlL","ACME_DebugMenuCtrlR","ACME_DebugMenuCtrlS","ACME_DebugMenuCtrlMeasure"];
        {uiNamespace setVariable [_x,_x];} forEach _names;
        call _cleanup;
        [_deleted isEqualTo _names,"disabled overlay left visible or hidden controls"] call _check;
        {[(uiNamespace getVariable _x)=="NONE","control handle survived cleanup"] call _check;} forEach _names;
    ''')


@pytest.mark.parametrize("screen_width,screen_height", [(2.37, 1.33), (4.74, 1.33), (0.50, 0.80)])
def test_narrow_overlay_has_two_columns_and_network_below_within_one_panel(screen_width, screen_height):
    source = read("debugMenuClinical")
    start = source.index("private _gap =")
    end = source.index("// A hidden, wide control", start)
    geometry = source[start:end]
    geometry = geometry.replace("safeZoneWAbs", str(screen_width)).replace("safeZoneH", str(screen_height))
    geometry = geometry.replace("safeZoneXAbs", "-1").replace("safeZoneY", "-0.16")
    geometry = re.sub(r'(_ctrl\w+) ctrlSetPosition (\[[^;]+\]);', r'_positions pushBack [\1,\2];', geometry)
    execute('private _ctrlB="back";private _ctrlH="header";private _ctrlL="left";private _ctrlR="right";private _ctrlS="network";private _positions=[];' + geometry + '''
        [_totalW<=0.54 && {_totalW>0.42},"overlay is not just slightly wider than original"] call _check;
        [count _positions==5,"wrong number of visible layout regions"] call _check;
        private _back=(_positions select 0) select 1;
        private _left=(_positions select 2) select 1;
        private _right=(_positions select 3) select 1;
        private _network=(_positions select 4) select 1;
        [(_network select 0)==(_back select 0) && {(_network select 2)==(_back select 2)},"network did not use full panel width"] call _check;
        [(_network select 1)>(_left select 1)+(_left select 3),"network overlaps clinical columns"] call _check;
        [abs (((_right select 0)+(_right select 2))-((_back select 0)+(_back select 2)))<0.00001,"columns extend past backing"] call _check;
        [abs (((_network select 1)+(_network select 3))-((_back select 1)+(_back select 3)))<0.00001,"backing does not cover entire overlay"] call _check;
        [(_left select 3)>0 && {(_network select 3)>0},"section has no room to render"] call _check;
    ''')


def test_original_navy_backing_is_created_below_all_text_and_ignores_mouse_input():
    source = read("debugMenuClinical")
    assert source.index('private _ctrlB =') < source.index('private _ctrlH =')
    assert '_ctrlB ctrlSetBackgroundColor [0.043, 0.082, 0.188, 0.86];' in source
    assert '_ctrlB ctrlEnable false;' in source
    # Introducing the backing to a running old overlay must first remove its existing text controls.
    before = source[:source.index('private _control =')]
    assert 'if (isNull _backdrop || {!((ctrlParent _backdrop) isEqualTo _display)}) then {call _cleanup;};' in before


def test_number_anchor_preserves_digits_decimals_units_and_full_text():
    source = definition('_padRight') + definition('_alignValue')
    execute(source + '''
        private _hr=[103] call _alignValue;
        private _map=[75] call _alignValue;
        private _temp=["37.5 C"] call _alignValue;
        private _negative=["-0.42"] call _alignValue;
        private _bleed=["1200 mL/min"] call _alignValue;
        [(_hr find "3")==4 && {(_map find "5")==4},"integer ones do not align"] call _check;
        [(_temp find ".")==5 && {(_negative find ".")==5},"decimal values do not share the integer anchor"] call _check;
        [count _hr==12 && {count _temp==12} && {count _bleed==12},"normal values shift the paired column"] call _check;
        [(_temp find "37.5 C")>=0 && {(_bleed find "1200 mL/min")>=0},"units or numbers were truncated"] call _check;
        private _long=["CONDITION VALUE LONGER THAN TWELVE"] call _alignValue;
        [_long=="CONDITION VALUE LONGER THAN TWELVE","long state text lost data"] call _check;
    ''')


def test_all_blocks_use_one_font_and_one_value_width_with_long_states():
    source = ''.join(definition(n) for n in ('_safe', '_padRight', '_alignValue', '_pair', '_one', '_formatRow', '_renderAll'))
    # Only engine text metrics and draws are substituted; actual row formatting/common-fit logic runs.
    execute('''
        private _cLabel="label";
        private _scale=0.58;
        private _totalW=0.54;private _w=0.265;private _headerH=0.075;
        private _clinicalH=0.60;private _networkH=0.25;
        private _ctrlH="head";private _ctrlL="left";private _ctrlR="right";private _ctrlS="net";
        private _measures=[];private _renders=[];
        private _measureBlock={
            params ["_rows","_size","_width","_height"];
            _measures pushBack [_rows,_size,_width,_height];
            [0.56,0.41,0.48,0.50] select ((count _measures)-1)
        };
        private _renderBlock={_renders pushBack _this;};
    ''' + source + '''
        private _header=["ACME DEBUG v1.2.3 | B157", "Patient: Long Complete Patient Name"];
        private _left=[
            ["HR",103,"good","BP","120/80","good"] call _pair,
            ["Ext","1200 mL/min","good","Junc",0,"good"] call _pair
        ];
        private _right=[
            ["AAJT","Z3+Ing-left+AxL+AxR","good","XStat","no","good"] call _pair,
            ["Internal",1200,"good","Suppress",1.2,"good"] call _pair
        ];
        private _network=[
            ["Role","client","good","MP","yes","good"] call _pair,
            ["Client",17,"good","Server","remote","good"] call _pair,
            ["NetID","2:13087","mute"] call _one
        ];
        call _renderAll;
        [count _renders==4 && {count _measures==4},"not all regions were included"] call _check;
        { [(_x select 2)==0.41,"overlay uses different font sizes"] call _check; } forEach _renders;
        private _leftRows=(_renders select 1) select 1;
        private _rightRows=(_renders select 2) select 1;
        private _networkRows=(_renders select 3) select 1;
        private _anchor=(_leftRows select 0) find "BP      ";
        [((_leftRows select 1) find "Junc    ")==_anchor,"units shifted second label"] call _check;
        [((_rightRows select 0) find "XStat   ")==_anchor,"long device state shifted second label"] call _check;
        [((_rightRows select 1) find "Suppress")==_anchor,"eight-character label lost alignment"] call _check;
        [((_networkRows select 0) find "MP      ")==_anchor,"machine labels do not align with clinical labels"] call _check;
        [((_networkRows select 1) find "Server  ")==_anchor,"network labels do not align"] call _check;
        [((_rightRows select 0) find "Z3+Ing-left+AxL+AxR")>=0,"shared column sizing lost a long value"] call _check;
        [((_rightRows select 1) find "Internal")>=0,"label was truncated"] call _check;
        [(((_renders select 0) select 1) select 1)=="Patient: Long Complete Patient Name","header was abbreviated"] call _check;
    ''')
