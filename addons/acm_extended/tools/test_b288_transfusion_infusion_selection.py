"""Execute the clamp selector against current physical bag identities.

Arma display/list primitives are explicit stand-ins; the active-bag resolver,
infusion matcher, clamp selector and dialog entry point execute production SQF.
"""
import pytest

from test_b273_transfusion_actions import compiled, gui, setup
from test_menu_death_lifecycle import execute, read


def fixture():
    selector = read("getSelectedInfusionEntryIndexes").replace(
        "isNull (findDisplay 86200)", "(_clampDisplayFixture isEqualTo objNull)")
    opener = read("openRollerClamp").replace(
        'createDialog "ACME_RollerClamp_Dialog";', "_opened = true;")
    return setup() + compiled("bagInfusionEntry") + r'''
        private _clampDisplayFixture=objNull;
        private _opened=false;
        private _notices=[];
        ace_common_fnc_displayTextStructured={_notices pushBack _this;};
        ACME_fnc_playClampSfx={};
        ACME_fnc_updateClampDialog={};
        _displayFixture setVariable ["ACME_txActivePane","infusion"];
        _infCtrl setVariable ["fixtureSelection",0];
        (_selection select 1) set [9,"calcium"];
        uiNamespace setVariable ["ACME_RollerClamp_Context",[]];
        private _dose={params ["_id","_bagId",["_index",2]];
            private _entry=[_id,"leftarm",_index,"Saline",0,true,-1,100,-1];
            _entry set [23,_bagId];_entry};
        private _entries=[["dose-a","calcium"] call _dose];
        private _publish={
            _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",_physical]]];
            _patient setVariable ["ACME_infusion_BagMedications",_entries];
        };
        call _publish;
    ''' + "ACME_fnc_getSelectedInfusionEntryIndexes={" + gui(selector) + "};\n" + \
        "ACME_fnc_openRollerClamp={" + gui(opener) + "};\n" + compiled("setClampPosition")


@pytest.mark.parametrize("topology,index", [("delete", 1), ("reorder", 4)])
def test_adjust_opens_all_additives_after_selected_physical_uid_moves(topology, index):
    change = {
        "delete": "_physical deleteAt 1;",
        "reorder": "_physical=[_physical select 0,_physical select 4,_physical select 3,_physical select 1,_physical select 2];",
    }[topology]
    execute(fixture() + r'''
        _entries pushBack (["dose-b","calcium"] call _dose);
    ''' + change + f'''
        call _publish;
        private _before=str _entries;
        private _ctx=["infusion"] call ACME_fnc_getSelectedActiveBagContext;
        [(_ctx select 2)=={index},"selected physical UID retained its old native index"] call _check;
        call ACME_fnc_openRollerClamp;
        [_opened && {{_notices isEqualTo []}},"adjust refused an identified moved infusion"] call _check;
        private _stored=uiNamespace getVariable ["ACME_RollerClamp_Context",[]];
        [(_stored select 1) isEqualTo [0,1] && {{(_stored select 2) isEqualTo ["dose-a","dose-b"]}} && {{(_stored select 3)==7}} && {{(_stored select 4)=="calcium"}},
            "clamp did not capture every additive and epoch for the selected bag"] call _check;
        [str _entries==_before,"selection wrote clinical medication state"] call _check;
    ''')


@pytest.mark.parametrize("change,allowed", [
    ('(_entries select 0) set [23,"other-bag"];', False),
    ('(_entries select 0) set [23,"orphan"];', False),
    ('(_physical select 2) set [8,"replacement"];(_selection select 1) set [9,"replacement"];', False),
    ('(_entries select 0) set [2,77];', True),
    ('(_entries select 0) set [1,"rightarm"];(_entries select 0) set [4,2];(_entries select 0) set [5,false];', True),
    ('(_entries select 0) set [23,""];', True),
    ('(_entries select 0) set [23,""];(_entries select 0) set [1,"LEFTARM"];', True),
    ('(_entries select 0) set [23,""];(_entries select 0) set [2,77];', False),
    ('(_entries select 0) set [23,""];(_entries select 0) set [4,2];', False),
    ('(_entries select 0) set [23,""];(_entries select 0) set [3,"Plasma"];', False),
    ('(_entries select 0) set [23,""];(_entries select 0) set [7,500];', False),
])
def test_identified_entries_and_exact_legacy_rows_do_not_borrow_another_bag(change, allowed):
    execute(fixture() + change + f'''
        call _publish;
        private _result=call ACME_fnc_getSelectedInfusionEntryIndexes;
        [(_result select 1) isEqualTo {"[0]" if allowed else "[]"},"entry mismatch or exact legacy compatibility was resolved incorrectly"] call _check;
    ''')


def test_multiple_identical_carriers_keep_their_own_additives():
    execute(fixture() + r'''
        private _other=+(_physical select 2);_other set [8,"neighbour"];
        _physical pushBack _other;
        _entries pushBack (["dose-neighbour","neighbour",2] call _dose);
        _entries pushBack (["dose-b","calcium",77] call _dose);
        _entries pushBack (["dose-orphan","orphan",2] call _dose);
        call _publish;
        private _result=call ACME_fnc_getSelectedInfusionEntryIndexes;
        [(_result select 1) isEqualTo [0,2],"same-looking carrier supplied another bag's medication entries"] call _check;
    ''')


def test_original_selected_uid_missing_at_same_index_does_not_open_a_replacement():
    execute(fixture() + r'''
        (_physical select 2) set [8,"replacement"];
        call _publish;
        call ACME_fnc_openRollerClamp;
        [!_opened && {count _notices==1},"stale selected UID opened same-index replacement"] call _check;
        [(uiNamespace getVariable ["ACME_RollerClamp_Context",[]]) isEqualTo [],"failed selection captured a replacement context"] call _check;
    ''')


