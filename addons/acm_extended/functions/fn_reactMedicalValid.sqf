/* Captured local view admission; dead patients remain accessible. No native state writes. */
params [["_context",[],[[]]]];
if (count _context != 9) exitWith {false};
_context params ["_medic","_patient","","","_epoch","_kit","_medicKit","_period","_owner"];
!isNull _medic && {!isNull _patient} && {local _medic} && {alive _medic}
    && {_medic isEqualTo (call ACME_fnc_controlledProvider)}
    && {!(_medic getVariable ["ACE_isUnconscious",false])}
    && {!(_medic getVariable ["ACME_persistenceFrozen",false])}
    && {!(_patient getVariable ["ACME_persistenceFrozen",false])}
    && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {_kit == (_patient getVariable ["ACME_equipmentKitEpoch",0])}
    && {_medicKit == (_medic getVariable ["ACME_equipmentKitEpoch",0])}
    && {_period == (_medic getVariable ["ACME_providerLocalityEpoch",0])}
    && {_owner == owner _patient}
    && {([_medic,_patient] call ACME_fnc_patientInteractionDistance)
        <= (missionNamespace getVariable ["ace_medical_gui_maxDistance",3])}
