// UI voice row: [ID, class, live gain, pitch, clip origin, length, native progress proof,
// last apply, applied gain, next native start, expiry]. -1 is the invalid ID; gain stays at index 2.
// Requests are [channel, class, pitch, cadence]. Silent channels retain bounded phase metadata but launch no audio.
// Arma 2.18 has no per-ID gain setter: material changes seek the same clip at most five times/second/voice.
// Keep query/stop/start/metadata rejection together even when a public caller is scheduled.
if (canSuspend) exitWith {private _args = _this; isNil {_args call ACME_fnc_stethoscopeAudioUpdate;};};
params ["_channels","_targets","_dt","_now",["_requests",[]]];
{
    _x params ["_index","_class","_pitch","_cadence"];
    private _channel = _channels select _index;
    // Retire the old clip through the same ownership proof used by Close.
    if ([_channel,_now] call ACME_fnc_stethoscopeAudioOwned) then {stopSound (_channel select 0);};
    _channel set [0,-1];
    _channel set [1,_class];
    _channel set [3,_pitch];
    _channel set [4,_now];
    _channel set [5,0];
    _channel set [6,[]];
    _channel set [10,_now + _cadence];
} forEach _requests;
{
    private _channel = _x;
    private _target = _targets select _forEachIndex;
    private _gain = _channel select 2;
    _gain = _gain + (_target - _gain) * (1 - exp (-_dt / 0.08));
    // The first PFH can have dt=0. Audible contact must not consume its first cadence at zero gain.
    if (_dt <= 0 && {_gain <= 0} && {_target > 0.0001}) then {_gain = _target;};
    if (_target <= 0.0001) then {_gain = 0;};
    _channel set [2,_gain];
    private _owned = [_channel,_now] call ACME_fnc_stethoscopeAudioOwned;
    if (!_owned) then {_channel set [0,-1]; _channel set [6,[]];};
    private _offset = ((_now - (_channel select 4)) max 0) * (_channel select 3);
    // A live native clip is authoritative for its completion; estimated wall time must not clip decoder latency.
    private _expired = !_owned && {_now >= (_channel select 10)
        || {(_channel select 5) > 0 && {_offset >= (_channel select 5)}}};
    if (_gain <= 0.0001 || {_expired}) then {
        if (_owned) then {stopSound (_channel select 0);};
        _channel set [0,-1];
        _channel set [6,[]];
        if (_expired) then {_channel set [1,""];};
    } else {
        private _seek = _owned && {abs (_gain - (_channel select 8)) >= 0.08};
        if ((_channel select 1) != "" && {_now >= (_channel select 9)} && {!_owned || {_seek}}) then {
            if (_owned) then {
                // Query progress, rather than replaying the attack or guessing an active decoder's phase.
                private _proof = _channel select 6;
                _offset = (_proof select 3) * (_proof select 1);
                _channel set [4,_now - (_offset / (_channel select 3))];
                stopSound (_channel select 0);
            };
            _channel set [0,-1];
            _channel set [6,[]];
            _channel set [9,_now + 0.2];
            private _id = playSoundUI [_channel select 1,_gain,_channel select 3,false,_offset];
            if (_id isEqualType 0 && {_id >= 0}) then {
                private _info = soundParams _id;
                // Missing native metadata is a failed start; no guessed ID ownership is retained for cleanup.
                if (count _info >= 5 && {(_info select 2) > _offset} && {(_info select 1) < 1}) then {
                    _channel set [0,_id];
                    _channel set [5,_info select 2];
                    _channel set [6,[_info select 0,_info select 2,_info select 3,_info select 1,_now]];
                    _channel set [7,_now];
                    _channel set [8,_gain];
                    _channel set [10,(_channel select 4) + ((_info select 2) / (_channel select 3))];
                } else {
                    // A returned ID can precede decoder metadata. Retire this fresh start immediately so a
                    // bounded retry cannot overlap an untracked voice; this command group is unscheduled.
                    stopSound _id;
                };
            };
        };
    };
} forEach _channels;
