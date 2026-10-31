params ["_entry"];
private _components = [_entry] call ACME_fnc_preparedComponents;
private _title = [_components apply {_x param [0,""]}] call ACME_fnc_infusionTitle;
private _parts = _components apply {
    format ["%1 %2", [_x select 0, _x select 1] call ACME_fnc_formatDose, [_x select 0] call ACME_fnc_infusionName]
};
format ["%1 | %2 mL solution · %3", _title, (_entry param [10, 0]) toFixed 1, _parts joinString " + "]
