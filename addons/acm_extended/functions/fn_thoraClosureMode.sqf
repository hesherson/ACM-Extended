/* Resolve chest-tube availability for the captured treating provider.
   B93 gives the chest seal its own tray slot, so this helper no longer aliases the tube slot into a seal slot.
   Keeping one tool identity per slot also means Doctors can choose a seal while carrying a chest-tube kit. */
params [["_medic", objNull, [objNull]]];
if (isNull _medic) exitWith {["tube", 0, false]};
private _tubeCount = [_medic, uiNamespace getVariable ["ACME_Thora_Patient", objNull], "ACM_ChestTubeKit"] call ACME_fnc_treatmentSupplyCount;
private _canTube = (_tubeCount > 0) && {[_medic, "chestTube"] call ACME_fnc_procedureAllowed};
["tube", [_tubeCount, 0] select (!_canTube), _canTube]
