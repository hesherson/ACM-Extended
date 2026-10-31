// Server-owned sources are audible to nearby providers and removable even after
// the treating client disconnects. The watchdog exists only while sources do.
if (!isServer) exitWith {};
params ["_op", ["_medic", objNull], ["_patient", objNull], ["_token", ""], ["_providerOwner", -1]];
private _active = missionNamespace getVariable ["ACME_wrapSfxSources", []];

if (_op == "start") then {
    if (!isNull _medic && {alive _medic} && {!isNull _patient} && {owner _medic == _providerOwner}) then {
        // An exact replay is still the same audible episode. Keep its emitter playing instead of deleting and
        // recreating it at frame zero; a newer token continues to replace only this provider's previous loop.
        private _sameEpisode = (_active findIf {
            (_x select 0) isEqualTo _medic && {(_x select 1) isEqualTo _patient}
                && {(_x select 2) == _token} && {(_x select 4) == _providerOwner}
                && {!isNull (_x select 3)}
        }) >= 0;
        if (!_sameEpisode) then {
            // A provider can run one ACE progress action at a time. Replace only
            // that provider's emitter; other medics treating this patient continue.
            _active = _active select {
                if ((_x select 0) isEqualTo _medic) then {
                    deleteVehicle (_x select 3);
                    false
                } else {true};
            };
            private _src = createSoundSource ["ACME_JunctionalPack_SoundSource", getPosATL _medic, [], 0];
            _src attachTo [_medic, [0, 0, 0]];
            _active pushBack [_medic, _patient, _token, _src, _providerOwner, isPlayer _medic, -1];
        };
    };
};

if (_op == "stop") then {
    _active = _active select {
        if ((_x select 0) isEqualTo _medic && {(_x select 2) == _token}) then {
            deleteVehicle (_x select 3);
            false
        } else {true};
    };
};

// Death/deletion, unconsciousness, disconnect or ownership transfer cannot
// leave an emitter attached to a provider who can no longer perform the action.
_active = _active select {
    _x params ["_provider", "_target", "_episode", "_src", "_origin", "_wasPlayer", "_nextQuiet"];
    private _valid = !isNull _provider && {alive _provider} && {!isNull _target}
        && {!isNull _src} && {owner _provider == _origin}
        && {!(_provider getVariable ["ACE_isUnconscious", false])}
        && {!_wasPlayer || {isPlayer _provider}};
    if (!_valid) then {
        deleteVehicle _src;
    } else {
        // Short renewed reservations cover variable-length wrapping without
        // guessing the treatment duration or leaving a long leak-audio mute.
        private _audioNow = serverTime;
        if (_audioNow >= _nextQuiet) then {
            // Another provider may already own a longer important-sound window. Shared reservations use serverTime.
            private _remaining = (_target getVariable ["ACME_SfxBusyUntil", 0]) - _audioNow;
            [_target, _remaining max 2.25] call ACME_fnc_markImportantSfx;
            _x set [6, _audioNow + 2];
        };
    };
    _valid
};
missionNamespace setVariable ["ACME_wrapSfxSources", _active];

private _pfh = missionNamespace getVariable ["ACME_wrapSfxPFH", -1];
if (_active isEqualTo []) then {
    if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
    missionNamespace setVariable ["ACME_wrapSfxPFH", -1];
} else {
    if (_pfh < 0) then {
        _pfh = [{["tick"] call ACME_fnc_wrapSfxServer;}, 0.25] call CBA_fnc_addPerFrameHandler;
        missionNamespace setVariable ["ACME_wrapSfxPFH", _pfh];
    };
};
