/* B269: owner-side ordering memory for ended ACCESS lease IDs.
 * This records cancellation only; manual/kit teardown keeps its own gear policy.
 * Public records survive patient ownership changes. IDs are session-unique;
 * retain at most 64 for 180 s, with no refresh/reordering on duplicate stops.
 * This is bounded replay protection, not sender authentication.
 */
params [["_patient", objNull, [objNull]], ["_ids", [], [[]]]];
if (isNull _patient || {!local _patient}) exitWith {false};
private _closed = +(_patient getVariable ["ACME_chestAccess_closedLeases", []]);
_closed = _closed select {(_x param [1, 0]) > serverTime};
{
    private _id = _x;
    if (_id isEqualType "" && {_id != ""}
        && {(_closed findIf {(_x param [0, ""]) == _id}) < 0}) then {
        _closed pushBack [_id, serverTime + 180];
    };
} forEach _ids;
if (count _closed > 64) then {_closed = _closed select [count _closed - 64, 64];};
_patient setVariable ["ACME_chestAccess_closedLeases", _closed, true];
true
