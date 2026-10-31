/* Provider-local battery reservation/retry lifecycle, independent of the panel.
 * Escrow rows: [immutableRequest,state,decision], state 0 pending, 1 physical
 * item returned, 2 patient owner confirmed, 3 server confirmation acknowledged.
 * Only state3 may expire. No timeout guesses a disposition.
 */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_ventBatteryRequest;};
    _result
};
params [["_operation", "recover", [""]], ["_medic", objNull, [objNull]], ["_payload", [], [[]]]];
if (isNull _medic || {!local _medic}) exitWith {false};
private _escrows = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
if !(_escrows isEqualType createHashMap) then {_escrows = createHashMap;};
private _awaits = _medic getVariable ["ACME_vent_batterySwapAwait", createHashMap];
if !(_awaits isEqualType createHashMap) then {_awaits = createHashMap;};
private _blocked = {
    (values _escrows findIf {
        private _blocked = false;
        if (_x isEqualType [] && {count _x == 3} && {(_x select 1) == 0}) then {
            private _request = _x select 0;
            _blocked = !(_request isEqualType []) || {count _request != 10};
            if (!_blocked) then {
                private _target = _request select 0;
                if (!isNull _target) then {
                    private _period = if (local _target) then {[clientOwner, _target getVariable ["ACME_providerLocalityEpoch", 0]]} else {_target getVariable ["ACME_vent_batterySwapOwnerPeriod", []]};
                    private _results = _target getVariable ["ACME_vent_batterySwapReceipts", createHashMap];
                    private _result = _results getOrDefault [_request select 2, []];
                    _blocked = (_request select 9) isEqualTo _period
                        && {(_request select 4) > (_target getVariable ["ACME_vent_batterySwapClosedBefore", -1])}
                        && {count _result != 5 || {!((_result select 0) isEqualTo _request)}};
                };
            };
        };
        _blocked
    }) >= 0
};
if (_operation == "blocked") exitWith {call _blocked};
if (_operation == "await") exitWith {
    // This local queue remembers only an observed ACK. It cannot authorize
    // adoption until ACK independently matches the public escrow and decision.
    if (!(count _payload in [3,5]) || {!((_payload select 0) isEqualType [])}
        || {count (_payload select 0) != 10}
        || {!(((_payload select 0) select 1) isEqualTo _medic)}
        || {!(((_payload select 0) select 2) isEqualType "")}) exitWith {false};
    private _id = (_payload select 0) select 2;
    private _old = _awaits getOrDefault [_id, []];
    if (_old isNotEqualTo [] && {!(_old isEqualTo _payload)}
        && {count _payload != 5 || {!((_old select 0) isEqualTo (_payload select 0))}}) exitWith {false};
    if (_old isEqualTo [] && {count _awaits >= 64}) exitWith {false};
    _awaits set [_id, +_payload];
    _medic setVariable ["ACME_vent_batterySwapAwait", _awaits, false];
    ["recover", _medic] call ACME_fnc_ventBatteryRequest;
    true
};
if (_operation == "start") exitWith {
    if (count _payload != 8) exitWith {false};
    _payload params ["_patient", "_supply", "_incoming", "_epoch", "_custody", "_source", "_issued", "_period"];
    if (!(_patient isEqualType objNull) || {isNull _patient} || {!(_source isEqualType objNull)}
        || {!(_supply isEqualType [])} || {count _supply != 4}
        || {!((_supply select 1) in (call ACME_fnc_ventBatteryItems))} || {!((_supply select 3) isEqualType "")}
        || {(_supply select 3) == ""} || {isNull _source}
        || {!(_incoming isEqualType 0)} || {!finite _incoming} || {_incoming < 0} || {_incoming > 100}
        || {_incoming != ([_supply select 1] call ACME_fnc_ventBatteryCharge)}
        || {!(_issued isEqualType 0)} || {!finite _issued} || {_issued < 0}
        || {!(_epoch isEqualType 0)} || {!finite _epoch} || {_epoch < 0} || {_epoch != floor _epoch}
        || {!(_custody isEqualType "")}
        || {!(_period isEqualType [])} || {count _period != 2}
        || {!((_period select 0) isEqualType 0)} || {!finite (_period select 0)} || {(_period select 0) < 0}
        || {isMultiplayer && {(_period select 0) < 2}}
        || {!((_period select 1) isEqualType 0)} || {!finite (_period select 1)} || {(_period select 1) < 0}) exitWith {false};
    {
        private _row = _escrows get _x;
        if (_row isEqualType [] && {count _row == 3} && {(_row select 1) == 3}
            && {serverTime > (((_row select 0) select 4) + 300)}) then {_escrows deleteAt _x;};
    } forEach keys _escrows;
    if (count _escrows >= 64 || {call _blocked}) exitWith {false};
    private _id = "vent-battery:" + (_supply select 3);
    private _request = [_patient, _medic, _id, _incoming, _issued, _epoch, _custody, +_supply, _source, +_period];
    _escrows set [_id, [_request, 0, []]];
    _medic setVariable ["ACME_vent_batterySwapEscrow", _escrows, true];
    uiNamespace setVariable ["ACME_vent_batterySwapRequest", _id];
    uiNamespace setVariable ["ACME_vent_batterySwapSupply", _supply];
    ["recover", _medic] call ACME_fnc_ventBatteryRequest;
    true
};
if (_operation == "tick") exitWith {
    {
        private _observed = _awaits get _x;
        if (_observed isEqualType [] && {count _observed in [3,5]}) then {
            private _request = _observed select 0;
            private _target = _request select 0;
            if (isNull _target) then {_awaits deleteAt _x;} else {_observed call ACME_fnc_ventBatteryAck;};
        };
    } forEach keys _awaits;
    _awaits = _medic getVariable ["ACME_vent_batterySwapAwait", createHashMap];
    private _active = count _awaits > 0;
    _escrows = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
    {
        private _row = _escrows get _x;
        if (!(_row isEqualType []) || {count _row != 3}) then {continue};
        _row params ["_request", "_state", "_decision"];
        if (!(_request isEqualType []) || {count _request != 10} || {!((_request select 1) isEqualTo _medic)}
            || {!(_state isEqualType 0)} || {_state >= 3}) then {continue};
        private _patient = _request select 0;
        // A deleted patient without a decision is ambiguous. Preserve custody;
        // neither a closed menu nor deletion proves no battery was installed.
        if (isNull _patient) then {continue};
        _active = true;
        if (_state == 2) then {
            ["ACME_ventBatteryDispositionClaim", [_request, _decision, "confirm"]] call CBA_fnc_serverEvent;
            continue;
        };
        if (_state == 0) then {
            [_patient, "ventBatteryExchange", ["apply", _request]] call ACME_fnc_ownerDispatch;
        } else {
            [_patient, "ventBatteryExchange", ["settled", _request, _decision]] call ACME_fnc_ownerDispatch;
            private _results = _patient getVariable ["ACME_vent_batterySwapReceipts", createHashMap];
            private _result = _results getOrDefault [_request select 2, []];
            if (count _result == 5 && {(_result select 0) isEqualTo _request} && {_result select 3}
                && {(_decision select [0,2]) isEqualTo [_result select 1, _result select 2]}) then {
                private _current = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
                _current set [_request select 2, [_request, 2, _decision]];
                _medic setVariable ["ACME_vent_batterySwapEscrow", _current, true];
            };
        };
    } forEach keys _escrows;
    _active
};
if (_operation != "recover" || {count _awaits == 0 && {(values _escrows findIf {
    private _live = false;
    if (_x isEqualType [] && {count _x == 3} && {(_x select 1) isEqualType 0} && {(_x select 1) < 3}) then {
        private _request = _x select 0;
        if (_request isEqualType [] && {count _request == 10}) then {
            private _target = _request select 0;
            _live = !isNull _target;
        };
    };
    _live
}) < 0}}) exitWith {false};
private _epoch = _medic getVariable ["ACME_providerLocalityEpoch", 0];
private _worker = _medic getVariable ["ACME_vent_batterySwapWorker", []];
if (count _worker == 3 && {(_worker select 0) == clientOwner} && {(_worker select 1) == _epoch}
    && {(_worker select 2) >= 0}) exitWith {true};
