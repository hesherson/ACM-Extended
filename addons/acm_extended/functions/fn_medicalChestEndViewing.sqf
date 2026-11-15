params ["_unit"];
private _session = _unit getVariable ["ACME_medicalChestViewing", []];
if (_session isEqualTo []) exitWith {};
_unit setVariable ["ACME_medicalChestViewing", []];
_session params ["_cargo", "_revision", "_deadline", "_nextReport"];
if (_nextReport > 0 && {!isNull _cargo}) then {
    [_cargo, _unit, _revision, false] remoteExecCall ["ACME_fnc_medicalChestView", 2];
};
