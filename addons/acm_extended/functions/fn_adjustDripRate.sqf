params [["_direction", 0, [0]]];
call ACME_fnc_updateClampDialog;
private _result = [] call ACME_fnc_getSelectedInfusionEntryIndexes;
if (_result isEqualTo []) exitWith {};
_result params ["_patient", "_indexes"];
if (_indexes isEqualTo []) exitWith {};
private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
private _entry = _entries select (_indexes select 0);
private _drops = _entry param [21,0];
if (!isNull (uiNamespace getVariable ["ACME_RollerClamp_DLG",displayNull])) then {
    _drops = [uiNamespace getVariable ["ACME_RollerClamp_Position",1]] call ACME_fnc_clampPositionToDrops;
};
private _step = if (_drops < 20) then {1} else {5};
_drops = ((_drops + _direction * _step) max ACME_infusion_minDropsPerMinute) min ACME_infusion_maxDropsPerMinute;
private _pos = [_drops] call ACME_fnc_dropsToClampPosition;
[_pos,true] call ACME_fnc_setClampPosition;
