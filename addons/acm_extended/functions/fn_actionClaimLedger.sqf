/* Bounded patient-owner request history for the DP/Hang Bag claim families.
 * Records survive ownership transfer; a clinical epoch change retires the old history.
 * Eight seconds exceeds the five-second admission window plus clock tolerance. Never
 * evict an unexpired cancellation: saturation blocks unknown claims for that window.
 * lookup is read-only unless pruning/epoch retirement or first saturation changes the compact history.
 */
params [
    ["_patient",objNull,[objNull]], ["_scope","",[""]], ["_medic",objNull,[objNull]],
    ["_token","",["",0]], ["_epoch",-1,[0]], ["_op","lookup",[""]],
    ["_sequence",0,[0]], ["_result",[],[[]]]
];
if (isNull _patient || {!local _patient} || {isNull _medic} || {_scope == ""} || {_token isEqualTo ""}
    || {_token isEqualType 0 && {!finite _token || {_token < 0}}}
    || {!finite _epoch} || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!finite _sequence} || {_sequence < 0} || {_sequence != floor _sequence}
    || {!(_op in ["lookup","accept","reject","cancel"])}) exitWith {["blocked",-1,[]]};
private _now = serverTime;
private _raw = _patient getVariable ["ACME_actionClaimHistory",[]];
private _rows = [];
private _blockedUntil = -1;
if (_raw isEqualType [] && {count _raw == 3} && {(_raw select 0) isEqualTo _epoch}) then {
    private _saved = _raw select 1;
    if (_saved isEqualType []) then {
        _rows = _saved select {
            _x isEqualType [] && {count _x == 7}
            && {(_x select 6) isEqualType 0} && {finite (_x select 6)} && {(_x select 6) > _now}
        };
    };
    private _until = _raw select 2;
    if (_until isEqualType 0 && {finite _until} && {_until > _now}) then {_blockedUntil = _until;};
};
private _index = _rows findIf {
    (_x select 0) isEqualTo _scope && {(_x select 1) isEqualTo _medic} && {(_x select 2) isEqualTo _token}
};
private _answer = ["new",-1,[]];
if (_index >= 0) then {
    private _record = _rows select _index;
    _answer = [_record select 3,_record select 4,+(_record select 5)];
} else {
    // A capacity refusal must stay refused even if earlier rows expire before this request does.
    if (count _rows >= 64 && {_blockedUntil <= _now}) then {_blockedUntil = _now + 8;};
    if (_blockedUntil > _now || {count _rows >= 64}) then {_answer = ["blocked",-1,[]];};
};
if (_op != "lookup") then {
    private _cancelled = (_answer select 0) == "cancelled";
    // Cancellation is terminal for this exact token. An old sequence cannot replace a newer result.
    if ((_op == "cancel" && {!_cancelled}) || {_op != "cancel" && {!_cancelled && {_sequence > (_answer select 1)}}}) then {
        private _state = switch (_op) do {case "accept": {"accepted"}; case "reject": {"rejected"}; default {"cancelled"};};
        private _row = [_scope,_medic,_token,_state,_sequence,+_result,_now + 8];
        if (_index >= 0) then {
            _rows set [_index,_row];
            _answer = [_state,_sequence,+_result];
        } else {
            if (count _rows < 64 && {_blockedUntil <= _now}) then {
                _rows pushBack _row;
                _answer = [_state,_sequence,+_result];
            } else {
                // A release still clears its live action in the caller. Hold off all unknown claims
                // until that unrecorded cancellation is too old for admission on any machine.
                if (_op == "cancel") then {_blockedUntil = _blockedUntil max (_now + 8);};
                _answer = ["blocked",-1,[]];
            };
        };
    };
};
private _next = [_epoch,_rows,_blockedUntil];
if !(_next isEqualTo _raw) then {_patient setVariable ["ACME_actionClaimHistory",_next,true];};
_answer
