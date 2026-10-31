// the cheyne-stokes respiration driver. it runs from a CBA pfh started in postinit. for every patient flagged
// ACME_cs_active, through the debug toggle or any future clinical trigger, it writes a true cheyne-stokes
// pattern into the respiration rate every frame:
// |        ___                         ___                          the peak, or hyperpnea
// |     _-'   '-_                    _-'   '-_
// |   _'         '_                _'         '_
// |  '             '_  ......     '             '_  ......          the apneic pause, flat, at about 0
// +--[ crescendo ][ decrescendo ][ apnea ]--[ next cycle ]--> time
// the breathing phase is a smooth raised-cosine envelope, waxing from near zero up to a peak rate, then waning
// back down. after it a flat apneic pause holds the rate at about 0, and then the cycle repeats.
// because we set the actual ACM_breathing_RespirationRate rather than only a display number, the check breathing
// of the medic reads the live rate and ACM's getetco2 turns the rising and falling rate into capnography that
// swings deep, then shallow, then flat.
if !(missionNamespace getVariable ["ACME_sys_cheyneStokes", true]) exitWith {
    // Preserve enrollment for re-enable, but release the active respiratory drive.
    {
        if (!isNull _x && {local _x} && {(_x getVariable ["ACME_cs_rrDrive", -1]) >= 0}) then {
            [_x, "ACME_cs_rrDrive", -1] call ACME_fnc_setVarNet;
        };
    } forEach (missionNamespace getVariable ["ACME_cs_activePatients", []]);
};

private _list = missionNamespace getVariable ["ACME_cs_activePatients", []];
if (_list isEqualTo []) exitWith {};

// the cycle shape, which is tunable. the total period is the breathe phase plus the apnea. a classic
// cheyne-stokes is a 45 to 90 s cycle with a distinct apneic pause, and the defaults below give a clearly
// readable cycle of about 50 s.
private _breatheDur = missionNamespace getVariable ["ACME_cs_breatheDur", 34];  // seconds of the waxing and waning hyperpnea hump.
private _apneaDur    = missionNamespace getVariable ["ACME_cs_apneaDur", 16];  // seconds of the apneic pause.
private _peakRR      = missionNamespace getVariable ["ACME_cs_peakRR", 30];  // breaths per minute at the crest of the hump.
private _troughRR    = missionNamespace getVariable ["ACME_cs_troughRR", 4];  // breaths per minute just before and after the hump, which is not zero.
private _apneaRR     = missionNamespace getVariable ["ACME_cs_apneaRR", 0];  // breaths per minute during the pause, which is apnea.
private _period      = _breatheDur + _apneaDur;

private _now = CBA_missionTime;
private _alive = [];

{
    private _p = _x;
    if (isNull _p || {!local _p}) then { continue; };
    if (!alive _p || {!(_p getVariable ["ACME_cs_active", false])}) then {
        // being pruned from the demo: release the rr drive, so the override stops pinning the rate of this unit.
        if (!isNull _p && {local _p} && {(_p getVariable ["ACME_cs_rrDrive", -1]) >= 0}) then { [_p, "ACME_cs_rrDrive", -1] call ACME_fnc_setVarNet; };
        continue;
    };
    // audible cheyne-stokes respirations ride along with the rr pattern, in crescendo and decrescendo cycles with a
    // true apnea. they pause under an active BVM and clear when the phase clears.
    if ((_p getVariable ["ACME_bs_pfh", -1]) == -1) then { [_p, "cheyne"] call ACME_fnc_breathSoundsStart; };
    _alive pushBack _p;

    private _start = _p getVariable ["ACME_cs_cycleStart", _now];
    private _phase = (_now - _start) mod _period;  // 0 to _period within the current cycle.

    private _rr = if (_phase < _breatheDur) then {
        // the hyperpnea hump: a raised cosine from the trough to the peak and back to the trough across the breathe
        // phase. the 0.5 minus 0.5 cos shape gives the smooth crescendo and then decrescendo that defines
        // cheyne-stokes, rather than a flat plateau.
        private _frac = _phase / _breatheDur;  // 0 to 1 across the hump.
        private _env  = 0.5 - (0.5 * cos (_frac * 360));  // 0 up to 1 and back to 0, smoothly.
        _troughRR + ((_peakRR - _troughRR) * _env)
    } else {
        // the apneic pause: the rate falls to the apnea level and holds until the next cycle.
        _apneaRR
    };

    _rr = round (_rr max 0 min 50);
    // publish the cheyne-stokes rate as a drive. the updateRespirationRate override, in fn_postInit, pins the live
    // ACM_breathing_RespirationRate to it and is the single writer of that value. the full pattern, including the
    // apneic drop to 0, still carries, because check breathing reads it and ACM's capnography follows, and nothing
    // here writes the live rate directly any more, so this debug demo can never fight the sole-writer.
    if ((_p getVariable ["ACME_cs_rrDrive", -1]) != _rr) then {
        [_p, "ACME_cs_rrDrive", _rr] call ACME_fnc_setVarNet;
    };
    // the target, or desired, rate must never be 0, because ACM's updateoxygen divides by
    // ACM_core_TargetVitals_RespirationRate, at around line 191 of fnc_updateoxygen, so a 0 target throws a zero
    // divisor. keep the target at a safe nonzero floor, because it represents the central drive the body is aiming
    // for rather than the momentary apneic rate.
} forEach _list;

// prune dead and cleared patients, so the list does not grow stale.
if (count _alive != count _list) then {
    missionNamespace setVariable ["ACME_cs_activePatients", _alive, false];
};
