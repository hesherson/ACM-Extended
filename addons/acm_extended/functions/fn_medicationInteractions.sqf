/* B38: current-exposure pharmacodynamic interactions, independent of syringe contents.
   Returns additive [HR, peripheral resistance, RR, CO2 sensitivity] targets.
   Native kinetics supply onset, dose normalization, washout and naloxone removal.
   Coefficients are bounded GAME tuning, not a clinical dosing or compatibility model.
   No persistent state, medication records, random arrests or rhythm labels are created.
   See audit/B38_POLYPHARMACY_MODEL.md for sources and limits. */
params ["_patient", ["_components", [0,0,0]], ["_reserve", 1]];
if (isNull _patient || {!alive _patient} || {isNil "ace_medical_status_fnc_getMedicationCount"}) exitWith {[0,0,0,0]};
private _get = {
    params ["_class", ["_canonical", ""]];
    private _value = [_patient, _class, false] call ACME_fnc_medicationCountCompat;
    if !(_value isEqualType 0 && {finite _value}) exitWith {0};
    if (_canonical != "") then {
        private _cfg = configFile >> "ACM_Medication" >> "Medications";
        private _fromRef = if (isNumber (_cfg >> _class >> "maxEffectDose")) then {getNumber (_cfg >> _class >> "maxEffectDose")} else {getNumber (_cfg >> "maxEffectDose")};
        private _toRef = getNumber (_cfg >> _canonical >> "maxEffectDose");
        // Legacy IM amiodarone used a dummy 1 mg reference. Normalize its effect
        // before applying the bound, rather than treating it as a full IV dose.
        _value = _value * ((_fromRef max 0.000001) / (_toRef max 0.000001));
    };
    _value max 0 min 16
};
private _loads = [0,0,0];
{
    private _value = _components param [_forEachIndex, 0];
    if (_value isEqualType 0 && {finite _value}) then {_loads set [_forEachIndex, _value max 0 min 16];};
} forEach _loads;
_loads params ["_ket", "_prop", "_mid"];
if !(_reserve isEqualType 0 && {finite _reserve}) then {_reserve = 1;};
private _vulnerability = 1 + 0.4 * (1 - (_reserve max 0 min 1));

// These counts are each drug's native reference equivalents, never summed raw mg.
// Fentanyl buccal products retain their native units and a separate game weight.
private _opioid = 0;
{
    _x params ["_class", "_weight"];
    _opioid = _opioid + ([_class] call _get) * _weight;
} forEach [["Morphine",1],["Morphine_IV",1],["Fentanyl",1],["Fentanyl_IV",1],["Fentanyl_BUC",0.5]];
_opioid = _opioid min 16;

// Only cross-drug effects are added here. Single-drug native depression and
// overdose syndromes stay in their existing channels and are never duplicated.
private _respLoad = _opioid * (_prop + _mid + 0.25 * _ket)
    + 0.7 * _prop * _mid + 0.2 * _ket * _mid;
private _respFraction = _respLoad / (1 + _respLoad);
private _depressantLoad = _opioid * (_prop + _mid) + 0.6 * _prop * _mid;
private _depressantFraction = _depressantLoad / (1 + _depressantLoad);
private _rr = -8 * _respFraction;
private _co2 = -0.20 * _respFraction;
private _svr = -14 * _depressantFraction * _vulnerability;

// Amiodarone + beta blockade can further slow nodal conduction. Native rhythm
// and hypoperfusion logic decide downstream deterioration; this is no AV-block
// waveform shortcut and does not force arrest or overwrite an existing rhythm.
private _amio = ((["Amiodarone_IV"] call _get) + (["Amiodarone", "Amiodarone_IV"] call _get)) min 16;
private _nodalLoad = _amio * (["Esmolol_IV"] call _get);
private _nodalFraction = _nodalLoad / (1 + _nodalLoad);
private _hr = -26 * _nodalFraction;
_svr = _svr - 8 * _nodalFraction * _vulnerability;

// The permissive prepared-mixture path now admits systemic phentolamine. Its
// native class has zero systemic targets because it was formerly local-only.
// Local infiltration never enters medication history, so only actual systemic
// exposure supplies this bounded vasodilation and modest tachycardia. Pressure
// support and depressant effects continue to meet in the native BP equation.
private _phent = ["Phentolamine"] call _get;
private _phentFraction = _phent / (0.5 + _phent);
_hr = _hr + 12 * _phentFraction;
_svr = _svr - 28 * _phentFraction;

if (_patient getVariable ["ace_medical_inCardiacArrest", false]) then {_hr = 0;};
[_hr, _svr, _rr, _co2]
