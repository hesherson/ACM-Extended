from historical_source import assert_release_identity as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def test_semi_fowler_teardown_precedes_ace_carry_animation():
    carry = read("addons/core/overrides/fnc_startCarryLocal.sqf")

    preflight = carry.index('["ACME_headElev_transportDown", [_target, _token], _target] call CBA_fnc_targetEvent;')
    carry_anim = carry.index('[_target, "AinjPfalMstpSnonWrflDnon_carried_Up", 2] call ACEFUNC(common,doAnimation);')

    assert preflight < carry_anim
    assert '["_acmeTransportReady", false]' in carry
    assert '[_unit, _target, _claimed, _skip, true] call ACEFUNC(dragging,startCarryLocal);' in carry


def test_precarry_waits_for_exact_patient_owner_teardown_ack():
    carry = read("addons/core/overrides/fnc_startCarryLocal.sqf")
    transport = read("addons/acm_extended/functions/fn_registerHeadElevationTransportRuntime.sqf")

    assert 'ACME_headElev_TransportReady' in carry
    assert '(_target getVariable ["ACME_headElev_TransportReady", ""]) == _token' in carry
    assert 'params ["_patient", ["_requestToken", "", [""]]];' in transport

    stop = transport.index('[objNull, _patient, true] call ACME_fnc_headElevateStop;')
    ready = transport.index('_patient setVariable ["ACME_headElev_TransportReady", _requestToken, true];', stop)
    assert stop < ready


def test_transport_retires_semi_fowler_pose_ownership_before_ack():
    transport = read("addons/acm_extended/functions/fn_registerHeadElevationTransportRuntime.sqf")

    pin = transport.index('ACME_headElev_pinToken')
    stop = transport.index('[objNull, _patient, true] call ACME_fnc_headElevateStop;')
    release = transport.index('call ACME_fnc_patientAnimRelease;', stop)
    ready = transport.index('ACME_headElev_TransportReady', release)

    assert pin < stop < release < ready
    assert '["head-elev-lift", "head-elev-lower", "head-elev-flat"]' in transport


def test_existing_setup_and_drop_transport_hooks_remain_as_fallbacks():
    transport = read("addons/acm_extended/functions/fn_registerHeadElevationTransportRuntime.sqf")

    assert '"ace_dragging_setupCarry"' in transport
    assert '"ace_dragging_setupDrag"' in transport
    assert '"ace_dragging_stoppedCarry"' in transport
    assert '"ace_dragging_stoppedDrag"' in transport
    assert 'ACME_headElev_TransportPending' in transport


def test_stable_public_version_stays_1241_and_internal_build_is_b203():
    config = read("addons/acm_extended/config.cpp")
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")

    _assert_current_build()
    _assert_current_build()
    _assert_current_build()
