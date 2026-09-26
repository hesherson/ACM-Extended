/* Shared simulation clock; pure read. This is a game response envelope. */
params ["_patient"];
if (isNull _patient || {!alive _patient} || {_patient getVariable ["ace_medical_inCardiacArrest", false]}) exitWith {0};
// If the rare vagal reflex fires, it supersedes the ordinary sympathetic laryngoscopy envelope
// for the duration of that event rather than creating simultaneous tachycardia and bradycardia.
if (CBA_missionTime < (_patient getVariable ["ACME_laryngo_vagalUntil",-1])) exitWith {0};
private _at = _patient getVariable ["ACME_laryngoStimulusAt", -1];
private _strength = _patient getVariable ["ACME_laryngoStimulusStrength", 0];
if (!(_at isEqualType 0) || {!finite _at} || {!(_strength isEqualType 0)} || {!finite _strength}) exitWith {0};
private _age = CBA_missionTime - _at;
if (_at < 0 || {_age < 0} || {_age >= 60}) exitWith {0};
private _rise = linearConversion [0, 3, _age, 0, 1, true];
// Do not restore an already-blunted response as an earlier dose wears off.
// Newly admitted fentanyl can attenuate the remainder without restarting its clock.
private _liveStrength = 1 - ([_patient] call ACME_fnc_fentanylOnBoard);
((_strength max 0 min 1) min (_liveStrength max 0 min 1)) * _rise * exp (-((_age - 3) max 0) / 20)
