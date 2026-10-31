"""Execute opt-in diagnostic lifecycle and sampling; engine telemetry is a fixture."""
import re

import pytest

from test_menu_death_lifecycle import execute, read
from test_historical_vial_execution import map_defaults
from source_scan import lex, matching, split_args


def setup():
    source = read("networkDiagnostics")
    for old, new in {
        "diag_tickTime": "_nowTime", "serverTime": "_serverClock",
        "diag_fps": "_fpsFixture", "diag_deltaTime": "_dtFixture",
        "hasInterface": "_interface", "isServer": "_server", "clientOwner": "7",
        "local _provider": "_providerLocal", "local _medic": "_providerLocal",
        "[objNull]": "[objNull, missionNamespace]",
        "toLowerANSI": "toLower",
    }.items():
        source = source.replace(old, new)
    source = re.sub(r"\bisNull (_\w+)", r"(\1 isEqualTo objNull)", source)
    source = re.sub(r"\bfinite (_\w+)", r"([\1] call _finite)", source)
    source = map_defaults(source)
    return r'''
        private _interface = true;
        private _server = false;
        private _providerLocal = true;
        private _serverClock = 1000;
        private _fpsFixture = 60;
        private _dtFixture = 0.016;
        private _workers = [];
        private _workerRemovals = [];
        private _finite = {params ["_value"]; _value isEqualType 0 && {abs _value < 1e30}};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        missionNamespace setVariable ["ACE_player", _medic];
        missionNamespace setVariable ["ACME_buildBatch", "B207"];
        CBA_fnc_addPerFrameHandler = {_workers pushBack _this; count _workers - 1};
        CBA_fnc_removePerFrameHandler = {_workerRemovals pushBack (_this select 0);};
    ''' + "ACME_fnc_networkDiagnostics={" + source + "};\n"


def test_default_report_sample_stop_and_unknown_operation_install_nothing():
    execute(setup() + r'''
        private _report = [] call ACME_fnc_networkDiagnostics;
        [!(_report get "active") && {count (_report get "samples") == 0}, "diagnostic not off by default"] call _check;
        [(["sample"] call ACME_fnc_networkDiagnostics) isEqualTo [], "inactive sample produced data"] call _check;
        ["stop"] call ACME_fnc_networkDiagnostics;
        ["bad-operation"] call ACME_fnc_networkDiagnostics;
        [count _workers == 0 && {count _workerRemovals == 0}, "passive operation changed worker state"] call _check;
        [isNil "ACME_networkDiagnostics_state" && {isNil "ACME_net_count"}, "passive operation changed namespace"] call _check;
    ''')


@pytest.mark.parametrize("initial", ["true", "false", "nil"])
def test_start_stop_idempotence_restores_previous_counter_flag(initial):
    execute(setup() + f'ACME_net_count={initial};' + r'''
        ACME_net_sent = createHashMapFromArray [["field", 12]];
        ["start", 2] call ACME_fnc_networkDiagnostics;
        ["start", 500] call ACME_fnc_networkDiagnostics;
        private _report = ["report"] call ACME_fnc_networkDiagnostics;
        [count _workers == 1 && {(_report get "limit") == 2}, "repeated start replaced session"] call _check;
        [((_workers select 0) select 1) == 1 && {ACME_net_count}, "incorrect worker interval/count flag"] call _check;
        ["stop"] call ACME_fnc_networkDiagnostics;
        ["stop"] call ACME_fnc_networkDiagnostics;
        [count _workerRemovals == 1, "stop removed worker more than once"] call _check;
        [(ACME_net_sent get "field") == 12, "diagnostics erased existing counters"] call _check;
    ''' + ('[isNil "ACME_net_count", "undefined flag was not restored"] call _check;' if initial == "nil" else
           f'[ACME_net_count isEqualTo {initial}, "prior counter flag lost"] call _check;'))


