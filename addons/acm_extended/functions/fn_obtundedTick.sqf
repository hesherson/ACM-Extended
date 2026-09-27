// Local awake-obtundation effects for ACE_player.
// B49: obtundation is cognitive/motor impairment, not a forced body posture. It never parks the patient prone or
// supine and never continuously owns their animation. A player who is already down gets a deliberately slow Get Up
// through the ACM getUp override. The only body failure generated here is a short probabilistic stumble when an
// obtunded player actually attempts to sprint.
//
// Vision intentionally mirrors ACE's severe-pain base blur scale: ACE maps severe pain to DynamicBlur 0..1. ACME
// uses the same 0..1 range, but breathes it in and out instead of leaving it fixed, and layers a soft black radial
// vignette/blink on top. Manual/debug obtundation uses this exact same stack even when the automatic system switch
// is off, so debug is a faithful preview of the real state.

private _p = ACE_player;
private _systemOn = missionNamespace getVariable ["ACME_sys_obtunded", false];
private _manual = !isNull _p && {_p getVariable ["ACME_obtunded_manual", false]};
private _active = !isNull _p
    && {alive _p}
    && {_p getVariable ["ACME_obtunded", false]}
    && {_systemOn || _manual}
    && {!(_p getVariable ["ACE_isUnconscious", false])};
private _wasActive = uiNamespace getVariable ["ACME_ObtundedActive", false];

// Retire all input/stance locks from the old prone/back implementation. Calling this every frame while active is
// cheap and, more importantly, means a hot-loaded older handler cannot keep the player pinned after the update.
[_p, false] call ACME_fnc_obtundedInputLock;

