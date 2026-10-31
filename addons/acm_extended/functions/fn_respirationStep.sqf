/* B213 monotonic observation-clock step. Pure arithmetic; no daytime, date, timeMultiplier or network clocks.
 * State: [startTick, previousTick, fractionalBreath, wholeBreaths, previousRate].
 * Use the last observed rate over the elapsed interval, then sample the new rate for the next interval.
 * Clamp the final interval to precisely 15 seconds, so a late PFH cannot inflate the result.
 * Output: [newState, numberOfNewBreaths, elapsedSeconds, complete].
 */
params ["_state", "_now", "_rate"];
_state params ["_start", "_last", "_phase", "_count", "_lastRate"];
if !(_rate isEqualType 0 && {finite _rate}) then {_rate = 0;};
_rate = (_rate max 0) min 80;
private _end = _start + 15;
private _sample = ((_now max _last) min _end) max _start;
private _delta = (_sample - _last) max 0;
_phase = _phase + (_delta * _lastRate / 60);
// A tiny tolerance prevents 14.999999 accumulated float seconds losing an exact boundary breath.
private _breaths = floor (_phase + 0.000001);
_phase = (_phase - _breaths) max 0;
_count = _count + _breaths;
private _elapsed = ((_sample - _start) max 0) min 15;
[[ _start, _sample, _phase, _count, _rate ], _breaths, _elapsed, _elapsed >= 15]
