/* Match ACE treatment useItem priority, including its conditional medic mode.
   Self treatment and a shared vehicle appear only once in downstream counts. */
params ["_medic", "_patient"];
if (isNull _medic) exitWith {[]};
private _mode = missionNamespace getVariable ["ace_medical_treatment_allowSharedEquipment", 0];
if (_mode == 3) then {_mode = [0, 1] select ([_medic] call ace_medical_treatment_fnc_isMedic);};
private _order = switch (_mode) do {
    case 1: {[_medic, _patient]};
    case 2: {[_medic]};
    default {[_patient, _medic]};
};
private _unique = [];
{if (!isNull _x) then {_unique pushBackUnique _x;};} forEach _order;
_unique
