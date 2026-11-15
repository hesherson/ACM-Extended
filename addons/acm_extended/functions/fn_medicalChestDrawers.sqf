/* Set a sampled phase on the native drawers while cabinet simulation is disabled. */
params ["_cabinet", "_plan", ["_fraction", 1]];
_plan params ["_names", "_phases", "_useSources"];
{
    private _phase = (_phases select _forEachIndex) * _fraction;
    if (_useSources) then {
        _cabinet animateSource [_x, _phase, true];
    } else {
        _cabinet animate [_x, _phase, true];
    };
} forEach _names;
