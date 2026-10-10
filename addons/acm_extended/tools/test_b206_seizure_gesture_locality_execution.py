"""Execute seizure presentation against Arma's server-only owner lookup contract.

The real sync function runs; locality, clientOwner, owner, and animation commands
are explicit engine fixtures. Network latency and actual gesture rendering are
outside SQF-VM's scope.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, read


def setup(server=False, local=False, interface=True, owner=0, client=11, session_owner=11):
    source = read("seizureGestureSync")
    # Replace engine boundaries before the shared adapter's default locality.
    for old, new in {
        "isServer": "_server", "hasInterface": "_interface",
        "local _patient": "_local", "alive _patient": "_living",
        "owner _patient": "_ownerId", "clientOwner": "_clientId",
        "objectParent _patient": "_parent", "gestureState _patient": "_gestureState",
    }.items():
        source = re.sub(r"(?<!\w)" + re.escape(old) + r"\b", lambda _: new, source)
    source = source.replace('_patient switchGesture "GestureEmpty";', '_played pushBack "GestureEmpty"; _gestureState = "";')
    source = source.replace('_patient switchGesture [_gesture, 0, 1, false];', '_played pushBack _gesture; _gestureState = _gesture;')
    return f'''
        private _server = {str(server).lower()};
        private _local = {str(local).lower()};
        private _interface = {str(interface).lower()};
        private _ownerId = {owner}; private _clientId = {client};
        private _validSession = [7, {session_owner}, 3];
    ''' + r'''
        private _living = true; private _parent = objNull;
        private _gestureState = ""; private _played = [];
        _patient setVariable ["ACME_clinicalEpoch", 7];
        _patient setVariable ["ACME_seizure_motionSession", _validSession];
        _patient setVariable ["ACME_seizure_observerSession", []];
    ''' + 'ACME_fnc_clinicalEpoch = {' + adapt(read("clinicalEpoch")) + '};\n' + \
        'private _sync = {' + adapt(source) + '};\n'


@pytest.mark.parametrize("settings", [
    {"local": True, "owner": 0, "client": 11},  # Owning player client.
    {"local": True, "interface": False, "owner": 0, "client": 11},  # Headless owner.
    {"local": False, "owner": 0, "client": 12},  # Remote rendering client.
    {"server": True, "local": True, "owner": 2, "client": 2, "session_owner": 2},  # Hosted owner.
    {"server": True, "local": False, "owner": 11, "client": 2},  # Host observes client casualty.
    {"server": True, "local": True, "interface": False, "owner": 2, "client": 2, "session_owner": 2},
])
def test_valid_session_renders_on_owner_and_interface_observers(settings):
    execute(setup(**settings) + r'''
        private _result = [_patient, _validSession, "ACME_SeizureSpasm0", true] call _sync;
        [_result && {_played isEqualTo ["ACME_SeizureSpasm0"]}, "valid owner session failed presentation"] call _check;
        [_patient, _validSession, "ACME_SeizureSpasm4", true] call _sync;
        [count _played == 2, "same session could not advance gesture"] call _check;
        [(_patient getVariable "ACME_seizure_observerSession") isEqualTo _validSession, "session token was not retained"] call _check;
    ''')


@pytest.mark.parametrize("settings", [
    {"local": True, "owner": 0, "client": 12},
    {"server": True, "local": False, "owner": 12, "client": 2},
    {"interface": False, "local": False, "owner": 0},
])
def test_known_wrong_owner_or_non_rendering_machine_does_not_play(settings):
    execute(setup(**settings) + r'''
        private _result = [_patient, [7, 11, 3], "ACME_SeizureSpasm0", true] call _sync;
        [!_result && {_played isEqualTo []}, "invalid owner or non-rendering machine played gesture"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_living = false;',
    '_patient setVariable ["ACME_clinicalEpoch", 8];',
    '_patient setVariable ["ACME_roc_paralyzed", true];',
    '_parent = missionNamespace;',
])
def test_remote_observer_retains_death_reset_paralysis_and_vehicle_guards(change):
    execute(setup() + change + r'''
        private _result = [_patient, [7, 11, 3], "ACME_SeizureSpasm0", true] call _sync;
        [!_result && {_played isEqualTo []}, "invalid clinical state revived visible seizure"] call _check;
    ''')


def test_owner_rejects_delayed_start_after_local_session_has_ended():
    execute(setup(local=True) + r'''
        _patient setVariable ["ACME_seizure_motionSession", []];
        private _result = [_patient, [7, 11, 3], "ACME_SeizureSpasm0", true] call _sync;
        [!_result && {_played isEqualTo []}, "retired local sequence restarted"] call _check;
    ''')


def test_remote_stop_matches_session_without_owner_lookup():
    execute(setup() + r'''
        [_patient, [7, 11, 3], "ACME_SeizureSpasm0", true] call _sync;
        [_patient, [7, 11, 2], "", false] call _sync;
        [count _played == 1, "stale stop cleared newer observer session"] call _check;
        [_patient, [7, 11, 3], "", false] call _sync;
        [_played isEqualTo ["ACME_SeizureSpasm0", "GestureEmpty"], "matching stop did not clear remote gesture"] call _check;
    ''')
