params ["_entry"];
private _parts = ([_entry] call ACME_fnc_preparedComponents) apply {
    format ["%1 %2", [_x select 0, _x select 1] call ACME_fnc_formatDose, [_x select 0] call ACME_fnc_infusionName]
};
format ["%1 | %2 mL solution", _parts joinString " + ", (_entry param [10, 0]) toFixed 1]
