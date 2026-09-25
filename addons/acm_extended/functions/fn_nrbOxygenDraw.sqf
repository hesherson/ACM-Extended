/* Medic-owner cargo transaction. A session high-water mark bounds storage while
   preventing duplicate reserve draws even when an acknowledgement is delayed >120 s.
   The ledger is replicated for normal locality transfer, not a crash-durable database. */
params ["_patient", "_medic", "_session", "_sequence", ["_hops", 0], ["_source", objNull]];
if (isNull _patient || {isNull _medic}) exitWith {};
if (isNull _source) then {_source = _medic;};
if (!local _source) exitWith {
    if (_hops < 4) then { ["ACME_nrbDraw", [_patient, _medic, _session, _sequence, _hops + 1, _source], _source] call CBA_fnc_targetEvent; };
};
// [session, highest sequence, last result, patient, last committed time]
private _ledger = +(_source getVariable ["ACME_nrb_drawLedger", []]);
private _index = _ledger findIf {(_x select 0) == _session};
private _highest = if (_index >= 0) then {(_ledger select _index) select 1} else {0};
private _ok = false;
private _known = false;
if (_index >= 0 && {_sequence <= _highest}) then {
    // Only one draw can be outstanding. Earlier sequences necessarily succeeded;
    // depletion terminates flow and cannot be followed by another successful sequence.
    _ok = _sequence < _highest || {(_ledger select _index) select 2};
    _known = true;
} else {
    private _pending = _patient getVariable ["ACME_nrb_drawPending", []];
    if ((_patient getVariable ["ACME_nrb_session", ""]) == _session
        && {_patient getVariable ["ACME_nrb_on", false]}
        && {(_patient getVariable ["ACME_nrb_medic", objNull]) == _medic}
        && {(_patient getVariable ["ACME_nrb_oxygenSource", _medic]) isEqualTo _source}
        && {count _pending >= 3} && {(_pending select 0) == _session}
        && {(_pending select 1) == _sequence}) then {
        _ok = alive _medic && {[_source] call ACM_breathing_fnc_useOxygenTankReserve};
        _known = true;
        if (_index >= 0) then { _ledger deleteAt _index; };
        _ledger = _ledger select {
            private _p = _x select 3;
            CBA_missionTime - (_x select 4) < 120 || {
                !isNull _p && {_p getVariable ["ACME_nrb_on", false]}
                && {(_p getVariable ["ACME_nrb_session", ""]) == (_x select 0)}
            }
        };
        _ledger pushBack [_session, _sequence, _ok, _patient, CBA_missionTime];
        _source setVariable ["ACME_nrb_drawLedger", _ledger, true];
    };
};
// Missing replicated request/session state is not depletion. The same request retries.
if (!_known) exitWith {};
["ACME_ownerCommand", [_patient, "nrbAck", [_patient, _session, _sequence, _ok]], _patient] call CBA_fnc_targetEvent;
