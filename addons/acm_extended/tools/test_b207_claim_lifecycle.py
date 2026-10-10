"""Execute B207 claim ordering against production SQF, with explicit transport.

The namespaces stand in for engine objects and the queue can duplicate or reorder
delivery deliberately. Production claim validation, ledger, Start, ClaimLocal,
ClaimAck and Hang Bag renewal code execute; rendering and physical teardown are
outside this fixture. These tests do not certify CBA transport or Arma timing.
"""
import re

import pytest

from test_b206_direct_pressure_network import network_source, setup as pressure_setup
from test_menu_death_lifecycle import execute, read
from historical_source import switch_case_body


def source(name, text=None):
    if text is None:
        text = read(name)
    # Fixtures supply only finite numbers. Preserve the numeric type guard while
    # replacing the engine's finite and native object/position boundaries.
    text = re.sub(r"\bfinite (_\w+)", r"(\1 isEqualType 0)", text)
    text = re.sub(r"\bfinite \((_[^()]+)\)", r"((\1) isEqualType 0)", text)
    text = text.replace("getPosASL _medic", "[0,0,0]")
    return network_source(name, text)


def setup():
    result = pressure_setup() + r'''
        private _hangActivated = [];
        private _restores = [];
        ACME_fnc_hangBagActivate = {_hangActivated pushBack _this;};
        ACME_fnc_hangBagPrepStop = {_restores pushBack _this;};
        ACME_fnc_hangBagFluidType = {"saline"};
        ACME_fnc_hangBagTick = {};
        ACME_fnc_ownerDispatch = {
            params ["_p","_op","_args"];
            if (_op == "directPressureClaim") then {
                _wire pushBack ["dp",[_p,_args select 0,_args select 1],_p getVariable ["TEST_owner",-1]];
            };
            if (_op in ["hangBagClaim","hangBagRenew","hangBagRelease"]) then {
                private _operation = if (_op == "hangBagClaim") then {"claim"} else {
                    if (_op == "hangBagRenew") then {"renew"} else {"release"}
                };
                _wire pushBack ["hang",[_p,_operation,_args],_p getVariable ["TEST_owner",-1]];
            };
        };
    '''
    for name in (
        "actionClaimValidate", "actionClaimLedger",
        "directPressureStart", "directPressureClaimLocal", "directPressureClaimAck",
        "hangBagStart", "hangBagClaimLocal", "hangBagClaimAck",
    ):
        result += f"ACME_fnc_{name}={{" + source(name) + "};"
    # Pending cancellation is the actual production branch. Active physical
    # teardown is a boundary: tests below inspect reservation/ACK ordering, not
    # prop deletion, lower-bag animation or equipment restoration.
    result += "ACME_fnc_hangBagStop={" + source(
        "hangBagStop", read("hangBagStop").split("private _visualEpoch =", 1)[0]
    ) + r'''
        _medic setVariable ["ACME_hang_Active",false];
        _medic setVariable ["ACME_hang_Claimed",false];
        [_patient,"hangBagRelease",[_medic,_episodeStart]] call ACME_fnc_ownerDispatch;
    };'''
    result += "private _hangTick={" + source(
        "hangBagTick", read("hangBagTick").split("// auto-lower when", 1)[0]
    ) + "};"
    return result + r'''
        private _deliver = {
            private _message = _wire deleteAt _this;
            _message params ["_event","_payload","_destination"];
            _machine = _destination;
            if (_event == "dp") then {_payload call ACME_fnc_directPressureClaimLocal;};
            if (_event == "hang") then {_payload call ACME_fnc_hangBagClaimLocal;};
            if (_event == "ACME_directPressureClaimAck") then {
                _acknowledgments pushBack _message;
                _payload call ACME_fnc_directPressureClaimAck;
            };
            if (_event == "ACME_hangClaimAck") then {
                _acknowledgments pushBack _message;
                _payload call ACME_fnc_hangBagClaimAck;
            };
        };
    '''


