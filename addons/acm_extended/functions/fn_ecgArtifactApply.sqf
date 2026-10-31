/* Add bounded harmless motion artifact to an ECG buffer and mark contaminated columns unsafe for SYNC flags. */
params ["_patient", "_arr", ["_safe", []]];
if (isNull _patient || {_arr isEqualTo []}) exitWith {[_arr,_safe]};
private _strength = [_patient] call ACME_fnc_ecgArtifactStrength;
if (_strength <= 0.001) exitWith {[_arr,_safe]};
private _out = +_arr;
private _mask = +_safe;
if (count _mask < count _out) then {_mask resize [count _out, true];};
private _phase = floor (CBA_missionTime / 0.03);
private _emg = 16 * (_strength ^ 4);
for "_i" from 0 to ((count _out)-1) do {
    // Sustained high-frequency EMG obscures the underlying complexes during convulsions.
    // Lesser manipulation produces baseline wander and intermittent bursts instead.
    private _wander = (sin ((_phase + _i) * 31)) * (1.6 * _strength + _emg)
        + (sin ((_phase + _i) * 117)) * (_emg * 0.65)
        + (sin ((_phase + _i) * 7)) * 0.9 * _strength;
    if (_strength >= 0.80) then {_mask set [_i, false];};
    _out set [_i, (_out select _i) + _wander];
};
private _bursts = 1 + floor (_strength * 2);
for "_b" from 1 to _bursts do {
    private _center = floor random (count _out);
    private _width = 2 + floor random 5;
    private _amp = random [7, 12, 18] * _strength;
    for "_j" from -_width to _width do {
        private _idx = _center + _j;
        if (_idx >= 0 && {_idx < count _out}) then {
            private _sign = [1,-1] select (((_j + _b) mod 2) == 0);
            private _shape = 1 - (abs _j / ((_width + 1) max 1));
            _out set [_idx, (_out select _idx) + (_sign * _amp * _shape) + random [-2,0,2]];
            _mask set [_idx, false];
        };
    };
};
[_out,_mask]