if (count _worker == 3 && {(_worker select 2) >= 0}) then {[_worker select 2] call CBA_fnc_removePerFrameHandler;};
private _handle = [{
    params ["_args", "_handle"];
    _args params ["_medic", "_owner", "_epoch"];
    private _stamp = if (isNull _medic) then {[]} else {_medic getVariable ["ACME_vent_batterySwapWorker", []]};
    private _same = _stamp isEqualTo [_owner, _epoch, _handle];
    if (isNull _medic || {!local _medic} || {clientOwner != _owner}
        || {(_medic getVariable ["ACME_providerLocalityEpoch", -1]) != _epoch} || {!_same}) exitWith {
        if (_same && {!isNull _medic} && {!local _medic}) then {
            private _awaits = _medic getVariable ["ACME_vent_batterySwapAwait", createHashMap];
            {
                private _observed = _awaits get _x;
                if (_observed isEqualType [] && {count _observed in [3,5]}) then {
                    private _forwarded = +_observed;
                    _forwarded set [3,1];
                    ["ACME_ventBatteryExchangeResult", _forwarded, _medic] call CBA_fnc_targetEvent;
                };
            } forEach keys _awaits;
            _medic setVariable ["ACME_vent_batterySwapAwait", createHashMap, false];
        };
        [_handle] call CBA_fnc_removePerFrameHandler;
        if (_same) then {_medic setVariable ["ACME_vent_batterySwapWorker", [], false];};
    };
    // Dead providers retain their own body/inventory and settle their exact
    // pending item. This worker deliberately has no alive/ACE_player/UI gate.
    if !(["tick", _medic] call ACME_fnc_ventBatteryRequest) then {
        [_handle] call CBA_fnc_removePerFrameHandler;
        _medic setVariable ["ACME_vent_batterySwapWorker", [], false];
    };
}, 1, [_medic, clientOwner, _epoch]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_vent_batterySwapWorker", [clientOwner, _epoch, _handle], false];
["tick", _medic] call ACME_fnc_ventBatteryRequest;
true
