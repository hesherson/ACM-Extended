/* B11: preserve ACE's menu gates; resolve only supported-patient pose distance.
   Reference: supplied ACE medical_gui/functions/fnc_canOpenMenu.sqf. */
params ["_player", "_target"];
private _controlledProvider = call ACME_fnc_controlledProvider;
// This remains a pure predicate. Repair only this client's legacy avatar input;
// callers asking about a distinct explicit actor retain that actor's gates.
if (!isNull _controlledProvider && {_player in [player, missionNamespace getVariable ["ACE_player", objNull]]}) then {
    _player = _controlledProvider;
};
if (!isNull findDisplay 312) exitWith {
    !isNull _target && {missionNamespace getVariable ["ace_medical_gui_enableZeusModule", true]}
    && {ace_medical_gui_enableMedicalMenu > 0}
};
(_player call ace_common_fnc_isAwake) && {!isNull _target}
&& {([_player, _target] call ACME_fnc_patientInteractionDistance) < ace_medical_gui_maxDistance
    || {vehicle _player == vehicle _target}}
&& {ace_medical_gui_enableMedicalMenu == 1
    || {ace_medical_gui_enableMedicalMenu == 2 && {!isNull objectParent _player || {!isNull objectParent _target}}}}
