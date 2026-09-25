"""Execute the legacy armor helper with explicit owner/network/gear fixtures.

Actual helper control flow runs in SQF-VM; Arma objects, gear commands and
config existence are mocked. Tests do not simulate network replication.
"""
import pytest

from test_menu_death_lifecycle import adapt, execute, read


def setup():
    source = read("acmSpawnerArmor")
    for command, fixture in {
        "local _patient": "_patientLocal",
        "isPlayer _patient": "_patientIsPlayer",
        "group _patient": "_patientGroup",
        "vest _patient": "_wornVest",
        'isClass (configFile >> "CfgWeapons" >> _vestClass)': "_vestClassExists",
        "_patient addVest _vestClass;": "_added pushBack _vestClass; _wornVest = _vestClass;",
        "grpNull": "objNull",
    }.items():
        source = source.replace(command, fixture)
    return '''
        private _patientLocal = true;
        private _patientIsPlayer = false;
        private _patientGroup = 7;
        private _wornVest = "";
        private _vestClassExists = true;
        private _added = [];
        missionNamespace setVariable ["ACM_mission_TrainingCasualtyGroup", _patientGroup];
        private _repair = {''' + adapt(source) + '''};
    '''


@pytest.mark.parametrize("local", ["true", "false"])
def test_completed_patient_never_re_equips_or_forwards_repair(local):
    execute(setup() + f"_patientLocal = {local};" + '''
        _patient setVariable ["ACME_acmSpawnerPlateCarrierDone", true];
        [_patient] call _repair;
        [_added isEqualTo [], "completed patient was re-equipped"] call _check;
        [_events isEqualTo [], "completed patient forwarded stale repair"] call _check;
        [_wornVest == "", "intentional treatment removal was overwritten"] call _check;
    ''')


def test_owner_discards_repair_queued_before_completion_marker_arrived():
    execute(setup() + '''
        _patientLocal = false;
        [_patient] call _repair;
        [count _events == 1, "unmarked remote casualty lost owner routing"] call _check;
        [(_events select 0 select 0) == "ACME_acmSpawnerArmorLocal", "wrong owner event"] call _check;
        _patient setVariable ["ACME_acmSpawnerPlateCarrierDone", true];
        _patientLocal = true;
        (_events select 0 select 1) call _repair;
        [_added isEqualTo [], "delayed owner delivery redressed treated patient"] call _check;
        [count _events == 1, "delayed repair forwarded another event"] call _check;
        [_wornVest == "", "delayed repair undid intentional carrier removal"] call _check;
    ''')


def test_unmarked_legacy_casualty_is_equipped_once_and_never_repaired_again():
    execute(setup() + '''
        [_patient] call _repair;
        [_added isEqualTo ["V_PlateCarrier1_rgr"], "legacy casualty lost fallback armor"] call _check;
        [_patient getVariable ["ACME_acmSpawnerPlateCarrierDone", false], "fallback did not mark completion"] call _check;
        _wornVest = "";
        [_patient] call _repair;
        [count _added == 1 && {_wornVest == ""}, "completed fallback overwrote later removal"] call _check;
        [_events isEqualTo [], "local legacy casualty forwarded an event"] call _check;
    ''')


def test_unmarked_legacy_casualty_keeps_existing_vest():
    execute(setup() + '''
        _wornVest = "ExistingMissionVest";
        [_patient] call _repair;
        [_added isEqualTo [] && {_wornVest == "ExistingMissionVest"}, "fallback replaced existing vest"] call _check;
        [_patient getVariable ["ACME_acmSpawnerPlateCarrierDone", false], "existing vest was not marked complete"] call _check;
    ''')
