"""Execute filtered bag movement and popover selection through production SQF.

Only Arma display/list/config primitives and external delivery are fixtures. The
native move function, infusion proxies, and generic context resolver run intact;
these cases do not certify native rendering or multiplayer transport timing.
"""
import re
import subprocess

import pytest

from test_b156_procedure_supplies import primitives
from test_menu_death_lifecycle import ROOT, adapt, execute, read


NATIVE_MOVE = "addons/circulation/functions/fnc_TransfusionMenu_MoveBag.sqf"
BASELINE = "e171dd8f2204063964a2f4f65e64332560f25824"


def gui(source, component="core"):
    """Translate engine UI commands before the shared adapter strips UI effects."""
    source = source.replace("findDisplay 86000", "_displayFixture")
    source = source.replace("IDC_TRANSFUSIONMENU_LEFTLISTPANEL", "86004")
    source = source.replace("IDC_TRANSFUSIONMENU_BUTTON_MOVEBAG", "86007")
    source = re.sub(
        r"(_\w+) displayCtrl ([^;\n]+)",
        r"([\1,\2] call _displayCtrl)", source)
    source = re.sub(r"\bctrlShown (_\w+)", r"([\1] call _shown)", source)
    source = re.sub(r"\blbCurSel (_\w+)", r"([\1] call _curSel)", source)
    source = re.sub(r"(_\w+) lbValue (_\w+)", r"([\1,\2] call _value)", source)
    source = re.sub(
        r"(_\w+) lbSetCurSel ([^;\n]+);",
        r"[\1,\2] call _setSelection;", source)
    source = re.sub(
        r"(_\w+) ctrlSet(?:Text|Tooltip) ([^;\n]+);",
        r"_controlWrites pushBack [\1,\2];", source)
    source = re.sub(
        r'getText \(configFile >> "CfgWeapons" >> [^\n]+? >> "displayName"\)',
        '"Fixture bag"', source)
    return primitives(adapt(source, component))


def compiled(name):
    return f"ACME_fnc_{name}={{" + gui(read(name)) + "};\n"


def setup(native_source=None):
    source = (ROOT / NATIVE_MOVE).read_text() if native_source is None else native_source
    return r'''
        private _displayFixture=missionNamespace;
        // Namespace objects stand in for handles; control keys are independent
        // from the patient/provider state stored in those same test namespaces.
        private _fluidCtrl=uiNamespace;
        private _infCtrl=profileNamespace;
        private _controlWrites=[];
        private _selectionWrites=[];
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _displayCtrl={params ["_d","_id"];
            switch (_id) do {case 86004:{_fluidCtrl};case 86129:{_infCtrl};case 86007:{_fluidCtrl};default {objNull}}};
        private _shown={(_this select 0) getVariable ["fixtureShown",true]};
        private _curSel={(_this select 0) getVariable ["fixtureSelection",-1]};
        private _value={params ["_c","_r"];(_c getVariable ["fixtureValues",[]]) param [_r,-1]};
        private _setSelection={params ["_c","_r"];
            _selectionWrites pushBack [_c,_r];
            private _size=count (_c getVariable ["fixtureValues",[]]);
            _c setVariable ["fixtureSelection",if (_r>=0 && {_r<_size}) then {_r} else {-1}];};
        uiNamespace setVariable ["ACM_circulation_TransfusionMenu_DLG",_displayFixture];
        _displayFixture setVariable ["ACME_txActionMenu",""];
        _displayFixture setVariable ["ACME_txActivePane","transfusion"];
        _fluidCtrl setVariable ["fixtureShown",true];
        _fluidCtrl setVariable ["fixtureValues",[0]];
        _fluidCtrl setVariable ["fixtureSelection",0];
        _infCtrl setVariable ["fixtureShown",true];
        _infCtrl setVariable ["fixtureValues",[1,2]];
        _infCtrl setVariable ["fixtureSelection",1];
        private _physical=[
            ["Plasma",100,1,1,true,-1,100,-1,"other-access"],
            ["Blood",300,1,0,true,0,500,-1,"blood"],
            ["Saline",90,1,0,true,-1,100,-1,"calcium"],
            ["Saline",50,1,2,true,-1,100,-1,"second-access"],
            ["ACME_Propofol",50,1,0,true,-1,50,-1,"propofol"]
        ];
        private _selection=[
            ["Blood",300,1,0,true,0,500,-1,1],
            ["Saline",90,1,0,true,-1,100,-1,2],
            ["ACME_Propofol",50,1,0,true,-1,50,-1,4]
        ];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",_physical]]];
        _patient setVariable ["ACME_infusion_BagMedications",[
            ["dose-calcium","leftarm",2,"Saline",0,true,-1,100,-1],
            ["dose-propofol","leftarm",4,"ACME_Propofol",0,true,-1,50,-1]
        ]];
        ACM_circulation_TransfusionMenu_Target=_patient;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
        ACM_circulation_TransfusionMenu_Selected_AccessSite=0;
        ACM_circulation_TransfusionMenu_SelectIV=true;
        ACM_circulation_TransfusionMenu_Selection_IVBags=_selection;
        ACM_circulation_TransfusionMenu_Move_Active=false;
        ACM_circulation_TransfusionMenu_Move_Active_Moving=false;
        missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex",-1];
        ACME_fnc_clinicalEpoch={7};
        ACME_fnc_updateTransfusionControls={};
        ACME_fnc_relinkInfusionBag={};
        ACME_fnc_clinicalNotice={};
        ACME_fnc_transfusionAccessValid={true};
        ACM_circulation_fnc_TransfusionMenu_UpdateBagList={};
    ''' + "ACM_circulation_fnc_TransfusionMenu_MoveBag={" + gui(source, "circulation") + "};\n" + \
        compiled("moveInfusionBag") + compiled("removeInfusionBag") + compiled("getSelectedActiveBagContext")


