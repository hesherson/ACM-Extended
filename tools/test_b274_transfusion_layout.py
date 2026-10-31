"""B274 menu corrections consume production geometry and presentation sources.

These contracts verify authored placement and popup isolation, not Arma text
rendering. The existing B273 geometry suite keeps screen-ratio and action bounds.
"""
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FUN = ROOT / "addons/acm_extended/functions"
LAYOUT = (FUN / "fn_layoutTransfusionMenu.sqf").read_text()
DIALOG_PATH = "addons/circulation/TransfusionMenu_Dialog.hpp"
DIALOG = (ROOT / DIALOG_PATH).read_text()
STYLES = (ROOT / "addons/acm_extended/TransfusionMenu_Styles.hpp").read_text()
DEFINES = (ROOT / "addons/circulation/TransfusionMenu_defines.hpp").read_text()
BASELINE = "e171dd8f2204063964a2f4f65e64332560f25824"


def class_block(source, name):
    match = re.search(rf"\bclass {re.escape(name)}\s*:[^{{]+\{{", source)
    assert match, f"production class {name} missing"
    start = match.end()
    depth = 1
    for index in range(start, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index]
    raise AssertionError(f"production class {name} is unclosed")


def native_rect(name, source=DIALOG):
    block = class_block(source, name)
    expressions = dict(re.findall(r"\b([xywh]) = QUOTE\((.*?)\);", block))
    env = {"ACM_UI_CANVAS_X": 0, "ACM_UI_CANVAS_W": 1, "safeZoneY": 0, "safeZoneH": 1,
           "ACM_TRANSFUSION_LEFT_X": .125, "ACM_TRANSFUSION_LEFT_W": .212}
    return tuple(eval(expressions[key], {"__builtins__": {}}, env) for key in "xywh")


def runtime_rect(idc, width=None):
    rows = re.findall(rf"\[{idc},(0\.\d+),(0\.\d+),(0\.\d+),(0\.\d+)\]", LAYOUT)
    assert rows, f"production runtime rectangle {idc} missing"
    rectangles = [tuple(map(float, row)) for row in rows]
    if width is not None:
        rectangles = [row for row in rectangles if row[2] == width]
    assert rectangles, f"production runtime rectangle {idc} width {width} missing"
    return rectangles[0]


def test_patient_name_restores_original_centered_top_anchor():
    original = subprocess.check_output(["git", "show", f"{BASELINE}:{DIALOG_PATH}"], cwd=ROOT, text=True)
    assert native_rect("PatientName") == pytest.approx(native_rect("PatientName", original))
    assert native_rect("PatientName") == pytest.approx((0, .095, 1, .05))
    assert "style = ST_CENTER;" in class_block(DIALOG, "PatientName")
    # PatientName's whole-canvas rectangle is intentionally not reflowed.
    assert not re.search(r"\[86001,", LAYOUT)


def test_stop_button_initial_and_final_rectangles_match_above_fluids():
    stop = runtime_rect(86006)
    assert native_rect("StopTransfusionButton") == pytest.approx(stop)
    assert stop == pytest.approx((.125, .188, .212, .029))
    assert stop[1] + stop[3] < runtime_rect(86004)[1]
    assert "call FUNC(TransfusionMenu_ToggleIVFlow)" in class_block(DIALOG, "StopTransfusionButton")


def test_preparing_an_infusion_and_hanging_a_set_share_the_inventory_action_row():
    hang = runtime_rect(86141, .097)
    prep = runtime_rect(86121)
    assert prep[1:] == pytest.approx(hang[1:])
    assert prep[0] >= hang[0] + hang[2]
    # This action belongs to the prepared-set selection, not the infusion list.
    assert prep[1] + prep[3] < runtime_rect(86130)[1]
    assert '[(_display displayCtrl 86121),"show",_preparedMode]' in LAYOUT


def test_give_is_the_single_full_width_prepared_infusion_footer_action():
    give = runtime_rect(86122)
    prepared = runtime_rect(86127)
    assert give[0] == prepared[0]
    assert give[2] == prepared[2]
    assert give[1] >= prepared[1] + prepared[3]
    assert runtime_rect(86121)[1] < prepared[1]
    # Prep is the only second authored action previously occupying this footer.
    assert give == pytest.approx((.673, .810, .202, .034))


@pytest.mark.parametrize("source_name", ["styles", "defines", "layout"])
def test_transfusion_chrome_colors_use_neutral_black_and_grey(source_name):
    source = {"styles": STYLES, "defines": DEFINES, "layout": LAYOUT}[source_name]
    if source_name == "defines":
        colors = re.findall(r"#define ACM_TRANSFUSION_COLOR_\w+ \{([^}]+)\}", source)
    elif source_name == "styles":
        colors = re.findall(r"color\w+\[\] = \{([^}]+)\};", source)
    else:
        colors = re.findall(r"ctrlSet(?:Text|Background)Color \[([^]]+)\]", source)
    assert colors, "production chrome palette missing"
    for color in colors:
        values = list(map(float, color.split(",")))
        assert len(values) == 4
        assert values[0] == values[1] == values[2], f"colored chrome remains: {color}"


