"""Run the real laryngoscopy close and owner placement code with queued delivery."""
import pytest
from test_menu_death_lifecycle import adapt, execute, read


def setup(state="migrated", ejecting=False, inserted=True, epoch=7, depth=0.601):
    close = adapt(read("laryngoClose").replace("finite _depth", "true"))
    commit = adapt(read("ettMigrationStateCommit"))
    return r'''
        ACME_fnc_suctionPublish = {};
        ACME_fnc_treatmentPoseStop = {};
        ACME_fnc_laryngoFlash = {};
        ACME_fnc_ettAirwayStateCommit = {};
        ACME_fnc_suctionSfxStop = {};
        ACME_fnc_reopenMedicalMenu = {};
        private _placements = [];
        ACME_fnc_setVarNet = {params ["_p", "_key", "_value"]; _p setVariable [_key, _value];};
        ACME_fnc_ettMigrationStateCommit = {_placements pushBack _this;};
        uiNamespace setVariable ["ACME_laryngo_patient", _patient];
        uiNamespace setVariable ["ACME_laryngo_medic", objNull];
        uiNamespace setVariable ["ACME_laryngo_migrationSyncLast", [0.6, 5, false]];
        uiNamespace setVariable ["ACME_laryngo_migrationSyncNext", 10.2];
        uiNamespace setVariable ["ACME_laryngo_idealFrame", 8];
        uiNamespace setVariable ["ACME_suctionEpoch", 7];
        uiNamespace setVariable ["ACME_laryngo_migrationTubeTime", 40];
        _patient setVariable ["ACME_ETT_Depth", 0.6];
        _patient setVariable ["ACME_ETT_Frame", 5];
        _patient setVariable ["ACME_ETT_Time", 40];
    ''' + f'''
        uiNamespace setVariable ["ACME_laryngo_state", "{state}"];
        uiNamespace setVariable ["ACME_laryngo_ejecting", {str(ejecting).lower()}];
        uiNamespace setVariable ["ACME_laryngo_tubeDepth", {depth}];
        _patient setVariable ["ACME_ETT_Inserted", {str(inserted).lower()}];
        _patient setVariable ["ACME_clinicalEpoch", {epoch}];
    ''' + 'ACME_fnc_clinicalEpoch={' + adapt(read("clinicalEpoch")) + '};\n' + \
        'private _close={' + close + '};\nprivate _ownerPlacement={' + commit + '};\n'


def test_close_flushes_subthreshold_adjustment_without_waiting_for_next_snapshot():
    execute(setup() + r'''
        [] call _close;
        [count _placements == 1, "close lost final migrated depth"] call _check;
        [abs ((((_placements select 0) select 2) select 0) - 0.601) < 0.00001, "close rounded real depth"] call _check;
        [uiNamespace getVariable ["ACME_laryngo_tubeDepth", -1] == 0, "close did not clear local tube"] call _check;
        (_placements select 0) call _ownerPlacement;
        [abs ((_patient getVariable "ACME_ETT_Depth") - 0.601) < 0.00001, "owner lost queued final placement"] call _check;
    ''')


@pytest.mark.parametrize("kwargs", [
    {"state": "idle"}, {"ejecting": True}, {"inserted": False},
    {"epoch": 8}, {"depth": 0}, {"depth": 0.6},
])
def test_close_does_not_commit_abandoned_removed_stale_or_unchanged_tube(kwargs):
    execute(setup(**kwargs) + r'''
        [] call _close;
        [count _placements == 0, "close committed invalid or unchanged migration"] call _check;
    ''')


@pytest.mark.parametrize("transition", [
    '_patient setVariable ["ACME_clinicalEpoch", 8];',
    '_patient setVariable ["ACME_ETT_Inserted", false];',
    '_patient setVariable ["ACME_ETT_Time", 41];',
])
def test_final_placement_rechecks_reset_and_extubation_after_network_delivery(transition):
    execute(setup() + r'''
        [] call _close;
        [count _placements == 1, "fixture did not enqueue final depth"] call _check;
    ''' + transition + r'''
        (_placements select 0) call _ownerPlacement;
        [(_patient getVariable "ACME_ETT_Depth") == 0.6, "delayed close packet rewrote reset or removed tube"] call _check;
    ''')


def test_first_frame_adjustment_uses_initial_tube_snapshot():
    init = read("laryngoInit")
    start = init.index('// Capture the existing tube before the first render/input.')
    end = init.index('private _pfh =', start)
    seed = adapt(init[start:end])
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_laryngo_migrationSyncLast", [-1, -1, false]];
    ''' + seed + r'''
        // No migrated render has run. Wheel input moved the restored tube before closing.
        uiNamespace setVariable ["ACME_laryngo_tubeDepth", 0.601];
        [] call _close;
        [count _placements == 1, "first-frame adjustment was lost"] call _check;
        (_placements select 0) call _ownerPlacement;
        [abs ((_patient getVariable "ACME_ETT_Depth") - 0.601) < 0.00001, "first-frame adjustment not preserved"] call _check;
    ''')
