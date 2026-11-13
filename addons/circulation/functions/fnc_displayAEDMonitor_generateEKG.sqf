// Compile-time ACM fork implementation of ACM_circulation_fnc_displayAEDMonitor_generateEKG.
// Organized rhythms are sampled from the AED's actual electrical beat clock instead of tiling an integer-width
// beat block. That matters because most real R-R periods are fractional monitor columns (for example 131 BPM is
// ~15.27 columns). Rounding every beat to 15 columns accumulated phase error, then later refreshes "caught up" by
// jumping a complex. Here every screen sample is evaluated against the exact 60/HR clock, so the R wave remains
// phase-locked to the audible AED beep without cumulative drift. Mid-sweep refreshes therefore regenerate the same
// timeline instead of inventing a second competing rhythm.
params ["_rhythm", "_spacing", "_arrayOffset", ["_sampleContext",[]]];

private _target = _sampleContext param [0,missionNamespace getVariable ["ACM_circulation_AED_Monitor_Target",objNull]];
if (!isNull _target) then {
    private _effective = [_target] call ACME_fnc_rhythmGet;
    // Native CPR/post-shock visual states retain precedence over an ACME proxy rhythm.
    if (_effective >= 100 && {!(_rhythm in [-1,1,2])}) then {_rhythm = _effective;};
};

// ACME custom rhythms keep their dedicated morphology generator. It uses the same sweep/beep anchoring contract.
if (_rhythm >= 100) exitWith {
    private _g = [_rhythm, _spacing, _arrayOffset, _sampleContext] call ACME_fnc_genRhythmEKG;
    private _result = [_target, _g select 0, _g select 1] call ACME_fnc_ecgArtifactApply;
    if (_sampleContext isNotEqualTo []) then {_result append [_g param [2,[]],_g param [3,[]]];};
    _result
};

// A morphology subtype, not a new rhythm code. CPR and post-shock visual states keep precedence.
private _widePEA = _rhythm == 5 && {[_target] call ACME_fnc_peaIsWide};
private _W = _sampleContext param [3,176];
private _lastIndex = _W - 1;
private _dt = 0.03;
private _now = CBA_missionTime;
private _cursorEpoch = if (!isNull _target) then {
    _target getVariable ["ACME_AED_MonitorCursorTime", _now]
} else {_now};
if (!(_cursorEpoch isEqualType 0) || {!finite _cursorEpoch}) then {_cursorEpoch = _now;};

private _rateHR = 0;
if (!isNull _target) then {
    _rateHR = [_target] call ACM_circulation_fnc_getEKGHeartRate;
    if (_rateHR <= 0 && {_rhythm in [-1,0,4]}) then {
        _rateHR = _target getVariable ["ace_medical_heartRate", 0];
    };
};
if (!(_rateHR isEqualType 0) || {!finite _rateHR}) then {_rateHR = 0;};
_rateHR = _rateHR max 0;
private _rr = if (_rateHR > 0) then {60 / _rateHR} else {0};

// During an active sweep, index _anchor is the sample that is on screen "now". At the right edge, the next
// refresh is for a new sweep, so index 0 becomes the time anchor. This prevents the 175 -> 1 wrap from changing
// ECG phase merely because the x-coordinate wrapped around.
private _anchor = 0;
if (!isNull _target) then {
    private _step = floor (_target getVariable ["ACM_circulation_AED_UpdateStep", 0]);
    if (_step >= 1 && {_step < _lastIndex}) then {_anchor = _step;};
};

private _lastBeat = -1;
private _previousRR = _rr;
private _nextRR = _rr;
if (!isNull _target) then {
    _lastBeat = _target getVariable ["ACM_circulation_AED_Pads_LastBeep", -1];
    _previousRR = _target getVariable ["ACME_AED_PreviousRR", _rr];
    _nextRR = _target getVariable ["ACME_AED_NextRR", _rr];
};
if (!(_previousRR isEqualType 0) || {!finite _previousRR} || {_previousRR <= 0}) then {_previousRR = _rr;};
if (!(_nextRR isEqualType 0) || {!finite _nextRR} || {_nextRR <= 0}) then {_nextRR = _rr;};
if (_lastBeat < 0 && {_rr > 0}) then {_lastBeat = _cursorEpoch;};
private _beatSerialBase = if (!isNull _target) then {_target getVariable ["ACME_AED_BeatSerial", 0]} else {0};
if (_sampleContext isNotEqualTo []) then {
    _sampleContext params ["","_start","_rate"];
    _cursorEpoch = _start;
    _anchor = 0;
    _rr = if (_rate > 0) then {60 / _rate} else {0};
};

