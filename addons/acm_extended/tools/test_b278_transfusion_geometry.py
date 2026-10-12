"""Native card lifecycle and pixel geometry execute checked-out SQF in SQF-VM.

Engine drawing/list commands are explicit fixture boundaries. These checks cover
persistent card pools, one shared scroll transform for all row content, and input
isolation; actual font/raster acceptance still requires Arma.
"""
from pathlib import Path
import re

import pytest

from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_b156_procedure_supplies import primitives

FUN = ROOT / "addons/acm_extended/functions"


def control_metadata(source):
    tokens = lex(source)
    pairs = matching(tokens)
    changes = []
    for index, token in enumerate(tokens):
        if token.value not in ("getVariable", "setVariable") or index == 0:
            continue
        if tokens[index - 1].value not in ("_group", "_hit", "_rail", "_emptyCaption"):
            continue
        assert tokens[index + 1].value == "["
        end = pairs[index + 1]
        left = tokens[index - 1].value
        argument = source[tokens[index + 1].offset:tokens[end].offset + 1]
        name = "_controlRead" if token.value == "getVariable" else "_controlSet"
        changes.append((tokens[index - 1].offset, tokens[end].offset + 1, f"([{left},{argument}] call {name})"))
    for start, end, text in reversed(changes):
        source = source[:start] + text + source[end:]
    return source


def renderer_source(name):
    source = (FUN / f"fn_{name}.sqf").read_text()
    source = source.replace("findDisplay 86000", "missionNamespace")
    source = source.replace("findDisplay 86200", "objNull").replace("findDisplay 84000", "objNull")
    source = re.sub(r"_display displayCtrl (\([^;]+?\)|_\w+)", r"\1", source)
    source = re.sub(r"_display ctrlCreate (\[[^;]+?\])", r"(\1 call _createControl)", source)
    source = re.sub(r"_group controlsGroupCtrl (\([^;]+?\)|_\w+|\d+)", r"[_group,\1]", source)
    source = source.replace("ctrlPosition _list", "(_positions get _list)")
    source = source.replace("lbSize _list", "(_counts get _list)").replace("lbCurSel _list", "(_selected get _list)")
    source = source.replace("_list lbTooltip _row", '""')
    for control in ("_list", "_group", "_rail", "_emptyCaption"):
        source = source.replace(f"isNull {control}", f"!({control} in _createdControls)")
    # Engine event registration records only the event name, never runs callbacks.
    tokens = lex(source)
    pairs = matching(tokens)
    edits = []
    for index, token in enumerate(tokens):
        if token.value != "ctrlAddEventHandler":
            continue
        end = pairs[index + 1]
        event = tokens[index + 2].value
        edits.append((tokens[index - 1].offset, tokens[end].offset + 1,
                      f'[{tokens[index - 1].value},"{event}"] call _registerEvent'))
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    source = re.sub(r"(\([^;]+?\)|_\w+) ctrlEnable (false|true)", r'[\1,"enable",\2] call ACME_fnc_transfusionUiSet', source)
    source = re.sub(r"_rail ctrlSetBackgroundColor ([^;]+)", r'[_rail,"background",\1] call ACME_fnc_transfusionUiSet', source)
    source = source.replace('_hit ctrlSetTooltip _tooltip', '[_hit,"tooltip",_tooltip] call ACME_fnc_transfusionUiSet')
    source = control_metadata(source)
    source = source.replace("safeZoneH", "1").replace("pixelW", "(1/1920)").replace("pixelH", "(1/1080)")
    return primitives(adapt(source))


