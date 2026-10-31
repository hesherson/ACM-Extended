// Validate a locally tracked UI voice before stopping it. Native IDs can be reused; the engine exposes no
// generation token. Reject observable reuse (missing/different clip or reset progress), rather than stopping it.
params ["_channel", ["_now", diag_tickTime]];
private _id = _channel param [0,-1];
private _proof = _channel param [6,[]];
if !(_id isEqualType 0 && {_id >= 0} && {count _proof == 5}) exitWith {false};
private _info = soundParams _id;
if (count _info < 5) exitWith {false};
_info params ["_path","_position","_length","_elapsed"];
_proof params ["_oldPath","_oldLength","_oldElapsed","_oldPosition","_polled"];
private _advance = ((_now - _polled) max 0) * ((_channel param [3,1]) max 1) + 0.25;
if (_path != _oldPath || {_length != _oldLength} || {_position >= 1}
    || {_position < (_oldPosition - 0.001)} || {_elapsed < (_oldElapsed - 0.01)}
    || {_elapsed > (_oldElapsed + _advance)}) exitWith {false};
_channel set [6,[_path,_length,_elapsed,_position,_now]];
true
