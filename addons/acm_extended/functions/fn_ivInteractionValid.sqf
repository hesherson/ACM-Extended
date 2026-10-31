/* Interactive IV callbacks require the clinician and limb still in reach.
 * Patient survival is deliberately irrelevant: access after death is supported.
 * Captured-session teardown uses ivUiValid alone to release its old resources.
 */
private _medic = uiNamespace getVariable ["ACME_IV_Medic", objNull];
private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
!isNull _medic && {!isNull _patient} && {local _medic} && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious", false])}
    && {!(_medic getVariable ["ACME_persistenceFrozen", false])}
    && {!(_patient getVariable ["ACME_persistenceFrozen", false])}
    && {_medic isEqualTo (call ACME_fnc_controlledProvider)}
    && {([_medic, _patient] call ACME_fnc_patientInteractionDistance)
        <= (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])}
