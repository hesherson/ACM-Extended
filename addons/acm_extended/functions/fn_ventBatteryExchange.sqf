/* Patient-owner battery transaction. Decisions outlive clinical/device changes.
 * Request: [patient,provider,id,incomingPct,issuedAt,epoch,custody,receipt,chargeSource,patientOwnerPeriod].
 * Receipt: [request,accepted,returnedPct,physicalSettlementConfirmed,decidedAt].
 * Unknown requests remain dependent on their exact public provider reservation.
 */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_ventBatteryExchange;};
    _result
};
params [["_operation", "apply", [""]], ["_request", [], [[]]], ["_decision", [], [[]]], ["_serverVerified", false, [false]]];
if (count _request != 10 || {!(_operation in ["apply", "settled", "claim", "authorize", "confirm"])}) exitWith {false};
_request params ["_patient", "_medic", "_id", "_incoming", "_issued", "_epoch", "_custody", "_supply", "_source", "_period"];
if (!(_patient isEqualType objNull) || {!(_medic isEqualType objNull)}
    || {isNull _patient} || {isNull _medic} || {!(_operation in ["authorize", "confirm"]) && {!local _patient}}
    || {!(_id isEqualType "")} || {_id == ""} || {count _id > 128}
    || {!(_incoming isEqualType 0)} || {!finite _incoming} || {_incoming < 0} || {_incoming > 100}
    || {!(_issued isEqualType 0)} || {!finite _issued} || {_issued < 0}
    || {!(_epoch isEqualType 0)} || {!finite _epoch} || {_epoch < 0} || {_epoch != floor _epoch}
    || {!(_custody isEqualType "")} || {count _custody > 128}
    || {!(_supply isEqualType [])} || {count _supply != 4}
    || {!(_source isEqualType objNull)}
    || {!((_supply select 0) isEqualType objNull)} || {!((_supply select 2) isEqualType objNull)}
    || {!((_supply select 1) in (call ACME_fnc_ventBatteryItems))} || {!((_supply select 3) isEqualType "")}
    || {_incoming != ([_supply select 1] call ACME_fnc_ventBatteryCharge)}
    || {_id != ("vent-battery:" + (_supply select 3))}
    || {!(_period isEqualType [])} || {count _period != 2}
    || {!((_period select 0) isEqualType 0)} || {!finite (_period select 0)} || {(_period select 0) < 0}
    || {isMultiplayer && {(_period select 0) < 2}}
    || {!((_period select 1) isEqualType 0)} || {!finite (_period select 1)} || {(_period select 1) < 0}) exitWith {false};
private _claimValid = count _decision == 2 && {(_decision select 0) isEqualType 0}
    && {finite (_decision select 0)} && {(_decision select 0) >= 0}
    && {!isMultiplayer || {(_decision select 0) >= 2}} && {(_decision select 0) == floor (_decision select 0)}
    && {(_decision select 1) isEqualType 0} && {finite (_decision select 1)}
    && {(_decision select 1) >= 0} && {(_decision select 1) == floor (_decision select 1)};
