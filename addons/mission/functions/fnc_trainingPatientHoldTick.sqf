#include "..\script_component.hpp"
/* The keeper owns only autonomous AI. It never wins over an unconscious, transported or treatment-posed patient. */
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {false};
if (!(_patient getVariable ["ACME_trainingCrouchOnly",false]) || {[_patient] call ace_common_fnc_isPlayer}) exitWith {
    private _saved = _patient getVariable ["ACME_trainingSavedAI",[]];
    if (count _saved == 4) then {
        {if (_x select 1) then {_patient enableAI (_x select 0);};} forEach (_saved select 0);
        _patient setUnitPos (_saved select 1);
        _patient setBehaviourStrong (_saved select 2);
        _patient setUnitCombatMode (_saved select 3);
        _patient forceSpeed -1;
        _patient setVariable ["ACME_trainingSavedAI",nil,true];
    };
    false
};
// Also repair a third-party AI reset, without ever disabling the patient's animation system.
{_patient disableAI _x;} forEach ["MOVE","PATH","TARGET","AUTOTARGET","AUTOCOMBAT","COVER","SUPPRESSION","FSM","WEAPONAIM"];
_patient forceSpeed 0;
if (_patient getVariable ["ACE_isUnconscious",false]
    || {_patient getVariable ["ace_medical_unconscious",false]}
    // B225: the wake token owns only the clip, NOT the complete awake/down episode.
    // Natural clip completion must never authorize this keeper to crouch the casualty.
    || {_patient getVariable ["ACM_core_Lying_State",false]}
    || {(toLowerANSI animationState _patient) == "acm_lyingstate"}
    || {!isNull objectParent _patient}
    || {!isNull attachedTo _patient}
    || {_patient call ace_common_fnc_isBeingDragged}
    || {_patient call ace_common_fnc_isBeingCarried}
    || {((_patient getVariable ["ACME_patientAnimLock",[]]) param [4,-1]) > serverTime}
    || {((_patient getVariable ["ACME_wakeVisualToken",[]]) param [1,-1]) > serverTime}
    || {_patient getVariable ["ACME_headElevated",false]}
    || {_patient getVariable ["ACM_airway_RecoveryPosition_State",false]}
    || {(_patient getVariable ["ACME_lido_seizureState",""]) == "active"}) exitWith {true};
_patient setUnitPos "MIDDLE";
// MIDDLE alone is insufficient for an unarmed survivor. Blend into a real unarmed kneeling idle.
if (stance _patient != "CROUCH" && {CBA_missionTime >= (_patient getVariable ["ACME_trainingCrouchRetryAt",-1])}) then {
    _patient setVariable ["ACME_trainingCrouchRetryAt",CBA_missionTime + 2];
    _patient playMoveNow "AmovPknlMstpSnonWnonDnon";
};
true
