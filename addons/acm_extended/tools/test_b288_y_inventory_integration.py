"""Run Y preparation, the native picker, whole UI and opaque custody together.

Production preparation, supply receipts, pending funding, server allocation,
native-grant decisions, projection, controller and layout execute. Arma cargo,
controls/config, clock advancement and CBA transport remain explicit boundaries.
This does not certify native pointer dispatch, rendering or multiplayer timing.
"""
import re

import pytest

from test_b226_transfusion_presentation import switch_ui_setup
from test_b274_transfusion_preparation import stage_setup
from test_b279_inventory_ledger import setup as ledger_setup, adapted
from test_b288_y_used_bags import setup as used_setup
from test_b288_y_ui_workflow import selection_boundary, ui_setup, ui_boundary_warnings_are_failures
from test_historical_medication_rows import iteration_scopes
from test_menu_death_lifecycle import F, execute


def setup(used=False):
    # Native lbClear clears both contents and selection. The older picker-only
    # fixture records labels separately, so make that native boundary complete
    # before sharing its data with the full UI/controller fixture.
    picker = switch_ui_setup().replace('_rows=[];', '_rows=[];_rowData=[];')
    picker = re.sub(r'\b_sel\b', '_nativeRightSelection', picker)
    prefix = ledger_setup() + (used_setup() if used else stage_setup()) + picker
    prefix = selection_boundary(prefix)
    # This VM lacks continue. Preserve Arma's per-iteration exit semantics when
    # a second preparation publishes the unchanged existing Y payload too.
    prefix += 'ACME_fnc_inventoryLedgerCommit={' + adapted(iteration_scopes((F/'fn_inventoryLedgerCommit.sqf').read_text())) + '};'
    prefix += 'ACME_fnc_preparedInventoryCommit={' + adapted((F/'fn_preparedInventoryCommit.sqf').read_text()) + '};'
    # Config is a native boundary too. Supply declared weight-family metadata
    # explicitly instead of querying the VM's empty config tree and tolerating
    # warnings that could hide a real controller/control type error.
    classes = (F/'fn_inventoryLedgerClass.sqf').read_text()
    classes = classes.replace('getNumber (configFile >> "CfgWeapons" >> _line >> "ItemInfo" >> "mass")', '(_nativeInventoryMasses get _line)')
    classes = classes.replace('getNumber (configFile >> "CfgWeapons" >> _x >> "ItemInfo" >> "mass")', '(_nativeInventoryMasses get _x)')
    classes = classes.replace('private _cfg = configFile >> "CfgMagazines" >> _class;', 'private _cfg = _class;')
    classes = classes.replace('isClass _cfg', 'true').replace('getNumber (_cfg >> "mass")', '_mass')
    prefix += r'''
        private _nativeInventoryMasses=createHashMapFromArray [
            ["ACME_YTubing",2],["ACME_IVLine",1],
            ["ACM_BloodBag_ON_500",12.5],["ACM_FreshBloodBag_500_17",12.5],
            ["ACM_SalineBag_500",12.5],["ACME_PlasmaLyteBag_500",12.5]
        ];
    '''
    prefix += 'ACME_fnc_inventoryLedgerClass={' + adapted(classes) + '};'
    return prefix + ui_setup() + r'''
        uiNamespace setVariable ["ACME_preparedListMode",false];
        ACM_circulation_Fluids_Array=["ACM_BloodBag_ON_500","ACM_FreshBloodBag_500_17","ACM_SalineBag_500","ACME_PlasmaLyteBag_500"];
        ACM_circulation_Fluids_Array_Data=["BloodIV_ON_500","FreshBloodBag_500_17","SalineIV_500","PlasmaLyteIV_500"];
        ACME_fnc_itemList={(_this select 0) getVariable ["fixtureStock",[]]};
        ACME_fnc_itemCount={params ["_u","_class"];{_x==_class} count (_u getVariable ["fixtureStock",[]])};
        ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory={
            _this call _switchInventory;
            _fixtureRightSelection=_nativeRightSelection;
        };
        private _choose={params ["_prefix"];
            _fixtureRightSelection=_rowData findIf {(_x find _prefix)==0};
            [_fixtureRightSelection>=0,"physical picker row missing"] call _check;
            [] call ACME_fnc_updateTransfusionControls;
        };
        private _finishBuild={(_waits select 0 select 1) call (_waits select 0 select 0);};
        private _refreshInventory={
            [false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
            [] call ACME_fnc_updateTransfusionControls;
        };
    '''


