"""Run dead-patient clamp input through production selection, owner and redraw.

Native display/control handles, locality and transport are explicit boundaries.
Mouse release executes the registered production callback; scroll, selection,
owner routing, clamp mutation and publication run their actual SQF decisions.
These simulations do not certify Arma pointer routing or transport timing.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from source_scan import lex, matching
from test_b273_transfusion_actions import gui
from test_b274_clamp_overlay import redraw_setup
from test_b288_transfusion_infusion_selection import fixture as selection_fixture
from test_menu_death_lifecycle import execute, read


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def mouse_release():
    source = read("onClampLoad")
    tokens = lex(source)
    pairs = matching(tokens)
    starts = [i + 2 for i, token in enumerate(tokens)
              if token.kind == "string" and token.value == "MouseButtonUp"
              and tokens[i + 1].value == "," and tokens[i + 2].value == "{"]
    assert len(starts) == 1
    start = starts[0]
    return source[tokens[start].offset:tokens[pairs[start]].offset + 1]


def compiled(name):
    source = read(name).replace("local _patient", "_ownerLocal")
    source = source.replace("owner _patient", "_patientOwner")
    source = source.replace("isEqualType objNull", "isEqualType profileNamespace")
    # SQF-VM lacks native finite; these cases supply only finite numeric values
    # or a separately rejected string. Native nonfinite values are not certified.
    source = re.sub(r'\bfinite (_\w+)', r'(\1 isEqualType 0)', source)
    source = source.replace("diag_frameno", "_frame")
    source = source.replace("findDisplay 86200", "_clampDisplayFixture")
    source = gui(source)
    return f"ACME_fnc_{name}={{" + source + "};\n"


def fixture():
    return selection_fixture() + r'''
        private _ownerLocal=true;
        private _patientOwner=2;
        private _frame=1;
        private _published=[];
        private _pendingPackets=[];
        private _resultPackets=[];
        private _fixtureEpoch=7;
        ACME_fnc_clinicalEpoch={_fixtureEpoch};
        CBA_fnc_targetEvent={
            if ((_this select 0)=="ACME_ownerCommand") then {_pendingPackets pushBack +_this;}
            else {_resultPackets pushBack +_this;};
        };
        ACME_fnc_setVarNet={params ["_p","_key","_value"];
            _published pushBack [_key,_value];_p setVariable [_key,_value];};
        // Complete clinical row emitted by infusionRegisterCore.
        _entries=[["dose-a","leftarm",2,"Saline",0,true,-1,100,-1,100,100,
            "Epinephrine","Epinephrine_IV",10,10,0,CBA_missionTime,0,CBA_missionTime,
            600,20,120,1,"calcium",0,0,0.1,1]];
        call _publish;
        call ACME_fnc_openRollerClamp;
        _clampDisplayFixture=missionNamespace;
        private _productionSelector=ACME_fnc_getSelectedInfusionEntryIndexes;
    ''' + redraw_setup() + r'''
        ACME_fnc_getSelectedInfusionEntryIndexes=_productionSelector;
        uiNamespace setVariable ["ACME_RollerClamp_Position",1];
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",false];
        uiNamespace setVariable ["ACME_RollerClamp_ScrollFrame",-1];
        uiNamespace setVariable ["ACME_RollerClamp_Edit",[]];
        uiNamespace setVariable ["ACME_RollerClamp_DLG",_clampDisplayFixture];
        uiNamespace setVariable ["ACME_RollerClamp_InitDisplay",_clampDisplayFixture];
        uiNamespace setVariable ["ACME_RollerClamp_Session",[_clampDisplayFixture,ACE_player,1,0]];
        missionNamespace setVariable ["ACME_infusion_clampScrollStep",0.1];
        missionNamespace setVariable ["ACME_infusion_clampScrollInvert",false];
        missionNamespace setVariable ["ACME_infusion_dropSets",[10,15,20,60]];
        ACME_fnc_playClampSfx={};
    ''' + "".join(compiled(name) for name in (
        "infusionMedicationStateCommit", "infusionClampLocal", "ownerDispatch",
        "setClampPosition", "scrollClamp", "cycleDropSet", "toggleClamp", "clampResult"
    )) + "private _release=" + gui(mouse_release()) + ";\n" + r'''
        private _deliver={
            private _packets=+_pendingPackets;_pendingPackets=[];
            _ownerLocal=true;
            {(_x select 1) call ACME_fnc_ownerDispatch;} forEach _packets;
        };
        private _deliverResults={
            private _packets=+_resultPackets;_resultPackets=[];
            {(_x select 1)call ACME_fnc_clampResult;}forEach _packets;
        };
        private _position={
            ((_patient getVariable ["ACME_infusion_BagMedications",[]]) select 0) select 22
        };
        private _readout={
            call ACME_fnc_updateClampDialog;
            uiNamespace getVariable ["ACME_RollerClamp_Position",-1]
        };
    '''


@pytest.mark.parametrize("alive", [False, True])
@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("input_kind,expected", [
    ("release", 0.37), ("scroll", 0.9), ("toggle", 0)
])
def test_clamp_input_commits_on_the_patient_owner_and_survives_redraw(alive, remote, input_kind, expected):
    inputs = {
        "release": r'''
            uiNamespace setVariable ["ACME_RollerClamp_Dragging",true];
            uiNamespace setVariable ["ACME_RollerClamp_Position",0.37];
            uiNamespace setVariable ["ACME_RollerClamp_DownTime",_nowTime-1];
            uiNamespace setVariable ["ACME_RollerClamp_ReleaseOnUp",false];
            [_infCtrl,0] call _release;
        ''',
        "scroll": "[_infCtrl,-1] call ACME_fnc_scrollClamp;",
        "toggle": "call ACME_fnc_toggleClamp;",
    }
    execute(fixture() + f'''
        _patientAlive={str(alive).lower()};
        _ownerLocal={str(not remote).lower()};
    ''' + inputs[input_kind] + f'''
        if ({str(remote).lower()}) then {{
            [count _pendingPackets==1,"remote input was not routed to patient owner"] call _check;
            [call _position==1,"remote caller mutated authoritative medication state"] call _check;
            [abs ((call _readout)-{expected})<0.0001,"wheel preview reset while owner reply was in flight"] call _check;
            call _deliver;
        }};
        [abs ((call _position)-{expected})<0.0001,"owner rejected clamp input or changed its value"] call _check;
        [abs ((call _readout)-{expected})<0.0001,"accepted clamp position reset during redraw"] call _check;
        [(_published findIf {{(_x select 0)=="ACME_infusion_BagMedications"}})>=0,
            "user clamp change was not published immediately"] call _check;
    ''')


@pytest.mark.parametrize("alive", [False, True])
@pytest.mark.parametrize("remote", [False, True])
def test_drop_set_change_uses_the_same_owner_gate_on_dead_and_alive_patients(alive, remote):
    execute(fixture() + f'''
        _patientAlive={str(alive).lower()};
        _ownerLocal={str(not remote).lower()};
        call ACME_fnc_cycleDropSet;
        if ({str(remote).lower()}) then {{call _deliver;}};
        call ACME_fnc_updateClampDialog;
        [((_patient getVariable "ACME_infusion_BagMedications") select 0 select 20)==60,
            "drop-set change was rejected"] call _check;
        [(uiNamespace getVariable ["ACME_RollerClamp_DropSet",0])==60,
            "accepted drop set reset during redraw"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_fixtureEpoch=8;",
    "_physical deleteAt 2;call _publish;",
    '(_physical select 2) set [8,"replacement"];call _publish;',
    '(_entries select 0) set [0,"replacement-dose"];call _publish;',
])
def test_queued_dead_patient_clamp_cannot_mutate_changed_epoch_or_missing_carrier(change):
    execute(fixture() + r'''
        _patientAlive=false;
        _ownerLocal=false;
        [0.37,true] call ACME_fnc_setClampPosition;
        [count _pendingPackets==1,"fixture did not queue real owner request"] call _check;
    ''' + change + r'''
        call _deliver;
        [call _position==1,"stale request changed replacement or removed bag"] call _check;
        [_published isEqualTo [],"stale request published a clamp mutation"] call _check;
    ''')


@pytest.mark.parametrize("position", [-0.1, 1.1, '"bad"'])
def test_dead_patient_clamp_still_rejects_invalid_network_position(position):
    execute(fixture() + f'''
        _patientAlive=false;
        [_patient,"infusionClamp",[_patient,["dose-a"],7,{position},-1]] call ACME_fnc_ownerDispatch;
        [call _position==1 && {{_published isEqualTo []}},"invalid position passed the dead-patient owner gate"] call _check;
    ''')


@pytest.mark.parametrize("alive", [False, True])
def test_remote_scrolls_accumulate_and_old_acknowledgement_does_not_reset_the_latest_input(alive):
    execute(fixture() + f"_patientAlive={str(alive).lower()};" + r'''
        _ownerLocal=false;
        [_infCtrl,-1] call ACME_fnc_scrollClamp;
        _frame=_frame+1;
        [_infCtrl,-1] call ACME_fnc_scrollClamp;
        [count _pendingPackets==2,"successive native scrolls did not dispatch"] call _check;
        [abs ((call _readout)-0.8)<0.0001,"scroll reset instead of accumulating pending input"] call _check;
        [call _position==1,"preview changed authoritative state before delivery"] call _check;
        private _first=_pendingPackets deleteAt 0;
        _ownerLocal=true;
        (_first select 1) call ACME_fnc_ownerDispatch;
        _ownerLocal=false;
        [abs ((call _position)-0.9)<0.0001,"first owner response did not carry its original input"] call _check;
        [abs ((call _readout)-0.8)<0.0001,"older owner response reset the newer local input"] call _check;
        call _deliver;
        [abs ((call _readout)-0.8)<0.0001,"final acknowledged scroll position changed"] call _check;
        private _edit=uiNamespace getVariable ["ACME_RollerClamp_Edit",[]];
        [count _edit==10 && {_edit select 8},
            "latest exact receipt was not retained as confirmed display state"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    "_fixtureEpoch=8;",
    "_physical deleteAt 2;call _publish;",
    '(_physical select 2) set [8,"replacement"];call _publish;',
    '(_entries select 0) set [23,"second-access"];call _publish;',
])
def test_pending_preview_is_retired_when_its_patient_epoch_or_bag_context_is_invalid(change):
    execute(fixture() + r'''
        _patientAlive=false;
        _ownerLocal=false;
        [_infCtrl,-1] call ACME_fnc_scrollClamp;
        [abs ((call _readout)-0.9)<0.0001,"fixture did not retain an in-flight preview"] call _check;
    ''' + change + r'''
        call ACME_fnc_updateClampDialog;
        [(uiNamespace getVariable ["ACME_RollerClamp_Edit",[]]) isEqualTo [],
            "invalidated bag or clinical epoch retained a stale clamp preview"] call _check;
    ''')


def test_unacknowledged_preview_expires_and_returns_to_authoritative_position():
    """Retain the case ID while requiring exact confirmation, never timer expiry."""
    execute(fixture() + r'''
        _patientAlive=false;
        _ownerLocal=false;
        [_infCtrl,-1] call ACME_fnc_scrollClamp;
        [abs ((call _readout)-0.9)<0.0001,"fixture did not retain in-flight preview"] call _check;
        _nowTime=_nowTime+20;
        [abs ((call _readout)-0.9)<0.0001,"wall time discarded an unconfirmed owner request"] call _check;
        private _edit=uiNamespace getVariable ["ACME_RollerClamp_Edit",[]];
        [count _edit==10 && {!(_edit select 8)},"prolonged delay lost the Applying receipt state"]call _check;
        call _deliver;
        [abs ((call _readout)-0.9)<0.0001,"exact owner confirmation changed the requested position"]call _check;
        _edit=uiNamespace getVariable ["ACME_RollerClamp_Edit",[]];
        [count _edit==10 && {_edit select 8},"exact owner echo did not confirm prolonged input"]call _check;
    ''')


def test_owner_rejects_ambiguous_duplicate_physical_uid_even_on_a_dead_patient():
    execute(fixture() + r'''
        _patientAlive=false;
        _physical pushBack (+(_physical select 2));
        call _publish;
        [_patient,"infusionClamp",[_patient,["dose-a"],7,0.37,-1]] call ACME_fnc_ownerDispatch;
        [call _position==1 && {_published isEqualTo []},
            "ambiguous physical carrier identity passed owner validation"] call _check;
    ''')


def test_remote_toggle_uses_pending_state_for_a_second_click_before_owner_reply():
    execute(fixture() + r'''
        _patientAlive=false;
        _ownerLocal=false;
        call ACME_fnc_toggleClamp;
        [call _readout==0,"first toggle did not preview closed clamp"] call _check;
        call ACME_fnc_toggleClamp;
        [call _readout==1,"second toggle reused stale open state instead of reopening"] call _check;
        [count _pendingPackets==2,"second toggle did not reach owner transport"] call _check;
        call _deliver;
        [call _readout==1 && {call _position==1},"two in-flight toggles did not finish open"] call _check;
    ''')


def test_remote_drop_set_cycles_accumulate_before_owner_reply():
    execute(fixture() + r'''
        _patientAlive=false;
        _ownerLocal=false;
        call ACME_fnc_cycleDropSet;
        call ACME_fnc_cycleDropSet;
        [(uiNamespace getVariable ["ACME_RollerClamp_DropSet",0])==10,
            "second drop-set click cycled stale replicated state"] call _check;
        [count _pendingPackets==2,"drop-set cycles did not both reach owner transport"] call _check;
        call _deliver;
        call ACME_fnc_updateClampDialog;
        [((_patient getVariable "ACME_infusion_BagMedications") select 0 select 20)==10,
            "owner did not retain the latest cycled drop set"] call _check;
        [(uiNamespace getVariable ["ACME_RollerClamp_DropSet",0])==10,
            "acknowledged drop-set preview reset"] call _check;
    ''')


def test_remote_drop_set_then_scroll_retains_the_pending_drop_set():
    execute(fixture() + r'''
        _patientAlive=false;
        _ownerLocal=false;
        call ACME_fnc_cycleDropSet;
        [_infCtrl,-1] call ACME_fnc_scrollClamp;
        [abs ((call _readout)-0.9)<0.0001,"scroll lost the requested clamp position"] call _check;
        [(uiNamespace getVariable ["ACME_RollerClamp_DropSet",0])==60,
            "scroll discarded the pending drop-set selection"] call _check;
        [count _pendingPackets==2,"combined inputs did not both reach owner transport"] call _check;
        call _deliver;
        call ACME_fnc_updateClampDialog;
        private _saved=(_patient getVariable "ACME_infusion_BagMedications") select 0;
        [(_saved select 20)==60 && {abs ((_saved select 22)-0.9)<0.0001},
            "owner lost the latest clamp or pending drop-set change"] call _check;
        [(uiNamespace getVariable ["ACME_RollerClamp_DropSet",0])==60
            && {abs ((call _readout)-0.9)<0.0001},"combined input readout reset after acknowledgement"] call _check;
    ''')


def test_remote_toggle_round_trip_does_not_mistake_the_initial_replica_for_final_confirmation():
    execute(fixture() + r'''
        _patientAlive=false;
        _ownerLocal=false;
        call ACME_fnc_toggleClamp;
        call ACME_fnc_toggleClamp;
        [call _readout==1,"two rapid toggles did not preview the final open position"] call _check;
        private _first=_pendingPackets deleteAt 0;
        _ownerLocal=true;
        (_first select 1) call ACME_fnc_ownerDispatch;
        _ownerLocal=false;
        [call _position==0,"first delivered toggle did not close authoritative clamp"] call _check;
        [call _readout==1,"older opposite toggle response reset the final open preview"] call _check;
        call _deliver;
        [call _position==1 && {call _readout==1},"final toggle response did not leave the clamp open"] call _check;
        private _edit=uiNamespace getVariable ["ACME_RollerClamp_Edit",[]];
        [count _edit==10 && {_edit select 8},
            "final exact toggle receipt was not confirmed after the earlier response"] call _check;
    ''')