@pytest.mark.parametrize("requested,expected", [(0, 1), (-10, 1), (120, 120), (600, 600), (9000, 600)])
def test_sample_caps_and_automatic_stop_are_bounded(requested, expected):
    execute(setup() + f'["start",{requested}] call ACME_fnc_networkDiagnostics;' + f'''
        for "_i" from 1 to {expected + 3} do {{
            _nowTime = 10 + _i;
            ["sample"] call ACME_fnc_networkDiagnostics;
        }};
        private _report = ["report"] call ACME_fnc_networkDiagnostics;
        [!(_report get "active") && {{count (_report get "samples") == {expected}}}, "sample cap leaked samples or worker"] call _check;
        [(_report get "stopReason") == "sample_limit" && {{count _workerRemovals == 1}}, "bounded worker did not stop"] call _check;
    ''')


def test_manual_sampling_cannot_exceed_one_hz_or_replay_old_worker_after_restart():
    execute(setup() + r'''
        ACME_net_count = false;
        ["start", 3] call ACME_fnc_networkDiagnostics;
        [(["sample"] call ACME_fnc_networkDiagnostics) isEqualTo [], "start sampled before interval"] call _check;
        _nowTime = 11;
        ["sample"] call ACME_fnc_networkDiagnostics;
        [(["sample"] call ACME_fnc_networkDiagnostics) isEqualTo [], "manual sample exceeded one Hz"] call _check;
        private _oldWorker = _workers select 0;
        ["stop"] call ACME_fnc_networkDiagnostics;
        ["start", 3] call ACME_fnc_networkDiagnostics;
        _nowTime = 12;
        [_oldWorker select 2, 0] call (_oldWorker select 0);
        [count ((["report"] call ACME_fnc_networkDiagnostics) get "samples") == 0, "old worker sampled new session"] call _check;
        ["sample"] call ACME_fnc_networkDiagnostics;
        [count ((["report"] call ACME_fnc_networkDiagnostics) get "samples") == 1, "new session did not sample"] call _check;
    ''')


def test_counter_deltas_are_snapshots_and_partial_resets_are_marked():
    execute(setup() + r'''
        ACME_net_sent = createHashMapFromArray [["a",100],["b",10]];
        ACME_net_saved = createHashMapFromArray [["a",50]];
        ACME_net_nonFiniteSuppressed = createHashMapFromArray [["a",2]];
        ["start"] call ACME_fnc_networkDiagnostics;
        ACME_net_sent set ["a",103];
        ACME_net_saved set ["a",55];
        _nowTime = 11;
        private _first = ["sample"] call ACME_fnc_networkDiagnostics;
        [(_first get "helperRequestDeltas") isEqualTo [[3,false],[5,false],[0,false]], "snapshot mutated with source counters"] call _check;
        private _firstFields=_first get "helperRequestFields";
        [((_firstFields select 0) get "a") isEqualTo [3,false],"sent field delta missing"] call _check;
        [((_firstFields select 1) get "a") isEqualTo [5,false],"saved field delta missing"] call _check;
        [count (_firstFields select 2)==0,"zero field delta was reported"] call _check;
        // a resets while b increases enough to hide it in the aggregate total.
        ACME_net_sent set ["a",1]; ACME_net_sent set ["b",200];
        ACME_net_saved = createHashMap;
        _nowTime = 12;
        private _second = ["sample"] call ACME_fnc_networkDiagnostics;
        [(_second get "helperRequestDeltas") isEqualTo [[191,true],[0,true],[0,false]], "counter reset produced misleading delta"] call _check;
        private _secondFields=_second get "helperRequestFields";
        [((_secondFields select 0) get "a") isEqualTo [1,true],"reset field delta missing"] call _check;
        [((_secondFields select 0) get "b") isEqualTo [190,false],"nonreset field delta missing"] call _check;
        [((_secondFields select 1) get "a") isEqualTo [0,true],"removed field reset missing"] call _check;
        [(ACME_net_sent get "a") == 1 && {(ACME_net_sent get "b") == 200}, "sample modified helper counters"] call _check;
        private _diagReport=["report"] call ACME_fnc_networkDiagnostics;
        ["NOT wire" in (_diagReport get "counterMeaning"), "wire-stat disclaimer missing"] call _check;
        ["variable -> [request delta, counter reset]" in (_diagReport get "fieldDeltaMeaning"), "field-delta meaning missing"] call _check;
    ''')


