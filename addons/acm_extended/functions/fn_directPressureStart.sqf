// Direct Pressure entry. Every body region now uses the same non-blocking persistent hold model.
// The clinical pressure state remains active while ordinary medical work is performed, but real ACM maneuvers
// temporarily suspend it and movement yields the provider pose. The same action can then release the hold.
params ["_medic", "_patient", ["_bodyPart", ""]];
_bodyPart = toLower _bodyPart;
if (isNull _medic || {isNull _patient}) exitWith {};

// Every region needs this provider's hands. Reject before cleanup can touch the
// input hints or animation of BVM or another continuous maneuver.
if (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]) exitWith {
    ["Another active maneuver is already in progress.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

if (_medic getVariable ["ACME_DP_Active", false]) exitWith {
    ["You're already holding direct pressure.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

// Clear any stale PFH/key/patient markers left by an interrupted prior hold before starting a new one.
[true, _medic] call ACME_fnc_directPressureStop;

// This synchronized marker is read by bleeding systems on the casualty owner. It is temporarily cleared by the
// tick whenever movement or another maneuver means the provider is no longer physically maintaining pressure.
_patient setVariable [format ["ACME_DP_press_%1", _bodyPart], _medic, true];

if (_bodyPart == "body") then {
    [_medic, _patient, _bodyPart] call ACME_fnc_directPressureTorso;
} else {
    if (_patient isEqualTo _medic) then {
        [_medic, _patient, _bodyPart] call ACME_fnc_directPressureSelf;
    } else {
        [_medic, _patient, _bodyPart] call ACME_fnc_directPressureLimb;
    };
};

if (_bodyPart in ["leftarm", "rightarm", "leftleg", "rightleg"]) then {
    ["ACME_DP_recalcBleed", [_patient], _patient] call CBA_fnc_targetEvent;
};
