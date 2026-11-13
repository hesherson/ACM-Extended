// Custom ECG generator for ACME rhythm codes 100 and above. Organized custom rhythms are sampled directly
// against the AED's absolute 30 ms screen-time axis and the same selected R-R interval used by the audible beat
// scheduler. This keeps the R wave phase-locked to the beep even when HR changes mid-sweep. Torsades is sampled
// from its own continuous absolute-time spindle. The legacy tiled builders remain below as a fallback surface,
// but rhythm codes 100-104 return from the direct sampler before reaching them.
// On the ACM screen convention, negative y is an upward deflection.
// _this is [_rhythm, _spacing, _arrayOffset].
params ["_rhythm", "_spacing", "_arrayOffset", ["_sampleContext",[]]];

private _W = _sampleContext param [3,176];  // aed_monitor_width.

// stock ACM passes an _arrayOffset of 0 and never advances it. the time-anchored phase below is what drives the
// scroll, so we no longer fold in the old constant half-spacing offset.

// the true beat period, in samples. prefer the monitor or display hr from the target patient, so the QRS spacing
// is not limited by ACM's rounded spacing argument. fall back to the _spacing conversion.
private _tgtForRate = _sampleContext param [0,missionNamespace getVariable ["ACM_circulation_AED_Monitor_Target",objNull]];
private _rateHR = 0;
if (!isNull _tgtForRate) then {
    _rateHR = [_tgtForRate] call ACM_circulation_fnc_getEKGHeartRate;
    if (_rateHR <= 0) then { _rateHR = _tgtForRate getVariable ["ace_medical_heartRate", 0]; };
};
private _scale = missionNamespace getVariable ["ACME_rhythm_ekgPeriodScale", 2.2222];
private _period = if (_rateHR > 0) then { round ((60 / _rateHR) / 0.03) } else { round ((_spacing max 1) * _scale) };
private _rPhase = 0;  // the block-phase of the r spike for the regular rhythms, which is the beep lock. 0 locks the beat boundary.

