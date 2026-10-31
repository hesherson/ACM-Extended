#include "..\script_component.hpp"
/* Only marked spawner patients. Behaviour is suppressed; ANIM and simulation remain available to medical care.
   One local active list follows locality and resumes crouching only after explicit medical lying release/transport/treatment. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}
    || {!(_patient getVariable ["ACME_trainingCrouchOnly",false])}) exitWith {false};
if ([_patient] call ace_common_fnc_isPlayer) exitWith {[_patient] call FUNC(trainingPatientHoldTick); false};
private _features = ["MOVE","PATH","TARGET","AUTOTARGET","AUTOCOMBAT","COVER","SUPPRESSION","FSM","WEAPONAIM"];
if (isNil {_patient getVariable "ACME_trainingSavedAI"}) then {
    _patient setVariable ["ACME_trainingSavedAI",[_features apply {[_x,_patient checkAIFeature _x]},unitPos _patient,behaviour _patient,unitCombatMode _patient],true];
};
{_patient disableAI _x;} forEach _features;
_patient setUnitCombatMode "BLUE";
_patient setBehaviourStrong "CARELESS";
_patient allowFleeing 0;
doStop _patient;
_patient forceSpeed 0;
private _patients = missionNamespace getVariable ["ACME_trainingHeldPatients",[]];
_patients pushBackUnique _patient;
missionNamespace setVariable ["ACME_trainingHeldPatients",_patients];
[_patient] call FUNC(trainingPatientHoldTick);
true
