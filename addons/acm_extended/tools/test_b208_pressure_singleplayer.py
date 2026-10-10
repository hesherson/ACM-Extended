"""Pressure claims must use the actual single-player zero-ID boundary.

The production validator/ledger/start/claim/ACK run against explicitly declared
engine identity values. This is not an Arma transport or animation test.
"""
import pytest

from test_b207_claim_lifecycle import setup
from test_b206_direct_pressure_network import network_source
from test_menu_death_lifecycle import execute, read


def singleplayer():
    return setup() + r'''
        missionNamespace setVariable ["TEST_multiplayer",false];
        _machine = 0;
        _medic setVariable ["TEST_owner",0];
        _patient setVariable ["TEST_owner",0];
        private _notices = [];
        ace_common_fnc_displayTextStructured = {_notices pushBack (_this select 0);};
    '''


@pytest.mark.parametrize("part", ["head","body","leftarm","rightarm","leftleg","rightleg"])
@pytest.mark.parametrize("epoch", [0,1], ids=["new-patient","after-reset"])
def test_singleplayer_zero_identity_pressure_starts_on_every_site(part, epoch):
    execute(singleplayer() + f'''
        _patient setVariable ["ACME_clinicalEpoch",{epoch}];
        [_medic,_patient,"{part}"] call ACME_fnc_directPressureStart;
        0 call _deliver; 0 call _deliver;
        [count _started == 1,"single-player pressure rejected an empty site"] call _check;
        [count _notices == 0,"successful pressure displayed a refusal"] call _check;
        [(_patient getVariable ["ACME_DP_press_{part}",objNull]) isEqualTo _medic,"single-player pressure marker missing"] call _check;
    ''')


def test_singleplayer_zero_identity_hang_bag_uses_same_validation():
    execute(singleplayer() + r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        0 call _deliver; 0 call _deliver;
        [count _hangActivated == 1,"single-player bag claim rejected zero identity"] call _check;
    ''')


def test_singleplayer_duplicate_pending_claim_keeps_first_deadline():
    execute(singleplayer() + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        private _first = +(_wire select 0);
        0 call _deliver;
        private _claim = +(_patient getVariable ["ACME_DP_claim_leftarm",[]]);
        _networkTime = 1002;
        _wire pushBack _first; 1 call _deliver;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo _claim,"zero-ID pending claim discarded or extended"] call _check;
        [((_wire select 1 select 1) select 4),"duplicate pending SP request was rejected"] call _check;
        [((_wire select 1 select 1) select 7) == 1003,"duplicate changed immutable grant deadline"] call _check;
    ''')


def test_singleplayer_pending_claim_survives_reconciliation():
    src = read("transientStateReconcile")
    region = src.split("// BVM reservation.",1)[0] + "// Direct Pressure claims and clinical markers." + src.split("// Direct Pressure claims and clinical markers.",1)[1].split("// Progressive bandage records.",1)[0]
    execute(singleplayer() + "private _reconcile={" + network_source("transientStateReconcile",region) + r'''};
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver;
        [_patient] call _reconcile;
        _networkTime=1002.5; CBA_missionTime=12.5;
        [_patient] call _reconcile;
        [count (_patient getVariable ["ACME_DP_claim_leftarm",[]]) == 5,"reconcile discarded a valid SP pending claim"] call _check;
        0 call _deliver;
        [count _started == 1,"pending SP claim never activated"] call _check;
    ''')


@pytest.mark.parametrize("patient_owner", [2,8,9,7])
def test_multiplayer_still_rejects_zero_identity(patient_owner):
    execute(setup() + f'''
        _patient setVariable ["TEST_owner",{patient_owner}]; _machine={patient_owner};
        [_patient,"claim",[_medic,"leftarm","zero",0,0,_networkTime]] call ACME_fnc_directPressureClaimLocal;
        [!((_wire select 0 select 1) select 4),"multiplayer accepted invalid zero identity"] call _check;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"invalid multiplayer claim reserved site"] call _check;
    ''')


