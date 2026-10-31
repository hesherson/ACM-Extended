/* Settle a decided battery reservation once at the original provider's current
 * owner. Exact public escrow plus owner decision authorizes receipt adoption.
 */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_ventBatteryAck;};
    _result
};
params [["_request", [], [[]]], ["_accepted", false, [false]], ["_returned", -1, [0]], ["_hops", 0, [0]], ["_confirmedClaim", [], [[]]]];
if (count _request != 10 || {!finite _returned} || {_returned < 0} || {_returned > 100}) exitWith {false};
_request params ["_patient", "_medic", "_id", "_incoming", "_issued", "_epoch", "_custody", "_supply", "_source", "_period"];
if (!(_medic isEqualType objNull) || {!(_patient isEqualType objNull)}
    || {isNull _medic} || {isNull _patient} || {!(_source isEqualType objNull)}
    || {!(_id isEqualType "")} || {_id == ""} || {count _id > 128}
    || {!(_incoming isEqualType 0)} || {!finite _incoming} || {_incoming < 0} || {_incoming > 100}
    || {!(_issued isEqualType 0)} || {!finite _issued} || {_issued < 0}
    || {!(_epoch isEqualType 0)} || {!finite _epoch} || {_epoch < 0} || {_epoch != floor _epoch}
    || {!(_custody isEqualType "")} || {count _custody > 128}
    || {!(_supply isEqualType [])} || {count _supply != 4}
    || {!((_supply select 1) in (call ACME_fnc_ventBatteryItems))} || {!((_supply select 3) isEqualType "")}
    || {_incoming != ([_supply select 1] call ACME_fnc_ventBatteryCharge)}
    || {_id != ("vent-battery:" + (_supply select 3))}
    || {!(_period isEqualType [])} || {count _period != 2}
    || {!((_period select 0) isEqualType 0)} || {!finite (_period select 0)} || {(_period select 0) < 0}
    || {isMultiplayer && {(_period select 0) < 2}}
    || {!((_period select 1) isEqualType 0)} || {!finite (_period select 1)} || {(_period select 1) < 0}) exitWith {false};
if (!local _medic) exitWith {
    // A queued target event can reach the former owner during a locality move.
    // Forward its exact observation; it confers no receipt authority here.
    if (_hops >= 0 && {_hops < 4}) then {
        private _forwarded = [_request, _accepted, _returned, _hops + 1];
        if (_confirmedClaim isNotEqualTo []) then {_forwarded pushBack _confirmedClaim;};
        ["ACME_ventBatteryExchangeResult", _forwarded, _medic] call CBA_fnc_targetEvent;
    };
    false
};
private _await = {
    private _observed = [_request, _accepted, _returned];
    if (_confirmedClaim isNotEqualTo []) then {_observed append [0, _confirmedClaim];};
    ["await", _medic, _observed] call ACME_fnc_ventBatteryRequest;
    false
};
private _escrows = _medic getVariable ["ACME_vent_batterySwapEscrow", createHashMap];
if !(_escrows isEqualType createHashMap) exitWith {false};
private _escrow = _escrows getOrDefault [_id, []];
if (_escrow isEqualTo []) exitWith {call _await};
if (count _escrow != 3 || {!((_escrow select 0) isEqualTo _request)}) exitWith {false};
private _retireObserved = {
    private _awaits = _medic getVariable ["ACME_vent_batterySwapAwait", createHashMap];
    _awaits deleteAt _id;
    _medic setVariable ["ACME_vent_batterySwapAwait", _awaits, false];
};
if (_confirmedClaim isNotEqualTo []) exitWith {
    if (count _confirmedClaim != 2 || {!((_confirmedClaim select 0) isEqualType 0)}
        || {!finite (_confirmedClaim select 0)} || {!((_confirmedClaim select 1) isEqualType 0)}
        || {!finite (_confirmedClaim select 1)} || {(_confirmedClaim select 0) < 0}
        || {(_confirmedClaim select 1) < 0}) exitWith {false};
    private _physical = [_accepted, _returned, _confirmedClaim];
    if ((_escrow select 1) >= 3) exitWith {
        if !((_escrow select 2) isEqualTo _physical) exitWith {false};
        call _retireObserved;
        true
    };
    if ((_escrow select 1) >= 1 && {!((_escrow select 2) isEqualTo _physical)}) exitWith {false};
    // This server certificate proves an already completed physical effect. It
    // repairs a stale replica without receipt adoption or any inventory write.
    _escrows set [_id, [_request, 3, _physical]];
    _medic setVariable ["ACME_vent_batterySwapEscrow", _escrows, true];
    private _awaits = _medic getVariable ["ACME_vent_batterySwapAwait", createHashMap];
    _awaits deleteAt _id;
    _medic setVariable ["ACME_vent_batterySwapAwait", _awaits, false];
    ["ACME_ventBatteryDispositionClaim", [_request, _physical, "confirm"]] call CBA_fnc_serverEvent;
    true
};
if ((_escrow select 1) >= 3) exitWith {
    private _physical = _escrow select 2;
    if (!(_physical isEqualType []) || {count _physical != 3}
        || {!((_physical select [0,2]) isEqualTo [_accepted, _returned])}) exitWith {false};
    // A completed immutable receipt remains sufficient after the patient's
    // replay window expires. Late ordinary ACKs do not create retry work.
    call _retireObserved;
    true
};
private _results = _patient getVariable ["ACME_vent_batterySwapReceipts", createHashMap];
if !(_results isEqualType createHashMap) exitWith {false};
private _result = _results getOrDefault [_id, []];
private _known = count _result == 5 && {(_result select 0) isEqualTo _request}
    && {(_result select 1) isEqualTo _accepted} && {(_result select 2) == _returned};