def renderer_setup():
    return r'''
        private _controlProps=createHashMap;private _controlValues=createHashMap;
        private _createdControls=[86004,86129,86005,86145,86127];
        private _creationCount=0;private _events=[];private _writes=[];
        private _mapDefault={params["_m","_a"];_a params["_k","_d"];if(_k in _m)then{_m get _k}else{_d}};
        private _controlRead={params["_c","_a"];_a params["_k","_d"];private _key=format["%1:%2",_c,_k];if(_key in _controlProps)then{_controlProps get _key}else{_d}};
        private _controlSet={params["_c","_a"];_a params["_k","_v"];_controlProps set[format["%1:%2",_c,_k],_v];};
        private _createControl={params["_class","_id"];_creationCount=_creationCount+1;_createdControls pushBack _id;_id};
        private _registerEvent={_events pushBack _this;};
        ACME_fnc_transfusionUiSet={params["_c","_property","_value"];private _key=format["%1:%2",_c,_property];
            if(!(_key in _controlValues)||{(_controlValues get _key)isNotEqualTo _value})then{_controlValues set[_key,_value];_writes pushBack _this;};true};
        private _positions=createHashMapFromArray[[86004,[.1,.2,.2,.21]],[86129,[.1,.55,.212,.187]],[86005,[.67,.279,.202,.235]],[86145,[.67,.279,.202,.235]],[86127,[.67,.636,.202,.149]]];
        private _counts=createHashMapFromArray[[86004,8],[86129,8],[86005,8],[86145,8],[86127,8]];
        private _selected=createHashMapFromArray[[86004,0],[86129,0],[86005,0],[86145,0],[86127,0]];
        ACME_fnc_transfusionCardIdentity={params["_l","_r"];if(_r<0)exitWith{[]};["fixture",_l,_r]};
        ACME_fnc_transfusionCardData={params["_l","_r"];[format["Fixture %1",_r],"125 mL remaining","Running","",[1,1,1,1],"native-fluid.paa","native-vial.paa",.5]};
        uiNamespace setVariable["ACME_preparedListMode",false];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
    ''' + 'ACME_fnc_transfusionCardWindow={' + adapt((FUN / 'fn_transfusionCardWindow.sqf').read_text()) + '};' + \
        '\n'.join('ACME_fnc_' + name + '={' + renderer_source(name) + '};' for name in ('transfusionRoundedFrame', 'updateTransfusionCards'))


def test_full_card_refresh_is_bounded_and_backing_lists_never_redraw():
    execute(renderer_setup() + r'''
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        private _created=_creationCount;private _registered=count _events;private _written=count _writes;
        [_created==27,"card/caption/rail pool is unbounded"]call _check;
        [count _events==84,"card input hooks were duplicated or absent"]call _check;
        for "_tick" from 0 to 10 do {[missionNamespace]call ACME_fnc_updateTransfusionCards;};
        [_creationCount==_created&&{count _events==_registered},"refresh allocated duplicate cards or callbacks"]call _check;
        [count _writes==_written,"unchanged refresh repainted identical card rectangles"]call _check;
        {[_controlValues get format["%1:show",_x] isEqualTo false,"native list drew over custom cards"]call _check;}forEach[86004,86129,86005,86145,86127];
        {[_controlValues get format["%1:enable",_x] isEqualTo false,"scrollbar decoration owns input"]call _check;}forEach[86610,86611,86612,86613,86614,86615,86616,86617,86618,86619];
    ''')


@pytest.mark.parametrize("offset", [0, 1, 5, 99])
def test_scrolling_rebinds_one_exact_card_rectangle_for_artwork_caption_and_hit(offset):
    execute(renderer_setup() + r'''
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
    ''' + f'missionNamespace setVariable["ACME_txCardOffset_86005",{offset}];' + r'''
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        private _window=[8,3,missionNamespace getVariable["ACME_txCardOffset_86005",0]]call ACME_fnc_transfusionCardWindow;
        for "_slot" from 0 to 2 do {
            private _group=86520+_slot;private _rect=_controlValues get format["%1:position",_group];
            private _hit=_controlValues get format["%1:position",[_group,9]];
            private _icon=_controlValues get format["%1:position",[_group,14]];
            private _vial=_controlValues get format["%1:position",[_group,15]];
            private _title=_controlValues get format["%1:position",[_group,10]];
            private _identity=[[_group,9],["ACME_txIdentity",[]]]call _controlRead;
            [(_identity select 2)==((_window select 1)select _slot),"visible slot targeted a different native row"]call _check;
            [(_hit select[0,2])isEqualTo[0,0]&&{(_hit select[2,2])isEqualTo(_rect select[2,2])},"card hit region disagreed with row drawing"]call _check;
            {[_x select 0>=0&&{(_x select 0)+(_x select 2)<=(_rect select 2)+.00001}&&{_x select 1>=0}&&{(_x select 1)+(_x select 3)<=(_rect select 3)+.00001},"row artwork or caption escaped its exact scrolled rectangle"]call _check;}forEach[_icon,_vial,_title];
            [(_vial select 3)<=.026&&{(_vial select 2)/(1/1920)<=((_vial select 3)/(1/1080))*.56},"infusion vial oversized its title row"]call _check;
            private _rail=_controlValues get "86614:position";
            [(_rect select 0)+(_rect select 2)<(_rail select 0)-4/1920,"rounded card encroaches into right scrollbar"]call _check;
            [(_rail select 0)+(_rail select 2)<=.872001,"scrollbar left preparation pane"]call _check;
        };
    ''')


