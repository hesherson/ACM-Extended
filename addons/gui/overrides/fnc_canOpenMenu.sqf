/* B11: preserve ACE's menu gates; resolve only supported-patient pose distance.
   Reference: supplied ACE medical_gui/functions/fnc_canOpenMenu.sqf. */
params ["_player", "_target"];

// ACE_player is normally maintained by ACE, but Zeus remote control can expose a short/stale identity window.
// Always evaluate the medical-menu gate against the CAManBase this client is actually controlling. Reconcile
// ACE_player at the same boundary so ACE/ACM menu helpers that still read the global see the same provider.
private _controlledProvider = call ACME_fnc_controlledProvider;
if (!isNull _controlledProvider) then {
    _player = _controlledProvider;
    if (hasInterface && {(isNil "ACE_player") || {ACE_player isNotEqualTo _controlledProvider}}) then {
        ACE_player = _controlledProvider;
    };
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
