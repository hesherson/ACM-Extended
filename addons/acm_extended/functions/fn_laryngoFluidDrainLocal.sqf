/* Patient-owner remaining-volume ledger. Concurrent providers subtract once each.
   Late requests cannot drain a new emesis episode or a healed/restored patient. */
params ["_patient", "_medic", "_epoch", "_id", "_expected", "_amount", ["_token", ""]];
if (!local _patient) exitWith {[_patient, "laryngoFluidDrain", _this] call ACME_fnc_ownerDispatch;};
if (isNull _patient || {isNull _medic} || {!alive _medic}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!(_amount isEqualType 0)} || {!finite _amount} || {_amount <= 0} || {_amount > 10}) exitWith {};
if (_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}) exitWith {};
private _session = (_patient getVariable ["ACME_suctionSessions", []]) select {(_x select 0) == _token && {(_x select 1) == _medic} && {(_x select 2) > CBA_missionTime}};
if (_session isEqualTo [] || {!alive _patient} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};
private _receipts = _patient getVariable ["ACME_laryngoEventReceipts", []];
if (_id in _receipts) exitWith {};
private _state = [_patient] call ACME_fnc_laryngoFluidState;
_state params ["_stamp", "_kind", "_remaining"];
if !(_stamp isEqualTo _expected) exitWith {};
if (_kind == "" || {_remaining <= 0}) exitWith {};
_receipts pushBack _id;
if (count _receipts > 64) then {_receipts deleteAt 0;};
_patient setVariable ["ACME_laryngoEventReceipts", _receipts, true];
private _totals = _patient getVariable ["ACME_suctionTotals", []];
private _ti = _totals findIf {(_x select 0) == _token};
if (_ti < 0) then {_ti = _totals pushBack [_token, 0, 0];};
private _manual = ((_session select 0) select 3) == "manual";
if (_manual) then {
    private _base = (_medic getVariable ["ACME_suctionManualSession", []]) param [2, 0];
    _amount = _amount min (((1000 - _base - ((_totals select _ti) select 2)) max 0) / 50);
};
private _removed = _remaining min _amount;
_remaining = (_remaining - _removed) max 0;
private _ml = _removed * 50;
private _total = _totals select _ti;
_total set [1, (_total select 1) + _ml];
if (_manual) then {_total set [2, (_total select 2) + _ml];};
_totals set [_ti, _total];
if (count _totals > 64) then {_totals deleteAt 0;};
_patient setVariable ["ACME_suctionTotals", _totals, true];
// Persist the exact remaining amount in the compartment that was physically debited. Native obstruction values
// are event counters; they are retained until the compartment reaches zero, while this ledger carries volume.
switch (_kind) do {
    case "v": {
        private _native = (_patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0]) max 0;
        _patient setVariable ["ACME_laryngo_poolVomit", [_native, _remaining], true];
    };
    case "b": {
        private _eventSerial = (_patient getVariable ["ACME_airwayBloodEventSerial", 0]) max 0;
        if (_eventSerial <= 0) then {
            _eventSerial = (_patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0]) max 0;
        };
        _patient setVariable ["ACME_laryngo_poolBlood", [_eventSerial, _remaining], true];
    };
    case "s": {
        private _secretions = _patient getVariable ["ACME_laryngo_secretions", []];
        _patient setVariable ["ACME_laryngo_secretions", [_secretions param [0, ""], _remaining], true];
    };
};
// Once the new compartment ledgers have been touched, retire the legacy shared ledger so it cannot be migrated
// again on a later event.
_patient setVariable ["ACME_laryngo_pool", [], true];
if (_remaining <= 0) then {
    if (_kind == "v") then {
        _patient setVariable ["ACME_laryngo_poolVomit", [], true];
        [_patient, [["vomit", 0], ["vomitGrace", CBA_missionTime]], true] call ACM_airway_fnc_setAirwayState;
        _patient setVariable ["ACME_laryngo_emesis", [], true];
    } else {
        if (_kind == "b") then {
            // Preserve the last event serial at zero volume. A later genuine bleeding event increments the serial
            // and therefore contributes exactly one new contamination delta. Clearing this ledger would make the
            // monotonic serial look like total current volume and could refill a freshly suctioned airway to the cap.
            private _eventSerial = (_patient getVariable ["ACME_airwayBloodEventSerial", 0]) max 0;
            _patient setVariable ["ACME_laryngo_poolBlood", [_eventSerial, 0], true];
            [_patient, [["blood", 0]], true] call ACM_airway_fnc_setAirwayState;
        };
        if (_kind == "s") then {_patient setVariable ["ACME_laryngo_secretions", [], true];};
    };
    [_patient, true] call ACM_airway_fnc_clearAirwayCheckedTime;
};
// Miss streaks end on successful placement, not on every squeeze or dialog reopen.