@pytest.mark.parametrize("patient_owner", [2, 8, 9, 7], ids=["dedicated", "player", "hc", "same-client"])
def test_duplicate_pressure_ack_preserves_active_reservation(patient_owner):
    execute(setup() + f'_patient setVariable ["TEST_owner",{patient_owner}];' + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver;
        private _ack = +(_wire select 0);
        0 call _deliver;
        _wire pushBack _ack; 0 call _deliver;
        [count _started == 1,"duplicate ACK repeated pressure presentation"] call _check;
        [count _wire == 0,"duplicate active ACK released its own reservation"] call _check;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo _medic,"duplicate ACK lost active pressure"] call _check;
    ''')


def test_pressure_start_returns_true_only_when_request_was_enqueued():
    execute(setup() + r'''
        private _requested = [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        [_requested isEqualTo true && {count _wire == 1},"new pressure request did not return enqueued status"] call _check;
        private _duplicate = [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        [_duplicate isEqualTo false && {count _wire == 1},"pending duplicate reported a new request"] call _check;
    ''')


@pytest.mark.parametrize("guard", [
    "_machine=9;",
    '_medic setVariable ["ACME_DP_Active",true];',
    '_medic setVariable ["ACM_circulation_isPerformingCPR",true];',
])
def test_pressure_start_guard_returns_false_without_request(guard):
    execute(setup() + guard + r'''
        private _requested = [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        [_requested isEqualTo false && {count _wire == 0},"guard returned success or sent a claim"] call _check;
    ''')


@pytest.mark.parametrize("action", ["dp", "hang"])
def test_release_arriving_before_claim_prevents_reacquisition(action):
    begin = '[_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;' if action == "dp" else '[_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;'
    cancel = r'''
        private _pending = _medic getVariable "ACME_DP_ClaimPending";
        [_patient,"directPressureClaim",["release",[_medic,"leftarm",_pending select 2,0,7]]] call ACME_fnc_ownerDispatch;
        _medic setVariable ["ACME_DP_ClaimPending",[]];
    ''' if action == "dp" else '[true,_medic] call ACME_fnc_hangBagStop;'
    check = '[(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"cancelled request reacquired DP"] call _check;' if action == "dp" else '[(_patient getVariable ["ACME_hang_Medic",objNull]) isEqualTo objNull,"cancelled request reacquired Hang"] call _check;'
    execute(setup() + begin + cancel + r'''
        [count _wire == 2,"missing claim or cancellation"] call _check;
        1 call _deliver; // Release overtakes the original request.
        0 call _deliver;
    ''' + check + r'''
        0 call _deliver;
        [count _started == 0 && {count _hangActivated == 0},"cancelled request activated presentation"] call _check;
    ''')


@pytest.mark.parametrize("sent_at", [994, 1001])
@pytest.mark.parametrize("action", ["dp", "hang"])
def test_old_and_future_requests_cannot_reserve_patient(action, sent_at):
    invoke = f'[_patient,"claim",[_medic,"leftarm","old",0,7,{sent_at}]] call ACME_fnc_directPressureClaimLocal;' if action == "dp" else f'[_patient,"claim",[_medic,1000,1.75,0,7,0,{sent_at}]] call ACME_fnc_hangBagClaimLocal;'
    accepted_index = 4 if action == "dp" else 3
    execute(setup() + '_machine=2;' + invoke + f'''
        [!(((_wire select 0) select 1) select {accepted_index}),"expired/future request accepted"] call _check;
    ''')


def test_pressure_old_release_and_duplicate_claim_cannot_replace_new_token():
    execute(setup() + r'''
        _machine = 2;
        private _old = [_medic,"leftarm","old",0,7,1000];
        [_patient,"claim",_old] call ACME_fnc_directPressureClaimLocal;
        [_patient,"claim",[_medic,"leftarm","new",0,7,1000]] call ACME_fnc_directPressureClaimLocal;
        [_patient,"release",_old] call ACME_fnc_directPressureClaimLocal;
        [_patient,"claim",_old] call ACME_fnc_directPressureClaimLocal;
        [((_patient getVariable "ACME_DP_claim_leftarm") select 1) == "new","old episode displaced replacement"] call _check;
        [(_patient getVariable "ACME_DP_press_leftarm") isEqualTo _medic,"old release cleared replacement clinical marker"] call _check;
    ''')


def test_duplicate_pressure_request_does_not_refresh_reservation_time():
    execute(setup() + r'''
        _machine = 2;
        private _claim = [_medic,"leftarm","once",0,7,1000];
        [_patient,"claim",_claim] call ACME_fnc_directPressureClaimLocal;
        private _reserved = +(_patient getVariable "ACME_DP_claim_leftarm");
        _networkTime = 1002;
        [_patient,"claim",_claim] call ACME_fnc_directPressureClaimLocal;
        [(_patient getVariable "ACME_DP_claim_leftarm") isEqualTo _reserved,"duplicate request extended reservation"] call _check;
        [((_wire select 1 select 1) select 4),"duplicate accepted request lost its cached result"] call _check;
    ''')


def test_hang_duplicate_renewal_does_not_extend_lease_or_reapply_flow():
    execute(setup() + r'''
        _machine = 2;
        [_patient,"claim",[_medic,1000,1.75,0,7,0,1000]] call ACME_fnc_hangBagClaimLocal;
        _networkTime = 1002;
        private _renew = [_medic,1000,2,0,7,1,1002];
        [_patient,"renew",_renew] call ACME_fnc_hangBagClaimLocal;
        private _lease = _patient getVariable "ACME_hang_LeaseUntil";
        _networkTime = 1003;
        _renew set [2,5];
        [_patient,"renew",_renew] call ACME_fnc_hangBagClaimLocal;
        [(_patient getVariable "ACME_hang_LeaseUntil") == _lease,"duplicate renewal extended lease"] call _check;
        [(_patient getVariable "ACME_hang_flowMult") == 2,"duplicate sequence changed flow"] call _check;
    ''')


def test_hang_reordered_renewal_cannot_regress_current_flow_or_lease():
    execute(setup() + r'''
        _machine = 2;
        [_patient,"claim",[_medic,1000,1.75,0,7,0,1000]] call ACME_fnc_hangBagClaimLocal;
        _networkTime = 1004;
        [_patient,"renew",[_medic,1000,3,0,7,2,1004]] call ACME_fnc_hangBagClaimLocal;
        private _lease = _patient getVariable "ACME_hang_LeaseUntil";
        _networkTime = 1004.5;
        [_patient,"renew",[_medic,1000,2,0,7,1,1002]] call ACME_fnc_hangBagClaimLocal;
        [(_patient getVariable "ACME_hang_flowMult") == 3,"older renewal regressed flow"] call _check;
        [(_patient getVariable "ACME_hang_LeaseUntil") == _lease,"older renewal changed lease"] call _check;
    ''')


def test_hang_old_rejection_after_newer_acceptance_does_not_stop_active_episode():
    execute(setup() + r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        0 call _deliver; 0 call _deliver;
        private _episode = _medic getVariable "ACME_hang_Start";
        _networkTime = 1004;
        [_patient,_medic,_episode,true,0,7,1010,2] call ACME_fnc_hangBagClaimAck;
        [_patient,_medic,_episode,false,0,7,1008,1] call ACME_fnc_hangBagClaimAck;
        [_medic getVariable ["ACME_hang_Active",false],"reordered stale rejection stopped current hold"] call _check;
        [count _hangActivated == 1,"renewal repeated Hang presentation"] call _check;
        [count _wire == 0,"reordered stale rejection released reservation"] call _check;
    ''')


def test_hang_late_old_release_cannot_clear_new_episode():
    execute(setup() + r'''
        _machine = 2;
        [_patient,"claim",[_medic,1000,1.75,0,7,0,1000]] call ACME_fnc_hangBagClaimLocal;
        [_patient,"release",[_medic,1000]] call ACME_fnc_hangBagClaimLocal;
        [_patient,"claim",[_medic,1000.1,3,0,7,0,1000]] call ACME_fnc_hangBagClaimLocal;
        [_patient,"release",[_medic,1000]] call ACME_fnc_hangBagClaimLocal;
        [(_patient getVariable "ACME_hang_Episode") == 1000.1,"late release removed new Hang episode"] call _check;
        [(_patient getVariable "ACME_hang_flowMult") == 3,"late release erased new Hang flow"] call _check;
    ''')


@pytest.mark.parametrize("action", ["dp", "hang"])
def test_patient_owner_migration_preserves_cancelled_request_tombstone(action):
    invocation = r'''[_patient,"release",[_medic,"leftarm","cancelled",0,7]] call ACME_fnc_directPressureClaimLocal;''' if action == "dp" else r'''[_patient,"release",[_medic,1000]] call ACME_fnc_hangBagClaimLocal;'''
    replay = r'''[_patient,"claim",[_medic,"leftarm","cancelled",0,7,1000]] call ACME_fnc_directPressureClaimLocal;''' if action == "dp" else r'''[_patient,"claim",[_medic,1000,1.75,0,7,0,1000]] call ACME_fnc_hangBagClaimLocal;'''
    index = 4 if action == "dp" else 3
    execute(setup() + '_machine=2;' + invocation + r'''
        _patient setVariable ["TEST_owner",9]; _machine=9;
    ''' + replay + f'''
        [!((_wire select 0 select 1) select {index}),"ownership transfer lost cancelled-token record"] call _check;
    ''')


@pytest.mark.parametrize("action", ["dp", "hang"])
def test_epoch_reset_rejects_cached_accepted_request(action):
    invocation = r'''[_patient,"claim",[_medic,"leftarm","once",0,7,1000]] call ACME_fnc_directPressureClaimLocal;''' if action == "dp" else r'''[_patient,"claim",[_medic,1000,1.75,0,7,0,1000]] call ACME_fnc_hangBagClaimLocal;'''
    index = 4 if action == "dp" else 3
    execute(setup() + '_machine=2;' + invocation + r'''
        _patient setVariable ["ACME_clinicalEpoch",1];
    ''' + invocation + f'''
        [!((_wire select 1 select 1) select {index}),"cached ACK bypassed new clinical epoch"] call _check;
    ''')


def test_hang_tick_assigns_monotonic_renewal_sequences_and_send_time():
    execute(setup() + r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        [(_wire select 0 select 1 select 2 select 5)==0,"initial Hang request lacks sequence zero"] call _check;
        [(_wire select 0 select 1 select 2 select 6)==1000,"initial Hang request lacks send time"] call _check;
        0 call _deliver; 0 call _deliver;
        _networkTime=1002;
        [[_medic,_patient],_medic getVariable "ACME_hang_PFH"] call _hangTick;
        [(_wire select 0 select 1 select 2 select 5)==1,"first renewal sequence incorrect"] call _check;
        [(_wire select 0 select 1 select 2 select 6)==1002,"first renewal lacks fresh send time"] call _check;
        0 call _deliver; 0 call _deliver;
        _networkTime=1004;
        [[_medic,_patient],_medic getVariable "ACME_hang_PFH"] call _hangTick;
        [(_wire select 0 select 1 select 2 select 5)==2,"second renewal sequence did not advance"] call _check;
    ''')


def test_full_ledger_keeps_cancellations_and_blocks_unrecorded_token_until_safe():
    execute(setup() + r'''
        _machine=2;
        for "_i" from 1 to 64 do {
            [_patient,"dp:leftarm",_medic,str _i,0,"cancel"] call ACME_fnc_actionClaimLedger;
        };
        _networkTime=1001;
        private _overflow = [_patient,"dp:leftarm",_medic,"overflow",0,"cancel"] call ACME_fnc_actionClaimLedger;
        [(_overflow select 0)=="blocked","ledger saturation silently lost cancellation"] call _check;
        [count ((_patient getVariable "ACME_actionClaimHistory") select 1)==64,"ledger is unbounded"] call _check;
        private _old = [_patient,"dp:leftarm",_medic,"1",0,"lookup"] call ACME_fnc_actionClaimLedger;
        [(_old select 0)=="cancelled","saturation evicted live cancellation"] call _check;
        _networkTime=1008.5;
        private _stillBlocked = [_patient,"dp:leftarm",_medic,"overflow",0,"lookup"] call ACME_fnc_actionClaimLedger;
        [(_stillBlocked select 0)=="blocked","pruning reopened unrecorded cancellation too early"] call _check;
        _networkTime=1009.1;
        private _fresh = [_patient,"dp:leftarm",_medic,"fresh",0,"lookup"] call ACME_fnc_actionClaimLedger;
        [(_fresh select 0)=="new","ledger saturation never recovered"] call _check;
    ''')


def test_cancellation_is_terminal_but_scoped_to_provider_action_and_epoch():
    execute(setup() + r'''
        _machine=2;
        [_patient,"dp:leftarm",_medic,"same",0,"cancel"] call ACME_fnc_actionClaimLedger;
        private _revive = [_patient,"dp:leftarm",_medic,"same",0,"accept",99,[true]] call ACME_fnc_actionClaimLedger;
        [(_revive select 0)=="cancelled","later sequence revived a cancelled token"] call _check;
        private _otherScope = [_patient,"dp:rightarm",_medic,"same",0,"lookup"] call ACME_fnc_actionClaimLedger;
        [(_otherScope select 0)=="new","cancellation leaked across body parts"] call _check;
        private _otherProvider = [_patient,"dp:leftarm",parsingNamespace,"same",0,"lookup"] call ACME_fnc_actionClaimLedger;
        [(_otherProvider select 0)=="new","cancellation leaked across providers"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",1];
        private _newEpoch = [_patient,"dp:leftarm",_medic,"same",1,"lookup"] call ACME_fnc_actionClaimLedger;
        [(_newEpoch select 0)=="new","new clinical epoch inherited old cancellation"] call _check;
    ''')


def test_pressure_same_frame_cancel_restart_uses_distinct_request_tokens():
    execute(setup() + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        private _first = _medic getVariable "ACME_DP_ClaimPending";
        [_patient,"directPressureClaim",["release",[_medic,"leftarm",_first select 2,0,7]]] call ACME_fnc_ownerDispatch;
        _medic setVariable ["ACME_DP_ClaimPending",[]];
        // Both clocks and frame number remain identical for this restart.
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        private _second = _medic getVariable "ACME_DP_ClaimPending";
        [(_first select 2) != (_second select 2),"same-frame restart reused cancelled token"] call _check;
        1 call _deliver; // Cancellation overtakes first claim.
        1 call _deliver; // Replacement reaches the owner next.
        0 call _deliver; // Original request arrives last.
        [((_patient getVariable "ACME_DP_claim_leftarm") select 1) == (_second select 2),"old same-frame claim displaced replacement"] call _check;
    ''')


def test_duplicate_ledger_cancellation_keeps_original_record_and_expiry():
    execute(setup() + r'''
        _machine=2;
        [_patient,"dp:leftarm",_medic,"once",0,"cancel"] call ACME_fnc_actionClaimLedger;
        private _original = +(_patient getVariable "ACME_actionClaimHistory");
        _networkTime=1003;
        [_patient,"dp:leftarm",_medic,"once",0,"cancel"] call ACME_fnc_actionClaimLedger;
        [(_patient getVariable "ACME_actionClaimHistory") isEqualTo _original,"duplicate cancellation mutated history or refreshed expiry"] call _check;
        _networkTime=1008.1;
        private _expired = [_patient,"dp:leftarm",_medic,"once",0,"lookup"] call ACME_fnc_actionClaimLedger;
        [(_expired select 0)=="new","duplicate cancellation extended retention"] call _check;
    ''')


def test_pressure_ack_after_reservation_replacement_cannot_activate():
    execute(setup() + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver;
        private _oldAck = _wire deleteAt 0;
        private _other = parsingNamespace;
        _other setVariable ["TEST_owner",11];
        _networkTime=1003.5;
        [_patient,"claim",[_other,"leftarm","replacement",0,11,1003.5]] call ACME_fnc_directPressureClaimLocal;
        [((_patient getVariable "ACME_DP_claim_leftarm") select 0) isEqualTo _other,"expired reservation did not admit replacement"] call _check;
        _wire=[];
        _networkTime=1003.9;
        _wire pushBack _oldAck;
        0 call _deliver;
        [count _started==0,"late expired ACK activated displaced pressure hold"] call _check;
        [count _wire==1,"late ACK did not retire its old token"] call _check;
        0 call _deliver;
        [((_patient getVariable "ACME_DP_claim_leftarm") select 0) isEqualTo _other,"late ACK release removed replacement claim"] call _check;
        [(_patient getVariable "ACME_DP_press_leftarm") isEqualTo _other,"late ACK overwrote replacement clinical marker"] call _check;
    ''')


@pytest.mark.parametrize("arrival,starts", [(1002.999, 1), (1003, 0)], ids=["before-deadline", "exact-deadline"])
def test_pressure_ack_grant_deadline_boundary(arrival, starts):
    execute(setup() + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver;
    ''' + f'''
        _networkTime={arrival};
        0 call _deliver;
        [count _started=={starts},"ACK activation violated strict grant deadline"] call _check;
    ''')


def test_pressure_duplicate_ack_after_grant_expiry_preserves_active_hold():
    execute(setup() + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver;
        private _duplicate = +(_wire select 0);
        0 call _deliver;
        _networkTime=1010;
        _wire pushBack _duplicate;
        0 call _deliver;
        [count _started==1,"expired duplicate ACK repeated active presentation"] call _check;
        [count _wire==0,"expired duplicate ACK released active reservation"] call _check;
        [(_patient getVariable "ACME_DP_press_leftarm") isEqualTo _medic,"expired duplicate ACK cleared active pressure"] call _check;
    ''')


def test_pressure_duplicate_request_ack_keeps_original_grant_deadline():
    execute(setup() + r'''
        _machine=2;
        private _request = [_medic,"leftarm","once",0,7,1000];
        [_patient,"claim",_request] call ACME_fnc_directPressureClaimLocal;
        private _first = (_wire select 0) select 1;
        [(_first param [7,-1])==1003,"initial ACK missing bounded grant deadline"] call _check;
        _networkTime=1002;
        [_patient,"claim",_request] call ACME_fnc_directPressureClaimLocal;
        private _duplicate = (_wire select 1) select 1;
        [(_duplicate param [7,-1])==(_first param [7,-2]),"duplicate ACK refreshed original grant deadline"] call _check;
        [(_duplicate select 4),"valid duplicate lost accepted decision"] call _check;
    ''')


def marker_setup():
    body = switch_case_body(read("ownerDispatch"), "directPressureMarker")
    return setup() + 'private _marker={params ["_patient","_args"];' + source("ownerDispatch", body) + r'''};
        _machine=2;
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Part","leftarm"];
        _medic setVariable ["ACME_DP_ClaimToken","replacement"];
        _medic setVariable ["ACME_DP_ClaimEpoch",0];
        _patient setVariable ["ACME_DP_claim_leftarm",[_medic,"replacement",0,7,1000]];
    '''


def test_pressure_old_marker_from_same_provider_cannot_mutate_replacement():
    execute(marker_setup() + r'''
        [_patient,[_medic,"leftarm",true,"old",0]] call _marker;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo objNull,"old positive marker reinstated yielded replacement"] call _check;
        [_patient,[_medic,"leftarm",true,"replacement",0]] call _marker;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo _medic,"current marker could not resume pressure"] call _check;
        [_patient,[_medic,"leftarm",false,"old",0]] call _marker;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo _medic,"old negative marker cleared replacement pressure"] call _check;
        [(_patient getVariable ["ACME_DP_LimbMedic",objNull]) isEqualTo _medic,"old negative marker cleared replacement limb holder"] call _check;
        [_patient,[_medic,"leftarm",false,"replacement",0]] call _marker;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo objNull,"current marker could not yield pressure"] call _check;
        [_patient,[_medic,"leftarm",true,"replacement",0]] call _marker;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo _medic,"current marker could not resume after yield"] call _check;
    ''')


@pytest.mark.parametrize("invalidate", [
    '_patient setVariable ["ACME_DP_claim_leftarm",[]];',
    '_patient setVariable ["ACME_clinicalEpoch",1];',
    '_patient setVariable ["ACME_DP_claim_leftarm",[parsingNamespace,"replacement",0,11,1000]];',
], ids=["no-claim", "reset-epoch", "other-provider"])
def test_pressure_positive_marker_requires_current_exact_owner_claim(invalidate):
    execute(marker_setup() + invalidate + r'''
        [_patient,[_medic,"leftarm",true,"replacement",0]] call _marker;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo objNull,"unclaimed or obsolete provider applied pressure marker"] call _check;
        [(_patient getVariable ["ACME_DP_LimbMedic",objNull]) isEqualTo objNull,"unclaimed or obsolete provider took limb marker"] call _check;
    ''')


def test_pressure_clot_requires_current_episode_token_and_clinical_epoch():
    body = switch_case_body(read("ownerDispatch"), "directPressureClot")
    execute(marker_setup() + 'private _clot={params ["_patient","_args"];' + source("ownerDispatch", body) + r'''};
        private _clots=[];
        ACM_damage_fnc_clotWoundsOnBodyPart={_clots pushBack _this;};
        [_patient,[_medic,"leftarm",true,"replacement",0]] call _marker;
        [_patient,[_medic,"leftarm","old",0]] call _clot;
        [count _clots==0,"old episode clot packet credited replacement hold"] call _check;
        [_patient,[_medic,"leftarm","replacement",0]] call _clot;
        [_clots isEqualTo [[_patient,"leftarm",2,3,true,false]],"current valid episode did not clot wounds"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",1];
        [_patient,[_medic,"leftarm","replacement",0]] call _clot;
        [count _clots==1,"stale clinical epoch clot changed reset patient"] call _check;
    ''')


def pressure_tick_prefix_setup():
    prefix = read("directPressureTick").split("// Movement is an explicit release", 1)[0]
    prefix = prefix.replace("diag_tickTime", "_localTime")
    return setup() + 'private _pressureTick={' + source("directPressureTick", prefix) + r'''};
        private _localTime=200;
        private _pressureStops=[];
        ACME_fnc_patientInteractionDistance={_distance};
        ACME_fnc_directPressureStop={
            _pressureStops pushBack _this;
            (_this select 1) setVariable ["ACME_DP_Active",false];
        };
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        0 call _deliver; 0 call _deliver;
        _pressureStops=[];
        _medic setVariable ["ACME_DP_PFH",0];
        _medic setVariable ["ACME_DP_Mode","limb"];
        _handlers pushBack [{},[],true];
        private _confirmedClaim=+(_patient getVariable "ACME_DP_claim_leftarm");
        _patient setVariable ["ACME_DP_claim_leftarm",[]];
        private _pressureTickArgs=[[_medic,_patient,"leftarm","limb"],0];
    '''


def test_pressure_claim_replication_recovers_within_grace_without_stopping():
    execute(pressure_tick_prefix_setup() + r'''
        _pressureTickArgs call _pressureTick;
        _localTime=202.9;
        _pressureTickArgs call _pressureTick;
        [count _pressureStops==0,"temporary missing claim stopped pressure before replication grace"] call _check;
        _patient setVariable ["ACME_DP_claim_leftarm",_confirmedClaim];
        _localTime=202.95;
        _pressureTickArgs call _pressureTick;
        [(_medic getVariable ["ACME_DP_ClaimLostAt",-2]) == -1,"matching replicated claim did not reset loss timer"] call _check;
        _localTime=205;
        _pressureTickArgs call _pressureTick;
        [count _pressureStops==0 && {_medic getVariable ["ACME_DP_Active",false]},"recovered claim inherited earlier loss timeout"] call _check;
    ''')


def test_pressure_permanent_claim_loss_stops_at_three_second_deadline():
    execute(pressure_tick_prefix_setup() + r'''
        _pressureTickArgs call _pressureTick;
        _localTime=202.999;
        _pressureTickArgs call _pressureTick;
        [count _pressureStops==0,"claim loss stopped before three-second grace"] call _check;
        _localTime=203;
        _pressureTickArgs call _pressureTick;
        [count _pressureStops==1,"permanent owner claim loss left local pressure running"] call _check;
        [!(_medic getVariable ["ACME_DP_Active",true]),"claim loss did not request active hold teardown"] call _check;
    ''')


def test_pressure_accepted_ack_resets_inherited_claim_loss_timer():
    execute(setup() + r'''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        _medic setVariable ["ACME_DP_ClaimLostAt",100];
        0 call _deliver; 0 call _deliver;
        [count _started==1,"valid new request did not activate"] call _check;
        [(_medic getVariable ["ACME_DP_ClaimLostAt",-2]) == -1,"new accepted ACK inherited old claim-loss timer"] call _check;
    ''')


@pytest.mark.parametrize("first,second", [(1234.567,1234.568),(100000.1,100000.2)])
def test_hang_distinct_numeric_episodes_do_not_share_rounded_ledger_key(first,second):
    execute(setup()+f'''
        _machine=2;_networkTime={first};
        private _first={first};private _second={second};
        [!(_first isEqualTo _second),"fixture episodes are not numerically distinct"] call _check;
        [_patient,"claim",[_medic,_first,1.75,0,7,0,_networkTime]] call ACME_fnc_hangBagClaimLocal;
        [_patient,"release",[_medic,_first]] call ACME_fnc_hangBagClaimLocal;
        [_patient,"claim",[_medic,_second,3,0,7,0,_networkTime]] call ACME_fnc_hangBagClaimLocal;
        [_patient,"release",[_medic,_first]] call ACME_fnc_hangBagClaimLocal;
        [(_patient getVariable ["ACME_hang_Episode",-1]) isEqualTo _second,"rounded token cancellation rejected new episode"] call _check;
        [(_patient getVariable ["ACME_hang_flowMult",1])==3,"old cancellation cleared replacement flow"] call _check;
    ''')


@pytest.mark.parametrize("now", [1234.567,100000])
def test_hang_same_frame_cancel_restart_stays_distinct_on_long_mission(now):
    execute(setup()+f'_networkTime={now};'+r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        private _first=_medic getVariable "ACME_hang_Start";
        [true,_medic] call ACME_fnc_hangBagStop;
        // Both timestamps and frame number stay fixed during this restart.
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        private _second=_medic getVariable "ACME_hang_Start";
        [_second>_first,"long-mission restart reused cancelled scalar episode"] call _check;
        1 call _deliver; // Old cancellation overtakes both requests.
        1 call _deliver; // Replacement reaches the owner first.
        0 call _deliver; // Original claim arrives after its cancellation.
        0 call _deliver; // Replacement accepted ACK.
        0 call _deliver; // Old rejected ACK cannot touch replacement.
        [(_patient getVariable ["ACME_hang_Episode",-1]) isEqualTo _second,"old claim displaced long-mission replacement"] call _check;
        [count _hangActivated==1,"replacement did not activate exactly once"] call _check;
        [_medic getVariable ["ACME_hang_Claimed",false],"delayed old ACK stopped replacement"] call _check;
        [count _wire==0,"old ACK released replacement"] call _check;
    ''')
