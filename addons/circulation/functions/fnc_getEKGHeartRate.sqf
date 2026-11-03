#include "..\script_component.hpp"
/*
 * Author: Blue / ACM Extended
 * Read the electrical heart rate used by the AED.
 *
 * This accessor is intentionally side-effect free.  fnc_updateEKGHeartRate is
 * the single writer for the cached electrical rate, so the beep scheduler,
 * numeric display and waveform renderer cannot each advance the same value in
 * one frame.
 */
params ["_patient"];

if (isNull _patient) exitWith {0};

if (alive (_patient getVariable [QACEGVAR(medical,CPR_provider), objNull])) exitWith {
    GET_HEART_RATE(_patient) max 0
};

if ([_patient] call FUNC(recentAEDShock) || {!(alive _patient)}) exitWith {0};

// Captured LS pacing is integrated by the native HR writer, not a second vital setter.
if (_patient getVariable ["acme_tempusls_capture", false]) exitWith {GET_HEART_RATE(_patient) max 0};

private _rhythm = _patient getVariable [QGVAR(Cardiac_RhythmState), ACM_Rhythm_Sinus];
private _effective = [_patient] call ACME_fnc_rhythmGet;

if (_effective >= 100) exitWith {
    private _target = _patient getVariable ["ACME_rhythm_targetHR", GET_HEART_RATE(_patient)];
    if (!(_target isEqualType 0) || {!finite _target}) then {_target = GET_HEART_RATE(_patient);};
    _target max 0
};

switch (_rhythm) do {
    case ACM_Rhythm_Asystole: {0};
    case ACM_Rhythm_VF;
    case ACM_Rhythm_PVT;
    case ACM_Rhythm_PEA: {
        private _cached = _patient getVariable [QGVAR(CardiacArrest_EKG_HR), -1];
        private _cachedRhythm = _patient getVariable ["ACME_AED_ElectricalRateRhythm", -999];
        // A rhythm transition may be observed by the display one frame before the AED rate-writer PFH runs.
        // Never expose the prior rhythm's cached number during that handoff.
        if (_cachedRhythm != _rhythm || {!(_cached isEqualType 0)} || {!finite _cached} || {_cached < 0}) then {
            switch (_rhythm) do {
                case ACM_Rhythm_VF: {170};
                case ACM_Rhythm_PVT: {220};
                default {
                    private _seed = _patient getVariable ["ACME_peaElectricalHR", 80];
                    if (!(_seed isEqualType 0) || {!finite _seed}) then {_seed = 80;};
                    (_seed max 60) min 100
                };
            }
        } else {
            _cached
        }
    };
    case ACM_Rhythm_VT;
    default {
        private _hr = GET_HEART_RATE(_patient);
        if (!(_hr isEqualType 0) || {!finite _hr}) then {_hr = 0;};
        _hr max 0
    };
}
