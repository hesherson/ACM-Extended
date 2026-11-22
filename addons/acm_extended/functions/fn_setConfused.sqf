/* B391 debug / ACE action: toggle the confused state on a player (works with the master switch off, as the
 * obtunded debug toggle does). */
params ["_medic", "_patient"];
if (isNull _patient) exitWith {};
if (!isPlayer _patient) exitWith {
    ["Confusion only applies to players, not AI.", 2.5, _medic] call ace_common_fnc_displayTextStructured;
};
private _on = !(_patient getVariable ["ACME_confused", false]);
[_patient, _on, true, "debug"] call ACME_fnc_confusedSet;
[(["Confusion cleared.", "Confused: garbled speech, swimming vision."] select _on), 2.5, _medic] call ace_common_fnc_displayTextStructured;
