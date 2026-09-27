/* B13: sedation uses native, route-specific effective counts. No second onset ramp.
   Times are configured in ACM_Medication; this is a simulation effect load, not clinical dosing. */
params ["_patient"];
if (isNull _patient || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {};
if (isNil "ace_medical_status_fnc_getMedicationCount") exitWith {};

// the raw midazolam dose on board, im plus iv, route-weighted like the ketamine model, where iv is the stronger
// route.
private _rIM = [_patient, "Midazolam", false] call ACME_fnc_medicationCountCompat;
private _rIV = [_patient, "Midazolam_IV", false] call ACME_fnc_medicationCountCompat;
private _raw = (_rIM * 0.5) + (_rIV * 0.8);

private _now = CBA_missionTime;

if (_raw <= 0.01) exitWith {
    // washed out: clear the onset stamp, so a future dose starts its onset from scratch.
    [_patient, "ACME_midaz_onsetT0", -1] call ACME_fnc_setVarNet;
    [_patient, "ACME_midaz_sedEffective", 0] call ACME_fnc_setVarNet;
};

// stamp the first moment midazolam is on board. later top-ups do not restart the clock, because the drug has been
// working the whole time.
private _t0 = _patient getVariable ["ACME_midaz_onsetT0", -1];
if (_t0 == -1) then {
    _t0 = _now;
    [_patient, "ACME_midaz_onsetT0", _t0] call ACME_fnc_setVarNet;
};

// B13: native effective counts already include onset and washout.
private _ramp = 1;
[_patient, "ACME_midaz_sedRamp", _ramp] call ACME_fnc_setVarNet;
[_patient, "ACME_midaz_sedEffective", (_raw * _ramp)] call ACME_fnc_setVarNet;
