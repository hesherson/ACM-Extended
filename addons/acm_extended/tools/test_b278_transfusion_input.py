"""Execute preparation and page handoffs against the production SQF.

Native display handles, list state and continuous-controller callbacks are engine
boundaries. The tests execute preparation gates, opener selection reset, pane
switches and navigation, including the original native action admission guard.
"""
import re
import subprocess

import pytest

from test_b156_procedure_supplies import primitives
from test_b274_transfusion_preparation import picker_setup, stage_setup
from test_b275_transfusion_return_access import setup as opener_setup
from test_menu_death_lifecycle import ROOT, adapt, execute, read


BASELINE = "18d16a5732b8d878d6e6c2f9dfdc3381e6235050"


def y_gate(source):
    # The current gate reads the production lifecycle-owned request snapshot.
    # Execute its real initializer too; the historical baseline predates it.
    intent = ''
    if 'private _yOwnsIntent =' in source:
        intent = source[source.index('private _yOwnsIntent ='):source.index('private _selCls0 =')]
    source = intent + source[source.index('private _ctrlY ='):source.index('[_display,_flTarget')]
    source = source.replace('_display displayCtrl 86142', 'profileNamespace')
    source = re.sub(r'_ctrlY ctrlSetText ([^;]+);', r'_buttonText=\1;', source)
    return primitives(adapt(source))


@pytest.mark.parametrize("existing_y,legacy_spiked", [(False, False), (True, False), (False, True), (True, True)])
def test_y_preparation_never_depends_on_selected_access_or_legacy_class_spike_state(existing_y, legacy_spiked):
    execute(r'''
        private _display=missionNamespace;private _targetPatient=_patient;
        private _selIsBlood=true;private _selValidSaline=false;
        private _yPending="";private _spikingActive=[];
        private _buttonEnabled=false;private _buttonText="";
        ACME_fnc_treatmentSupplyCount={1};
        ACME_fnc_transfusionUiSet={if ((_this select 1)=="enable") then {_buttonEnabled=_this select 2;};};
        missionNamespace setVariable ["ACME_yPendingSaline",""];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1];
    ''' + f'private _yPrepped={str(existing_y).lower()};private _normalSpiked={str(legacy_spiked).lower()};' +
        y_gate(read("updateTransfusionControls")) + r'''
        [_buttonEnabled && {_buttonText=="Spike Y tubing"},"available blood/Y components cannot stage without selecting a patient access"] call _check;
    ''')


