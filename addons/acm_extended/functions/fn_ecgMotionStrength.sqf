/* Read-only monitor motion envelope. Never converts the rhythm, changes vitals or touches the beat clock.
 * Read replicated physiology/actual rendered movement, not provider-local seizure controller flags.
 * Held recovery/Semi-Fowler poses are quiet; their entry/lowering/rolling is not. */
params ["_patient"];
if (isNull _patient) exitWith {0};
private _s = 0;
if (alive _patient
    && {(_patient getVariable ["ACME_lido_seizureState", ""]) == "active"}
    && {!(_patient getVariable ["ACME_seizure_suppressed", false])}
    && {!(_patient getVariable ["ACME_roc_paralyzed", false])}) then {
    if (([_patient] call ACME_fnc_seizureMotorMode) == "full") then {_s = 0.98;} else {
        // Only an actual short motor pulse contaminates late-arrest ECG; quiet intervals are not convulsions.
        if (((toLowerANSI (gestureState _patient)) find "acme_seizurespasm") == 0
            || {CBA_missionTime < (_patient getVariable ["ACME_seizure_observerUntil",-1]) + 0.15}) then {_s = 0.82;};
    };
};
private _anim = toLowerANSI animationState _patient;
private _blend = _patient getUnitMovesInfo 3;
private _rate = getAnimSpeedCoef _patient;
if (_rate > 0.01) then {
    if ((_anim find "roll") >= 0) then {_s = _s max 0.78;};
    if (_anim in ["acme_headelevpatientgrab", "acme_headelevpatientrelease"]) then {_s = _s max 0.62;};
};
if (_blend isEqualType 0 && {_blend < 0.99}) then {
        // Static target RTMs still move the patient while the skeleton blends into/out of them.
        if (_anim == "acm_recoveryposition") then {_s = _s max 0.72;};
        if ((_anim find "headelev") >= 0 || {(_anim find "headturn") >= 0}
            || {(_anim find "lying") >= 0}) then {_s = _s max 0.48;};
        if ((_anim find "ainj") == 0) then {_s = _s max 0.40;};
};
// Do not treat a vehicle's steady world velocity as loose electrodes moving on its occupant.
// Ground locomotion, dragging and carrying retain proportional motion artifacts.
if (isNull objectParent _patient) then {
    private _speed = vectorMagnitude velocity _patient;
    if (_speed > 0.05) then {_s = _s max (0.15 + ((_speed / 3) min 1) * 0.55);};
    if (_patient getVariable ["ace_dragging_isDragged", false]) then {_s = _s max 0.72;};
    if (_patient getVariable ["ace_dragging_isCarried", false]) then {_s = _s max 0.55;};
};
_s min 1
