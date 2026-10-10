/* Read-only delivery settings. Stored device choices always survive a live mode toggle.
   Return: [simple, mode, RR, VT, FiO2, PEEP, PInsp, PS, trigger, I:E, kg, pressure limit].
   SIMPLE is an adult gameplay model, not a clinical ventilator prescription. */
params [["_patient", objNull, [objNull]]];
private _simple = (missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((_patient getVariable ["ACME_vent_nivMask", false] || {[_patient] call ACME_fnc_ventMaskSelected}))};
private _bpm = _patient getVariable ["ACME_vent_bpm", 12];
if (!(_bpm isEqualType 0) || {!finite _bpm}) then {_bpm = 12;};
_bpm = _bpm max 1;
if (_simple) exitWith {
    private _arrest = _patient getVariable ["ace_medical_inCardiacArrest", false];
    // Preserve the existing ventilator's abstract oxygen source. B33 has no
    // cylinder ledger; Simple adds no tank or mask requirement.
    [true, "SIMPLE", _bpm min 60, if (_arrest) then {420} else {500}, 95,
        if (_arrest) then {0} else {5}, 20, 10, -2, 2, 70, 35]
};
private _mode = _patient getVariable ["ACME_vent_mode", "SIMV VC PS"];
private _vt = (_patient getVariable ["ACME_vent_vt", 500]) max 1;
private _peep = _patient getVariable ["ACME_vent_peep", 5];
private _kg = (_patient getVariable ["ACME_vent_weight", 70]) max 1;
if (_mode == "IMV VC (CPR)") then {
    _bpm = missionNamespace getVariable ["ACME_vent_cprRate", 10];
    _vt = ((_kg * (missionNamespace getVariable ["ACME_vent_cprVtPerKg", 6])) max 300) min 500;
    _peep = 0;
};
private _pinsp = (_patient getVariable ["ACME_vent_pinsp", round (8 + (12 * (_vt / 500)))]) max (11 max (_peep + 1)) min 60;
[false, _mode, _bpm, _vt, _patient getVariable ["ACME_vent_fio2", 21], _peep, _pinsp,
    (_patient getVariable ["ACME_vent_psup", 10]) max 0 min 50,
    _patient getVariable ["ACME_vent_trigSensCmH2O", missionNamespace getVariable ["ACME_vent_trigSensCmH2O", -2]],
    _patient getVariable ["ACME_vent_ie", 2], _kg, _patient getVariable ["ACME_vent_alertPLimit", 40]]
