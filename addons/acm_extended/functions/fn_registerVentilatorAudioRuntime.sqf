/*
 * Phase 23 runtime ownership: Ventilator server sound-source lifecycle, local alarm cadence and audio/logbook events.
 *
 * Extracted intact from ACME_fnc_postInit. The helper is invoked synchronously at the
 * original registration point so CBA handler/PFH order is unchanged.
 */

// running-ventilator sound, a client-side positional loop. every half second, any actively ventilated patient
// within earshot of the local player re-triggers the vent sfx at the patient once its previous clip has played
// out. ACME_vent_driving is the globally broadcast flag. it is client-local and positional, so whoever stands
// near a running vent hears it whatever machine the patient is local to. the clip runs about 5.72 s, and the
// retrigger comes a little early to avoid a gap.
// the ventilator running sound splits by locality on purpose.
// the loop is an engine-looped CfgSFX sound source. createSoundSource makes a global object, so exactly one
// machine must own it, and that is the server. if every client ran this, each would spawn its own copy and you
// would hear n ventilators. the engine loops it, so it is gapless and cannot overlap itself, and a delete stops
// it dead on the frame.
// the startup and shutdown are one-shots. Explicit local=true makes each client play them only for itself and
// the server tells them when through an event.
// the sequence is strictly serial, so the three clips never overlap.
// START plays ventilator_startup_sfx, at 2.32 s. the loop source is not created until that clip has run its
// full length, so the running loop cannot begin while the startup still sounds.
// RUNNING is the looping ventilator_running_sfx source, created only at the handover point.
// STOP deletes the loop source, which silences it on the frame, then plays ventilator_shutdown_sfx, at 2.32 s.
// the loop is deleted before the shutdown clip plays and created only after the startup clip ends, so no two of
// the three are ever audible together.
if (isServer) then {
    ACME_vent_soundSources = [];
    // B204: the 10 Hz sound handover loop must never enumerate the whole mission. Seed once for hot-loaded/legacy
    // state, then maintain a small explicit registry from vent custody/owner lifecycle events.
    ACME_vent_serverPatients = allUnits select {
        (_x getVariable ["ACME_vent_onPatient", false])
            || {_x getVariable ["ACME_vent_configured", false]}
            || {(_x getVariable ["ACME_vent_sndState", 0]) != 0}
            || {!isNull (_x getVariable ["ACME_vent_sndSrc", objNull])}
    };
    ["ACME_ventServerTrack", {
        params [["_patient", objNull, [objNull]], ["_active", true, [true]]];
        if (isNull _patient) exitWith {};
        if (_active
            || {_patient getVariable ["ACME_vent_onPatient", false]}
            || {_patient getVariable ["ACME_vent_configured", false]}
            || {(_patient getVariable ["ACME_vent_sndState", 0]) != 0}
            || {!isNull (_patient getVariable ["ACME_vent_sndSrc", objNull])}) then {
            ACME_vent_serverPatients pushBackUnique _patient;
        } else {
            ACME_vent_serverPatients = ACME_vent_serverPatients - [_patient];
        };
    }] call CBA_fnc_addEventHandler;
    [{
        private _now = CBA_missionTime;
        private _keptSources = [];
        {
            _x params ["_trackedPatient", "_trackedSource"];
            private _orphan = isNull _trackedPatient || {!alive _trackedPatient}
                || {isNull _trackedSource}
                || {!((_trackedPatient getVariable ["ACME_vent_sndSrc", objNull]) isEqualTo _trackedSource)};
            if (_orphan) then {
                if (!isNull _trackedSource) then { detach _trackedSource; deleteVehicle _trackedSource; };
                if (!isNull _trackedPatient && {(_trackedPatient getVariable ["ACME_vent_sndSrc", objNull]) isEqualTo _trackedSource}) then {
                    _trackedPatient setVariable ["ACME_vent_sndSrc", objNull];
                    if ((_trackedPatient getVariable ["ACME_vent_sndState", 0]) == 2) then {
                        [_trackedPatient, "ACME_vent_sndState", 0] call ACME_fnc_setVarNet;
                    };
                };
            } else {
                _keptSources pushBack _x;
            };
        } forEach ACME_vent_soundSources;
        ACME_vent_soundSources = _keptSources;
        {
            private _pat = _x;
            if (alive _pat) then {
                private _driving = _pat getVariable ["ACME_vent_driving", false];
                private _src = _pat getVariable ["ACME_vent_sndSrc", objNull];
                private _state = _pat getVariable ["ACME_vent_sndState", 0];  // 0 off, 1 startup, 2 looping, 3 shutting down

                if (_state == 3) then {
                    // state 3, shutting down. the shutdown clip is already playing. the loop is kept alive for the overlap window
                    // and cut when sndloopkillat is reached, so the running hum runs into the spool-down with no gap. it runs
                    // whatever the driving state, so the overlap always completes. the sndquietuntil cooldown, set when the
                    // shutdown fired, holds any restart's startup off until the shutdown clip finishes, so a fast restart cannot
                    // overlap the spool-down.
                    if (_now >= (_pat getVariable ["ACME_vent_sndLoopKillAt", 0])) then {
                        if (!isNull _src) then { detach _src; deleteVehicle _src; };
                        _pat setVariable ["ACME_vent_sndSrc", objNull];
                        _pat setVariable ["ACME_vent_sndState", 0, true];
                        _pat setVariable ["ACME_vent_sndLoopAt", 0];
                    };
                } else {
                if (_driving) then {
                    if (_state == 0) then {
                        // hold the startup off until any preceding shutdown clip has finished, so a fast off-then-on cannot layer a
                        // new startup over the tail of a shutdown. until then, do nothing this pass.
                        if (_now >= (_pat getVariable ["ACME_vent_sndQuietUntil", 0])) then {
                            // START. tell every client to play the startup clip, and time the handover to the loop. the handover lands a
                            // small overlap before the startup clip ends, so the turbine spool-up runs into the running loop with no
                            // audible gap between them.
                            private _audience = allPlayers select {alive _x && {(_x distance _pat) <= 50}}; if !(_audience isEqualTo []) then {["ACME_ventSndFade", [_pat, "in"], _audience] call CBA_fnc_targetEvent;};
                            private _len = missionNamespace getVariable ["ACME_vent_startupSndLen", 2.324];  // must match ventilator_startup_sfx
                            private _ov  = missionNamespace getVariable ["ACME_vent_sndOverlap", 0.11];  // crossfade length
                            _pat setVariable ["ACME_vent_sndLoopAt", _now + (_len - _ov) max 0];
                            _pat setVariable ["ACME_vent_sndState", 1, true];
                        };
                    } else {
                        if (_state == 1 && {_now >= (_pat getVariable ["ACME_vent_sndLoopAt", 0])} && {isNull _src}) then {
                            // handover. bring the loop up while the tail of the startup still sounds, so the spool-up blends into the
                            // running hum. it attaches to the casualty so it tracks them.
                            _src = createSoundSource ["ACME_VentRun_SoundSource", getPosATL _pat, [], 0];
                            _src attachTo [_pat, [0,0,0]];
                            _pat setVariable ["ACME_vent_sndSrc", _src];
                            ACME_vent_soundSources pushBack [_pat, _src];
                            _pat setVariable ["ACME_vent_sndState", 2, true];
                        };
                    };
                } else {
                    if (_state != 0) then {
                        // STOP. the loop and the shutdown clip overlap by a small amount, so the running hum runs into the turbine
                        // spool-down with no audible gap. fire the shutdown now and let the loop keep sounding for the overlap window
                        // before it is cut, which sndloopkillat schedules.
                        if (_state == 2) then {
                            private _audience = allPlayers select {alive _x && {(_x distance _pat) <= 50}}; if !(_audience isEqualTo []) then {["ACME_ventSndFade", [_pat, "out"], _audience] call CBA_fnc_targetEvent;};
                            private _shutLen = missionNamespace getVariable ["ACME_vent_shutdownSndLen", 2.324];
                            private _ov = missionNamespace getVariable ["ACME_vent_sndOverlap", 0.11];
                            _pat setVariable ["ACME_vent_sndQuietUntil", _now + _shutLen];
                            // keep the loop alive for the overlap. a per-frame check below then deletes it.
                            _pat setVariable ["ACME_vent_sndLoopKillAt", _now + _ov];
                            _pat setVariable ["ACME_vent_sndState", 3, true];  // 3 = shutting down (loop still up)
                        } else {
                            // still in the startup phase, state 1, with no loop yet. there is nothing to overlap, so reset.
                            if (!isNull _src) then { detach _src; deleteVehicle _src; };
                            _pat setVariable ["ACME_vent_sndSrc", objNull];
                            _pat setVariable ["ACME_vent_sndState", 0, true];
                            _pat setVariable ["ACME_vent_sndLoopAt", 0];
                        };
                    };
                };
                };
            } else {
                // Death can interrupt startup/shutdown before a source exists. Retire the state as well as the
                // source, otherwise a source-less nonzero state pins the corpse in this 10 Hz registry forever.
                private _src = _pat getVariable ["ACME_vent_sndSrc", objNull];
                if (!isNull _src) then {
                    detach _src; deleteVehicle _src;
                    _pat setVariable ["ACME_vent_sndSrc", objNull];
                };
                [_pat, "ACME_vent_sndState", 0] call ACME_fnc_setVarNet;
                _pat setVariable ["ACME_vent_sndLoopAt", 0];
            };
        } forEach (+(missionNamespace getVariable ["ACME_vent_serverPatients", []]));

        // Dead patients have completed source cleanup above. Old attached/configured flags must not retain them;
        // a new living casualty is registered by ventilator custody/configuration, independently of this list.
        // Retain only living attached/configured patients and patients whose shutdown/source cleanup is in flight.
        ACME_vent_serverPatients = (missionNamespace getVariable ["ACME_vent_serverPatients", []]) select {
            !isNull _x && {alive _x} && {
                (_x getVariable ["ACME_vent_onPatient", false])
                    || {_x getVariable ["ACME_vent_configured", false]}
                    || {(_x getVariable ["ACME_vent_sndState", 0]) != 0}
                    || {!isNull (_x getVariable ["ACME_vent_sndSrc", objNull])}
            }
        };
    }, 0.1, []] call CBA_fnc_addPerFrameHandler;  // tight tick: the intro -> loop handover must land on time
};

