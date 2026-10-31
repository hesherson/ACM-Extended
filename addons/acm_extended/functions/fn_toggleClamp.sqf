call ACME_fnc_updateClampDialog;
private _drops = -1;
private _display = uiNamespace getVariable ["ACME_RollerClamp_DLG",displayNull];
if (!isNull _display) then {
    _drops = [uiNamespace getVariable ["ACME_RollerClamp_Position",1]] call ACME_fnc_clampPositionToDrops;
} else {
    private _result = call ACME_fnc_getSelectedInfusionEntryIndexes;
    if !(_result isEqualTo []) then {
        _result params ["_patient","_indexes"];
        if !(_indexes isEqualTo []) then {
            private _entries = _patient getVariable ["ACME_infusion_BagMedications",[]];
            _drops = (_entries select (_indexes select 0)) param [21,60];
        };
    };
};
if (_drops < 0) then {
    _drops = [uiNamespace getVariable ["ACME_RollerClamp_Position",1]] call ACME_fnc_clampPositionToDrops;
};
private _position = if (_drops > 0) then {0} else {missionNamespace getVariable ["ACME_infusion_defaultClampPosition",1]};
[_position,false] call ACME_fnc_setClampPosition;