// Stable, time-derived monitor noise. Regenerating a buffer produces the same local baseline rather than a fresh
// random trace, which removes refresh seams while retaining a live-looking signal.
private _fnc_noise = {
    params ["_sampleIndex", "_amp", ["_salt", 0]];
    (((sin (((_sampleIndex * 137.507) + _salt) mod 360)) * 0.62)
        + ((sin (((_sampleIndex * 47.311) + 91 + _salt) mod 360)) * 0.38)) * _amp
};

private _arr = [];
private _safe = [];
_arr resize [_W, 0];
_safe resize [_W, true];
private _peaks = [];
private _phases = [];
private _beats = _sampleContext param [4,[]];
private _beatIndex = 0;
_phases resize [_W,99];

for "_i" from 0 to _lastIndex do {
    private _sampleTime = _cursorEpoch + ((_i - _anchor) * _dt);
    private _sampleIndex = floor (_sampleTime / _dt);
    private _value = 0;
    private _isSafe = true;

    switch (_rhythm) do {
        case 1: { // Asystole: deterministic low-amplitude baseline noise.
            _value = [_sampleIndex, 1.8, 13] call _fnc_noise;
        };
        case 2: { // VF: continuous chaotic signal. No organized QRS/beep lock is appropriate.
            _value =
                (sin (((_sampleIndex * 71.7) + 11) mod 360)) * 14
                + (sin (((_sampleIndex * 31.9) + 123) mod 360)) * 9
                + (sin (((_sampleIndex * 113.3) + 41) mod 360)) * 6;
            _value = _value + ([_sampleIndex, 3.0, 211] call _fnc_noise);
            _isSafe = false;
        };
        default {
            // Organized electrical activity. Choose the nearest actual electrical beat, then sample the morphology
            // relative to that beat. Beat centers stay at n * (60/HR) seconds even when that interval is fractional
            // in 0.03-second monitor columns.
            if (_rr <= 0) then {
                _value = [_sampleIndex, 1.5, 7] call _fnc_noise;
            } else {
                // Use the exact interval that the audible scheduler selected for the immediately previous and
                // immediately next beat. Farther-away future/past beats can use the current nominal RR; they will be
                // replaced long before the sweep reaches them. This makes the on-screen R wave and the sound consume
                // one clock even while HR is changing.
                private _beatTime = _lastBeat;
                private _beatNumber = 0;
                if (_sampleTime >= _lastBeat) then {
                    private _nextBeat = _lastBeat + _nextRR;
                    if (_sampleTime <= _nextBeat) then {
                        if (abs (_sampleTime - _nextBeat) < abs (_sampleTime - _lastBeat)) then {
                            _beatTime = _nextBeat;
                            _beatNumber = 1;
                        };
                    } else {
                        private _n = round ((_sampleTime - _nextBeat) / (_rr max 0.05));
                        _beatTime = _nextBeat + (_n * _rr);
                        _beatNumber = 1 + _n;
                    };
                } else {
                    private _previousBeat = _lastBeat - _previousRR;
                    if (_sampleTime >= _previousBeat) then {
                        if (abs (_sampleTime - _previousBeat) < abs (_sampleTime - _lastBeat)) then {
                            _beatTime = _previousBeat;
                            _beatNumber = -1;
                        };
                    } else {
                        private _n = round ((_sampleTime - _previousBeat) / (_rr max 0.05));
                        _beatTime = _previousBeat + (_n * _rr);
                        _beatNumber = -1 + _n;
                    };
                };
                // BeatSerial increments on the exact audible beat. Adding the relative beat number means a beat that
                // was predicted as +1 before the beep keeps the SAME morphology after it becomes beat 0 on the next
                // refresh. Without this, PEA/custom beat variation could visibly change shape at the beep boundary.
                if (_beats isNotEqualTo []) then {
                    while {_beatIndex+1 < count _beats
                        && {abs (_sampleTime-((_beats select (_beatIndex+1)) select 0)) < abs (_sampleTime-((_beats select _beatIndex) select 0))}} do {
                        _beatIndex = _beatIndex+1;
                    };
                    (_beats select _beatIndex) params ["_plannedAt","_plannedSerial"];
                    _beatTime = _plannedAt;
                    _beatNumber = _plannedSerial - _beatSerialBase;
                };
                private _beatOrdinal = _beatSerialBase + _beatNumber;
                private _deltaSec = _sampleTime - _beatTime;
                private _offset = round (_deltaSec / _dt);
                if (_sampleContext isNotEqualTo []) then {
                    _phases set [_i,_offset];
                    if (_rhythm != -1 && {_deltaSec >= -_dt/2} && {_deltaSec < _dt/2}) then {_peaks pushBack _i;};
                };

                // Default PEA uses the same P-QRS-T morphology as sinus. Electrical organization
                // never implies a pulse: native rhythm 5 remains authoritative for physiology.
                private _template = if ((_rr / _dt) < 18) then {
                    [0,-4,-40,22,4,-4,2,0]
                } else {
                    [0,-1,-5,2,-4,-40,25,5,0,-5,-7,-1,5,4,0.8]
                };
                private _rIndex = if ((_rr / _dt) < 18) then {2} else {5};
                private _noiseAmp = 1.8;

                switch (_rhythm) do {
                    case -1: { // CPR artifact / organized compression trace.
                        _template = [0,-5,-10,-20,-40,-45,-45,-42,-35,-24,-14,-8,-4];
                        _rIndex = 5;
                        _noiseAmp = 5.0;
                    };
                    case 5: {
                        if (_widePEA) then {
                            // Preserve the existing broad complex for severe uncovered transfusion burden.
                            _template = [0,-2,-8,-20,-38,-50,-48,-36,-16,5,18,27,23,14,6,1,0];
                            _rIndex = 5;
                            _noiseAmp = 2.6;
                        };
                    };
                    case 3;
                    case 4: { // PVT / VT broad ventricular complex.
                        _template = [5,-30,-47,-49,-49,-47,-42,-34,-24];
                        _rIndex = 3;
                        _noiseAmp = 2.5;
                    };
                    default {}; // Sinus and narrow PEA keep the shared template above.
                };

                private _templateIndex = _rIndex + _offset;
                if (_templateIndex >= 0 && {_templateIndex < count _template}) then {
                    _value = _template select _templateIndex;
                    _isSafe = false;

                    if (_widePEA) then {
                        // Wide PEA retains its deterministic beat-to-beat variation; narrow PEA keeps sinus morphology.
                        // It survives a buffer refresh without the complex changing shape underneath the sweep.
                        private _amp = 0.84 + (0.30 * ((sin (((_beatOrdinal * 73) + 19) mod 360) + 1) / 2));
                        private _tAmp = 0.78 + (0.44 * ((sin (((_beatOrdinal * 41) + 117) mod 360) + 1) / 2));
                        private _base = (sin (((_beatOrdinal * 29) + 53) mod 360)) * 2.4;
                        _value = (_value * _amp) + _base;
                        if (_templateIndex >= 9) then {_value = (_value - _base) * _tAmp + _base;};
                        if (_templateIndex in [4,7,8] && {abs (sin (((_beatOrdinal * 97) + 7) mod 360)) > 0.72}) then {
                            _value = _value + ((sin (((_beatOrdinal * 131) + (_templateIndex * 17)) mod 360)) * 5.5);
                        };
                    };

                    _value = _value + ([_sampleIndex, _noiseAmp, (_beatOrdinal * 17) + (_rhythm * 31)] call _fnc_noise);
                } else {
                    private _baselineAmp = if (_widePEA) then {2.2} else {1.4};
                    _value = [_sampleIndex, _baselineAmp, (_rhythm * 37)] call _fnc_noise;
                };
            };
        };
    };

    _arr set [_i, _value];
    _safe set [_i, _isSafe];
};

private _result = [_target,_arr,_safe] call ACME_fnc_ecgArtifactApply;
if (_sampleContext isNotEqualTo []) then {_result append [_peaks,_phases];};
_result
