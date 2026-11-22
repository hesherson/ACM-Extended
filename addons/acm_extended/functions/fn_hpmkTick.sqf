// sustain HPMK passive rewarming. for each wrapped patient who is stable enough to retain and generate heat, drift
// the core temp, ACME_hypo_temp, slowly up toward normothermic at 37 c. ACM's circulation handler reads that temp
// for the lethal-triad effects, meaning the coagulopathy, the pressor refractoriness and the bradycardia, so
// rewarming reverses them on its own as the number climbs.
// stable enough means perfusing: alive, not in cardiac arrest, with a real pulse and a MAP above the floor. an
// unstable or non-perfusing patient cannot drive passive rewarming. that is realistic, because severe
// hypothermia, often bradycardic and hypotensive, fails this gate and needs active rewarming.
if (isNil "ACME_hpmk_activePatients") exitWith {};
if !(missionNamespace getVariable ["ACME_sys_hpmk", true]) exitWith {
    { if (!isNull _x && {local _x}) then { _x setVariable ["ACME_hpmk_lastTickLocal", CBA_missionTime, false]; }; } forEach ACME_hpmk_activePatients;
};

private _rate = missionNamespace getVariable ["ACME_hpmk_warmRatePerMin", 0.6];
private _minMAP = missionNamespace getVariable ["ACME_hpmk_minMAP", 60];
{
    private _u = _x;
    if (isNull _u || {!alive _u} || {!(_u getVariable ["ACME_hpmk_on", false])}) then { continue };
    if !(local _u) then { continue };
    // the shell is on him and he lies as it is made (put back if something took either away)
    [_u] call ACME_fnc_hpmkDress;
    private _now = CBA_missionTime;
    private _dt = ((_now - (_u getVariable ["ACME_hpmk_lastTickLocal", _now - 5])) max 0) min 10;
    _u setVariable ["ACME_hpmk_lastTickLocal", _now, false];
    private _step = _rate * (_dt / 60);
    private _temp = _u getVariable ["ACME_hypo_temp", 37];
    if (_temp >= 36.9) then { continue };  // already normothermic.
    if (_u getVariable ["ace_medical_inCardiacArrest", false]) then { continue };
    if ((_u getVariable ["ace_medical_heartRate", 0]) < 20) then { continue };  // no perfusing pulse.
    private _bp = _u call ace_medical_status_fnc_getBloodPressure;  // [dia, sys], including our offsets.
    _bp params [["_dia", 0], ["_sys", 0]];
    private _map = _dia + ((_sys - _dia) / 3);
    if (_map < _minMAP) then { continue };  // too hypotensive to rewarm.
    // the chest is exposed for care, so the seal is broken over the chest and left arm and the blanket only retains
    // partial warmth. rewarming runs at ACME_hpmk_exposedWarmFactor, defaulting to 0.80, which is 80 percent, while
    // exposed.
    private _eff = _step;
    if ((_u getVariable ["ACME_hpmk_state", "wrapped"]) == "exposed") then {
        _eff = _eff * (missionNamespace getVariable ["ACME_hpmk_exposedWarmFactor", 0.80]);
    };
    private _new = (_temp + _eff) min 37;
    [_u, _new, true, true, false] call ACME_fnc_hypothermiaTemperatureCommit;
    // hardcore hypothermia: there is no rewarmed-to-normothermia confirmation in the log.
    if (_new >= 36.9 && {!isNil "ace_medical_treatment_fnc_addToLog"} && {!(missionNamespace getVariable ["ACME_hcEff_hpmk", false])}) then {
        [_u, "activity", "Rewarmed to normothermia (HPMK)", []] call ace_medical_treatment_fnc_addToLog;
    };
} forEach (+ACME_hpmk_activePatients);
ACME_hpmk_activePatients = ACME_hpmk_activePatients select {!isNull _x && {local _x} && {alive _x} && {_x getVariable ["ACME_hpmk_on", false]}};
