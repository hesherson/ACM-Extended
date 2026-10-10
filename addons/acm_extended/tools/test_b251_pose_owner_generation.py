"""B251: expired pose-exit callbacks cannot reclaim stance after away/back locality."""
from test_historical_pose_lifecycle import ended_setup, execute


def test_old_owner_cannot_crouch_provider_after_away_and_back():
    execute(ended_setup() + r"""
        [count _waits==1,"missing normal delayed exit"] call _check;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        _stance="STAND";
        [_waits select 0] call _deliver;
        [count _positions==0 && {count _moves==0} && {count _waits==1},
            "old owner started a crouch correction after locality round trip"] call _check;
    """)


def test_old_owner_cannot_release_nested_stance_after_away_and_back():
    execute(ended_setup() + r"""
        _stance="STAND";
        [_waits select 0] call _deliver;
        [count _waits==2,"missing final stance release"] call _check;
        _positions=[]; _moves=[];
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        [_waits select 1] call _deliver;
        [count _positions==0 && {count _moves==0},
            "nested cleanup removed new owner's stance"] call _check;
    """)


def test_stale_handoff_release_cannot_reset_stance_after_away_and_back():
    execute(ended_setup(True) + r"""
        [count _waits==2,"missing dual handoff cleanup"] call _check;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        {[_x] call _deliver;} forEach +_waits;
        [count _positions==0 && {count _moves==0},
            "old handoff callback touched newer owner stance"] call _check;
    """)


def test_unchanged_locality_still_releases_normal_and_handoff_stance():
    execute(ended_setup(True) + r"""
        [count _waits==2,"missing handoff cleanup"] call _check;
        [_waits select 0] call _deliver;
        [_positions isEqualTo ["AUTO"],"valid handoff no longer releases temporary stance"] call _check;
    """)
