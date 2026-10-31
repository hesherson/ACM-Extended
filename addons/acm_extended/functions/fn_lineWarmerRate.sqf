/* Proposed rate in mL/min. The downstream warmer caps the fluid that is actually
 * flowing; it cannot accelerate a slower gravity/clamp/perfusion-limited rate. */
params ["_patient", "_part", "_iv", "_site", "_type", ["_rate", 0, [0]]];
if (!finite _rate || {_rate <= 0}) exitWith {0};
if !([_patient, _part, _iv, _site] call ACME_fnc_lineWarmer) exitWith {_rate};
switch (_type) do {
    case "Saline";
    case "ACME_SalineY": {_rate min 200};
    case "Plasma": {_rate min 100};
    default {_rate};
}
