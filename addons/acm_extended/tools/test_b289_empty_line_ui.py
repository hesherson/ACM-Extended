"""Execute empty installed-line list, card and input decisions together.

Only native display/list/config primitives are fixtures. The checked-out slot
validator, native list builder, card identity/view/input and context resolvers
run intact; this does not certify Arma pointer routing or screen rendering.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from source_scan import lex, matching
from test_b156_procedure_supplies import primitives
from test_menu_death_lifecycle import ROOT, adapt, execute, read


@pytest.fixture(autouse=True)
def no_native_boundary_warnings(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def ui(source, component="core"):
    source = source.replace("IDC_TRANSFUSIONMENU_LEFTLISTPANEL", "86004")
    source = source.replace('C_LLSTRING(FreshBloodBag_Short)', '"Fresh blood %1"')
    source = source.replace('LLSTRING(TransfusionMenu_FluidRemaining)', '"Remaining %1 mL"')
    source = source.replace("findDisplay 86000", "_fixtureDisplay")
    source = source.replace("findDisplay 86200", "objNull").replace("findDisplay 84000", "objNull")
    source = source.replace("ctrlParent _hit", "_fixtureDisplay")
    source = re.sub(r'(_\w+) displayCtrl ([^;\n]+)', r'([\1,\2] call _displayCtrl)', source)
    source = re.sub(r'\bctrlIDC (_\w+)', r'(\1 getVariable ["idc",86004])', source)
    source = re.sub(r'\bctrlShown (_\w+)', r'(\1 getVariable ["shown",true])', source)
    source = re.sub(r'\blbSize (_\w+)', r'(count (\1 getVariable ["rows",[]]))', source)
    source = re.sub(r'\blbCurSel (_\w+)', r'(\1 getVariable ["sel",-1])', source)
    source = re.sub(r'\blbClear (_\w+);', r'[\1] call _clear;', source)
    source = re.sub(r'(_\w+) lbSetCurSel ([^;\n]+);', r'[\1,\2] call _select;', source)
    source = re.sub(r'(_\w+) lbAdd ([^;\n]+)', r'([\1,\2] call _add)', source)
    columns = {"lbValue": 0, "lbData": 1, "lbText": 2, "lbColor": 3,
               "lbPicture": 4, "lbTooltip": 5, "lbPictureRight": 6}
    for command, column in columns.items():
        source = re.sub(r'(_\w+) ' + command + r' (_\w+|\d+)',
                        rf'([\1,\2,{column}] call _get)', source)
    tokens = lex(source)
    pairs = matching(tokens)
    setters = {"lbSetValue": 0, "lbSetData": 1, "lbSetText": 2,
               "lbSetColor": 3, "lbSetPicture": 4, "lbSetTooltip": 5,
               "lbSetPictureRight": 6}
    edits = []
    for i, token in enumerate(tokens[:-1]):
        if token.value in setters and tokens[i + 1].value == "[":
            end = pairs[i + 1]
            args = source[tokens[i + 1].offset:tokens[end].offset + 1]
            edits.append((tokens[i - 1].offset, tokens[end].offset + 1,
                          f'[{tokens[i - 1].value},{setters[token.value]},{args}] call _set'))
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    source = re.sub(r'getText \(_config >> "[^"]+"\)', '"Fixture item"', source)
    source = re.sub(r'getText \(configFile >> "CfgWeapons" >>[^;]+? >> "picture"\)', '"line.paa"', source)
    source = re.sub(r'private _config = \(configFile >> "CfgWeapons" >> _itemClassName\);', 'private _config=configNull;', source)
    return primitives(adapt(source, component))


def compiled(name):
    return f"ACME_fnc_{name}={{" + ui(read(name)) + "};\n"


def fixture():
    native = (ROOT / "addons/circulation/functions/fnc_TransfusionMenu_UpdateBagList.sqf").read_text()
    return r'''
        private _fixtureDisplay=missionNamespace;
        private _list=profileNamespace;
        private _hit=missionNamespace;
        private _selectedCalls=0;private _paints=0;private _listClears=0;
        private _mapDefault={params ["_m","_a"];_a params ["_k","_d"];
            if (_k in _m) then {_m get _k} else {_d}};
        private _displayCtrl={params ["_d","_id"];if (_id==86004) then {_list} else {objNull}};
        private _get={params ["_l","_r","_col"];
            private _rows=_l getVariable ["rows",[]];
            if (_r<0 || {_r>=count _rows}) exitWith {[-1,"","",[1,1,1,1],"","",""] select _col};
            (_rows select _r) select _col};
        private _set={params ["_l","_col","_args"];_args params ["_r","_value"];
            private _rows=_l getVariable ["rows",[]];(_rows select _r) set [_col,_value];
            _l setVariable ["rows",_rows];};
        private _add={params ["_l","_text"];private _rows=_l getVariable ["rows",[]];
            _rows pushBack [-1,"",_text,[1,1,1,1],"","",""];
            _l setVariable ["rows",_rows];count _rows-1};
        private _clear={params ["_l"];_listClears=_listClears+1;_l setVariable ["rows",[]];_l setVariable ["sel",-1];};
        private _select={params ["_l","_r"];_l setVariable ["sel",_r];};
        _list setVariable ["rows",[]];_list setVariable ["sel",-1];_list setVariable ["idc",86004];
        _list setVariable ["shown",true];
        private _nativeIV=true;private _fixtureEpoch=7;
        ACME_fnc_clinicalEpoch={_fixtureEpoch};
        ACM_circulation_fnc_hasIV={_nativeIV};
        ACM_circulation_fnc_getAccessType={1};
        ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
        ACME_fnc_updateTransfusionControls={_selectedCalls=_selectedCalls+1;};
        ACME_fnc_updateTransfusionCards={_paints=_paints+1;};
        ACM_circulation_fnc_formatFluidBagName={"Fixture fluid"};
        ACME_fnc_fluidLabelVolume={format ["%1 (%2 mL)",_this select 0,_this select 1]};
        ACME_fnc_transfusionBagPresentation={[_this select 3,[1,1,1,1]]};
        private _mark=["leftarm","front",0.5,0.5,"hub","","",16,-1,1,"upper",0,1,0,"hub-1",[true,true,true,true,false,0,false],[]];
        private _bags=[];
        private _publish={
            _patient setVariable ["ACME_IV_Marks",[_mark]];
            _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",_bags]]];
        };
        call _publish;
        _patient setVariable ["ACME_YLines",[]];
        _patient setVariable ["ACME_detachedBags",[]];
        _patient setVariable ["ACME_IV_DisconnectedBagUIDs",[]];
        ACM_circulation_TransfusionMenu_Target=_patient;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
        ACM_circulation_TransfusionMenu_Selected_AccessSite=0;
        ACM_circulation_TransfusionMenu_SelectIV=true;
        ACM_circulation_TransfusionMenu_Selection_IVBags=[];
        uiNamespace setVariable ["ACM_circulation_TransfusionMenu_DLG",_fixtureDisplay];
        _fixtureDisplay setVariable ["ACME_txActivePane","transfusion"];
        _fixtureDisplay setVariable ["ACME_txActionMenu",""];
        _hit setVariable ["ACME_txListIDC",86004];_hit setVariable ["ACME_txCapacity",2];
        _hit setVariable ["ACME_txPatient",_patient];
    ''' + "".join(compiled(name) for name in (
        "transfusionAccessValid", "isYLineAccess", "ivSiteIndex", "ivLineSlot",
        "transfusionCardIdentity", "transfusionCardResolve", "transfusionCardWindow",
        "transfusionCardSelect", "transfusionCardData", "getSelectedIVLineContext",
        "getSelectedActiveBagContext",
    )) + "ACM_circulation_fnc_TransfusionMenu_UpdateBagList={" + ui(native, "circulation") + "};\n"


def select_line():
    return r'''
        [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
        _hit setVariable ["ACME_txIdentity",[_list,0] call ACME_fnc_transfusionCardIdentity];
        [_hit] call ACME_fnc_transfusionCardSelect;
    '''


@pytest.mark.parametrize("hidden", [False, True], ids=["native-list", "hidden-native-list-with-cards"])
def test_empty_installed_line_builds_a_selectable_card_without_creating_a_fluid_bag(hidden):
    execute(fixture() + f'_list setVariable ["shown",{str(not hidden).lower()}];' + r'''
        private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
    ''' + select_line() + r'''
        [count (_list getVariable "rows")==1,"installed empty tubing remained invisible"] call _check;
        [(_list getVariable "sel")==0 && {_selectedCalls==1},"empty line card did not select its native row"] call _check;
        private _identity=[_list,0] call ACME_fnc_transfusionCardIdentity;
        [_identity isEqualTo ["line","leftarm",true,0,"hub-1",7],"line card impersonated a physical bag"] call _check;
        [(call ACME_fnc_getSelectedIVLineContext) isEqualTo [_patient,"leftarm",true,0,"hub-1",7],"selected card lost its exact installed line"] call _check;
        [(["transfusion"] call ACME_fnc_getSelectedActiveBagContext) isEqualTo [],"empty apparatus became a medication bag context"] call _check;
        private _data=[_list,0] call ACME_fnc_transfusionCardData;
        [(_data select 0)=="IV line" && {(_data select 1)=="No bag attached"},"empty-line card was blank or mislabeled"] call _check;
        [(_data select 7)==-1 && {(_data select 8)==0} && {(_data select 6)==""},"empty line rendered a fake volume/progress or medication vial"] call _check;
        [_before==str (_patient getVariable "ACM_circulation_IV_Bags"),"presentation inserted a phantom fluid bag"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_nativeIV=false;",
    "(_mark select 15) set [3,false];call _publish;",
    'ACM_circulation_TransfusionMenu_SelectIV=false;',
    'ACM_circulation_TransfusionMenu_Selected_AccessSite=1;',
    'ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";',
    '_patient setVariable ["ACME_IV_Marks",[]];',
])
def test_absent_or_different_access_never_creates_an_empty_line_row(change):
    execute(fixture() + change + r'''
        [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
        [(_list getVariable "rows") isEqualTo [],"nonexistent/wrong line gained a usable slot"] call _check;
        [(call ACME_fnc_getSelectedIVLineContext) isEqualTo [],"missing line produced an attach context"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_fixtureEpoch=8;",
    "(_mark select 15) set [3,false];call _publish;",
    '_mark set [14,"replacement-hub"];call _publish;',
    '_patient setVariable ["ACME_IV_Marks",[]];',
    '_bags=[["Saline",500,1,0,true,-1,500,-1,"bag-new"]];call _publish;',
])
def test_stale_line_cards_cannot_select_or_present_old_apparatus(change):
    execute(fixture() + r'''
        [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
        _hit setVariable ["ACME_txIdentity",[_list,0] call ACME_fnc_transfusionCardIdentity];
    ''' + change + r'''
        [_hit] call ACME_fnc_transfusionCardSelect;
        [(_list getVariable "sel")==-1 && {_selectedCalls==0},"stale empty-line card was accepted"] call _check;
        _list setVariable ["sel",0];
        [(call ACME_fnc_getSelectedIVLineContext) isEqualTo [],"stale native selection authorized bag attachment"] call _check;
        private _data=[_list,0] call ACME_fnc_transfusionCardData;
        [(_data select [0,4]) isEqualTo ["","","",""],"removed line retained a usable-looking card"] call _check;
    ''')


def test_line_repaint_preserves_identity_but_replaces_slot_with_the_real_bag():
    execute(fixture() + select_line() + r'''
        private _identity=[_list,0] call ACME_fnc_transfusionCardIdentity;
        [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
        [(_list getVariable "sel")==0 && {([_list,0] call ACME_fnc_transfusionCardIdentity) isEqualTo _identity},"repaint dropped the same empty-line selection"] call _check;
        private _clears=_listClears;
        [true] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
        [_listClears==_clears,"steady empty-line update churned native selection"] call _check;
        _bags=[["Saline",500,1,0,true,-1,500,-1,"bag-new"]];call _publish;
        [true] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
        [count (_list getVariable "rows")==1,"real attachment left a duplicate empty line"] call _check;
        private _next=[_list,0] call ACME_fnc_transfusionCardIdentity;
        [(_next select 0)=="active" && {(_next select 4)=="bag-new"},"attached bag did not replace the empty-slot identity"] call _check;
        [(_list getVariable "sel")==-1,"empty-line selection silently became the new bag"] call _check;
    ''')


def spike_fixture():
    source = read("transfusionSpikeOrAdd")
    source = source.replace('getText (configFile >> "ace_medical_treatment" >> "IV" >> _action >> "type")', '_chosenType')
    source = source.replace("objectParent ACE_player", "objNull")
    return fixture() + select_line() + r'''
        private _rightList=uiNamespace;
        _rightList setVariable ["idc",86005];_rightList setVariable ["sel",0];
        private _chosenType="Saline";
        private _direct=[];private _extraLineQueries=0;private _extraLineTakes=0;
        private _notices=[];
        _displayCtrl={params ["_d","_id"];switch (_id) do {
            case 86004:{_list};case 86005:{_rightList};default{objNull}}};
        ACME_fnc_attachBagToLine={_direct pushBack +_this;};
        ACME_fnc_treatmentSupplyCount={_extraLineQueries=_extraLineQueries+1;0};
        ACME_fnc_treatmentSupplyTake={_extraLineTakes=_extraLineTakes+1;[]};
        ACME_fnc_clinicalNotice={_notices pushBack _this;};
        uiNamespace setVariable ["ACME_preparedListMode",false];
        missionNamespace setVariable ["ACME_piggybackPending",[]];
        missionNamespace setVariable ["ACME_yPending",""];
        missionNamespace setVariable ["ACME_yPendingSaline",""];
        ACM_circulation_TransfusionMenu_Selected_Inventory=0;
    ''' + "ACME_fnc_transfusionSpikeOrAdd={" + ui(source) + "};\n"


@pytest.mark.parametrize("kind,bag,action", [
    ("Saline", "ACM_SalineBag_500", "SalineIV_500"),
    ("Plasma", "ACE_plasmaIV_500", "PlasmaIV_500"),
    ("PlasmaLyte", "ACME_PlasmaLyteBag_500", "PlasmaLyteIV_500"),
    ("Blood", "ACM_BloodBag_ON_500", "BloodIV_ON_500"),
    ("", "ACM_FreshBloodBag_500_1", "FreshBloodBag_500_1"),
])
def test_actual_spike_action_attaches_selected_basic_fluid_to_installed_line_without_second_tubing(kind, bag, action):
    execute(spike_fixture() + f'''
        _chosenType="{kind}";
        _rightList setVariable ["rows",[[0,"{bag}|{action}","Bag",[1,1,1,1],"bag.paa","",""]]];
        [] call ACME_fnc_transfusionSpikeOrAdd;
        [_direct isEqualTo [["{bag}","{action}","hub-1",false]],"real menu action failed to attach its selected bag to the captured line"] call _check;
        [_extraLineQueries==0 && {{_extraLineTakes==0}} && {{_waits isEqualTo []}},"installed-line action charged for a second line or started ordinary spike preparation"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_fixtureEpoch=8;",
    "(_mark select 15) set [3,false];call _publish;",
    '_mark set [14,"replacement-hub"];call _publish;',
    '_bags=[["Saline",500,1,0,true,-1,500,-1,"bag-new"]];call _publish;',
])
def test_actual_spike_action_refuses_stale_empty_slot_instead_of_starting_another_preparation(change):
    execute(spike_fixture() + r'''
        _rightList setVariable ["rows",[[0,"ACM_SalineBag_500|SalineIV_500","Bag",[1,1,1,1],"bag.paa","",""]]];
    ''' + change + r'''
        [] call ACME_fnc_transfusionSpikeOrAdd;
        [_direct isEqualTo [] && {_extraLineQueries==0} && {_extraLineTakes==0}
            && {_waits isEqualTo []},"stale line input redirected to another bag/line or debited stock"] call _check;
        [count _notices==1,"stale slot failure was silent"] call _check;
    ''')


def test_cooler_resume_keeps_the_selected_line_uid_and_marks_only_the_withdrawn_bag_as_cooled():
    execute(spike_fixture() + r'''
        _chosenType="Blood";
        _rightList setVariable ["rows",[[0,"ACM_BloodBag_ON_500|BloodIV_ON_500|COOLER","Bag",[1,1,1,1],"bag.paa","",""]]];
        [["ACM_BloodBag_ON_500","BloodIV_ON_500",[]]] call ACME_fnc_transfusionSpikeOrAdd;
        [_direct isEqualTo [["ACM_BloodBag_ON_500","BloodIV_ON_500","hub-1",true]],"cooler resume lost exact line or cooled provenance"] call _check;
        [_extraLineQueries==0 && {_extraLineTakes==0},"cooler direct attachment charged another IV line"] call _check;
    ''')
