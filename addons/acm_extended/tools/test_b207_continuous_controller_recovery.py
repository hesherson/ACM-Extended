"""Execute actual controller acquisition, callback failure and exact-session recovery.

Engine locality/UI commands are adapted; intentional SQF throws propagate through
the production OnStart/perFrame callsites before the existing reconcile pass runs.
"""
import pytest

from test_menu_death_lifecycle import adapt, core, execute, read


def setup(kind="core"):
    reconcile = read("providerStateReconcile")
    reconcile = reconcile.replace("hasInterface", "_hasInterface").replace("local _provider", "_providerLocal")
    reconcile = reconcile.replace("isNull ACE_player", "(ACE_player isEqualTo objNull)")
    for name in ("_lastSeen", "_invalidAt", "_startedAt", "_requestedAt"):
        reconcile = reconcile.replace(f"finite {name}", f"({name} isEqualType 0)")
    controller = core("beginContinuousAction") if kind == "core" else adapt(read("beginStethoscopeAction"))
    # Real dialog creation is an engine boundary. Default tests are non-dialog;
    # the missing-dialog test explicitly exercises failed native display creation.
    controller = controller.replace("findDisplay _dialogID", "objNull")
    return r'''
        private _hasInterface = true;
        private _providerLocal = true;
        private _cancelled = 0;
        private _started = 0;
        private _frames = 0;
        private _caught = 0;
        private _onStart = { _started = _started + 1; (_this select 1) setVariable ["test_reserved", true]; };
        private _onCancel = { _cancelled = _cancelled + 1; (_this select 1) setVariable ["test_reserved", false]; };
        private _perFrame = {_frames = _frames + 1;};
        ACME_fnc_treatmentPoseStart = {12};
        ACME_fnc_treatmentPoseStop = {};
        private _events = [];
        CBA_fnc_localEvent = {_events pushBack _this;};
    ''' + 'ACM_core_fnc_setContinuousActionState = {' + core("setContinuousActionState").replace(', _value, _public]', ', _value]') + '};\n' + \
        'private _start = {' + controller + '};\n' + \
        'private _reconcile = {' + adapt(reconcile) + '};\n' + r'''
        private _recover = {
            CBA_missionTime = 18; _nowTime = 18; call _reconcile;
            CBA_missionTime = 19; _nowTime = 19; call _reconcile;
        };
    '''