def native_sources(blood="ACM_BloodBag_ON_500", action="BloodIV_ON_500", build=True):
    code = r'''
        _medic setVariable ["ACME_usedBags",[]];
        _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing","ACME_PlasmaLyteBag_500","ACME_IVLine"]];
        call _refreshInventory;
        ["ACM_BloodBag_ON_500|"] call _choose;
        [] call ACME_fnc_transfusionYTubing;
        [_controlValues get "86142:text"=="Select Flush Saline","real picker missed saline step"] call _check;
        [count _rowData==1 && {((_rowData select 0) find "ACM_SalineBag_500|")==0},"real picker offered non-saline during pairing"] call _check;
        ["ACM_SalineBag_500|"] call _choose;
        [] call ACME_fnc_transfusionYTubing;
        [_controlValues get "86142:text"=="Build Y Tubing","whole UI missed paired state"] call _check;
    '''
    if build:
        code += r'''
        [] call ACME_fnc_transfusionYTubing;
        [count _waits==1 && {_controlValues get "86142:text"=="Building..."}
            && {(_controlValues get "86142:enable") isEqualTo false},"real native sources did not enter Building"] call _check;
    '''
    return code.replace("ACM_BloodBag_ON_500", blood).replace("BloodIV_ON_500", action)


def used_sources():
    return r'''
        _medic setVariable ["fixtureStock",["ACME_YTubing"]];
        _medic setVariable ["ACME_usedBags",[+_bloodRow,+_salineRow]];
        call _refreshInventory;
        ["Blood|usedbag|USED|blood1"] call _choose;
        [] call ACME_fnc_transfusionYTubing;
        ["Saline|usedbag|USED|saline1"] call _choose;
        [] call ACME_fnc_transfusionYTubing;
        [] call ACME_fnc_transfusionYTubing;
        [count _waits==1 && {_controlValues get "86142:text"=="Building..."},"real used overlays did not enter Building"] call _check;
    '''


@pytest.mark.parametrize('blood,action', [
    ('ACM_BloodBag_ON_500','BloodIV_ON_500'),
    ('ACM_FreshBloodBag_500_17','FreshBloodBag_500_17'),
])
def test_native_picker_build_funds_one_carrier_then_next_nonblood_uses_ordinary_spike(blood,action):
    execute(setup() + native_sources(blood,action) + r'''
        CBA_missionTime=CBA_missionTime+2.5;call _finishBuild;
        [count (_medic getVariable ["ACME_inventoryPending",createHashMap])==1
            && {count (_medic getVariable ["native",[]])==0},"accepted preparation skipped pending funding"] call _check;
        [uiNamespace getVariable ["ACME_preparedListMode",false] && {([86145] call _uiNativeSize)==1},"pending prepared custody was not visible"] call _check;
        call _broker;private _ack=+(_replies select 0);call _reply;
        [count (_medic getVariable ["native",[]])==1 && {count (_medic getVariable ["ACME_inventoryPending",createHashMap])==0},"native carrier grant failed"] call _check;
        private _sets=_medic getVariable ["ACME_preparedIVSets",[]];
        [count _sets==1 && {(_sets select 0 select 8)=="yset"} && {([86145] call _uiNativeSize)==1},"settled Y set disappeared from whole UI"] call _check;
        call _finishBuild;_ack call ACME_fnc_inventoryLedgerReply;call _flush;
        [count (_medic getVariable "native")==1 && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1}
            && {count _debits==3},"replayed completion/ACK duplicated funded set or components"] call _check;
        [false] call ACME_fnc_togglePreparedSets;
        ["ACME_PlasmaLyteBag_500|"] call _choose;
        [(_controlValues get "86142:show") isEqualTo false && {(_controlValues get "86141:show") isEqualTo true}
            && {_controlValues get "86141:text"=="Spike Bag"},"next nonblood selection inherited the Y action"] call _check;
        [] call ACME_fnc_transfusionSpikeOrAdd;
        [count _waits==2,"ordinary next bag could not schedule its spike"] call _check;
        (_waits select 1 select 1) call (_waits select 1 select 0);call _flush;
        _sets=_medic getVariable ["ACME_preparedIVSets",[]];
        [count _sets==2 && {{(_x select 8)=="yset"} count _sets==1}
            && {{(_x select 8)=="premixed"} count _sets==1} && {count (_medic getVariable "native")==2},"ordinary spike was converted into another Y set"] call _check;
    ''')