// ventilator alarm tones.
// three priorities and three patterns, so a medic can tell how much trouble they are in without a look at the
// screen. that is why a real ventilator uses distinct cadences instead of one generic buzz.
// HIGH, 3: 5 beeps, and the burst repeats every 2 s. the patient is not ventilated, or is injured, right now.
// medium, 2: 3 beeps, and the burst repeats every 5 s. the ventilation is inadequate. it is dangerous and not
// instantly fatal.
// LOW, 1: 1 beep, once, and never again. it is informational, says its piece and stops.
// this is client-side with explicit local=true, so each medic drives their own tones for the casualties
// near them. a silence stops the tone, but fn_ventalarmtick un-silences on any new alarm, so it cannot deafen
// you.
if (hasInterface) then {
    ACME_vent_alarmSnd = createHashMap;  // netid -> [prio, beepsleft, nextbeept, nextburstt, lowdone]
    ACME_vent_alarmCandidates = [];
    ACME_vent_alarmDiscoverAt = -1;
    ACME_vent_alarmViewer = objNull;
    ACME_vent_alarmVehicle = objNull;
    private _beepLen = missionNamespace getVariable ["ACME_vent_alarmBeepLen", 0.336];  // matches the ogg
    [{
        params ["_args"];
        _args params ["_beepLen"];
        private _plr = ACE_player;
        if (isNull _plr) exitWith {};
        private _now = diag_tickTime;
        // Candidate discovery is not the beep clock. Refresh at 2 Hz, or immediately when the listener changes
        // player/vehicle. Vehicle crew are explicit because nearEntities may omit embarked CAManBase objects.
        private _listenerVehicle = vehicle _plr;
        if (_now >= ACME_vent_alarmDiscoverAt || {_plr isNotEqualTo ACME_vent_alarmViewer}
            || {_listenerVehicle isNotEqualTo ACME_vent_alarmVehicle}) then {
            private _candidates = [];
            {
                if (_x isKindOf "CAManBase") then {_candidates pushBackUnique _x;} else {
                    {_candidates pushBackUnique _x;} forEach (crew _x);
                };
            } forEach (_plr nearEntities [["CAManBase", "LandVehicle", "Air", "Ship"], 25]);
            {_candidates pushBackUnique _x;} forEach (crew _listenerVehicle);
            ACME_vent_alarmCandidates = _candidates;
            ACME_vent_alarmDiscoverAt = _now + 0.5;
            ACME_vent_alarmViewer = _plr;
            ACME_vent_alarmVehicle = _listenerVehicle;
        };
        private _gap = _beepLen + (missionNamespace getVariable ["ACME_vent_alarmBeepGap", 0.04]);
        private _seen = [];

        {
            private _pat = _x;
            // Leaving range silences immediately; discovery latency never extends an audible alarm.
            if (isNull _pat || {!alive _pat} || {_plr distance _pat > 25}) then {continue};
            private _id = netId _pat;
            private _alarms = _pat getVariable ["ACME_vent_alarms", []];
            private _prio = _pat getVariable ["ACME_vent_alarmPrio", 0];
            private _silUntil = _pat getVariable ["ACME_vent_alarmSilencedUntil", 0];
            private _silenced = serverTime < _silUntil;
            if (_alarms isEqualTo [] || {_silenced} || {_prio <= 0}) then {
                ACME_vent_alarmSnd deleteAt _id;  // nothing to say, or acknowledged: reset the pattern
            } else {
                _seen pushBack _id;
                private _st = ACME_vent_alarmSnd getOrDefault [_id, [0, 0, 0, 0, false]];
                _st params ["_sPrio", "_beepsLeft", "_nextBeepT", "_nextBurstT", "_lowDone"];

                // the priority changed, either worse or better. restart the pattern at once, so the cadence always reflects
                // what is wrong now and not what was wrong a moment ago.
                if (_sPrio != _prio) then {
                    _sPrio = _prio; _beepsLeft = 0; _nextBurstT = _now; _lowDone = false;
                };

                private _burstN = switch (_prio) do { case 3: {5}; case 2: {3}; default {1} };
                private _period = switch (_prio) do { case 3: {2}; case 2: {5}; default {1e9} };  // LOW never repeats

                if (_beepsLeft <= 0 && {_now >= _nextBurstT}) then {
                    if (_prio == 1 && {_lowDone}) then {
                        // LOW has spoken once already. it does not nag.
                    } else {
                        _beepsLeft = _burstN;
                        _nextBeepT = _now;
                        _nextBurstT = _now + _period;
                        if (_prio == 1) then { _lowDone = true; };
                    };
                };

                if (_beepsLeft > 0 && {_now >= _nextBeepT}) then {
                    // airframe noise. the alarm stays audible in a running aircraft and is only slightly attenuated. the engine
                    // and rotor noise of the airframe does the real masking naturally, rather than the mod silencing the machine
                    // artificially. the alarm count and the red bell on the panel stay the reliable read, and a crew member who
                    // listens can still catch the tone.
                    private _mv = vehicle ACE_player;
                    private _inVeh = (_mv != ACE_player);
                    private _vol = if (_inVeh && {_mv isKindOf "Air"} && {isEngineOn _mv}) then {
                        missionNamespace getVariable ["ACME_flightNoise_alarmVol", 1.0]
                    } else { 1.3 };
                    // a vehicle interior muffles a 3d sound placed at the world position of the patient to inaudible, which is why
                    // the beeps went silent the moment you got inside one. when the operator is in a vehicle, emit the tone at the
                    // operator instead. they are with the patient, because the circuit leash keeps them within 2.5 m, so the cabin
                    // does not block their own machine's alarm. on foot, keep it at the patient so it stays spatially correct.
                    private _src = if (_inVeh) then { ACE_player } else { _pat };
                    // the alarm volume setting, under main MENU, ADV SETTINGS, ALARM VOLUME, scales the tone. level 3 is the
                    // default and leaves _vol as it was, so the existing balance does not change. level 1 is where night brightness
                    // puts you, because the robust low setting lowers the brightness and the volume together. the point of that
                    // mode is to avoid being seen and heard.
                    private _avSteps = missionNamespace getVariable ["ACME_vent_alarmVolSteps", [0.35, 0.65, 1.0, 1.6]];
                    private _avIdx = ((uiNamespace getVariable ["ACME_vent_alarmVol", 3]) - 1) max 0 min ((count _avSteps) - 1);
                    // volume is range. a quiet alarm is not only quieter where you stand, it carries less far, which makes a turn
                    // down a real tactical decision rather than a comfort setting. at full volume it reaches 25 m. at the lowest
                    // audible step it barely leaves the casualty. you silence it entirely when the machine is giving your position
                    // away, and the cost is that nobody hears it change either.
                    private _avol = _vol * (_avSteps select _avIdx);
                    private _arange = (missionNamespace getVariable ["ACME_vent_alarmRangeMax", 25])
                        * (_avol max 0) min (missionNamespace getVariable ["ACME_vent_alarmRangeMax", 25]);
                    playSound3D ["acm_extended\sound\vent_alarm_sfx.ogg", _src, false, getPosASL _src, _avol, 1, (_arange max 2), 0, true];
                    _beepsLeft = _beepsLeft - 1;
                    _nextBeepT = _now + _gap;
                };

                ACME_vent_alarmSnd set [_id, [_sPrio, _beepsLeft, _nextBeepT, _nextBurstT, _lowDone]];
            };
        } forEach ACME_vent_alarmCandidates;

        // forget the casualties we can no longer hear, so their pattern restarts cleanly when we come back.
        { if !(_x in _seen) then { ACME_vent_alarmSnd deleteAt _x; }; } forEach (keys ACME_vent_alarmSnd);
    }, 0.05, [_beepLen]] call CBA_fnc_addPerFrameHandler;
};