def test_prepared_view_and_nested_menu_hide_only_their_own_cards():
    execute(renderer_setup() + r'''
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        uiNamespace setVariable["ACME_preparedListMode",true];
        missionNamespace setVariable["ACME_txActionMenu","bag"];
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        [(_controlValues get "86500:show")isEqualTo false&&{(_controlValues get "86520:show")isEqualTo false},"hidden native pane leaked an interactive card"]call _check;
        [(_controlValues get "86530:show")isEqualTo true&&{(_controlValues get "86510:show")isEqualTo true},"prepared switch hid unrelated infusions"]call _check;
        missionNamespace setVariable["ACME_txActionMenu",""];
        uiNamespace setVariable["ACME_preparedListMode",false];
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        [(_controlValues get "86500:show")isEqualTo true&&{(_controlValues get "86520:show")isEqualTo true}&&{(_controlValues get "86530:show")isEqualTo false},"return from popover did not restore sole card layer"]call _check;
        [_creationCount==27&&{count _events==84},"view switch allocated another runtime"]call _check;
    ''')


@pytest.mark.parametrize("width,height", [(1280, 960), (1920, 1080), (3440, 1440), (5120, 1440)])
def test_corner_radius_uses_identical_whole_pixels_on_all_nine_slices(width, height):
    source = (FUN / "fn_transfusionRoundedFrame.sqf").read_text()
    source = source.replace("isNull _group", "false").replace("_group controlsGroupCtrl _i", "_i").replace("_piece ctrlEnable false;", "")
    source = source.replace("safeZoneH", "1").replace("pixelW", f"(1/{width})").replace("pixelH", f"(1/{height})")
    execute(r'''
        private _group=profileNamespace;private _pieces=[];
        ACME_fnc_transfusionUiSet={params["_c","_p","_v"];if(_p=="position"&&{_c isEqualType 0})then{_pieces set[_c,_v];};true};
    ''' + 'ACME_fnc_transfusionRoundedFrame={' + adapt(source) + '};' + f'''
        {{
            [_group,_x,"panel",.007]call ACME_fnc_transfusionRoundedFrame;
            private _rx=(_pieces select 0)select 2;private _ry=(_pieces select 0)select 3;
            [abs(_rx*{width}-_ry*{height})<.0001&&{{abs(round(_rx*{width})-_rx*{width})<.0001}},"fractional or unequal physical corner radius"]call _check;
            {{[abs((_pieces select _x select 2)-_rx)<.00001&&{{abs((_pieces select _x select 3)-_ry)<.00001}},"opposing corner shape changed"]call _check;}}forEach[0,2,6,8];
        }}forEach[[0,0,.21,.03],[0,0,.10,.09],[0,0,.78,.84]];
    ''')


def test_detail_panel_is_left_aligned_beneath_infusions_without_covering_navigation():
    layout = (FUN / "fn_layoutTransfusionMenu.sqf").read_text()
    positions = {int(i): tuple(map(float, (x, y, w, h))) for i, x, y, w, h in re.findall(r"\[(86129|86131|86172|86171),([\d.]+),([\d.]+),([\d.]+),([\d.]+)\]", layout)}
    card, adjust, actions, details = (positions[i] for i in (86129, 86131, 86172, 86171))
    assert details[0] == card[0] == adjust[0]
    assert card[1] + card[3] < adjust[1] and adjust[1] == actions[1]
    assert adjust[0] + adjust[2] < actions[0]
    assert adjust[1] + adjust[3] < details[1]
    assert details[1] + details[3] <= .890
    text = (FUN / "fn_updateTransfusionLineDetails.sqf").read_text()
    assert '"ACME_txDetailsViewport"' in text
    assert text.index('private _viewport = ctrlPosition _group;') > text.index('_display setVariable ["ACME_detailsContent", _content];')
    assert 'class ACME_TransfusionInlineDetails: RscControlsGroupNoHScrollbars' in (ROOT / 'addons/acm_extended/TransfusionMenu_Styles.hpp').read_text()
    dialog = (ROOT / "addons/circulation/TransfusionMenu_Dialog.hpp").read_text()
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    assert '#include "TransfusionMenu_Surfaces.hpp"' not in dialog + config