if (_operation in ["authorize", "confirm"]) exitWith {
    // The server is the single writer across patient AND provider locality.
    // Public patient dispositions are receipts, never authority to grant again.
    if (!isServer) exitWith {false};
    private _journals = missionNamespace getVariable ["ACME_vent_batteryDispositionJournal", createHashMap];
    private _journal = _journals getOrDefault [_patient, [createHashMap, -1]];
    _journal params ["_rows", "_closedBefore"];
    private _old = _rows getOrDefault [_id, []];
    private _results = _patient getVariable ["ACME_vent_batterySwapReceipts", createHashMap];
    private _result = _results getOrDefault [_id, []];
    if (_operation == "confirm") exitWith {
        if (count _old != 8 || {!((_old select 0) isEqualTo _request)}
            || {!(_decision isEqualTo [_old select 1, _old select 2, _old select [3,2]])}) exitWith {false};
        private _pending = missionNamespace getVariable ["ACME_vent_batteryDispositionConfirmPending", createHashMap];
        private _escrows = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
        private _escrow = _escrows getOrDefault [_id, []];
        private _physicalProof = count _escrow == 3 && {(_escrow select 0) isEqualTo _request}
            && {(_escrow select 1) >= 1} && {(_escrow select 2) isEqualTo _decision};
        private _confirmed = (_old select 5) || _physicalProof;
        private _acknowledged = (_old select 7) || {_physicalProof && {(_escrow select 1) >= 3}};
        if (_confirmed) then {
            _old set [5, true];
            _old set [7, (_old select 7) || _acknowledged];
            _rows set [_id, _old];
            _journals set [_patient, [_rows, _closedBefore]];
            missionNamespace setVariable ["ACME_vent_batteryDispositionJournal", _journals];
        };
        if (_acknowledged) then {_pending deleteAt _id;} else {_pending set [_id, [+_request, +_decision]];};
        missionNamespace setVariable ["ACME_vent_batteryDispositionConfirmPending", _pending];
        if (_confirmed) then {
            // Restore only the completed immutable receipt after packet loss or
            // patient handoff. This carries no permission to fit another cell.
            [_patient, "ventBatteryExchange", ["settled", _request, _decision, true]] call ACME_fnc_ownerDispatch;
        };
        if (_confirmed && {!_acknowledged}) then {
            ["ACME_ventBatteryExchangeResult", [_request, _old select 1, _old select 2, 0, _old select [3,2]], _medic] call CBA_fnc_targetEvent;
        };
        if (count (missionNamespace getVariable ["ACME_vent_batteryDispositionConfirmPending", createHashMap]) > 0
            && {(missionNamespace getVariable ["ACME_vent_batteryDispositionConfirmWorker", -1]) < 0}) then {
            private _handle = [{
                params ["", "_handle"];
                private _pending = missionNamespace getVariable ["ACME_vent_batteryDispositionConfirmPending", createHashMap];
                private _keys = keys _pending;
                private _cursor = missionNamespace getVariable ["ACME_vent_batteryDispositionConfirmCursor", 0];
                {
                    private _index = (_cursor + _forEachIndex) mod count _keys;
                    private _id = _keys select _index;
                    private _row = _pending get _id;
                    private _request = _row select 0;
                    if (isNull (_request select 0) || {isNull (_request select 1)}) then {
                        // Deletion cannot create a new claimant. Retain the
                        // unresolved journal, retire its impossible retry work.
                        _pending deleteAt _id;
                        missionNamespace setVariable ["ACME_vent_batteryDispositionConfirmPending", _pending];
                    } else {
                        ["confirm", _request, _row select 1] call ACME_fnc_ventBatteryExchange;
                    };
                } forEach (_keys select [0, 16]);
                missionNamespace setVariable ["ACME_vent_batteryDispositionConfirmCursor", (_cursor + 16) mod ((count _keys) max 1)];
                if (count (missionNamespace getVariable ["ACME_vent_batteryDispositionConfirmPending", createHashMap]) == 0) then {
                    [_handle] call CBA_fnc_removePerFrameHandler;
                    missionNamespace setVariable ["ACME_vent_batteryDispositionConfirmCursor", 0];
                    if ((missionNamespace getVariable ["ACME_vent_batteryDispositionConfirmWorker", -1]) == _handle) then {
                        missionNamespace setVariable ["ACME_vent_batteryDispositionConfirmWorker", -1];
                    };
                };
            }, 1, []] call CBA_fnc_addPerFrameHandler;
            missionNamespace setVariable ["ACME_vent_batteryDispositionConfirmWorker", _handle];
        };
        _confirmed
    };
    if (!_claimValid) exitWith {false};
    if (_old isNotEqualTo []) exitWith {
        if (count _old != 8 || {!((_old select 0) isEqualTo _request)}) exitWith {false};
        [_patient, "ventBatteryExchange", ["claim", _request, _old select [3,2], true]] call ACME_fnc_ownerDispatch;
        true
    };
    {
        private _row = _rows get _x;
        if (_row select 5 && {_row select 7}
            && {serverTime > ((((_row select 0) select 4) + 180) max ((_row select 6) + 180))}) then {
            _closedBefore = _closedBefore max ((_row select 0) select 4);
            _rows deleteAt _x;
        };
    } forEach keys _rows;
    _journals set [_patient, [_rows, _closedBefore]];
    missionNamespace setVariable ["ACME_vent_batteryDispositionJournal", _journals];
    if (_issued <= _closedBefore || {count _rows >= 128}
        || {isMultiplayer && {owner _medic != (_decision select 0)}}
        || {!isMultiplayer && {!local _medic}}
        || {count _result != 5} || {!((_result select 0) isEqualTo _request)}) exitWith {false};
    _rows set [_id, [+_request, _result select 1, _result select 2, _decision select 0, _decision select 1, false, serverTime, false]];
    _journals set [_patient, [_rows, _closedBefore]];
    missionNamespace setVariable ["ACME_vent_batteryDispositionJournal", _journals];
    [_patient, "ventBatteryExchange", ["claim", _request, _decision, true]] call ACME_fnc_ownerDispatch;
    true
};