if (_active) then {
    if (!_wasActive) then {
        uiNamespace setVariable ["ACME_ObtundedActive", true];
        uiNamespace setVariable ["ACME_obtunded_fxStart", diag_tickTime];
        uiNamespace setVariable ["ACME_obtunded_blinkStart", -1];
        uiNamespace setVariable ["ACME_obtunded_blinkUntil", -1];
        uiNamespace setVariable ["ACME_obtunded_blinkNext", diag_tickTime + 1.5 + random 2.0];
        uiNamespace setVariable ["ACME_obtunded_lucidNext", diag_tickTime + (missionNamespace getVariable ["ACME_obtunded_lucidStartDelay", 8])];
        uiNamespace setVariable ["ACME_obtunded_lucidUntil", 0];
        uiNamespace setVariable ["ACME_obtunded_lucidActive", false];
        uiNamespace setVariable ["ACME_ObtundedSprintWasDown", false];
        uiNamespace setVariable ["ACME_ObtundedSprintNextFall", 0];

        private _dbNew = ppEffectCreate ["DynamicBlur", 816]; // ACE reserves 813/814/815.
        _dbNew ppEffectEnable true;
        _dbNew ppEffectForceInNVG true;
        _dbNew ppEffectAdjust [0];
        _dbNew ppEffectCommit 0;
        uiNamespace setVariable ["ACME_Obtunded_DB", _dbNew];

        private _ccNew = ppEffectCreate ["ColorCorrections", 13510];
        _ccNew ppEffectEnable true;
        _ccNew ppEffectForceInNVG true;
        _ccNew ppEffectAdjust [1,1,0,[0,0,0,0],[0,0,0,1],[0,0,0,0],[0.70,0.95,0,0,0,0,1]];
        _ccNew ppEffectCommit 0;
        uiNamespace setVariable ["ACME_Obtunded_CC", _ccNew];

        [_p, true] call ACME_fnc_obtundedVoice;
        (missionNamespace getVariable ["ACME_obtunded_muffleFade", 1.0]) fadeSound
            (missionNamespace getVariable ["ACME_obtunded_muffleLevel", 0.35]);
    };

    // If another PP reinitialization destroyed one of our handles while the episode remained active, recreate only
    // the missing handle instead of requiring the player to leave/re-enter obtundation.
    private _db = uiNamespace getVariable ["ACME_Obtunded_DB", -1];
    if (!(_db isEqualType 0) || {_db < 0}) then {
        _db = ppEffectCreate ["DynamicBlur", 816];
        _db ppEffectEnable true;
        _db ppEffectForceInNVG true;
        uiNamespace setVariable ["ACME_Obtunded_DB", _db];
    };
    private _cc = uiNamespace getVariable ["ACME_Obtunded_CC", -1];
    if (!(_cc isEqualType 0) || {_cc < 0}) then {
        _cc = ppEffectCreate ["ColorCorrections", 13510];
        _cc ppEffectEnable true;
        _cc ppEffectForceInNVG true;
        uiNamespace setVariable ["ACME_Obtunded_CC", _cc];
    };

    private _now = diag_tickTime;
    private _start = uiNamespace getVariable ["ACME_obtunded_fxStart", _now];

    // Brief lucid windows remain part of the state. They reduce, but do not completely remove, visual and audio
    // impairment. The debug path uses the same timings because _active includes manual states.
    private _lucidUntil = uiNamespace getVariable ["ACME_obtunded_lucidUntil", 0];
    private _lucidNext = uiNamespace getVariable ["ACME_obtunded_lucidNext", _now + 8];
    if (_now >= _lucidNext && {_now >= _lucidUntil}) then {
        _lucidUntil = _now
            + (missionNamespace getVariable ["ACME_obtunded_lucidDurMin", 2])
            + random (missionNamespace getVariable ["ACME_obtunded_lucidDurRand", 2]);
        uiNamespace setVariable ["ACME_obtunded_lucidUntil", _lucidUntil];
        uiNamespace setVariable ["ACME_obtunded_lucidNext",
            _lucidUntil
            + (missionNamespace getVariable ["ACME_obtunded_lucidIntervalMin", 15])
            + random (missionNamespace getVariable ["ACME_obtunded_lucidIntervalRand", 20])
        ];
    };
    private _lucid = _now < _lucidUntil;
    private _prevLucid = uiNamespace getVariable ["ACME_obtunded_lucidActive", false];
    if (_lucid isNotEqualTo _prevLucid) then {
        uiNamespace setVariable ["ACME_obtunded_lucidActive", _lucid];
        [_p, !_lucid] call ACME_fnc_obtundedVoice;
        (missionNamespace getVariable ["ACME_obtunded_muffleFade", 1.0]) fadeSound
            (if (_lucid) then {0.78} else {missionNamespace getVariable ["ACME_obtunded_muffleLevel", 0.35]});
    };

    // ACE's high-pain DynamicBlur tops out at 1.0. Stay on that same scale and continuously cross-fade between a
    // mild and severe value. A lucid window collapses the band toward almost-clear without snapping to clear.
    private _cycle = (missionNamespace getVariable ["ACME_obtunded_blurCycle", 4.5]) max 1;
    private _wave = 0.5 + (0.5 * sin (((_now - _start) / _cycle) * 360));
    private _bMin = (missionNamespace getVariable ["ACME_obtunded_blurWaveMin", 0.12]) max 0 min 1;
    private _bMax = (missionNamespace getVariable ["ACME_obtunded_blurWaveMax", 1.0]) max _bMin min 1;
    private _blur = _bMin + ((_bMax - _bMin) * _wave);
    if (_lucid) then { _blur = _blur min (missionNamespace getVariable ["ACME_obtunded_lucidBlur", 0.08]); };

    // Heavy-lidded blink over the breathing vignette. It is a radial ColorCorrections eye in the same family as
    // ACE's blackout, but the patient remains medically conscious and retains control.
    private _blinkNext = uiNamespace getVariable ["ACME_obtunded_blinkNext", _now + 3];
    private _blinkStart = uiNamespace getVariable ["ACME_obtunded_blinkStart", -1];
    private _blinkUntil = uiNamespace getVariable ["ACME_obtunded_blinkUntil", -1];
    private _blinkDur = (missionNamespace getVariable ["ACME_obtunded_blinkDuration", 0.6]) max 0.1;
    if (_now >= _blinkNext && {_now >= _blinkUntil}) then {
        _blinkStart = _now;
        _blinkUntil = _now + _blinkDur;
        uiNamespace setVariable ["ACME_obtunded_blinkStart", _blinkStart];
        uiNamespace setVariable ["ACME_obtunded_blinkUntil", _blinkUntil];
        private _bMinGap = missionNamespace getVariable ["ACME_obtunded_blinkIntervalMin", 3.0];
        private _bMaxGap = missionNamespace getVariable ["ACME_obtunded_blinkIntervalMax", 5.5];
        uiNamespace setVariable ["ACME_obtunded_blinkNext", _blinkUntil + _bMinGap + random ((_bMaxGap - _bMinGap) max 0)];
    };
    private _blinkClose = 0;
    if (_blinkStart >= 0 && {_now < _blinkUntil}) then {
        private _bp = ((_now - _blinkStart) / _blinkDur) max 0 min 1;
        _blinkClose = sin (_bp * 180);
    };

    private _vigMin = missionNamespace getVariable ["ACME_obtunded_vignetteMin", 0.10];
    private _vigMax = missionNamespace getVariable ["ACME_obtunded_vignetteMax", 0.34];
    private _ambDark = _vigMin + ((_vigMax - _vigMin) * (1 - _wave));
    if (_lucid) then { _ambDark = _ambDark * 0.45; };
    private _blackAlpha = _ambDark + ((1 - _ambDark) * _blinkClose);
    private _vIn  = linearConversion [0,1,_blinkClose,0.70,0.18,true];
    private _vOut = linearConversion [0,1,_blinkClose,0.95,0.30,true];

    private _inZeus = !isNull curatorCamera;
    _db ppEffectEnable (!_inZeus);
    _cc ppEffectEnable (!_inZeus);
    if (!_inZeus) then {
        _db ppEffectAdjust [_blur];
        _db ppEffectCommit (missionNamespace getVariable ["ACME_obtunded_blurFadeIn", 0.18]);
        _cc ppEffectAdjust [
            1,1,0,
            [0,0,0,_blackAlpha],
            [0,0,0,1],
            [0,0,0,0],
            [_vIn,_vOut,0,0,0,0,1]
        ];
        _cc ppEffectCommit 0.10;
    };

    // Sprinting is the only circumstance in which obtundation itself may drop the body. A held sprint key counts
    // once per press/attempt, not once per frame, and the short cooldown prevents a key bounce from producing a
    // chain of falls. This uses only Arma's engine-unconscious/ragdoll state; ACE medical unconsciousness is never set.
    private _moving = (inputAction "MoveForward" > 0.1)
        || {inputAction "MoveBack" > 0.1}
        || {inputAction "TurnLeft" > 0.1}
        || {inputAction "TurnRight" > 0.1}
        || {inputAction "MoveLeft" > 0.1}
        || {inputAction "MoveRight" > 0.1};
    private _sprintDown = _moving && {((inputAction "Turbo") > 0.1) || {(inputAction "MoveFastForward") > 0.1}};
    private _sprintWasDown = uiNamespace getVariable ["ACME_ObtundedSprintWasDown", false];
    if (_sprintDown && {!_sprintWasDown}) then {
        private _nextFall = uiNamespace getVariable ["ACME_ObtundedSprintNextFall", 0];
        if (_now >= _nextFall
            && {isNull objectParent _p}
            && {isNull attachedTo _p}
            && {!(_p call ace_common_fnc_isBeingDragged)}
            && {!(_p call ace_common_fnc_isBeingCarried)}
            && {!(_p getVariable ["ACME_obtunded_sprintRagdollActive", false])}
            && {random 1 < (missionNamespace getVariable ["ACME_obtunded_sprintFallChance", 0.35])}) then {
            private _dur = missionNamespace getVariable ["ACME_obtunded_sprintFallDuration", 1.25];
            private _cd = missionNamespace getVariable ["ACME_obtunded_sprintFallCooldown", 2.5];
            private _epoch = [_p] call ACME_fnc_clinicalEpoch;
            private _serial = (_p getVariable ["ACME_obtunded_sprintRagdollSerial", 0]) + 1;
            private _token = [_epoch, clientOwner, _serial];
            uiNamespace setVariable ["ACME_ObtundedSprintNextFall", _now + _cd];
            _p setVariable ["ACME_obtunded_sprintRagdollSerial", _serial, false];
            _p setVariable ["ACME_obtunded_sprintRagdollToken", _token, true];
            _p setVariable ["ACME_obtunded_sprintRagdollActive", true, true];
            _p setUnconscious true;
            [{
                params ["_u", "_epoch", "_token"];
                if (isNull _u || {!local _u} || {!alive _u}) exitWith {};
                if (([_u] call ACME_fnc_clinicalEpoch) != _epoch) exitWith {};
                if !((_u getVariable ["ACME_obtunded_sprintRagdollToken", []]) isEqualTo _token) exitWith {};
                if !(_u getVariable ["ACME_obtunded_sprintRagdollActive", false]) exitWith {};
                if (!(_u getVariable ["ACE_isUnconscious", false])) then {_u setUnconscious false;};
                _u setVariable ["ACME_obtunded_sprintRagdollActive", false, true];
                _u setVariable ["ACME_obtunded_sprintRagdollToken", [], true];
            }, [_p, _epoch, _token], _dur] call CBA_fnc_waitAndExecute;
        };
    };
    uiNamespace setVariable ["ACME_ObtundedSprintWasDown", _sprintDown];

    // Small head sway remains an ambient cue, but it never changes body posture.
    private _swayPow = missionNamespace getVariable ["ACME_obtunded_swayPower", 0.07];
    if (_swayPow > 0) then {
        private _swayNext = uiNamespace getVariable ["ACME_Obtunded_SwayT", 0];
        if (_now >= _swayNext) then {
            private _ivl = missionNamespace getVariable ["ACME_obtunded_swayInterval", 2.0];
            addCamShake [_swayPow, _ivl * 1.2, 3];
            uiNamespace setVariable ["ACME_Obtunded_SwayT", _now + _ivl];
        };
    };
} else {
    // Independent voice sanitation catches interrupted/debug episodes and old hot-loaded state.
    private _voiceGuardAt = uiNamespace getVariable ["ACME_ObtundedVoiceGuardAt", 0];
    if (diag_tickTime >= _voiceGuardAt) then {
        uiNamespace setVariable ["ACME_ObtundedVoiceGuardAt", diag_tickTime + 1];
        if (!isNull _p) then {[_p, false] call ACME_fnc_obtundedVoice;};
    };

    if (_wasActive) then {
        if (!isNull _p) then {
            _p setAnimSpeedCoef 1;
            if (_p getVariable ["ACME_obtunded_sprintRagdollActive", false]) then {
                _p setVariable ["ACME_obtunded_sprintRagdollActive", false, true];
                if (!(_p getVariable ["ACE_isUnconscious", false])) then {_p setUnconscious false;};
            };
            _p setVariable ["ACME_obtunded_sprintRagdollToken", [], true];
        };
        private _cc = uiNamespace getVariable ["ACME_Obtunded_CC", -1];
        private _db = uiNamespace getVariable ["ACME_Obtunded_DB", -1];
        if (_cc isEqualType 0 && {_cc >= 0}) then {
            _cc ppEffectAdjust [1,1,0,[0,0,0,0],[0,0,0,1],[0,0,0,0],[0.70,0.95,0,0,0,0,1]];
            _cc ppEffectCommit 0.20;
            [{params ["_h"]; if (_h isEqualType 0) then {_h ppEffectEnable false; ppEffectDestroy _h;};}, [_cc], 0.22] call CBA_fnc_waitAndExecute;
        };
        if (_db isEqualType 0 && {_db >= 0}) then {
            _db ppEffectAdjust [0];
            private _out = missionNamespace getVariable ["ACME_obtunded_blurFadeOut", 0.45];
            _db ppEffectCommit _out;
            [{params ["_h"]; if (_h isEqualType 0) then {_h ppEffectEnable false; ppEffectDestroy _h;};}, [_db], _out + 0.05] call CBA_fnc_waitAndExecute;
        };
        uiNamespace setVariable ["ACME_Obtunded_CC", -1];
        uiNamespace setVariable ["ACME_Obtunded_DB", -1];
        uiNamespace setVariable ["ACME_obtunded_lucidActive", false];
        uiNamespace setVariable ["ACME_ObtundedSprintWasDown", false];
        uiNamespace setVariable ["ACME_ObtundedActive", false];
        if (!isNull _p) then {[_p, false] call ACME_fnc_obtundedVoice;};
        (missionNamespace getVariable ["ACME_obtunded_muffleFade", 1.0]) fadeSound 1;
    };
};