// client side. Play the baked fade-in and fade-out with explicit local=true because every
// client that should hear it has to call it itself.
if (hasInterface) then {
    ["ACME_ventSndFade", {
        params ["_pat", "_which"];
        if (isNull _pat) exitWith {};
        if ((ACE_player distance _pat) > 40) exitWith {};  // out of earshot; do not bother
        private _file = if (_which == "in") then {
            "acm_extended\sound\ventilator_startup_sfx.ogg"
        } else {
            "acm_extended\sound\ventilator_shutdown_sfx.ogg"
        };
        // volume 3, not the 1.6 of the loop. these are event cues the operator should hear clearly as the machine
        // powers up and shuts down, not ambience. the distance is 30 so they carry across a cabin.
        playSound3D [_file, _pat, false, getPosASL _pat, 3, 1, 30, 0, true];
    }] call CBA_fnc_addEventHandler;

    // logbook. this records freshly raised alarms into the device log of the operating medic. only the medic whose
    // device is on this patient records it, so each operator's logbook is the history of their own machine.
    ["ACME_ventAlarmLog", {
        params ["_pat", "_fresh"];
        if (isNull _pat) exitWith {};
        if ((ACE_player getVariable ["ACME_vent_devicePatient", objNull]) isEqualTo _pat) then {
            {
                // alarms carry higher severity than alerts. tag by the severity table so the swatch color is right. anything
                // drawn from the alarm list, HIGH included, is an ALARM. the amber ALERT tag is reserved for operator
                // alert-limit changes.
                ["ALARM", _x] call ACME_fnc_ventLogbookAdd;
            } forEach _fresh;
        };
    }] call CBA_fnc_addEventHandler;
};
