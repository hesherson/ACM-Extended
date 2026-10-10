"""B253: a stopped continuous worker must not keep its old provider lease after away/back."""
from pathlib import Path
from test_menu_death_lifecycle import adapt, execute

SOURCE = Path(__file__).resolve().parents[1] / "functions" / "fn_providerStateReconcile.sqf"


def _setup():
    body=SOURCE.read_text(encoding="utf-8-sig")
    # Execute only the continuous-controller reconciliation, not unrelated
    # client-side DP/preflight UI code requiring native engine objects.
    body=body.split("// Input preflight and Direct Pressure pending requests below belong",1)[0] + "\n_repairs\n"
    body=body.replace("local _provider", "true")
    # SQF-VM does not implement finite. These fixtures use numeric heartbeat values.
    body=body.replace("finite _lastSeen", "(_lastSeen isEqualType 0)")
    body=body.replace("finite _invalidAt", "(_invalidAt isEqualType 0)")
    body=body.replace("finite _startedAt", "(_startedAt isEqualType 0)")
    body=body.replace("finite _requestedAt", "(_requestedAt isEqualType 0)")
    return """
        private _cancelled=0;
        ACM_core_fnc_setContinuousActionState={
            params ["_p","_changes"];
            {if ((_x select 0)=="active") then {ACM_core_ContinuousAction_Active=_x select 1;};} forEach _changes;
        };
        private _worker={
            _cancelled=_cancelled+1;
            ACM_core_ContinuousAction_Active=false;
        };
        private _workerArgs=[];
        for "_i" from 0 to 17 do {_workerArgs pushBack 0;};
        _workerArgs set [17,0];
        _medic setVariable ["ACME_providerLocalityEpoch",0];
        _medic setVariable ["ACM_core_ContinuousAction_Session",[_patient,42]];
        _medic setVariable ["ACM_core_ContinuousAction_LastSeen",CBA_missionTime];
        ACM_core_ContinuousAction_Epoch=42;
        ACM_core_ContinuousAction_Active=true;
        ACM_core_ContinuousAction_Controller=[_medic,_patient,42,_worker,_workerArgs,4];
        ACME_fnc_ownerDispatch={};
    """ + "private _repair={"+adapt(body)+"};"


def test_departed_then_returned_owner_is_cancelled_without_heartbeat_timeout():
    execute(_setup()+r"""
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        call _repair;
        [_cancelled==0 && {ACM_core_ContinuousAction_Active},"debounce was bypassed"] call _check;
        _nowTime=_nowTime+1.5;
        call _repair;
        [_cancelled==1 && {!ACM_core_ContinuousAction_Active},"stale controller ignored locality mismatch"] call _check;
    """)


def test_healthy_locality_generation_is_never_cancelled():
    execute(_setup()+r"""
        call _repair;
        _nowTime=_nowTime+1.5;
        call _repair;
        [_cancelled==0 && {ACM_core_ContinuousAction_Active},"matching provider was cancelled"] call _check;
    """)


def test_legacy_controller_without_generation_uses_heartbeat_fallback():
    execute(_setup()+r"""
        private _old=ACM_core_ContinuousAction_Controller;
        private _args=_old select 4;
        _args deleteAt 17;
        _old set [4,_args];
        ACM_core_ContinuousAction_Controller=_old;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        call _repair;
        _nowTime=_nowTime+1.5;
        call _repair;
        [_cancelled==0 && {ACM_core_ContinuousAction_Active},"legacy session cancelled without heartbeat expiry"] call _check;
    """)


def test_recorded_worker_generation_is_last_argument_not_a_new_wire_field():
    src=SOURCE.read_text(encoding="utf-8-sig")
    assert '(_controller select 4) param [17, -1, [0]]' in src
    assert '(_provider getVariable ["ACME_providerLocalityEpoch", 0]) != _localityGeneration' in src
    worker=(Path(__file__).resolve().parents[2] / "core" / "functions" / "fnc_beginContinuousAction.sqf").read_text(encoding="utf-8-sig")
    assert 'false, _localityEpoch];' in worker
