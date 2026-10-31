"""B250: expired patient-animation reconciliation must release speed and collision custody."""
from pathlib import Path

from test_menu_death_lifecycle import adapt, execute
from test_b156_animation_choreography import patient_setup

FUNCTIONS = Path(__file__).resolve().parents[1] / "functions"


def _reconcile_setup():
    source = (FUNCTIONS / "fn_transientStateReconcile.sqf").read_text(encoding="utf-8-sig")
    fragment = source.split("// Expired patient animation lease.", 1)[1].split(
        "if !(_repairs isEqualTo []) then {", 1
    )[0]
    # SQF-VM cannot execute the Arma finite primitive. The test supplies only
    # finite numbers and separately retains the source-shape assertion.
    fragment = fragment.replace("finite _expires", "(_expires isEqualType 0)")
    return (
        patient_setup()
        + 'private _collisionRestored=0; ACME_fnc_headElevCollision={_collisionRestored=_collisionRestored+1;};'
        + 'private _repairLease={params ["_patient"]; private _netNow=_serverTime; '
        + 'private _mark={};'
        + adapt(fragment)
        + '};'
    )


def test_expired_moving_lease_releases_rate_and_keeps_token_reusable():
    execute(_reconcile_setup() + r"""
        _patient setVariable ["ACME_patientAnimLock", ["old","head-elev-lift","provider",1,9,1.5]];
        _patient setVariable ["ACME_patientAnimSpeedToken", "old"];
        _testAnimationSpeed = 1.5;
        [_patient] call _repairLease;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo [], "expired lease still locked patient"] call _check;
        [(_patient getVariable ["ACME_patientAnimSpeedToken","?"]) == "", "expired lease stranded animation speed owner"] call _check;
        [_testAnimationSpeed == 1 && {_collisionRestored == 1}, "expired lease stranded accelerated casualty/collision"] call _check;
        [! ("old" in (_patient getVariable ["ACME_patientAnimRetired",[]])), "natural expiry tombstoned a reusable transaction"] call _check;
    """)


def test_active_moving_lease_is_not_reset_by_reconciliation():
    execute(_reconcile_setup() + r"""
        _patient setVariable ["ACME_patientAnimLock", ["new","head-elev-lift","provider",1,20,1.5]];
        _patient setVariable ["ACME_patientAnimSpeedToken", "new"];
        _testAnimationSpeed = 1.5;
        [_patient] call _repairLease;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) select 0) == "new", "valid lease cleared early"] call _check;
        [_testAnimationSpeed == 1.5 && {(_patient getVariable ["ACME_patientAnimSpeedToken",""])=="new"},
            "valid lease lost acceleration"] call _check;
        [_collisionRestored == 0, "active lease reset collision mass"] call _check;
    """)


def test_malformed_expired_record_cleans_orphan_speed_token():
    execute(_reconcile_setup() + r"""
        _patient setVariable ["ACME_patientAnimLock", ["","legacy","provider",1,9,1.5]];
        _patient setVariable ["ACME_patientAnimSpeedToken", "orphan"];
        _testAnimationSpeed = 1.5;
        [_patient] call _repairLease;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo [], "malformed expired lease not cleared"] call _check;
        [(_patient getVariable ["ACME_patientAnimSpeedToken","?"]) == "", "orphan speed token not retired"] call _check;
        [_testAnimationSpeed == 1 && {_collisionRestored == 1}, "orphan speed token left casualty accelerated/collision"] call _check;
    """)


def test_expired_lease_uses_exact_token_release_instead_of_only_raw_clear():
    source = (FUNCTIONS / "fn_transientStateReconcile.sqf").read_text(encoding="utf-8-sig")
    snippet = source.split("// Expired patient animation lease.", 1)[1].split(
        'if !(_repairs isEqualTo []) then {', 1
    )[0]
    assert '[_patient, _token, false] call ACME_fnc_patientAnimRelease;' in snippet
    assert '[_patient, _speedToken, false] call ACME_fnc_patientAnimRelease;' in snippet
    assert '(_patient getVariable ["ACME_patientAnimLock", []]) isEqualTo []' in snippet
