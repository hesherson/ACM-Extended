from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def test_full_circulation_map_is_local_each_tick_and_publication_is_rate_limited():
    s = read("addons/acm_extended/functions/fn_circStateCommit.sqf")

    assert '_patient setVariable ["ACME_circ_State", _state, false];' in s
    assert 'ACME_circ_stateNetInterval' in s
    assert 'ACME_circ_stateNetAt' in s
    assert 'ACME_circ_stateNetSig' in s
    assert '(_now - _lastAt) >= _interval' in s
    assert '_patient setVariable ["ACME_circ_State", _state, true];' in s
    assert '"ACME_circ_State", (_sent getOrDefault ["ACME_circ_State", 0]) + 1' in s


def test_nonempty_historical_circ_map_no_longer_pins_patient_active():
    owner = read("addons/acm_extended/functions/fn_ownerRegister.sqf")
    circ = read("addons/acm_extended/functions/fn_circHandle.sqf")

    assert 'count (_patient getVariable ["ACME_circ_State", createHashMap]) > 0' not in owner
    assert '{count _circState > 0}' not in circ
    assert 'private _circNeeds =' in owner
    assert 'private _circStateNeedsTick = {' in circ


def test_recovered_patient_leaves_4hz_circulation_registry():
    s = read("addons/acm_extended/functions/fn_circHandle.sqf")

    assert 'private _keepCirc =' in s
    assert 'ACME_circ_activePatients pushBackUnique _patient;' in s
    assert 'ACME_circ_activePatients = ACME_circ_activePatients - [_patient];' in s


def test_circulation_snapshot_default_is_two_seconds():
    s = read("addons/acm_extended/functions/fn_initNetworkSyncConfig.sqf")
    assert "ACME_circ_stateNetInterval = 2.0;" in s


def test_b203_keeps_public_stable_version_1241():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    config = read("addons/acm_extended/config.cpp")

    assert 'version = "1.2.4.1";' in config
    assert 'ACME_buildBatch = "B208";' in startup