@pytest.mark.parametrize("kind", ["core", "stethoscope"])
@pytest.mark.parametrize("phase", ["start", "frame"])
def test_failed_callback_runs_original_cleanup_once_and_allows_retry(kind, phase):
    failure = '''_onStart = { _started = _started + 1; (_this select 1) setVariable ["test_reserved", true]; throw "forced start failure"; };''' if phase == "start" else '''_perFrame = { _frames = _frames + 1; throw "forced frame failure"; };'''
    execute(setup(kind) + failure + r'''
        try {
            [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
            CBA_missionTime = 13; _nowTime = 13;
            call _tick;
        } catch {_caught = _caught + 1;};
        [_caught == 1 && {_patient getVariable ["test_reserved",false]}, "fixture did not interrupt real callback"] call _check;
        private _old = missionNamespace getVariable "ACM_core_ContinuousAction_Controller";
        call _recover;
        [_cancelled == 1 && {!(_patient getVariable ["test_reserved",true])}, "recovery skipped original cancellation"] call _check;
        [!ACM_core_ContinuousAction_Active && {ACM_core_ContinuousAction_PFH == -1}, "orphan controller remained active"] call _check;
        [!((_handlers select (_old select 5)) select 2), "orphan PFH was not removed"] call _check;
        [(_medic getVariable ["ACM_core_ContinuousAction_Session",[]]) isEqualTo [], "orphan actor reservation remained"] call _check;
        [_old select 4,_old select 5] call (_old select 3);
        [_cancelled == 1, "duplicate old worker repeated clinical cleanup"] call _check;
        _onStart = {_started = _started + 1;}; _perFrame = {};
        [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
        [ACM_core_ContinuousAction_Active && {_started == 2}, "retry did not acquire cleared controller"] call _check;
        private _new = missionNamespace getVariable "ACM_core_ContinuousAction_Controller";
        [_old select 4,_old select 5] call (_old select 3);
        [ACM_core_ContinuousAction_Active && {_cancelled == 1}, "old worker cancelled successor"] call _check;
        [(missionNamespace getVariable "ACM_core_ContinuousAction_Controller") isEqualTo _new, "old worker changed successor record"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["core", "stethoscope"])
def test_second_local_provider_cannot_steal_machine_global_controller(kind):
    execute(setup(kind) + r'''
        [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
        private _old = missionNamespace getVariable "ACM_core_ContinuousAction_Controller";
        [[missionNamespace,parsingNamespace,"body"],_onStart,_onCancel,_perFrame] call _start;
        [count _handlers == 1 && {_started == 1}, "incoming provider bypassed native exclusivity"] call _check;
        [(missionNamespace getVariable "ACM_core_ContinuousAction_Controller") isEqualTo _old, "incoming provider overwrote current actor"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["core", "stethoscope"])
@pytest.mark.parametrize("interface", [True, False])
def test_reconcile_tracks_recorded_ai_not_controlled_player(kind, interface):
    execute(setup(kind) + f'_hasInterface = {str(interface).lower()};' + r'''
        ACE_player = missionNamespace;
        [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
        CBA_missionTime = 18; _nowTime = 18;
        _medic setVariable ["ACM_core_ContinuousAction_LastSeen",18];
        call _reconcile;
        CBA_missionTime = 19; _nowTime = 19; call _reconcile;
        [ACM_core_ContinuousAction_Active && {_cancelled == 0}, "player session displaced healthy AI controller"] call _check;
        _medic setVariable ["ACM_core_ContinuousAction_LastSeen",0];
        call _recover;
        [_cancelled == 1 && {!ACM_core_ContinuousAction_Active}, "recorded AI was not recovered"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["core", "stethoscope"])
def test_cancel_callback_successor_keeps_its_controller_and_ui(kind):
    execute(setup(kind) + r'''
        private _nextPatient = parsingNamespace;
        _onCancel = {
            _cancelled = _cancelled + 1;
            [[_medic,_nextPatient,"body"],{}, {},{}] call _start;
            ACM_core_ContinuousAction_ShouldReopen = true;
        };
        [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
        ACM_core_ContinuousAction_ShouldReopen = true;
        ACM_core_ContinuousAction_Active = false;
        call _tick;
        [ACM_core_ContinuousAction_Active && {_cancelled == 1}, "old cancellation cleared successor"] call _check;
        [((missionNamespace getVariable "ACM_core_ContinuousAction_Controller") select 1) isEqualTo _nextPatient, "wrong recorded successor patient"] call _check;
        [!("ACM_core_openMedicalMenu" in (_events apply {_x select 0})), "old cancellation reopened over successor UI"] call _check;
    ''')


def test_failed_stethoscope_display_creation_releases_reservation_once():
    execute(setup("stethoscope") + r'''
        private _result = [[_medic,_patient,"body"],_onStart,_onCancel,_perFrame,false,99] call _start;
        [!_result && {_started == 1} && {_cancelled == 1}, "missing scope display skipped cleanup"] call _check;
        [!(_patient getVariable ["test_reserved",true]), "missing display stranded patient state"] call _check;
        [!ACM_core_ContinuousAction_Active && {ACM_core_ContinuousAction_PFH == -1}, "missing display left a controller"] call _check;
        [count _handlers == 1 && {!((_handlers select 0) select 2)}, "failed display worker survived"] call _check;
    ''')


def test_external_bvm_cleanup_does_not_replay_recorded_cancellation():
    execute(setup() + r'''
        [[_medic,_patient,"body"],_onStart,_onCancel,_perFrame] call _start;
        // bvmCleanupLocal already releases clinical state and retires its native PFH.
        ACM_core_ContinuousAction_Active = false;
        [ACM_core_ContinuousAction_PFH] call CBA_fnc_removePerFrameHandler;
        ACM_core_ContinuousAction_PFH = -1;
        call _reconcile;
        [_cancelled == 0, "explicit BVM cleanup was repeated"] call _check;
        [(missionNamespace getVariable ["ACM_core_ContinuousAction_Controller",[]]) isEqualTo [], "retired BVM retained controller code"] call _check;
    ''')


@pytest.mark.parametrize("kind", ["core", "stethoscope"])
def test_failed_startup_cannot_be_kept_alive_by_successful_later_frames(kind):
    execute(setup(kind)+r'''
        _onStart={
            (_this select 1) setVariable ["test_reserved",true];
            throw "forced incomplete startup";
        };
        try {
            [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
        } catch {_caught=_caught+1;};
        private _old=missionNamespace getVariable "ACM_core_ContinuousAction_Controller";
        // CBA keeps dispatching an installed PFH after the original startup call failed.
        // Its perFrame callback is deliberately healthy: it must not conceal failed initialization.
        for "_i" from 11 to 22 do {
            CBA_missionTime=_i;_nowTime=_i;call _tick;call _reconcile;
        };
        [_caught==1,"startup did not throw at actual callback boundary"] call _check;
        [_cancelled==1 && {!ACM_core_ContinuousAction_Active},"successful frames sustained incomplete startup"] call _check;
        [!(_patient getVariable ["test_reserved",true]),"incomplete startup retained clinical reservation"] call _check;
        [!((_handlers select (_old select 5)) select 2),"incomplete startup kept its PFH"] call _check;
        [_old select 4,_old select 5] call (_old select 3);
        [_cancelled==1,"late worker repeated incomplete-startup cleanup"] call _check;
    ''')


def test_failed_stethoscope_startup_old_worker_cannot_wildcard_clear_successor_pose():
    # Execute the real pose-release identity guards and state/handler retirement.
    # Subsequent animation synchronization is outside this controller regression.
    pose_stop=adapt(read("treatmentPoseStop").split("// Every phase",1)[0])
    execute(setup("stethoscope")+'ACME_fnc_treatmentPoseStop={'+pose_stop+'};'+r'''
        _onStart={throw "forced failure before pose allocation";};
        try {
            [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
        } catch {};
        private _old=missionNamespace getVariable "ACM_core_ContinuousAction_Controller";
        call _recover;
        _onStart={};
        ACME_fnc_treatmentPoseStart={
            _medic setVariable ["ACME_treatmentPoseState",[42,"stethoscope","",2,0,-1]];
            42
        };
        [[_medic,_patient,"head"],_onStart,_onCancel,_perFrame] call _start;
        private _newPose=+(_medic getVariable "ACME_treatmentPoseState");
        [_old select 4,_old select 5] call (_old select 3);
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _newPose,"unallocated old pose token wildcard-cleared successor"] call _check;
        [ACM_core_ContinuousAction_Active && {_cancelled==1},"old incomplete startup cancelled successor"] call _check;
    ''')
