#include "..\script_component.hpp"
/*
    B67 single ROSC eligibility read.

    ACM remains the owner of the cardiac-arrest state and CPRSucceeded transition. ACME's only job here is to
    make every ROSC caller consume the same composed circulation state and the same strict ACM blood-volume gate.
    This avoids a shock path, reversible-PEA worker and ACM event handler each re-implementing slightly different
    criteria.

    Returns: [eligible <BOOL>, reason <STRING>]
*/
params [["_patient", objNull, [objNull]], ["_refresh", true, [true]]];
if (isNull _patient) exitWith {[false, "INVALID"]};
if (!local _patient) exitWith {[false, "NOT LOCAL"]};
if (!alive _patient) exitWith {[false, "DEAD"]};
if (!(IN_CRDC_ARRST(_patient))) exitWith {[false, "NOT IN CARDIAC ARREST"]};

if (_refresh) then {[_patient] call FUNC(updateCirculationState);};

private _volume = GET_BLOOD_VOLUME(_patient);
if (_volume <= ACM_REVERSIBLE_CA_BLOODVOLUME) exitWith {[false, "BLOOD VOLUME"]};
// Plasma can restore circulating preload without replacing lost oxygen-carrying
// cells. The ACE total-volume gate above counts blood + plasma + saline, so
// it cannot be the sole rescue condition after fatal red-cell loss.
// Keep the requirement below the reversible-volume threshold: resuscitation
// may still work after substantial blood loss, but plasma-only filling cannot
// immediately resurrect a patient with almost no native blood remaining.
private _bloodCarrying = _patient getVariable [QGVAR(Blood_Volume), _volume];
private _minBlood = missionNamespace getVariable ["ACME_rosc_minBloodCarryingVolume", 2.75];
if (_bloodCarrying < _minBlood) exitWith {[false, "INSUFFICIENT BLOOD / OXYGEN CAPACITY"]};

if (!(GET_CIRCULATIONSTATE(_patient))) exitWith {
    private _reason = _patient getVariable ["ACME_rosc_blockedBy", ""];
    if (_reason == "") then {
        _reason = switch (true) do {
            case (GET_OXYGEN(_patient) < ACM_OXYGEN_HYPOXIA): {"HYPOXIA"};
            case (_patient getVariable [QEGVAR(breathing,TensionPneumothorax_State), false]): {"TENSION PNEUMOTHORAX"};
            case ((_patient getVariable [QEGVAR(breathing,Hemothorax_Fluid), 0]) > ACM_TENSIONHEMOTHORAX_THRESHOLD): {"HEMOTHORAX"};
            case (_volume < BLOOD_VOLUME_CLASS_4_HEMORRHAGE): {"BLOOD VOLUME"};
            default {"REVERSIBLE CAUSE"};
        };
    };
    [false, _reason]
};

[true, ""]