def test_menu_omits_branding_and_redundant_line_service_caption():
    visible_sources = " ".join((DIALOG + LAYOUT).upper().split())
    assert "ACME TRANSFUSION" not in visible_sources
    assert "LINE FLOW AND SERVICE" not in visible_sources
    assert '"Line Details >"' not in LAYOUT
    assert not re.search(r"\[86179,", LAYOUT)


@pytest.mark.parametrize("dialog_id", [86200, 84000])
def test_native_popup_guards_precede_menu_layout_and_controller_mutations(dialog_id):
    controller = (FUN / "fn_updateTransfusionControls.sqf").read_text()
    for source in [LAYOUT, controller]:
        guard = source.index(f"findDisplay {dialog_id}")
        assert guard < source.index("displayCtrl")
        assert guard < source.index("setVariable")


def test_line_details_are_inline_and_do_not_create_a_nested_display():
    open_details = (FUN / "fn_transfusionLineDetails.sqf").read_text()
    update_details = (FUN / "fn_updateTransfusionLineDetails.sqf").read_text()
    assert "createDialog" not in open_details + update_details
    assert "findDisplay 86190" not in LAYOUT + open_details + update_details
    assert "call ACME_fnc_updateTransfusionLineDetails" in LAYOUT
    assert runtime_rect(86171) == pytest.approx((.125, .822, .212, .068))
    # The inline painter stays on the existing menu tick and cannot modify care.
    assert "ownerDispatch" not in update_details
    assert "addPerFrameHandler" not in update_details
    assert not re.search(r"_patient setVariable", update_details)


def inline_fixture():
    """Adapt only engine handles/config/rendering; execute the full inline painter."""
    helpers = ROOT / "addons/acm_extended/tools"
    if str(helpers) not in sys.path:
        sys.path.insert(0, str(helpers))
    from test_menu_death_lifecycle import adapt, execute
    from test_historical_vial_execution import map_defaults
    from test_b275_piggyback import fn
    presentation = "".join(fn(name) for name in (
        "isYLineAccess", "piggybackLine", "piggybackRole", "piggybackFlow",
        "fluidLabelVolume", "transfusionBagPresentation", "infusionName",
    ))
    # Native weapon configuration is an engine boundary; leave the production
    # label/role/thermal logic intact and let its type fallback name the bag.
    presentation = presentation.replace('private _cfg = configFile >> "CfgWeapons" >> _class;', 'private _cfg = configFile;')
    presentation = presentation.replace('getText (_cfg >> "shortName")', '""').replace('getText (_cfg >> "displayName")', '""')
    # No engine localization table exists here; execute the alias and its
    # production missing-translation fallback using the unchanged string key.
    presentation = presentation.replace('localize format', 'format')
    source = (FUN / "fn_updateTransfusionLineDetails.sqf").read_text()
    source = source.replace("findDisplay 86000", "_displayFixture")
    source = source.replace("findDisplay 86200", "_clampFixture")
    source = source.replace("findDisplay 84000", "_drawFixture")
    # The display handles are namespace stand-ins; this VM accepts isNull on
    # objNull but cannot apply it to a namespace-valued open display.
    for handle in ["_clampFixture", "_drawFixture"]:
        source = source.replace(f"isNull ({handle})", f"({handle} isEqualTo objNull)")
    source = source.replace("_display displayCtrl 86171", "_groupFixture")
    source = source.replace("_group controlsGroupCtrl 86192", "_ctrlFixture")
    source = source.replace("ctrlPosition _ctrl", "[0,0,.28,.09]")
    source = source.replace("ctrlPosition _group", "[0,0,.29,.09]")
    source = source.replace("ctrlTextHeight _ctrl", ".12")
    source = source.replace("safeZoneH", "1")
    source = source.replace("pixelW", "(1/1920)").replace("pixelH", "(1/1080)")
    source = source.replace("_ctrl ctrlSetStructuredText parseText _content;", "_paints pushBack _content;")
    source = re.sub(r'getText \(configFile >> "CfgWeapons" >> .*? >> "displayName"\)', '""', source)
    source = adapt(map_defaults(source))
    setup = r'''
        private _displayFixture=missionNamespace;
        private _groupFixture=uiNamespace;
        private _ctrlFixture=profileNamespace;
        private _clampFixture=objNull;
        private _drawFixture=objNull;
        private _paints=[];
        private _uiWrites=[];
        private _serviceState=[20,0,true,true,false,""];
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        ACME_fnc_transfusionUiSet={_uiWrites pushBack _this;true};
        ACME_fnc_transfusionAccessValid={true};
        ACME_fnc_yServiceState={_serviceState};
        ACME_fnc_lineWarmer={false};
        ACM_circulation_fnc_getIVFlowRate={0};
        ACM_circulation_fnc_formatFluidBagName={_this select 0};
        CBA_fnc_replace={params ["_value","_search","_replacement"];
            private _at=_value find _search;
            while {_at>=0} do {_value=(_value select [0,_at])+_replacement+(_value select [_at+count _search]);_at=_value find _search;};
            _value
        };
        ACME_fnc_pressureLevel={if ((_this select 0 select 0)==1) then {.5} else {.9}};
        ACME_fnc_formatDose={format ["%1 %2mg",_this select 0,_this select 1]};
        _displayFixture setVariable ["ACME_detailsContent",""];
        ACM_circulation_TransfusionMenu_Target=_patient;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
        ACM_circulation_TransfusionMenu_SelectIV=true;
        ACM_circulation_TransfusionMenu_Selected_AccessSite=0;
        private _bags=createHashMapFromArray [
            ["leftarm",[["Blood",300,1,0,true,0,500,-1,"blood"],
                        ["Saline",20,1,1,true,-1,100,-1,"neighbor"],
                        ["ACME_Propofol",50,1,0,false,-1,50,-1,"io"]]],
            ["rightarm",[["Saline",200,1,0,true,-1,500,-1,"right"]]]];
        _patient setVariable ["ACM_circulation_IV_Bags",_bags];
        _patient setVariable ["ACME_YLines",["leftarm#true#0"]];
        _patient setVariable ["ACME_piCuffs",createHashMapFromArray [["blood",[1]],["neighbor",[2]],["io",[2]]]];
        _patient setVariable ["ACME_infusion_BagMedications",[
            ["calcium","leftarm",0,"Blood",0,true,-1,500,-1,0,0,"Calcium",0,100,75],
            ["other","leftarm",1,"Saline",1,true,-1,100,-1,0,0,"Propofol",0,300,225]]];
    '''
    return setup + presentation + "ACME_fnc_updateTransfusionLineDetails={" + source + "};\n", execute


