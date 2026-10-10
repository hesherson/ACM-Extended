/* Patient-owner remaining-volume ledger. Concurrent providers subtract once each.
   Late requests cannot drain a new emesis episode or a healed/restored patient. */
params ["_patient", "_medic", "_epoch", "_id", "_expected", "_amount", ["_token", ""]];
if (!local _patient) exitWith {[_patient, "laryngoFluidDrain", _this] call ACME_fnc_ownerDispatch;};
if (isNull _patient || {isNull _medic} || {!alive _medic}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!(_amount isEqualType 0)} || {!finite _amount} || {_amount <= 0} || {_amount > 10}) exitWith {};
if (_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}) exitWith {};
private _session = (_patient getVariable ["ACME_suctionSessions", []]) select {(_x select 0) == _token && {(_x select 1) == _medic} && {(_x select 2) > CBA_missionTime}};
if (_session isEqualTo [] || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};
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
// Persist partial secretion debits in their compartment as well as the active
// ledger, so a later native blood/vomit event cannot restore already-suctioned fluid.
if (_removed > 0 && {_kind in ["b", "s"]}) then {
    private _field = if (_kind == "b") then {"ACME_airwayBloodRefillAt"} else {"ACME_airwaySecretionRefillAt"};
    _patient setVariable [_field, CBA_missionTime + 30, true];
};
// Blood has its own partial-volume ledger, even when vomit temporarily covers it.
if (_kind == "b") then {
    _patient setVariable ["ACME_laryngo_bloodRemaining", [_patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0], _remaining], true];
};
if (_kind == "s") then {
    private _secretions = _patient getVariable ["ACME_laryngo_secretions", []];
    _patient setVariable ["ACME_laryngo_secretions", [_secretions param [0, ""], _remaining], true];
};
if (_remaining <= 0) then {
    if (_kind == "v") then {
        [_patient, [["vomit", 0], ["vomitGrace", CBA_missionTime]], true] call ACM_airway_fnc_setAirwayState;
        _patient setVariable ["ACME_laryngo_emesis", [], true];
    } else {
        if (_kind == "b") then {
            [_patient, [["blood", 0]], true] call ACM_airway_fnc_setAirwayState;
            _patient setVariable ["ACME_laryngo_bloodRemaining", [], true];
        };
        if (_kind == "s") then {_patient setVariable ["ACME_laryngo_secretions", [], true];};
    };
    [_patient, true] call ACM_airway_fnc_clearAirwayCheckedTime;
    _patient setVariable ["ACME_laryngo_pool", [], true];
    // The next compartment has its own initial volume; clearing vomit does not clear blood.
    private _next = [_patient] call ACME_fnc_laryngoFluidState;
    _stamp = _next select 0;
    _remaining = _next select 2;
};
_patient setVariable ["ACME_laryngo_pool", [_stamp, _remaining], true];
// Miss streaks end on successful placement, not on every squeeze or dialog reopen.