// A missing public decision may simply be in transit. A discarded old decision
// is ambiguous too. Neither case authorizes physical receipt adoption/refund.
if (!_known) exitWith {if (_result isEqualTo []) then {call _await}; false};
// The observed decision is now independently proven. Any opaque observation
// with this ID can retire; a failed physical refund remains in public escrow.
private _awaits = _medic getVariable ["ACME_vent_batterySwapAwait", createHashMap];
if (_awaits isEqualType createHashMap) then {
    _awaits deleteAt _id;
    _medic setVariable ["ACME_vent_batterySwapAwait", _awaits, false];
};
private _decision = [_accepted, _returned];
private _dispositions = _patient getVariable ["ACME_vent_batterySwapDispositions", createHashMap];
private _disposition = _dispositions getOrDefault [_id, []];
private _claim = if (count _disposition == 3 && {(_disposition select 0) isEqualTo _request}) then {_disposition select [1,2]} else {[]};
if ((_escrow select 1) > 0) exitWith {
    private _physical = _escrow select 2;
    if (count _physical != 3 || {!((_physical select [0,2]) isEqualTo _decision)}) exitWith {false};
    if ((_escrow select 1) == 1 && {_known}) then {
        if (_result select 3) then {
            _escrows set [_id, [_request, 2, _physical]];
            _medic setVariable ["ACME_vent_batterySwapEscrow", _escrows, true];
            ["ACME_ventBatteryDispositionClaim", [_request, _physical, "confirm"]] call CBA_fnc_serverEvent;
        } else {
            [_patient, "ventBatteryExchange", ["settled", _request, _physical]] call ACME_fnc_ownerDispatch;
        };
    };
    true
};
if (_known && {_result select 3}) exitWith {
    // A late provider replica can still show state zero after its former owner
    // physically settled. The owner's confirmation is not a second refund.
    if (_claim isEqualTo []) exitWith {
        [_patient, "ventBatteryExchange", ["claim", _request,
            [clientOwner, _medic getVariable ["ACME_providerLocalityEpoch", 0]]]] call ACME_fnc_ownerDispatch;
        false
    };
    _escrows set [_id, [_request, 2, _decision + [_claim]]];
    _medic setVariable ["ACME_vent_batterySwapEscrow", _escrows, true];
    ["ACME_ventBatteryDispositionClaim", [_request, _decision + [_claim], "confirm"]] call CBA_fnc_serverEvent;
    true
};
if (_claim isEqualTo []) exitWith {
    [_patient, "ventBatteryExchange", ["claim", _request,
        [clientOwner, _medic getVariable ["ACME_providerLocalityEpoch", 0]]]] call ACME_fnc_ownerDispatch;
    false
};
if !(_claim isEqualTo [clientOwner, _medic getVariable ["ACME_providerLocalityEpoch", 0]]) exitWith {false};
_decision pushBack _claim;
if (count _supply != 4 || {isNull _source}) exitWith {false};
private _supplies = missionNamespace getVariable ["ACME_supplyReceipts", createHashMap];
private _receiptId = _supply select 3;
private _local = _supplies getOrDefault [_receiptId, []];
if (_local isNotEqualTo [] && {!(_local isEqualTo _supply)}) exitWith {false};
if (_local isEqualTo []) then {
    _supplies set [_receiptId, +_supply];
    missionNamespace setVariable ["ACME_supplyReceipts", _supplies];
};
private _oldCharge = _source getVariable ["ACME_vent_spareBattery", _incoming];
_source setVariable ["ACME_vent_spareBattery", _returned, true];
private _returnItem = if (_accepted) then {[_returned] call ACME_fnc_ventBatteryCharge} else {_supply select 1};
if !([_supply, true, _returnItem] call ACME_fnc_treatmentSupplyRefund) exitWith {
    // The supply API can fail after deleting its local receipt. Keep this
    // disposition unresolved and retain exact adoption evidence for retry.
    _source setVariable ["ACME_vent_spareBattery", _oldCharge, true];
    false
};
_escrows set [_id, [_request, 1, _decision]];
_medic setVariable ["ACME_vent_batterySwapEscrow", _escrows, true];
if (_known) then {[_patient, "ventBatteryExchange", ["settled", _request, _decision]] call ACME_fnc_ownerDispatch;};
if ((uiNamespace getVariable ["ACME_vent_batterySwapRequest", ""]) == _id) then {
    uiNamespace setVariable ["ACME_vent_batterySwapRequest", ""];
    uiNamespace setVariable ["ACME_vent_batterySwapSupply", []];
};
if (hasInterface && {(missionNamespace getVariable ["ACE_player", objNull]) isEqualTo _medic}) then {
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    if (!isNull _dlg && {(uiNamespace getVariable ["ACME_vent_target", objNull]) isEqualTo _patient}) then {
        (_dlg displayCtrl 88001) ctrlSetText (if (_accepted) then {format ["BATTERY %1%2 OFF", round _incoming, "%"]} else {"SWAP CONFLICT"});
        (_dlg displayCtrl 88001) ctrlShow true;
        uiNamespace setVariable ["ACME_vent_swapMsgUntil", diag_tickTime + 2.5];
    };
};
true
