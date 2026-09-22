/*
 * Shared pharmacologic unconsciousness.
 * 1.0 is induction. Once induction is established, the lower maintenance
 * threshold keeps that same anesthetic state active until washout.
 */
params [["_patient", objNull, [objNull]]];

if (isNull _patient || {!alive _patient}) exitWith {false};

private _load = [_patient] call ACME_fnc_sedationOnBoard;
private _maintenance = call ACME_fnc_sedationThreshold;
private _owned = _patient getVariable ["ACME_ket_sedated", false];

(_load >= 1) || {_owned && {_load >= _maintenance}}
