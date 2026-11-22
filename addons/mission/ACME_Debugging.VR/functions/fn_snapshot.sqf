params ["_caller"];
private _subjects = missionNamespace getVariable ["ACMEQA_patients", []];
private _live = allPlayers select {_x getVariable ["ACMEQA_patientRole", ""] == "player"};
_subjects = _subjects + (_live apply {["player", _x]});
private _patientRows = _subjects apply {
    _x params ["_role", "_patient"];
    [_role, alive _patient, _patient getVariable ["ACE_isUnconscious", false], animationState _patient,
        local _patient, getPosATL _patient, typeOf (objectParent _patient), typeOf (attachedTo _patient),
        typeOf (_patient getVariable ["acme_sked_litter", objNull]), _patient getVariable ["acme_sked_stowed", false],
        _patient getVariable ["ACME_hpmk_state", ""], _patient getVariable ["ACME_headElevated", false],
        !isNull (_patient getVariable ["ACME_headElev_propObj", objNull]), vest _patient]
};
private _chest = (missionNamespace getVariable ["ACMEQA_chests", []]) apply {
    [typeOf _x, _x getVariable ["ACME_medicalChestState", []],
        _x getVariable ["ACME_medicalChestDrawerFraction", -1], count (_x getVariable ["ACME_medicalChestViewers", []])]
};
[[animationState _caller, getPosATL _caller, typeOf (attachedTo _caller),
    typeOf (_caller getVariable ["acme_sked_bearing", objNull])], _patientRows, _chest]