@pytest.mark.parametrize("invalidate,reason", [
    ('_distance=20;', "out-of-range"),
    ('_networkTime=1006;', "request-expired"),
    ('_patient setVariable ["ACME_clinicalEpoch",1];', "patient-epoch"),
    ('missionNamespace setVariable ["ACME_sys_dp",false];', "system-disabled"),
    ('(_wire select 0 select 1 select 2) set [4,0];', "provider-identity"),
])
def test_unrelated_refusals_never_report_an_occupied_site(invalidate, reason):
    execute(setup() + r'''
        private _notices=[];
        ace_common_fnc_displayTextStructured={_notices pushBack (_this select 0);};
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
    ''' + invalidate + r'''
        0 call _deliver; 0 call _deliver;
        [count _started == 0,"rejected request activated pressure"] call _check;
        [count _notices == 1,"rejection must explain why it did not start"] call _check;
        [((_notices select 0) find "already being maintained") < 0,"unrelated refusal misreported contention"] call _check;
    ''' + f'''
        [((_medic getVariable ["ACME_DP_LastClaimFailure",[]]) select 2) == "{reason}","specific rejection reason lost"] call _check;
    ''')


def test_real_contention_keeps_specific_busy_message():
    execute(setup() + r'''
        private _other=parsingNamespace;
        _other setVariable ["TEST_owner",11];
        _machine=2;
        [_patient,"claim",[_other,"leftarm","other",0,11,_networkTime]] call ACME_fnc_directPressureClaimLocal;
        _wire=[];
        _machine=7;
        private _notices=[];
        ace_common_fnc_displayTextStructured={_notices pushBack (_this select 0);};
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver; 0 call _deliver;
        [count _started == 0,"competing provider stole site"] call _check;
        [(_notices select 0) == "Direct pressure is already being maintained on this site.","real contention did not explain occupied site"] call _check;
        [((_medic getVariable ["ACME_DP_LastClaimFailure",[]]) select 2) == "site-busy","busy reason lost"] call _check;
    ''')


def test_delayed_accepted_reply_explains_expiry_instead_of_silently_failing():
    execute(setup() + r'''
        private _notices=[];
        ace_common_fnc_displayTextStructured={_notices pushBack (_this select 0);};
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver;
        _networkTime=1004; 0 call _deliver;
        [count _started == 0,"expired owner grant started pressure"] call _check;
        [count _notices == 1 && {(_notices select 0) == "Direct pressure confirmation timed out. Try again."},"expired grant did not explain retry"] call _check;
        [((_medic getVariable ["ACME_DP_LastClaimFailure",[]]) select 2) == "grant-expired","grant expiry reason lost"] call _check;
        0 call _deliver;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"expired grant was not released"] call _check;
    ''')


def test_hosted_local_provider_uses_its_actual_client_identity():
    execute(setup() + r'''
        _machine=2;
        _medic setVariable ["TEST_owner",2];
        // A local provider is checked with clientOwner, without relying on owner as a local-session identity.
        _engineOwner={0};
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver; 0 call _deliver;
        [count _started == 1,"hosted local provider compared against remote-owner query"] call _check;
    ''')


def test_singleplayer_target_event_can_reply_synchronously():
    execute(singleplayer() + r'''
        CBA_fnc_targetEvent={(_this select 1) call ACME_fnc_directPressureClaimAck;};
        ACME_fnc_ownerDispatch={
            params ["_p","_operation","_arguments"];
            if (_operation == "directPressureClaim") then {
                [_p,_arguments select 0,_arguments select 1] call ACME_fnc_directPressureClaimLocal;
            };
        };
        private _requested=[_medic,_patient,"body"] call ACME_fnc_directPressureStart;
        [_requested && {count _started == 1},"synchronous local reply did not activate pressure"] call _check;
        [(_medic getVariable ["ACME_DP_ClaimPending",[]]) isEqualTo [],"synchronous reply left stale pending state"] call _check;
    ''')


def test_singleplayer_zero_identity_never_admits_nonlocal_provider():
    execute(singleplayer() + r'''
        _medic setVariable ["TEST_owner",7];
        [_patient,"claim",[_medic,"leftarm","nonlocal",0,0,_networkTime]] call ACME_fnc_directPressureClaimLocal;
        [!((_wire select 0 select 1) select 4),"single-player bypass admitted a nonlocal provider"] call _check;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"nonlocal SP request reserved site"] call _check;
    ''')