// Perfusing custom rhythms use the same exact-time sampler as the forked native ECG. This removes fractional-column
// drift from atrial tach/SVT, and AFib consumes the same irregular next-RR interval that fnc_handleAED uses for its
// audible beep. The future strip is regenerated after every actual beep, so an AFib QRS cannot wander away from the
// audio clock even though its R-R intervals are intentionally irregular.
if (_rhythm in [100,101,102,103,104]) exitWith {
    private _dt = 0.03;
    private _lastIndex = _W - 1;
    private _now = CBA_missionTime;
    private _cursorEpoch = if (!isNull _tgtForRate) then {
        _tgtForRate getVariable ["ACME_AED_MonitorCursorTime", _now]
    } else {_now};
    if (!(_cursorEpoch isEqualType 0) || {!finite _cursorEpoch}) then {_cursorEpoch = _now;};
    private _rrNominal = if (_rateHR > 0) then {60 / _rateHR} else {0.75};
    private _anchor = 0;
    if (!isNull _tgtForRate) then {
        private _step = floor (_tgtForRate getVariable ["ACM_circulation_AED_UpdateStep", 0]);
        if (_step >= 1 && {_step < _lastIndex}) then {_anchor = _step;};
    };

    private _lastBeat = if (!isNull _tgtForRate) then {
        _tgtForRate getVariable ["ACM_circulation_AED_Pads_LastBeep", -1]
    } else {-1};
    if (_lastBeat < 0) then {_lastBeat = _cursorEpoch;};
    private _prevRR = if (!isNull _tgtForRate) then {_tgtForRate getVariable ["ACME_AED_PreviousRR", _rrNominal]} else {_rrNominal};
    private _nextRR = if (!isNull _tgtForRate) then {_tgtForRate getVariable ["ACME_AED_NextRR", _rrNominal]} else {_rrNominal};
    if (!(_prevRR isEqualType 0) || {!finite _prevRR} || {_prevRR <= 0}) then {_prevRR = _rrNominal;};
    if (!(_nextRR isEqualType 0) || {!finite _nextRR} || {_nextRR <= 0}) then {_nextRR = _rrNominal;};

    private _noiseAt = {
        params ["_idx", "_amp", ["_salt",0]];
        (((sin (((_idx * 127.31) + _salt) mod 360)) * 0.58)
            + ((sin (((_idx * 43.73) + 79 + _salt) mod 360)) * 0.42)) * _amp
    };

    private _out = [];
    private _outSafe = [];
    _out resize [_W, 0];
    _outSafe resize [_W, true];
    private _isAFib = _rhythm in [100,103];
    private _peaks = [];
    private _phases = [];
    private _beats = _sampleContext param [4,[]];
    private _beatIndex = 0;
    _phases resize [_W,99];
    private _beatSerialBase = if (!isNull _tgtForRate) then {_tgtForRate getVariable ["ACME_AED_BeatSerial", 0]} else {0};
    if (_sampleContext isNotEqualTo []) then {
        _sampleContext params ["","_start","_rate"];
        _cursorEpoch = _start;
        _anchor = 0;
        _rrNominal = 60 / (_rate max 1);
    };

    // Torsades has no normal QRS beep while the AED arrest alarm owns the audio, so its clock is absolute time rather
    // than LastBeep. Sampling it directly at each SCREEN index is still essential: index _anchor is "now", which means
    // a mid-sweep rhythm refresh cannot restart the torsades strip at x=0 and splice a different time three seconds
    // later into the current cursor. The spindle, polarity twist and entry morph are deterministic in time.
    if (_rhythm == 102) exitWith {
        private _out = [];
        private _outSafe = [];
        _out resize [_W, 0];
        _outSafe resize [_W, false];
        private _startAt = if (!isNull _tgtForRate) then {_tgtForRate getVariable ["ACME_rhythm_torsadesStart", _now]} else {_now};
        if (!(_startAt isEqualType 0) || {!finite _startAt}) then {_startAt = _now;};
        private _entryMinSec = missionNamespace getVariable ["ACME_rhythm_torsadesEntryMinSec", 6];
        private _entrySweeps = missionNamespace getVariable ["ACME_rhythm_torsadesEntrySweeps", 3];
        private _entryWindow = _entryMinSec max (_entrySweeps * _W * _dt);
        private _twistBeats = (missionNamespace getVariable ["ACME_rhythm_torsadesTwistBeats", 7]) max 1;
        private _floorAmp = (missionNamespace getVariable ["ACME_rhythm_torsadesFloor", 0.12]) max 0 min 1;
        private _rrT = _rrNominal max (_dt * 5);
        private _narrow = [0,-4,-38,19,5,-4,2,0,0];
        private _ventA = [0,-8,-34,-47,27,-25,13,-7,0];
        private _ventB = [0,-13,-42,15,-37,20,-15,8,0];
        private _ventC = [0,-5,-26,-50,22,-20,10,-9,0];
        private _variants = [_ventA,_ventB,_ventC];
        private _templateLen = count _narrow;

        for "_i" from 0 to _lastIndex do {
            private _sampleTime = _cursorEpoch + ((_i - _anchor) * _dt);
            private _elapsed = (_sampleTime - _startAt) max 0;
            private _pRaw = (_elapsed / (_entryWindow max 0.1)) max 0 min 1;
            private _p = _pRaw * _pRaw * (3 - 2 * _pRaw);
            private _beatFloat = (_sampleTime - _startAt) / _rrT;
            private _beatIndex = floor _beatFloat;
            private _beatPhase = _beatFloat - _beatIndex;
            if (_beatPhase < 0) then {_beatPhase = _beatPhase + 1; _beatIndex = _beatIndex - 1;};
            private _ti = floor (_beatPhase * _templateLen) min (_templateLen - 1);
            private _shape = _variants select (abs _beatIndex mod (count _variants));
            private _base = _narrow select _ti;
            private _vent = _shape select _ti;
            private _ectopyBoost = if ((abs _beatIndex mod 4) == 3) then {0.22 * (1 - _p)} else {0};
            private _m = (_p + _ectopyBoost) min 1;
            private _morph = _base + ((_vent - _base) * _m);

            private _twistAngle = ((_beatIndex + _beatPhase) * (180 / _twistBeats));
            private _env = sin _twistAngle;
            private _twist = linearConversion [0.12, 1, _p, 0, 1, true];
            private _targetAmp = _floorAmp + ((1 - _floorAmp) * abs _env);
            private _amp = (1 - _twist) + (_twist * _targetAmp);
            private _targetPol = if (_env < 0) then {-1} else {1};
            private _pol = (1 - _twist) + (_twist * _targetPol);
            private _sampleIndex = floor (_sampleTime / _dt);
            private _teeth = (sin (((_sampleIndex * 149.3) + (_beatIndex * 23)) mod 360)) * (4.5 * _p);
            private _micro = [_sampleIndex, (1.0 + (2.5 * _p)), 102 + (_beatIndex * 11)] call _noiseAt;
            _out set [_i, (_morph * _amp * _pol) + _teeth + _micro];
        };
        [_out, _outSafe]
    };

    for "_i" from 0 to _lastIndex do {
        private _sampleTime = _cursorEpoch + ((_i - _anchor) * _dt);
        private _sampleIndex = floor (_sampleTime / _dt);
        private _beatTime = _lastBeat;
        private _beatNumber = 0;

        // The immediately adjacent beats use the same selected RR values as the audible scheduler. This is used
        // for every organized custom rhythm, not only AFib, so a changing atrial tach/SVT rate cannot create a
        // one-cycle visual/audio disagreement. Beyond those adjacent beats, nominal RR is only a prediction.
        if (_sampleTime >= _lastBeat) then {
            private _nextBeat = _lastBeat + _nextRR;
            if (_sampleTime <= _nextBeat) then {
                if (abs (_sampleTime - _nextBeat) < abs (_sampleTime - _lastBeat)) then {
                    _beatTime = _nextBeat;
                    _beatNumber = 1;
                };
            } else {
                private _n = round ((_sampleTime - _nextBeat) / (_rrNominal max 0.05));
                _beatTime = _nextBeat + (_n * _rrNominal);
                _beatNumber = 1 + _n;
            };
        } else {
            private _previousBeat = _lastBeat - _prevRR;
            if (_sampleTime >= _previousBeat) then {
                if (abs (_sampleTime - _previousBeat) < abs (_sampleTime - _lastBeat)) then {
                    _beatTime = _previousBeat;
                    _beatNumber = -1;
                };
            } else {
                private _n = round ((_sampleTime - _previousBeat) / (_rrNominal max 0.05));
                _beatTime = _previousBeat + (_n * _rrNominal);
                _beatNumber = -1 + _n;
            };
        };

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
        private _delta = _sampleTime - _beatTime;
        private _offset = round (_delta / _dt);
        if (_sampleContext isNotEqualTo []) then {
            _phases set [_i,_offset];
            if (_delta >= -_dt/2 && {_delta < _dt/2}) then {_peaks pushBack _i;};
        };
        private _template = [];
        private _rIndex = 0;
        private _baseline = 0;
        private _noiseAmp = 1.8;

        switch (_rhythm) do {
            case 100;
            case 103: {
                _template = if ((_rrNominal / _dt) < 11) then {[0,-44,18,-4,0]} else {[0,-46,18,-3,-7,-9,-6,-2,0]};
                _rIndex = 1;
                // Persistent fibrillatory baseline, deterministic in absolute time so buffer regeneration cannot pop.
                _baseline = (sin (((_sampleIndex * 29.7) + 17) mod 360)) * 3.2
                    + (sin (((_sampleIndex * 53.1) + 101) mod 360)) * 2.0;
                _noiseAmp = 1.8;
            };
            case 101: {
                _template = if ((_rrNominal / _dt) < 15) then {[0,-5,-42,22,3,-3,0]} else {[0,-6,-8,-2,2,-44,25,5,-4,-2,5,8,2]};
                _rIndex = if (count _template < 10) then {2} else {5};
                _noiseAmp = 1.5;
            };
            case 104: {
                _template = if ((_rrNominal / _dt) < 11) then {[0,-44,18,-4,0]} else {[0,-46,18,-3,-7,-9,-6,-2,0]};
                _rIndex = 1;
                _noiseAmp = 1.4;
            };
        };

        private _ti = _rIndex + _offset;
        private _value = _baseline + ([_sampleIndex, if (_isAFib) then {1.2} else {0.9}, _rhythm] call _noiseAt);
        private _isSafe = true;
        if (_ti >= 0 && {_ti < count _template}) then {
            private _amp = 0.94 + (0.12 * ((sin (((_beatOrdinal * 67) + (_rhythm * 3)) mod 360) + 1) / 2));
            _value = _baseline + ((_template select _ti) * _amp) + ([_sampleIndex, _noiseAmp, (_beatOrdinal * 19) + _rhythm] call _noiseAt);
            _isSafe = false;
        };
        _out set [_i, _value];
        _outSafe set [_i, _isSafe];
    };

    if (_sampleContext isNotEqualTo []) then {[_out,_outSafe,_peaks,_phases]} else {[_out,_outSafe]}
};

