/* Patient-owner burp transaction. Cooldown precedes physiology, animation and logging. */
params ["_medic","_patient",["_bodyPart","body"]];
if (isNull _patient || {isNull _medic}) exitWith {};
if (!local _patient) exitWith {["ACME_ownerCommand",[_patient,"burp",_this],_patient] call CBA_fnc_targetEvent;};
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious",false]}
    || {(_medic distance _patient) > 5}) exitWith {};
if !([_patient,true] call ACME_fnc_chestSealBurpReady) exitWith {};
// A corpse can still be handled, but no physiological worker should restart.
if (alive _patient) then {[_patient,"burp"] call ACME_fnc_ptxTreat;};
_patient setVariable ["ACME_CS_lastBurp",CBA_missionTime,true];
[_patient, "burp", "Burped chest seal", [], _medic, 0] call ACME_fnc_chestSealLogOnce;
[_medic,"chestSealBurpGesture",[_medic,_patient]] call ACME_fnc_ownerDispatch;
