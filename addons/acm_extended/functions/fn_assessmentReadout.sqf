/* B227: normal-speed observed duration may grow during a graph blend; the UI must not rewind.
 * Keep one progress owner, hold the last second until actual completion, never synthesize success. */
params ["_elapsed", "_duration", ["_previous", [-1, 0]], ["_complete", false]];
if (_complete) exitWith {[0, 1]};
private _seconds = ceil ((_duration - _elapsed) max 1);
if ((_previous param [0, -1]) >= 0) then {_seconds = _seconds min (_previous select 0);};
private _ratio = ((_elapsed / (_duration max 0.001)) max 0) min 0.99;
[_seconds max 1, _ratio max (_previous param [1, 0])]
