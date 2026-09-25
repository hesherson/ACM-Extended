"""Execute pending-entry heartbeats and server episode renewal from real SQF.

UI namespaces substitute engine objects; network messages are delivered explicitly.
No game engine timing or transport simulation is claimed.
"""
import pytest

from test_menu_death_lifecycle import adapt, execute, read


def heartbeat():
    source = read('chestSealNetInit')
    start = source.index('private _now = diag_tickTime;')
    end = source.index('        {\n            private _entry = ACME_CS_pending', start)
    source = source[start:end].replace('local _medic', '_isLocal')
    return adapt(source)


def setup():
    return '''
        private _isLocal = true;
        private _heartbeat = {''' + heartbeat() + '''};
        private _session = {''' + adapt(read('chestSealSession')).replace('(_x select 0) == _viewer', '(_x select 0) isEqualTo _viewer') + '''};
        ACME_CS_sessions = missionNamespace;
        uiNamespace setVariable ["ACME_CS_DLG", objNull];
        uiNamespace setVariable ["ACME_CS_SessionToken", "pending-one"];
        uiNamespace setVariable ["ACME_CS_Medic", _medic];
        uiNamespace setVariable ["ACME_CS_Patient", _patient];
        uiNamespace setVariable ["ACME_CS_sessionNextPing", 0];
    '''


def test_pending_entry_renews_captured_medic_without_dialog():
    execute(setup() + '''
        // The active player can change; the captured episode still owns renewal.
        ACE_player = missionNamespace;
        [_patient, _medic, "join", "pending-one"] call _session;
        _events = [];
        _track = _session;
        {
            _nowTime = _x;
            CBA_missionTime = _x;
            call _heartbeat;
            private _member = ((ACME_CS_sessions getVariable "casualty") select 1) select 0;
            [(_member select 0) isEqualTo _medic,"heartbeat changed owner"] call _check;
            [(_member select 1) == _x,"pending entry was not renewed"] call _check;
            [(_member select 2) == "pending-one","pending token changed"] call _check;
            [CBA_missionTime - (_member select 1) <= 15,"membership expired during prep"] call _check;
        } forEach [10, 15, 20, 25, 30, 35];
        [count _events == 6,"heartbeat did not preserve five-second cadence"] call _check;
        _nowTime = 39.9;
        call _heartbeat;
        [count _events == 6,"early heartbeat duplicated"] call _check;
        [((_events select 0) select 1) isEqualTo [_patient,_medic,"ping","pending-one"],"heartbeat payload wrong"] call _check;
    ''')


def test_invalid_provider_or_closed_episode_stops_pending_heartbeat():
    execute(setup() + '''
        uiNamespace setVariable ["ACME_CS_SessionToken", ""];
        call _heartbeat;
        uiNamespace setVariable ["ACME_CS_SessionToken", "pending-one"];
        _alive = false;
        call _heartbeat;
        _alive = true;
        _isLocal = false;
        call _heartbeat;
        _isLocal = true;
        _medic setVariable ["ACE_isUnconscious",true];
        call _heartbeat;
        _medic setVariable ["ACE_isUnconscious",false];
        uiNamespace setVariable ["ACME_CS_Medic",objNull];
        call _heartbeat;
        [count _events == 0,"invalid session continued renewal"] call _check;
    ''')


def test_late_ping_cannot_enroll_absent_viewer_or_replace_new_episode():
    execute(setup() + '''
        [_patient,"keeper","join","keep"] call _session;
        [_patient,_medic,"ping","old"] call _session;
        [count ((ACME_CS_sessions getVariable "casualty") select 1) == 1,"ping enrolled absent viewer"] call _check;
        [_patient,_medic,"join","old"] call _session;
        [_patient,_medic,"leave","old"] call _session;
        [_patient,_medic,"ping","old"] call _session;
        [count ((ACME_CS_sessions getVariable "casualty") select 1) == 1,"late ping resurrected closed viewer"] call _check;
        [_patient,_medic,"join","new"] call _session;
        CBA_missionTime = 20;
        [_patient,_medic,"ping","old"] call _session;
        [_patient,_medic,"ping",""] call _session;
        private _member = ((ACME_CS_sessions getVariable "casualty") select 1) select 1;
        [(_member select 1) == 10 && {(_member select 2) == "new"},"stale ping overwrote current episode"] call _check;
        [_patient,_medic,"ping","new"] call _session;
        _member = ((ACME_CS_sessions getVariable "casualty") select 1) select 1;
        [(_member select 1) == 20 && {(_member select 2) == "new"},"current ping failed to renew"] call _check;
    ''')


@pytest.mark.parametrize('name,mode', [('chestSealInit', 'join'), ('chestSealRequest', 'sync')])
def test_panel_join_and_snapshot_retry_preserve_episode_token(name, mode):
    source = read(name)
    start = source.index('["ACME_CS_session",')
    end = source.index('call CBA_fnc_serverEvent;', start) + len('call CBA_fnc_serverEvent;')
    execute(setup() + '\nprivate _viewer = _medic; _track = _session;\n' +
            adapt(source[start:end]) + '''
        private _member = ((ACME_CS_sessions getVariable "casualty") select 1) select 0;
        [(_member select 2) == "pending-one", "session reconstruction lost episode"] call _check;
        CBA_missionTime = 30;
        call _heartbeat;
        _member = ((ACME_CS_sessions getVariable "casualty") select 1) select 0;
        [(_member select 1) == 30, "reconstructed session rejects its heartbeat"] call _check;
    ''')


def test_pending_banner_cleanup_survives_player_change_but_preserves_new_episode():
    source = read('chestAccessPreparing').replace('ctrlDelete _oldCtrl;', '_removed pushBack _oldCtrl;')
    execute('private _preparing = {' + adapt(source) + '};' + '''
        uiNamespace setVariable ["ACME_ChestAccessPreparing",["banner","old",_patient]];
        ACE_player = missionNamespace;
        [false,_medic,_patient,"old"] call _preparing;
        [_removed isEqualTo ["banner"],"respawn left old banner visible"] call _check;
        [(uiNamespace getVariable "ACME_ChestAccessPreparing") isEqualTo [],"old banner metadata survived"] call _check;
        uiNamespace setVariable ["ACME_ChestAccessPreparing",["new-banner","new",_patient]];
        [false,_medic,_patient,"old"] call _preparing;
        [_removed isEqualTo ["banner"],"old close deleted replacement banner"] call _check;
        [((uiNamespace getVariable "ACME_ChestAccessPreparing") select 1) == "new","old close cleared replacement metadata"] call _check;
    ''')
