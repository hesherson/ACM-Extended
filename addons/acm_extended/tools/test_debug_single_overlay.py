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
    source = definition("_renderBlock")
    source = source.replace('_ctrlM ctrlSetStructuredText parseText format [_template, _size, _body];',
                            '_measured pushBack (format [_template, _size, _body]);')
    source = source.replace('_ctrlM ctrlSetStructuredText parseText format [_template, _size, _x];',
                            '_measured pushBack (format [_template, _size, _x]);')
    source = source.replace("ctrlTextWidth _ctrlM", "_metricW").replace("ctrlTextHeight _ctrlM", "_metricH")
    source = source.replace('_ctrl ctrlSetStructuredText parseText format [_template, _fit, _body];',
                            '_rendered pushBack [_ctrl, _fit, format [_template, _fit, _body]];')
    execute(f'private _metricW={width};private _metricH={height};private _measured=[];private _rendered=[];' +
        source + '''
        [7, ["ACME DEBUG v1.2.3 | B154", "Patient: Long Complete Patient Name"], 0.62, 0.34, 1] call _renderBlock;
        [count _rendered==1 && {count _measured==3},"each row and full height were not measured before render"] call _check;
        private _result=_rendered select 0; private _fit=_result select 1;private _body=_result select 2;
        [_fit>0 && {_fit<=0.62},"fit grew or invalidated font size"] call _check;
        [(_metricW*_fit/0.62)<=0.320001,"width fit would wrap"] call _check;
        [(_metricH*_fit/0.62)<=0.980001,"height fit would clip"] call _check;
        [(_body find "ACME DEBUG v1.2.3 | B154")>=0,"title/build was truncated"] call _check;
        [(_body find "Patient: Long Complete Patient Name")>=0,"patient name was truncated"] call _check;
    ''')


def test_section_color_spacing_and_values_survive_shared_formatting():
    source = ''.join(definition(n) for n in ("_safe", "_padRight", "_alignValue", "_pair", "_sect"))
    execute('private _cTitle="#D9A441";private _cSect=_cTitle;private _cLabel="label";' + source + '''
        private _section=["PERFUSION / BLEEDING"] call _sect;
        [(_section find "<br/>")==0,"missing space before section"] call _check;
        [(_section find _cTitle)>0,"section title color differs from main title"] call _check;
        private _row=["HR",103,"good","BP","120/80","good"] call _pair;
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


def test_single_subtle_backing_is_created_below_all_text_and_ignores_mouse_input():
    source = read("debugMenuClinical")
    assert source.index('private _ctrlB =') < source.index('private _ctrlH =')
    assert '_ctrlB ctrlSetBackgroundColor [0, 0, 0, 0.20];' in source
    assert '_ctrlB ctrlEnable false;' in source
    # Introducing the backing to a running old overlay must first remove its existing text controls.
    before = source[:source.index('private _control =')]
    assert 'if (isNull _backdrop || {!((ctrlParent _backdrop) isEqualTo _display)}) then {call _cleanup;};' in before
