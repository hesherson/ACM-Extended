// hardcore circulation: a pressor is not volume.
// call it as [_patient] call ACME_fnc_hcCircTick, from fn_circhandle.
// the most common serious error in hemorrhagic shock is squeezing an empty tank. norepinephrine on a casualty who
// is two liters down raises the number on the monitor by clamping down the periphery, while the tissue behind
// that clamp gets less blood than it did before. the blood pressure looks treated and the patient is worse.
// outside hardcore a pressor simply works, which is the simplification. under hardcore it works exactly as
// advertised on the display and quietly does harm underneath, and the tell is available to anyone who looks at
// something other than the blood pressure: the lactate climbs, the skin mottles and the capillary refill
// lengthens.
// fill the tank first and none of this happens. that is the entire lesson, and it is not written down anywhere in
// the interface because in real life it is not written down anywhere either.
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};
// Use the same bounded owner-local elapsed clock as other clinical effects;
// the 4 Hz maintenance worker is independent of rendering/server frame rate.
private _dt = [_patient, "hcCirc", 0.25, 5] call ACME_fnc_clinicalTickDelta;
if (!(missionNamespace getVariable ["ACME_hcEff_circ", false])) exitWith {
    [_patient, "ACME_hc_pressorDebt", 0] call ACME_fnc_setVarNet;
};
private _pressor = (_patient getVariable ["ACME_pressorResistAdd", 0]) max 0;
if (_pressor <= 0.5) exitWith {
    // off pressors: the debt clears slowly, because the tissue that was starved takes time to recover.
    private _d = (_patient getVariable ["ACME_hc_pressorDebt", 0]) - (0.15 * _dt);
    [_patient, "ACME_hc_pressorDebt", (_d max 0), 0.05, 2] call ACME_fnc_setVarNetApprox;
};
if (_pressor <= 0.5) exitWith {};

// how empty is the tank. ACE tracks the blood volume directly, so this needs no new state.
// it is ace_medical_bloodVolume rather than blood_volume. the wrong name silently returned the default 6 liters, so
// the casualty always looked fully filled and this whole mechanic could never fire.
private _vol = _patient getVariable ["ace_medical_bloodVolume", 6];
private _deficit = ((6 - _vol) / 6) max 0;

// a pressor on a full tank is fine. on an empty one it is doing damage in proportion to how empty it is.
if (_deficit < (missionNamespace getVariable ["ACME_hcCirc_safeDeficit", 0.15])) exitWith {};

private _rate = (missionNamespace getVariable ["ACME_hcCirc_debtRate", 0.9]) * _deficit;
private _debt = ((_patient getVariable ["ACME_hc_pressorDebt", 0]) + (_rate * _dt))
    min (missionNamespace getVariable ["ACME_hcCirc_debtMax", 100]);
[_patient, "ACME_hc_pressorDebt", _debt, 0.05, 2] call ACME_fnc_setVarNetApprox;

// the debt is the tissue damage, and it surfaces where tissue damage surfaces: acidosis. it is fed into the
// existing acidosis model rather than being a separate hidden number, so everything downstream of acidosis, the
// coagulopathy, the rhythm and the pressor response itself, degrades the way it already knows how to.
[_patient, "ACME_acidosis_pressorDebt", (_debt / 100), 0.002, 2] call ACME_fnc_setVarNetApprox;
