"""Historical IDs retained; Lower Head now directly lays flat without a preliminary roll.

The delayed work under test is the accepted lower completion, not a removed roll retry.
Engine objects, scheduling, collision and animation are explicit stand-ins.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_head_completion import setup


def begin(rollable=True, quiet=False):
    # SQF-VM does not implement finite; these fixtures use finite default durations only.
    return setup().replace("finite _rollTime", "true") + f'''
        _actualSide="back";
        ACME_fnc_chestSealCanPhysicalRoll={{{str(rollable).lower()}}};
        [_medic,_patient,{str(quiet).lower()}] call ACME_fnc_headElevateStop;
        [count _rolls==0 && {{count _waits==1}},"direct lower completion missing or obsolete pre-roll returned"] call _check;
        private _retry=_waits select 0; _waits=[];
        _collisions=[]; _moves=[]; _restores=[]; _events=[]; _holdClears=[];
        _patient setVariable ["ACME_CS_facing","back"];
        _patient setVariable ["ACME_headElev_treatments",["new-workspace"]];
    '''


@pytest.mark.parametrize('token',[ 'placement:two', '' ])
@pytest.mark.parametrize('elevated',[False, True])
@pytest.mark.parametrize('rollable',[False,True])
def test_retired_pre_roll_retry_cannot_touch_a_new_placement(token,elevated,rollable):
    execute(begin(rollable) + f'''
        _patient setVariable ["ACME_headElev_startEpoch",100];
        _patient setVariable ["ACME_headElev_poseToken","{token}"];
        _patient setVariable ["ACME_headElevated",{str(elevated).lower()}];
        [_retry] call _deliver;
        [(_patient getVariable ["ACME_CS_facing",""])=="back","stale retry rewrote facing"] call _check;
        [(_patient getVariable ["ACME_headElev_poseToken",""])=="{token}","stale retry retired new placement"] call _check;
        [(_patient getVariable ["ACME_headElev_treatments",[]]) isEqualTo ["new-workspace"],"stale retry cleared new treatments"] call _check;
        [count _holdClears==0 && {{count _collisions==0}} && {{count _restores==0}} && {{count _moves==0}} && {{count _waits==0}},"stale retry changed presentation"] call _check;
    ''')


@pytest.mark.parametrize('rollable',[False,True])
@pytest.mark.parametrize('quiet',[False,True])
def test_current_pre_roll_retry_lowers_once_and_preserves_recovery(rollable,quiet):
    execute(setup() + f'''
        _actualSide="back";
        ACME_fnc_chestSealCanPhysicalRoll={{{str(rollable).lower()}}};
        [_medic,_patient,{str(quiet).lower()}] call ACME_fnc_headElevateStop;
        [count _rolls==0,"lower incorrectly added a preliminary body roll"] call _check;
        [!(_patient getVariable ["ACME_headElevated",true]),"current lower retained elevation"] call _check;
        [(_patient getVariable ["ACME_CS_facing",""])=="front","lower lost supine facing"] call _check;
        [count _holdClears==1 && {{count _waits=={0 if quiet else 1}}},"wrong completion scheduling"] call _check;
    ''' + ('''
        private _retry=_waits select 0; _waits=[];
        [abs ((_retry select 2)-(1.4/1.5))<0.000001,"authored lower delay changed"] call _check;
        [_retry] call _deliver;
        [count _moves==2,"release and rest sequence incomplete"] call _check;
        private _before=[count _holdClears,count _moves,count _restores,count _collisions,count _waits];
        [_retry] call _deliver;
        [[count _holdClears,count _moves,count _restores,count _collisions,count _waits] isEqualTo _before,"duplicate lower completion ran twice"] call _check;
    ''' if not quiet else '''
        [count _moves==0,"quiet cancellation must not replay release theatre"] call _check;
    ''') + '''
        [_restores isEqualTo [["support",[_patient]],["access",[_patient]]],"gear recovery handoff changed"] call _check;
    ''')


def test_remote_retry_has_no_local_side_effects():
    execute(begin() + '''
        _patientLocal=false;
        [_retry] call _deliver;
        [(_patient getVariable ["ACME_CS_facing",""])=="back","remote retry wrote facing"] call _check;
        [count _holdClears==0 && {count _restores==0} && {count _moves==0},"remote retry continued locally"] call _check;
    ''')


def test_dead_current_placement_keeps_existing_death_recovery():
    execute(begin() + '''
        _patientAlive=false;
        [_retry] call _deliver;
        // Death owns reset/recovery, not a stale living-animation completion.
        [count _death==0,"completion duplicated death recovery"] call _check;
        [count _moves==0 && {count _collisions==0} && {count _restores==0},"dead retry ran living theatre"] call _check;
    ''')
