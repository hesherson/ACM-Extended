/* B223: presentation-only taper after the initial 20-second arrest convulsion window.
   The two random samples are injectable for deterministic tests; no physiology is mutated.
   At 20 s: 80-120 ms, 4-8 s quiet. At 200+ s: 40-60 ms, 20-40 s quiet. */
params [["_arrestAge", 200, [0]], ["_durationSample", -1, [0]], ["_gapSample", -1, [0]]];
if (!finite _arrestAge) then {_arrestAge = 200;};
if (_durationSample < 0) then {_durationSample = random 1;};
if (_gapSample < 0) then {_gapSample = random 1;};
private _taper = ((_arrestAge - 20) / 180) max 0 min 1;
[(0.08 + 0.04 * (_durationSample max 0 min 1)) * (1 - 0.5 * _taper),
 (4 + 4 * (_gapSample max 0 min 1)) * (1 + 4 * _taper)]