def test_local_claim_ages_use_their_own_clocks_and_samples_omit_patient_identity():
    execute(setup() + r'''
        _medic setVariable ["ACME_DP_ClaimPending",[_patient,"leftarm","private-token",2]];
        _medic setVariable ["ACME_DP_ClaimRequestedAt",8];
        _medic setVariable ["ACME_hang_Active",true];
        _medic setVariable ["ACME_hang_Claimed",true];
        _medic setVariable ["ACME_hang_ClaimSequence",3];
        _medic setVariable ["ACME_hang_ClaimAckSequence",2];
        _medic setVariable ["ACME_hang_ClaimRequestedAt",999];
        ACME_clinical_activePatients = [_patient,_medic];
        ACME_networkCompatStatus = "incompatible";
        ACME_networkCompatLocalStatus = "ok";
        ACME_networkCompatServerBuild = "B206";
        ["start"] call ACME_fnc_networkDiagnostics;
        _nowTime = 11; _serverClock = 1004;
        private _sample = ["sample"] call ACME_fnc_networkDiagnostics;
        [(_sample get "directPressure") isEqualTo ["pending",3,false], "DP age used wrong clock"] call _check;
        [(_sample get "hangBag") isEqualTo ["renewing",5,3,2], "Hang age or renewal state wrong"] call _check;
        [((_sample get "registrySizes") select 1) isEqualTo ["ACME_clinical_activePatients",2], "registry size was not sampled"] call _check;
        [((_sample get "compatibility") select 1) == "incompatible", "compatibility status missing"] call _check;
        [!("private-token" in str _sample) && {!("NAMESPACE" in toUpper str _sample)}, "sample leaked actor/token references"] call _check;
        [(_medic getVariable "ACME_DP_ClaimPending") isEqualTo [_patient,"leftarm","private-token",2], "sample changed claim"] call _check;
    ''')


@pytest.mark.parametrize("server,interface,role", [
    (True, False, "dedicated_server"), (True, True, "listen_server"),
    (False, True, "player_client"), (False, False, "headless_client"),
])
def test_machine_role_and_invalid_telemetry_are_explicit(server, interface, role):
    execute(setup() + f'_server={str(server).lower()}; _interface={str(interface).lower()};' + r'''
        _fpsFixture = -1; _dtFixture = -1;
        ["start"] call ACME_fnc_networkDiagnostics;
        _nowTime = 11;
        private _sample = ["sample"] call ACME_fnc_networkDiagnostics;
        private _report = ["report"] call ACME_fnc_networkDiagnostics;
        [(_sample get "fps") == -1 && {(_sample get "frameDelta") == -1}, "invalid telemetry was treated as valid"] call _check;
    ''' + f'[((_report get "machine") select 0) == "{role}", "machine role incorrect"] call _check;')


def test_diagnostic_has_no_world_scan_broadcast_or_automatic_registration():
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", read("networkDiagnostics"), flags=re.S)
    for forbidden in ("allUnits", "allPlayers", "nearestObjects", "remoteExec", "publicVariable",
                      "CBA_fnc_globalEvent", "CBA_fnc_targetEvent", "setVarNet", "getPlayerUID"):
        assert forbidden not in source
    assert source.count("CBA_fnc_addPerFrameHandler") == 1
    assert "CBA_fnc_removePerFrameHandler" in source
    assert "case \"start\"" in source
    tokens = lex(source)
    pairs = matching(tokens)
    for index, token in enumerate(tokens[:-1]):
        if token.value == "setVariable":
            assert len(split_args(tokens, index + 2, pairs[index + 1], pairs)) == 2