@pytest.mark.parametrize("change,expected", [
    ('_entries pushBack (["new-additive","calcium"] call _dose);reverse _entries;', "[0,1]"),
    ('_physical deleteAt 2;', "[]"),
    ('(_physical select 2) set [8,"replacement"];', "[]"),
    ('(_entries select 0) set [23,"orphan"];', "[]"),
    ('_entries pushBack (["dose-b","other-access",3] call _dose);_capturedIds pushBack "dose-b";', "[]"),
    ('_entries pushBack (["dose-b","calcium"] call _dose);_capturedIds pushBack "missing-dose";', "[0,1]"),
    ('private _copy=+(_physical select 2);_physical pushBack _copy;', "[]"),
])
def test_open_clamp_uses_captured_medication_ids_and_one_existing_physical_uid(change, expected):
    execute(fixture() + r'''
        private _capturedIds=["dose-a"];
        _clampDisplayFixture=missionNamespace;
    ''' + change + f'''
        call _publish;
        uiNamespace setVariable ["ACME_RollerClamp_Context",[_patient,[77],_capturedIds,7]];
        private _before=str _entries;
        private _result=call ACME_fnc_getSelectedInfusionEntryIndexes;
        [(_result select 1) isEqualTo {expected},"stored clamp retargeted or lost its physical bag binding"] call _check;
        [str _entries==_before,"stored clamp validation mutated medication state"] call _check;
    ''')


def test_open_clamp_epoch_change_invalidates_captured_medication_ids():
    execute(fixture() + r'''
        _clampDisplayFixture=missionNamespace;
        uiNamespace setVariable ["ACME_RollerClamp_Context",[_patient,[0],["dose-a"],6]];
        [(call ACME_fnc_getSelectedInfusionEntryIndexes) isEqualTo [],"old clinical epoch retained its clamp context"] call _check;
    ''')


def test_captured_bag_uid_cannot_follow_a_restamped_medication_id_to_another_live_bag():
    execute(fixture() + r'''
        call ACME_fnc_openRollerClamp;
        _clampDisplayFixture=missionNamespace;
        (_entries select 0) set [23,"second-access"];
        call _publish;
        private _result=call ACME_fnc_getSelectedInfusionEntryIndexes;
        [(_result select 1) isEqualTo [],"captured physical UID followed a reused medication ID to another live carrier"] call _check;
    ''')


def test_legacy_captured_index_context_keeps_its_existing_compatibility():
    execute(fixture() + r'''
        _clampDisplayFixture=missionNamespace;
        uiNamespace setVariable ["ACME_RollerClamp_Context",[_patient,[0]]];
        [(call ACME_fnc_getSelectedInfusionEntryIndexes) isEqualTo [_patient,[0]],"legacy captured clamp context changed shape"] call _check;
    ''')


@pytest.mark.parametrize("change,expected", [
    ('_physical deleteAt 1;', "[0]"),
    ('_physical deleteAt 2;', "[]"),
    ('(_physical select 2) set [8,"replacement"];', "[]"),
    ('(_entries select 0) set [23,"second-access"];', "[]"),
])
def test_final_clamp_commit_without_either_dialog_validates_its_captured_physical_bag(change, expected):
    execute(fixture() + r'''
        call ACME_fnc_openRollerClamp;
        _displayFixture=objNull;
        _clampDisplayFixture=objNull;
    ''' + change + f'''
        call _publish;
        private _result=call ACME_fnc_getSelectedInfusionEntryIndexes;
        [(_result select 1) isEqualTo {expected},"closed-dialog clamp fallback lost or retargeted its captured bag"] call _check;
        [0.37,true] call ACME_fnc_setClampPosition;
        [count _events=={1 if expected == "[0]" else 0},"final closed-dialog clamp position was lost or dispatched for a removed/replaced bag"] call _check;
        if (count _events==1) then {{
            private _request=_events select 0;
            [(_request select 1)=="infusionClamp" && {{(_request select 2) isEqualTo [_patient,["dose-a"],7,0.37,-1]}},
                "final position did not dispatch the captured medication identity and epoch"] call _check;
        }};
    ''')


def test_final_clamp_commit_without_either_dialog_rejects_stale_epoch():
    execute(fixture() + r'''
        call ACME_fnc_openRollerClamp;
        _displayFixture=objNull;
        _clampDisplayFixture=objNull;
        ACME_fnc_clinicalEpoch={8};
        [(call ACME_fnc_getSelectedInfusionEntryIndexes) isEqualTo [],"closed-dialog fallback bypassed clinical epoch validation"] call _check;
    ''')


def test_without_either_dialog_or_stored_context_there_is_no_selection():
    execute(fixture() + r'''
        _displayFixture=objNull;
        _clampDisplayFixture=objNull;
        [(call ACME_fnc_getSelectedInfusionEntryIndexes) isEqualTo [],"missing dialogs created a clamp selection without captured context"] call _check;
    ''')


@pytest.mark.parametrize("context", [
    '[_patient,[0]]',
    '[_patient,[77],["dose-a"],7]',
])
def test_closed_dialog_fallback_preserves_legacy_stored_context_shapes(context):
    execute(fixture() + f'''
        _displayFixture=objNull;
        _clampDisplayFixture=objNull;
        uiNamespace setVariable ["ACME_RollerClamp_Context",{context}];
        [(call ACME_fnc_getSelectedInfusionEntryIndexes) isEqualTo [_patient,[0]],"validated closed-dialog fallback lost legacy context compatibility"] call _check;
    ''')
