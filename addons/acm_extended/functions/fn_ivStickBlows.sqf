/* Deterministic placement outcome from the original puncture, never a random reroll.
   Accuracy is distance / hit radius, captured by ivMinigameClick and retained by the B7 view journal.
   Misses always infiltrate. Blood pressure already narrows the hit radius in ivSiteDifficulty.
   The wrist catalog adds a very small oversized-catheter tolerance without an automatic blood-loss veto. */
params [["_bodyPart", "", [""]], ["_site", ""], ["_gauge", 16, [0]],
    ["_hit", false, [true]], ["_accuracy", 1, [0]]];
if (!_hit) exitWith {true};
if !(_site isEqualTypeAny ["", 0]) exitWith {true};
if !(_gauge in [14, 16, 18, 20]) exitWith {true};
if (!finite _accuracy || {_accuracy < 0} || {_accuracy > 1}) exitWith {true};
private _vein = [_bodyPart, _site] call ACME_fnc_ivVeinCatalog;
if ((count _vein) == 0) exitWith {false};
private _maxG = _vein getOrDefault ["maxG", 16];
if (_gauge >= _maxG) exitWith {false};
private _steps = (_maxG - _gauge) / 2;
private _defaultTolerance = switch (true) do {
    case (_steps >= 3): {0.15};
    case (_steps >= 2): {0.35};
    default {0.60};
};
private _tolerance = _vein getOrDefault ["oversizeTolerance", _defaultTolerance];
_accuracy > _tolerance
