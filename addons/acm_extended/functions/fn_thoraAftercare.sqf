/* Callback-time check; disabling new incisions never disables existing aftercare. */
params ["_medic", "_patient", "_operation", ["_device", 1]];
if (isNull _patient || {!([_medic, "thoracostomy", true] call ACME_fnc_procedureAllowed)}) exitWith {};
switch (_operation) do {
    case "drain": {
        if !(_device in [0, 1]) exitWith {};
        if (_device == 0) then {
            private _used = [_medic, _patient, ["ACM_SuctionBag"]] call ace_medical_treatment_fnc_useItem;
            if ((_used param [1, ""]) != "ACM_SuctionBag") then {_device = -1;};
        } else {
            if (([_medic,_patient,"ACM_ACCUVAC"] call ACME_fnc_treatmentSupplyCount)<1) then {_device = -1;};
        };
        if (_device < 0) exitWith {};
        [_medic, _patient, _device] call ACM_breathing_fnc_Thoracostomy_drain;
    };
    case "reseal": {[_medic, _patient] call ACM_breathing_fnc_Thoracostomy_resealChestTube;};
    case "close": {
        if ((_patient getVariable ["ACME_thora_tube_left", false])
            || {_patient getVariable ["ACME_thora_tube_right", false]}) exitWith {};
        if (([_medic, _patient, ["ACE_surgicalKit"]] call ace_medical_treatment_fnc_hasItem)
            || {_patient getVariable ["ACM_breathing_Thoracostomy_UsedKit", false]}) then {
            [_medic, _patient] call ACM_breathing_fnc_Thoracostomy_close;
        };
    };
};