def test_used_overlay_partial_volumes_survive_real_allocation_delay_and_replayed_ack():
    execute(setup(True) + used_sources() + r'''
        [(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow,_salineRow] && {count _debits==0},"building materialized or consumed partial rows early"] call _check;
        CBA_missionTime=CBA_missionTime+2.5;call _finishBuild;
        [(_medic getVariable "ACME_usedBags") isEqualTo [] && {count _debits==1},"used sources were not debited once"] call _check;
        private _sets=_medic getVariable ["ACME_preparedIVSets",[]];
        [count _sets==1 && {(_sets select 0 select 9)==183} && {(_sets select 0 select 10)==47},"pending actual backend inflated partial volumes"] call _check;
        [] call ACME_fnc_updateTransfusionControls;
        [([86145] call _uiNativeSize)==1 && {count (_medic getVariable "native")==0},"UI required native grant before displaying funded pending set"] call _check;
        call _broker;private _ack=+(_replies select 0);call _reply;
        call _finishBuild;_ack call ACME_fnc_inventoryLedgerReply;call _flush;
        _sets=_medic getVariable ["ACME_preparedIVSets",[]];
        [count _sets==1 && {(_sets select 0 select 9)==183} && {(_sets select 0 select 10)==47}
            && {count (_medic getVariable "native")==1} && {count _debits==1},"grant/replay changed exact partial Y custody"] call _check;
    ''')


def test_paused_mission_does_not_admit_another_build_or_debit_before_scheduled_commit():
    execute(setup() + native_sources() + r'''
        private _before=+(_medic getVariable "fixtureStock");private _missionAt=CBA_missionTime;
        _nowTime=_nowTime+20;[] call ACME_fnc_updateTransfusionControls;
        [] call ACME_fnc_transfusionYTubing;
        [CBA_missionTime==_missionAt && {count _waits==1} && {count _debits==0}
            && {(_medic getVariable "fixtureStock") isEqualTo _before},"wall clock funded/rescheduled a mission-clock build"] call _check;
        [_controlValues get "86142:text"=="Building..." && {(_controlValues get "86142:enable") isEqualTo false},"whole UI lost the pending build"] call _check;
        CBA_missionTime=CBA_missionTime+2.5;call _finishBuild;call _flush;
        [count (_medic getVariable "native")==1 && {count _debits==3},"delayed commit did not fund exactly one actual carrier"] call _check;
    ''')