private _results = _patient getVariable ["ACME_vent_batterySwapReceipts", createHashMap];
if !(_results isEqualType createHashMap) then {_results = createHashMap;};
private _old = _results getOrDefault [_id, []];
if (_operation == "settled" && {_serverVerified} && {_old isEqualTo []}) exitWith {
    if (count _decision != 3 || {!((_decision select 0) isEqualType true)}
        || {!((_decision select 1) isEqualType 0)} || {!finite (_decision select 1)}
        || {(_decision select 1) < 0} || {(_decision select 1) > 100}
        || {!((_decision select 2) isEqualType [])} || {count (_decision select 2) != 2}
        || {count _results >= 128}) exitWith {false};
    _results set [_id, [+_request, _decision select 0, _decision select 1, true, serverTime]];
    [_patient, "ACME_vent_batterySwapReceipts", _results] call ACME_fnc_setVarNet;
    true
};
private _reply = {
    params ["_accepted", "_returned"];
    ["ACME_ventBatteryExchangeResult", [_request, _accepted, _returned], _medic] call CBA_fnc_targetEvent;
    _accepted
};
if (_old isNotEqualTo []) exitWith {
    if (count _old != 5 || {!((_old select 0) isEqualTo _request)}) exitWith {false};
    if (_old select 3 && {_operation != "claim"}) exitWith {[_old select 1, _old select 2] call _reply};
    private _dispositions = _patient getVariable ["ACME_vent_batterySwapDispositions", createHashMap];
    if !(_dispositions isEqualType createHashMap) exitWith {false};
    private _disposition = _dispositions getOrDefault [_id, []];
    if (_operation == "claim") exitWith {
        if (!_claimValid) exitWith {false};
        if (!_serverVerified) exitWith {
            ["ACME_ventBatteryDispositionClaim", [_request, _decision, "authorize"]] call CBA_fnc_serverEvent;
            false
        };
        private _escrows = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
        private _escrow = _escrows getOrDefault [_id, []];
        if (count _escrow != 3 || {!((_escrow select 0) isEqualTo _request)}) exitWith {false};
        if (_disposition isNotEqualTo []) then {
            _serverVerified = _disposition isEqualTo [_request, _decision select 0, _decision select 1];
        } else {
            _dispositions set [_id, [+_request, _decision select 0, _decision select 1]];
            [_patient, "ACME_vent_batterySwapDispositions", _dispositions] call ACME_fnc_setVarNet;
        };
        // An old granted effect is uncertain until its claimant confirms. It
        // cannot be handed to a replacement owner merely because time passed.
        if (!_serverVerified) exitWith {false};
        [_old select 1, _old select 2] call _reply
    };
    if (_operation == "settled" && {!_serverVerified}) then {
        private _escrows = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
        private _escrow = _escrows getOrDefault [_id, []];
        _serverVerified = count _decision == 3 && {(_decision select [0,2]) isEqualTo [_old select 1, _old select 2]}
            && {count _disposition == 3} && {(_disposition select 0) isEqualTo _request}
            && {(_decision select 2) isEqualTo (_disposition select [1,2])}
            && {count _escrow == 3} && {(_escrow select 0) isEqualTo _request}
            && {(_escrow select 1) >= 1} && {(_escrow select 2) isEqualTo _decision};
    };
    if (_operation == "settled" && {!_serverVerified}) exitWith {false};
    if (_operation == "settled") then {
        _old set [3, true];
        _results set [_id, _old];
        [_patient, "ACME_vent_batterySwapReceipts", _results] call ACME_fnc_setVarNet;
    };
    // Replay before checking live epoch/custody/provider/age. A committed
    // exchange still returns its old fitted charge after any of those change.
    [_old select 1, _old select 2] call _reply
};
if (_operation != "apply") exitWith {false};
// A prior ownership period may have committed before its public decision
// arrived. Its missing receipt cannot authorize another fitted-battery write.
if (_period isNotEqualTo [clientOwner, _patient getVariable ["ACME_providerLocalityEpoch", 0]]) exitWith {false};
private _escrows = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
if !(_escrows isEqualType createHashMap) exitWith {false};
private _escrow = _escrows getOrDefault [_id, []];
if (count _escrow != 3 || {!((_escrow select 0) isEqualTo _request)} || {(_escrow select 1) != 0}) exitWith {false};