private _noisy = {
    params ["_clean", "_n"];
    private _o = [];
    { _o pushBack (random [(_x - _n), _x, (_x + _n)]); } forEach _clean;
    _o
};
private _flatGap = {  // near-isoelectric jitter between complexes, for the organized rhythms.
    params ["_len"];
    private _a = [];
    for "_i" from 1 to (_len max 0) do { _a pushBack (random [-2, 0, 2]); };
    _a
};
private _fibGap = {  // a fibrillatory baseline, for AFib. it is a chaotic, wandering, low-amplitude undulation.
    params ["_len"];
    private _a = [];
    private _v = random [-4, 0, 4];
    for "_i" from 1 to (_len max 0) do {
        _v = ((_v + (random [-2.6, 0, 2.6])) max -8) min 8;
        _a pushBack _v;
    };
    _a
};
private _safeRun = {
    params ["_count", ["_safe", false]];
    private _a = [];
    for "_i" from 1 to (_count max 0) do { _a pushBack _safe; };
    _a
};
// the corrected inter-beat gap for a complex of the given length: the period minus the complex itself.
private _gapFor = { params ["_len"]; ((_period - _len) max 2) };

private _arr = [];
private _safe = [];

switch (true) do {
    // 100 is AFib with RVR and 103 is AFib at a controlled rate. there is no p wave, the QRS is narrow, the r-r is
    // irregularly irregular, and the baseline is fibrillatory. the rate comes through _period.
    case (_rhythm == 100);
    case (_rhythm == 103): {
        private _qrs = if (_period < 11) then { [0,-44,18,-4,0] } else { [0,-46,18,-3,-7,-9,-6,-2,0] };  // a narrow spike plus a rounded t.
        private _n = 4;
        private _base = [count _qrs] call _gapFor;
        private _repeat = (ceil(_W / ((count _qrs) + _base)) + 4);
        for "_i" from 0 to _repeat do {
            // irregularly irregular r-r. the jitter is scaled off the full beat period rather than the tiny inter-beat gap,
            // because at fast RVR rates the gap collapses to about 2 or 3 samples, so gap-scaled jitter was nearly
            // invisible. period-scaled jitter keeps the beat-to-beat spacing obviously variable even when fast, plus a
            // frequent longer pause. that is the hallmark of AFib. all of it is tunable.
            private _jDown = missionNamespace getVariable ["ACME_rhythm_afibJitterDown", 0.45];  // a fraction of the period, giving a shorter r-r.
            private _jUp   = missionNamespace getVariable ["ACME_rhythm_afibJitterUp",   0.70];  // a fraction of the period, giving a longer r-r.
            private _pauseChance = missionNamespace getVariable ["ACME_rhythm_afibPauseChance", 0.32];
            private _jitter = round (random [-(_period * _jDown), 0, (_period * _jUp)]);
            private _pause  = if ((random 1) < _pauseChance) then { round (_period * (random [0.4, 0.85, 1.5])) } else { 0 };
            private _gap = (_base + _jitter + _pause) max 2;
            _arr = _arr + ([_gap] call _fibGap) + ([_qrs, _n] call _noisy);
            _safe = _safe + ([_gap, true] call _safeRun) + ([count _qrs] call _safeRun);
        };
    };
    // 101 is atrial tachycardia: a small ectopic p, a narrow QRS and regular fast spacing.
    case (_rhythm == 101): {
        private _step = if (_period < 15) then { [0,-5,-42,22,3,-3,0] } else { [0,-6,-8,-2,2,-44,25,5,-4,-2,5,8,2] };  // p, pr, QRS and t.
        private _n = 2;
        private _gap = [count _step] call _gapFor;
        _rPhase = _gap + (_step find (selectMin _step));
        private _repeat = (ceil(_W / ((count _step) + _gap)) + 2);
        for "_i" from 0 to _repeat do {
            _arr = _arr + ([_gap] call _flatGap) + ([_step, _n] call _noisy);
            _safe = _safe + ([_gap, true] call _safeRun) + ([count _step] call _safeRun);
        };
    };
    // 102 is polymorphic vt, or torsades de pointes. it is a continuous run of sharp, narrow QRS complexes, with no
    // flat baseline between them, whose amplitude waxes and wanes in a sinusoidal spindle and whose polarity flips
    // as the axis twists around the isoelectric line. that twisting spindle is the whole point of the morphology.
    // the old version used one wide rounded bump with a barely moving envelope, which read as uniform paced humps
    // with flat gaps rather than torsades. this rebuild uses a sharp complex, a near-zero gap, a smooth per-sample
    // spindle so complexes shrink to almost nothing at the nodes and swell between them, and a polarity that inverts
    // at each node.
    case (_rhythm == 102): {
        // Torsades entry is an actual time-based morph. The transition lasts the longer of the configured minimum
        // or the configured number of full 176-column monitor sweeps. Every generated beat uses its presentation
        // time within the buffer, so progress reaches exactly 1.0 at the end of the window rather than jumping by
        // stage cutoffs. The patient is clinically in torsades immediately; this is the evolving onset morphology.
        private _tgt = missionNamespace getVariable ["ACM_circulation_AED_Monitor_Target", objNull];
        private _startAt = if (!isNull _tgt) then {_tgt getVariable ["ACME_rhythm_torsadesStart", -1]} else {-1};
        private _entryMinSec = missionNamespace getVariable ["ACME_rhythm_torsadesEntryMinSec", 6];
        private _entrySweeps = missionNamespace getVariable ["ACME_rhythm_torsadesEntrySweeps", 3];
        private _entryWindow = _entryMinSec max (_entrySweeps * _W * 0.03);
        private _elapsed = if (_startAt >= 0) then {(CBA_missionTime - _startAt) max 0} else {_entryWindow};
        private _twistBeats = missionNamespace getVariable ["ACME_rhythm_torsadesTwistBeats", 7];
        private _floor = missionNamespace getVariable ["ACME_rhythm_torsadesFloor", 0.12];
        private _noiseBase = missionNamespace getVariable ["ACME_rhythm_torsadesBeatNoise", 5];
        private _degPerBeat = 180 / (_twistBeats max 1);
        private _beatClock = floor (CBA_missionTime / 0.27);
        private _beatIndex = 0;
        private _narrow = [0,-4,-38,19,5,-4,2,0,0];
        private _ventA = [0,-8,-34,-47,27,-25,13,-7,0];
        private _ventB = [0,-13,-42,15,-37,20,-15,8,0];
        private _ventC = [0,-5,-26,-50,22,-20,10,-9,0];
        private _variants = [_ventA,_ventB,_ventC];
        _rPhase = 2;

        for "_i" from 0 to 48 do {
            private _sampleAhead = (count _arr) * 0.03;
            private _pRaw = ((_elapsed + _sampleAhead) / (_entryWindow max 0.1)) max 0 min 1;
            // smoothstep avoids a hard shoulder at either end of the conversion.
            private _p = _pRaw * _pRaw * (3 - 2 * _pRaw);
            private _shape = _variants select ((_beatClock + _beatIndex) mod (count _variants));
            private _ang = (_beatClock + _beatIndex) * _degPerBeat;
            private _env = sin _ang;
            private _twist = linearConversion [0.12, 1, _p, 0, 1, true];
            private _targetAmp = _floor + ((1 - _floor) * abs _env);
            private _amp = (1 - _twist) + (_twist * _targetAmp);
            private _targetPol = if (_env < 0) then {-1} else {1};
            private _pol = (1 - _twist) + (_twist * _targetPol);
            private _beat = [];
            {
                private _j = _forEachIndex;
                private _base = _narrow select _j;
                private _v = _shape select _j;
                // Early on, every fourth beat becomes ventricular sooner, reproducing the conversion/entry strip
                // before the entire run becomes polymorphic.
                private _ectopyBoost = if (((_beatClock + _beatIndex) mod 4) == 3) then {0.22 * (1 - _p)} else {0};
                private _m = (_p + _ectopyBoost) min 1;
                private _morph = _base + ((_v - _base) * _m);
                private _frac = _j / (((count _shape) - 1) max 1);
                // asymmetric high-frequency teeth make the mature trace jagged/sawtooth-like without turning it
                // into random VF. The term grows continuously with torsades progress.
                private _sawPhase = (_frac * 4) - floor (_frac * 4);
                private _saw = ((_sawPhase * 2) - 1) * (5.5 * _p);
                private _micro = random [-(1.0 + 2.0*_p),0,(1.0 + 2.5*_p)];
                _beat pushBack ((_morph * _amp * _pol) + _saw + _micro);
            } forEach _shape;

            private _baseGap = ((_period - (count _beat)) max 0) min 8;
            private _gap = round (_baseGap * (1 - _p));
            if (_gap > 0) then {
                private _gapNoise = [];
                for "_g" from 1 to _gap do {
                    private _wander = random [-(1 + 3*_p),0,(1 + 3*_p)];
                    _gapNoise pushBack _wander;
                };
                _arr = _arr + _gapNoise;
                _safe = _safe + ([_gap, true] call _safeRun);
            };
            _arr = _arr + ([_beat, 1.5 + (_noiseBase * _p)] call _noisy);
            _safe = _safe + ([count _beat] call _safeRun);
            _beatIndex = _beatIndex + 1;
            if ((count _arr) > (_W + 32)) exitWith {};
        };
    };
    // 104 is SVT: a narrow QRS, very fast, regular, with no visible p. the rate comes through _period.
    case (_rhythm == 104): {
        private _qrs = if (_period < 11) then { [0,-44,18,-4,0] } else { [0,-46,18,-3,-7,-9,-6,-2,0] };
        private _n = 2;
        private _gap = [count _qrs] call _gapFor;
        _rPhase = _gap + (_qrs find (selectMin _qrs));
        private _repeat = (ceil(_W / ((count _qrs) + _gap)) + 2);
        for "_i" from 0 to _repeat do {
            _arr = _arr + ([_gap] call _flatGap) + ([_qrs, _n] call _noisy);
            _safe = _safe + ([_gap, true] call _safeRun) + ([count _qrs] call _safeRun);
        };
    };
};

// the phase, locked to ACM's own AED beep timestamp. ACM owns the audio, and the custom rhythm waveforms only use
// that timestamp for visual alignment.
private _period_c = _period max 1;
private _phase = 0;
private _lastBeat = -1;
private _tgt = missionNamespace getVariable ["ACM_circulation_AED_Monitor_Target", objNull];
if (!isNull _tgt) then {
    _lastBeat = _tgt getVariable ["ACM_circulation_AED_Pads_LastBeep", -1];
};
if (_lastBeat >= 0) then {
    _phase = (_rPhase + floor ((CBA_missionTime - _lastBeat) / 0.03)) mod _period_c;
} else {
    _phase = (floor (CBA_missionTime / 0.03)) mod _period_c;
};
if (_phase > 0 && {_phase < count _arr}) then {
    _arr deleteRange [0, _phase];
    if (_phase < count _safe) then { _safe deleteRange [0, _phase]; };
};

if (_arrayOffset > 0) then { _arr deleteRange [0, (_arrayOffset min (count _arr))]; };
if (count _safe < 1) then { _safe resize [_W, true]; };
_arr resize [_W, 0];

[_arr, _safe]