def test_initial_render_failure_still_leaves_one_scheduled_source_funded_build():
    execute(setup() + native_sources(build=False) + r'''
        private _renderer=ACME_fnc_updateTransfusionControls;
        private _caught=false;
        ACME_fnc_updateTransfusionControls={throw "injected native render failure";};
        try {[] call ACME_fnc_transfusionYTubing;} catch {_caught=true;};
        [_caught && {count _waits==1} && {count _debits==0},"presentation failure stranded or prematurely funded the build"] call _check;
        ACME_fnc_updateTransfusionControls=_renderer;
        CBA_missionTime=CBA_missionTime+2.5;call _finishBuild;call _flush;
        [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_preparedIVSets")==1}
            && {count _debits==3},"queued build could not recover its actual funding after render failure"] call _check;
    ''')


def test_completion_render_failure_cannot_leave_actual_funding_or_busy_flags_half_settled():
    execute(setup() + native_sources() + r'''
        private _renderer=ACME_fnc_updateTransfusionControls;
        private _caught=false;
        ACME_fnc_updateTransfusionControls={throw "injected completion render failure";};
        CBA_missionTime=CBA_missionTime+2.5;
        try {call _finishBuild;} catch {_caught=true;};
        [_caught && {count (_medic getVariable "ACME_inventoryPending")==1} && {count _debits==3},"render failure lost or repeated source funding"] call _check;
        [(missionNamespace getVariable ["ACME_yBuildPending",[]]) isEqualTo []
            && {(_medic getVariable ["ACME_yBuildPending",[]]) isEqualTo []}
            && {(missionNamespace getVariable ["ACME_yPending",""])==""}
            && {(missionNamespace getVariable ["ACME_yPendingSaline",""])==""},"render failure left committed custody marked as a live recipe/build"] call _check;
        ACME_fnc_updateTransfusionControls=_renderer;
        call _flush;call _finishBuild;call _flush;
        [count (_medic getVariable "native")==1 && {count (_medic getVariable "ACME_preparedIVSets")==1}
            && {count _debits==3},"post-render recovery duplicated actual source funding"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_medic setVariable ["ACME_persistenceFrozen",true];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    'ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";',
    'missionNamespace setVariable ["ACME_yPending",""];',
])
def test_canceled_actual_build_keeps_sources_and_never_allocates_a_native_identity(change):
    execute(setup(True) + used_sources() + change + r'''
        CBA_missionTime=CBA_missionTime+2.5;call _finishBuild;call _flush;
        [(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow,_salineRow]
            && {(_medic getVariable "fixtureStock") isEqualTo ["ACME_YTubing"]} && {count _debits==0},"canceled actual build consumed source funding"] call _check;
        [(_medic getVariable ["ACME_preparedIVSets",[]]) isEqualTo [] && {count (_medic getVariable "native")==0}
            && {count (_medic getVariable "ACME_inventoryPending")==0},"canceled actual build left native/virtual funded state"] call _check;
        [(missionNamespace getVariable ["ACME_yPending",""])=="" && {(missionNamespace getVariable ["ACME_yPendingSaline",""])==""}
            && {(_medic getVariable ["ACME_yBuildPending",[]]) isEqualTo []},"canceled build left pairing or save blockers armed"] call _check;
    ''')


def test_late_allocation_ack_from_replaced_kit_cannot_materialize_into_its_successor():
    execute(setup() + native_sources() + r'''
        CBA_missionTime=CBA_missionTime+2.5;call _finishBuild;call _broker;
        private _ack=+(_replies select 0);
        _medic setVariable ["ACME_equipmentKitEpoch",1];
        _medic setVariable ["ACME_preparedIVSets",[]];
        _medic setVariable ["fixtureStock",["new-kit"]];
        call _reply;_ack call ACME_fnc_inventoryLedgerReply;
        [_medic] call ACME_fnc_inventoryLedgerReconcile;
        [(_medic getVariable "native") isEqualTo [] && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []}
            && {(_medic getVariable "fixtureStock") isEqualTo ["new-kit"]},"late grant materialized old Y funding in the new kit"] call _check;
        [(missionNamespace getVariable "ACME_inventoryTokenSequence")==1 && {count _debits==3},"retired kit reused identity or debited new supplies"] call _check;
    ''')