@pytest.mark.parametrize("caller", ["[]", "[_fluidCtrl]"])
def test_native_fluid_move_uses_lbvalue_after_infusions_are_filtered_out(caller, monkeypatch):
    # The shared helper accepts engine warnings. A ButtonClick's [control]
    # must also avoid the typed-params warning that would otherwise be hidden.
    real_run = subprocess.run

    def run_without_warnings(*args, **kwargs):
        result = real_run(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(subprocess, "run", run_without_warnings)
    execute(setup() + r'''
        // Visible row zero owns selection index two, which owns physical index four.
        // Native ButtonClick supplies [control]; its nonnumeric value must use
        // the visible list's stored selection index just like a no-arg call.
        _fluidCtrl setVariable ["fixtureValues",[2]];
    ''' + caller + r''' call ACM_circulation_fnc_TransfusionMenu_MoveBag;
        [ACM_circulation_TransfusionMenu_Move_IVBagContents isEqualTo (_physical select 4),
            "native move used visible row instead of stored selection index"] call _check;
        [count _events==1 && {((_events select 0 select 2) select 2)=="propofol"},
            "owner reservation targeted the wrong physical bag UID"] call _check;
        [(_events select 0 select 2 select 3)=="reserve","native move did not reserve"] call _check;
    ''')


def test_baseline_reproduces_wrong_bag_for_filtered_visible_row():
    old = subprocess.check_output(["git", "show", f"{BASELINE}:{NATIVE_MOVE}"], cwd=ROOT, text=True)
    execute(setup(old) + r'''
        _fluidCtrl setVariable ["fixtureValues",[2]];
        [] call ACM_circulation_fnc_TransfusionMenu_MoveBag;
        [(ACM_circulation_TransfusionMenu_Move_IVBagContents select 8)=="blood",
            "immutable B272 negative control no longer reproduces filtered-row bug"] call _check;
    ''')


def test_explicit_infusion_move_does_not_require_a_native_visible_row():
    execute(setup() + r'''
        _fluidCtrl setVariable ["fixtureSelection",-1];
        [2] call ACM_circulation_fnc_TransfusionMenu_MoveBag;
        [(ACM_circulation_TransfusionMenu_Move_IVBagContents select 8)=="propofol",
            "explicit selection index was interpreted as a visible Fluids row"] call _check;
        [count _events==1,"explicit infusion move failed to reserve"] call _check;
        [_selectionWrites isEqualTo [],"native explicit move altered list selection"] call _check;
    ''')


@pytest.mark.parametrize("index", [-1, 3, 9])
def test_invalid_move_selection_does_not_arm_or_dispatch(index):
    execute(setup() + f'''
        _fluidCtrl setVariable ["fixtureSelection",-1];
        [{index}] call ACM_circulation_fnc_TransfusionMenu_MoveBag;
        [!ACM_circulation_TransfusionMenu_Move_Active && {{_events isEqualTo []}},
            "invalid move selection mutated or dispatched"] call _check;
    ''')


@pytest.mark.parametrize("tracked,want_uid,want_index", [(-1, "propofol", 4), (2, "calcium", 2)])
def test_infusion_proxy_resolves_physical_bag_without_selecting_a_fluid_row(tracked, want_uid, want_index):
    execute(setup() + f'''
        missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex",{tracked}];
        [call ACME_fnc_moveInfusionBag,"infusion move proxy rejected a valid selection"] call _check;
        [ACM_circulation_TransfusionMenu_Move_IVBagContents isEqualTo (_physical select {want_index}),
            "infusion move proxy lost stable physical index"] call _check;
        [count _events==1 && {{(_events select 0 select 2 select 2)=="{want_uid}"}},
            "infusion proxy reserved another physical bag"] call _check;
        [_selectionWrites isEqualTo [] && {{[_fluidCtrl] call _curSel==0}},
            "infusion proxy selected an unrelated or nonexistent Fluids row"] call _check;
        [count _waits==1,"selected dose did not retain the native move-completion relink"] call _check;
    ''')


@pytest.mark.parametrize("action,operation", [("moveInfusionBag", "bagMove"), ("removeInfusionBag", "infusionRemove")])
@pytest.mark.parametrize("menu,allowed", [("infusion", True), ("bag", False), ("", False)])
def test_hidden_infusion_actions_require_their_own_popover(action, operation, menu, allowed):
    result = str(allowed).lower()
    execute(setup() + f'''
        _infCtrl setVariable ["fixtureShown",false];
        _displayFixture setVariable ["ACME_txActionMenu","{menu}"];
        private _accepted=call ACME_fnc_{action};
        [_accepted isEqualTo {result},"hidden infusion action used the wrong popover context"] call _check;
        [count _events=={int(allowed)},"hidden action incorrectly dispatched or failed to dispatch"] call _check;
        if ({result}) then {{
            [(_events select 0 select 1)=="{operation}" && {{(_events select 0 select 2 select 2)=="propofol"}},
                "hidden action targeted another bag"] call _check;
        }};
        [_selectionWrites isEqualTo [] && {{[_fluidCtrl] call _curSel==0}},
            "hidden infusion action mutated unrelated Fluids selection"] call _check;
    ''')


@pytest.mark.parametrize("pane,own_menu,index,kind", [("transfusion", "bag", 1, "Blood"), ("infusion", "infusion", 4, "ACME_Propofol")])
@pytest.mark.parametrize("menu", ["", "bag", "infusion", "inventory"])
@pytest.mark.parametrize("shown", [False, True])
def test_generic_resolver_keeps_exact_context_and_accepts_only_own_hidden_popover(pane, own_menu, index, kind, menu, shown):
    allowed = shown or menu == own_menu
    execute(setup() + f'''
        private _c=[_fluidCtrl,_infCtrl] select ("{pane}"=="infusion");
        _c setVariable ["fixtureShown",{str(shown).lower()}];
        _displayFixture setVariable ["ACME_txActionMenu","{menu}"];
        private _context=["{pane}"] call ACME_fnc_getSelectedActiveBagContext;
        [(_context isNotEqualTo []) isEqualTo {str(allowed).lower()},
            "resolver accepted an unrelated hidden pane or lost its own popover"] call _check;
        if ({str(allowed).lower()}) then {{
            [(_context select 0) isEqualTo _patient && {{(_context select 1)=="leftarm"}}
                && {{(_context select 2)=={index}}} && {{(_context select 3)=="{kind}"}}
                && {{(_context select 5)==0}} && {{(_context select 6)}}
                && {{(_context select 12)==0}},
                "resolver confused visible row, selection tuple, physical index, or access"] call _check;
        }};
        [_selectionWrites isEqualTo [],"read-only resolver changed a list selection"] call _check;
    ''')


@pytest.mark.parametrize("argument", ['"auto"', '[]'])
def test_automatic_and_nonstring_caller_context_resolves_owning_infusion_pane(argument):
    execute(setup() + f'''
        _displayFixture setVariable ["ACME_txActivePane","infusion"];
        _displayFixture setVariable ["ACME_txActionMenu","infusion"];
        _infCtrl setVariable ["fixtureShown",false];
        private _context=[{argument}] call ACME_fnc_getSelectedActiveBagContext;
        [count _context==13 && {{(_context select 2)==4}},
            "automatic/PFH caller lost its exact hidden infusion context"] call _check;
    ''')
