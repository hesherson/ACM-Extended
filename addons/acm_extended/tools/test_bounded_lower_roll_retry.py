"""Execute actual Lower Head retries; engine calls are recorded, not rendered."""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_head_completion import setup


def begin(rollable=True, quiet=False):
    # SQF-VM does not implement finite; these fixtures use finite default durations only.
    return setup().replace("finite _rollTime", "true") + f'''
        _actualSide="back";
        ACME_fnc_chestSealCanPhysicalRoll={{{str(rollable).lower()}}};
        [_medic,_patient,{str(quiet).lower()}] call ACME_fnc_headElevateStop;
        [count _waits==1,"pre-roll continuation missing"] call _check;
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
    execute(begin(rollable,quiet) + f'''
        [abs ((_retry select 2)-{1.93 if rollable else .08})<0.0001,"roll delay changed"] call _check;
        [_retry] call _deliver;
        [!(_patient getVariable ["ACME_headElevated",true]),"current retry did not lower"] call _check;
        [(_patient getVariable ["ACME_CS_facing",""])=="front","current retry lost supine request"] call _check;
        [count _holdClears==1 && {{count _waits=={0 if quiet else 1}}},"retry lost its normal handoff"] call _check;
        private _before=[count _holdClears,count _moves,count _restores,count _collisions,count _waits];
        [_retry] call _deliver;
        [[count _holdClears,count _moves,count _restores,count _collisions,count _waits] isEqualTo _before,"duplicate retry ran twice"] call _check;
    ''' + ('''
        [_waits select 0] call _deliver;
        [_moves isEqualTo [[_patient,"ACME_HeadElevPatientRelease",2],[_patient,"ACM_LyingState",2]],"lower choreography changed"] call _check;
        [_collisions isEqualTo [[_patient,false],[_patient,true]],"normal collision recovery changed"] call _check;
    ''' if not quiet else '') + '''
        [_restores isEqualTo [["support",[_patient]],["access",[_patient]]],"normal gear recovery handoff changed"] call _check;
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
        [_death isEqualTo [[_patient]],"current dead placement lost recovery delegation"] call _check;
        [count _moves==0 && {count _collisions==0} && {count _restores==0},"dead retry ran living theatre"] call _check;
    ''')