def test_inline_details_follow_exact_live_access_and_repaint_only_changed_content():
    setup, execute = inline_fixture()
    execute(setup + r'''
        private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        private _first=_paints select 0;
        [_first find "Calcium 100mg added" >=0 && {_first find "Calcium 75mg" <0}
            && {_first find "Pressure cuff: 50%" >=0} && {_first find "Y line: Prime needed" >=0},
            "inline details lost selected access information"] call _check;
        [_first find "Pressure cuff: 90%" <0 && {_first find "Propofol" <0},
            "inline details leaked a neighboring IV or IO access"] call _check;
        [_before isEqualTo str (_patient getVariable "ACM_circulation_IV_Bags"),
            "read-only inline painter mutated patient bags"] call _check;
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        [count _paints==1,"unchanged details replayed structured text"] call _check;
        (_bags get "leftarm" select 0) set [1,250];
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        [count _paints==1,"bag-list volume tick repainted unchanged inline metadata"] call _check;
        // Delivery changes the internal remaining dose, not the label of what was added.
        (_patient getVariable "ACME_infusion_BagMedications" select 0) set [14,50];
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        [count _paints==1 && {(_paints select 0) find "Calcium 100mg added" >=0},
            "remaining medication changed the fixed added-dose label or repainted unchanged details"] call _check;
        // A further accepted injection increases the operator-known total and must repaint once.
        (_patient getVariable "ACME_infusion_BagMedications" select 0) set [13,150];
        (_patient getVariable "ACME_infusion_BagMedications" select 0) set [14,100];
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        [count _paints==2 && {(_paints select 1) find "Calcium 150mg added" >=0}
            && {(_paints select 1) find "Calcium 100mg" <0},
            "details did not refresh a further confirmed medication addition"] call _check;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        [count _paints==3 && {(_paints select 2) find "Y line" <0}
            && {(_paints select 2) find "Pressure cuff" <0} && {(_paints select 2) find "Calcium" <0},
            "details retained the previous selected access"] call _check;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
        _serviceState=[40,50,false,true,true,"Flush"];
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        private _service=_paints select 3;
        [_service find "Y line: Primed" >=0 && {_service find "Reserve Flush Saline: 40 mL" >=0}
            && {_service find "Flush in progress: 50 mL reserved" >=0}
            && {_service find "Flush required before" <0},
            "inline service details lost reserve or active operation state"] call _check;
    ''')


@pytest.mark.parametrize("popup", ["clamp", "draw"])
def test_inline_painter_stops_before_ui_writes_when_native_popup_is_open(popup):
    setup, execute = inline_fixture()
    execute(setup + f'_{popup}Fixture=_groupFixture;' + r'''
        [_displayFixture] call ACME_fnc_updateTransfusionLineDetails;
        [_paints isEqualTo [] && {_uiWrites isEqualTo []},
            "inline details wrote into an active native treatment popup"] call _check;
        [(_displayFixture getVariable "ACME_detailsContent")=="",
            "popup guard advanced the menu content cache"] call _check;
    ''')