private _closedBefore = _patient getVariable ["ACME_vent_batterySwapClosedBefore", -1];
if !(_closedBefore isEqualType 0 && {finite _closedBefore}) then {_closedBefore = -1;};
// Only physically settled decisions can expire. An unacknowledged accepted
// exchange is retained regardless of how many later viewers service the device.
{
    private _row = _results get _x;
    if (_row isEqualType [] && {count _row == 5} && {_row select 3}
        && {serverTime > ((((_row select 0) select 4) + 180) max ((_row select 4) + 180))}) then {
        _closedBefore = _closedBefore max ((_row select 0) select 4);
        _results deleteAt _x;
        private _dispositions = _patient getVariable ["ACME_vent_batterySwapDispositions", createHashMap];
        if (_x in _dispositions) then {
            _dispositions deleteAt _x;
            [_patient, "ACME_vent_batterySwapDispositions", _dispositions] call ACME_fnc_setVarNet;
        };
    };
} forEach keys _results;
if (_closedBefore != (_patient getVariable ["ACME_vent_batterySwapClosedBefore", -1])) then {
    [_patient, "ACME_vent_batterySwapClosedBefore", _closedBefore] call ACME_fnc_setVarNet;
};
// A forgotten old decision is not proof that the reserved battery was unused.
// Leave its custody unresolved; never authorize adoption/refund from that gap.
if (_issued <= _closedBefore) exitWith {false};
// Backpressure preserves every pending accepted/rejected decision. Capacity is
// not a clinical failure or a terminal rejection: the same request retries.
if (count _results >= 128) exitWith {false};
private _fresh = _issued > _closedBefore && {_issued <= serverTime + 2} && {serverTime - _issued <= 120};
private _valid = _fresh && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {_custody == (_patient getVariable ["ACME_vent_custodyId", ""])}
    && {!(_patient getVariable ["ACME_vent_recovering", false])}
    && {alive _medic} && {[_medic] call ace_common_fnc_isAwake}
    && {([_medic, _patient] call ACME_fnc_patientInteractionDistance) <= ace_medical_gui_maxDistance}
    && {!isNull _source};
// A carried preset has no server custody allocation; it must still be the
// provider's actual carried device. Mounted devices require explicit custody.
_valid = _valid && {if (_custody == "") then {
    _patient isEqualTo _medic && {([_patient, "ACME_Ventilator"] call ace_common_fnc_getCountOfItem) > 0}
} else {_patient getVariable ["ACME_vent_onPatient", false]}};
private _accepted = _valid && {serverTime >= (_patient getVariable ["ACME_vent_batterySwapLockUntil", -1])};
private _returned = _incoming;
if (_accepted) then {
    _returned = _patient getVariable ["ACME_vent_battery", 100];
    if !(_returned isEqualType 0 && {finite _returned}) then {_returned = 100;};
    _returned = _returned max 0 min 100;
    _patient setVariable ["ACME_vent_battery", _incoming, true];
    _patient setVariable ["ACME_vent_battWarned", 0, true];
    _patient setVariable ["ACME_vent_batterySwapLockUntil", serverTime + 1, true];
};
_results set [_id, [+_request, _accepted, _returned, false, serverTime]];
[_patient, "ACME_vent_batterySwapReceipts", _results] call ACME_fnc_setVarNet;
[_accepted, _returned] call _reply