def test_previous_y_gate_reproduces_the_existing_line_and_legacy_counter_lockout():
    old = subprocess.run(["git", "show", f"{BASELINE}:addons/acm_extended/functions/fn_updateTransfusionControls.sqf"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    execute(r'''
        private _display=missionNamespace;private _targetPatient=_patient;
        private _selIsBlood=true;private _selValidSaline=false;
        private _yPending="";private _spikingActive=[];
        private _normalSpiked=true;private _yPrepped=true;
        private _buttonEnabled=true;private _buttonText="";
        ACME_fnc_treatmentSupplyCount={1};
        ACME_fnc_transfusionUiSet={if ((_this select 1)=="enable") then {_buttonEnabled=_this select 2;};};
        missionNamespace setVariable ["ACME_yPendingSaline",""];
    ''' + y_gate(old) + r'''
        [!_buttonEnabled,"baseline did not reproduce the preparation lockout"] call _check;
    ''')


@pytest.mark.parametrize("blood,tubing,busy", [(False, 1, False), (True, 0, False), (True, 1, True)])
def test_y_start_still_requires_a_blood_selection_tubing_and_idle_preparation(blood, tubing, busy):
    execute(r'''
        private _display=missionNamespace;private _targetPatient=_patient;
        private _selValidSaline=false;private _yPending="";
        private _normalSpiked=false;private _yPrepped=false;
        private _buttonEnabled=true;private _buttonText="";
        ACME_fnc_transfusionUiSet={if ((_this select 1)=="enable") then {_buttonEnabled=_this select 2;};};
        missionNamespace setVariable ["ACME_yPendingSaline",""];
    ''' + f'private _selIsBlood={str(blood).lower()};private _spikingActive={(["busy"] if busy else [])!r};ACME_fnc_treatmentSupplyCount={{{tubing}}};'.replace("'busy'", '"busy"') +
        y_gate(read("updateTransfusionControls")) + '[!_buttonEnabled,"unavailable Y components or busy preparation became clickable"] call _check;')


def test_full_y_recipe_can_stage_before_any_access_is_established():
    execute(stage_setup() + r'''
        ACM_circulation_TransfusionMenu_Selected_AccessSite=-1;
        _rowData=["ACM_BloodBag_ON_500|BloodIV_ON_500","ACM_SalineBag_500|SalineIV_500"];
        _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
        [] call ACME_fnc_transfusionYTubing;
        _selection=1;[] call ACME_fnc_transfusionYTubing;
        [] call ACME_fnc_transfusionYTubing;
        [count _waits==1,"preparation incorrectly required patient IV/IO"] call _check;
        (_waits select 0 select 1) call (_waits select 0 select 0);
        [count (_medic getVariable ["ACME_preparedIVSets",[]])==1,"no-access preparation lost staged Y custody"] call _check;
        [uiNamespace getVariable ["ACME_preparedListMode",false],"finished set did not open prepared chooser"] call _check;
        [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText && {_bagRefreshes==0},"preparation changed patient bags"] call _check;
    ''')


def test_prepared_toggle_repaints_each_reopened_display_even_when_picker_signature_is_unchanged():
    execute(picker_setup() + r'''
        private _paints=[];
        ACME_fnc_updateTransfusionControls={_paints pushBack [_display,uiNamespace getVariable ["ACME_preparedListMode",false]];};
        [] call ACME_fnc_togglePreparedSets;
        [(_paints select 0) isEqualTo [missionNamespace,true],"first prepared click did not repaint its display"] call _check;
        // A native close/reopen supplies a new display; inventory picker state may still be identical.
        _display=profileNamespace;
        _display setVariable ["ACME_txPickerSignature",str [false,[]]];
        uiNamespace setVariable ["ACME_preparedListMode",false];
        [] call ACME_fnc_togglePreparedSets;
        [(_paints select 1) isEqualTo [profileNamespace,true],"prepared click after reopening did not paint new display"] call _check;
        [] call ACME_fnc_togglePreparedSets;
        [(_paints select 2) isEqualTo [profileNamespace,false],"return to inventory left prepared cards visible"] call _check;
        [(_display getVariable ["ACME_txActivePane",""])=="inventory","pane identity did not follow manual toggle"] call _check;
    ''')


def test_opener_discards_previous_patient_infusion_selection_before_no_access_fallback():
    execute(opener_setup() + r'''
        private _ivPresent=[];private _ioPresent=[];
        missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex",4];
        missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex",7];
        missionNamespace setVariable ["ACME_pull_selTrueIndex",7];
        [_medic,_patient,"leftarm"] call _openBeforeUi;
        [ACM_circulation_TransfusionMenu_Selected_AccessSite==-1,"opener invented access for inventory preparation"] call _check;
        [(missionNamespace getVariable "ACME_infusion_SelectedActiveInfusionSelectionIndex")==-1,"old selected row index survived reopen"] call _check;
        [(missionNamespace getVariable "ACME_infusion_SelectedActiveInfusionTrueIndex")==-1 && {(missionNamespace getVariable "ACME_pull_selTrueIndex")==-1},"old patient bag index selected new patient custody"] call _check;
    ''')


def nav_setup(nav_source=None):
    nav = (read("skPageNavigate") if nav_source is None else nav_source).replace("findDisplay 84000", "_drawDisplay").replace("findDisplay 86000", "_txDisplay")
    nav = nav.replace("isNull (_drawDisplay)", "(_drawDisplay isEqualTo objNull)").replace("isNull (_txDisplay)", "(_txDisplay isEqualTo objNull)")
    nav = nav.replace("closeDialog 0;", '_drawDisplay=objNull;_txDisplay=objNull;missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",objNull];')
    core = (ROOT / "addons/core/functions/fnc_beginContinuousAction.sqf").read_text()
    admission = core[:core.index("// Bind only a session")]
    return r'''
        private _drawDisplay=objNull;private _txDisplay=missionNamespace;
        private _queued=[];private _opens=[];private _cleanupCalls=0;
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        CBA_fnc_execNextFrame={_queued pushBack _this;};
        CBA_fnc_waitAndExecute={_queued pushBack _this;};
        ACME_fnc_skStoreEnsureIds={[]};ACME_fnc_skSetView={};
        ACM_core_fnc_setContinuousActionState={};
        uiNamespace setVariable ["ACME_pageTransitionEpoch",0];
        missionNamespace setVariable ["ACME_pageTransitionPending",false];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","rightleg"];
        private _staleArgs=[_medic,_patient,"rightleg",[],true,false,{}, {},84000];
        missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch",9];
        private _oldWorker={_cleanupCalls=_cleanupCalls+1;ACM_core_ContinuousAction_Active=false;};
        missionNamespace setVariable ["ACM_core_ContinuousAction_Controller",[_medic,_patient,9,_oldWorker,_staleArgs,3]];
    ''' + 'private _nativeAdmission={' + primitives(adapt(admission)) + ';true};' + r'''
        ACME_fnc_skOpenDraw={
            params ["_size","_target","_part"];
            if !([[_medic,_target,_part],{},{},{}] call _nativeAdmission) exitWith {};
            _opens pushBack [_target,_part,uiNamespace getVariable ["ACME_SK_RequestedView",""]];
        };
        ACM_circulation_fnc_openTransfusionMenu={_opens pushBack _this;};
    ''' + 'ACME_fnc_skPageNavigate={' + primitives(adapt(nav)) + '};'


def test_previous_navigation_reproduces_rejected_open_behind_a_closed_draw_controller():
    old = subprocess.run(["git", "show", f"{BASELINE}:addons/acm_extended/functions/fn_skPageNavigate.sqf"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    execute(nav_setup(old) + r'''
        ACM_core_ContinuousAction_Active=true;
        ["right"] call ACME_fnc_skPageNavigate;
        (_queued select 0 select 1) call (_queued select 0 select 0);
        [_opens isEqualTo [] && {_cleanupCalls==0} && {ACM_core_ContinuousAction_Active},"baseline did not reproduce rejected native open behind closed drawer"] call _check;
    ''')


@pytest.mark.parametrize("direction,view", [("left", "body"), ("right", "syringe")])
def test_transfusion_page_buttons_retire_only_closed_draw_lock_and_preserve_patient(direction, view):
    execute(nav_setup() + 'ACM_core_ContinuousAction_Active=true;' + f'["{direction}"] call ACME_fnc_skPageNavigate;' + r'''
        // Native tx unload already cleared its global patient before the queued open executes.
        [isNull (missionNamespace getVariable "ACM_circulation_TransfusionMenu_Target"),"fixture did not unload native transfusion target"] call _check;
        (_queued select 0 select 1) call (_queued select 0 select 0);
    ''' + f'''
        [_opens isEqualTo [[_patient,"rightleg","{view}"]] && {{_cleanupCalls==1}},"navigation failed on closed drawer gate or lost requested patient/page"] call _check;
    ''')


@pytest.mark.parametrize("mutation", [
    '(_staleArgs) set [8,-1];',
    'missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch",10];',
    'private _other=missionNamespace getVariable "ACM_core_ContinuousAction_Controller";_other set [0,_patient];',
])
def test_page_navigation_never_releases_an_unrelated_live_hold_or_newer_controller(mutation):
    execute(nav_setup() + 'ACM_core_ContinuousAction_Active=true;' + mutation + r'''
        ["right"] call ACME_fnc_skPageNavigate;
        (_queued select 0 select 1) call (_queued select 0 select 0);
        [_cleanupCalls==0 && {ACM_core_ContinuousAction_Active} && {_opens isEqualTo []},"page navigation preempted an unrelated active maneuver"] call _check;
    ''')


@pytest.mark.parametrize("replacement", ["epoch", "display"])
def test_delayed_page_handoff_does_not_overwrite_a_newer_open_workspace(replacement):
    change = 'uiNamespace setVariable ["ACME_pageTransitionEpoch",99];' if replacement == "epoch" else '_drawDisplay=profileNamespace;'
    execute(nav_setup() + r'''
        ["right"] call ACME_fnc_skPageNavigate;
    ''' + change + r'''
        (_queued select 0 select 1) call (_queued select 0 select 0);
        [_opens isEqualTo [] && {_cleanupCalls==0},"stale navigation callback replaced a successor display"] call _check;
    ''')


def test_same_source_teardown_lag_retries_before_native_open():
    execute(nav_setup() + r'''
        ["right"] call ACME_fnc_skPageNavigate;
        _txDisplay=missionNamespace; // Native teardown still exposes the old source for one frame.
        (_queued select 0 select 1) call (_queued select 0 select 0);
        [count _queued==2 && {_opens isEqualTo []},"closing source was abandoned or reopened before its teardown"] call _check;
        _txDisplay=objNull;
        (_queued select 1 select 1) call (_queued select 1 select 0);
        [_opens isEqualTo [[_patient,"rightleg","syringe"]],"same-source retry did not open requested page"] call _check;
    ''')


def test_same_source_teardown_retry_is_bounded_and_restores_the_source_button():
    execute(nav_setup() + r'''
        ["right"] call ACME_fnc_skPageNavigate;
        _txDisplay=missionNamespace;
        for "_i" from 0 to 20 do {(_queued select _i select 1) call (_queued select _i select 0);};
        [count _queued==21 && {_opens isEqualTo []},"teardown retries were unbounded or opened while source remained live"] call _check;
        [!(missionNamespace getVariable ["ACME_pageTransitionPending",true]),"bounded teardown failure stranded its source button"] call _check;
    ''')


def test_repeated_close_frame_click_cannot_queue_self_patient_fallback():
    execute(nav_setup() + r'''
        ["right"] call ACME_fnc_skPageNavigate;
        ["right"] call ACME_fnc_skPageNavigate;
        [count _queued==1,"second click queued another page for self after source closed"] call _check;
    ''')
