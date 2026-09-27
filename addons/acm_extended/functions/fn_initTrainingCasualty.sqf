// Compatibility armor watcher for legacy/external ACM training casualty creation.
// This fork's two patient spawners use a carrier-equipped unit class and mark
// PlateCarrierDone during creation, so this fallback never redresses those patients.
// Only unmarked training-group casualties use the delayed owner-local repair path.
ACME_acmSpawnerPlateCarrierEnabled = missionNamespace getVariable ["ACME_acmSpawnerPlateCarrierEnabled", true];
ACME_acmSpawnerPlateCarrierClass   = missionNamespace getVariable ["ACME_acmSpawnerPlateCarrierClass", "V_PlateCarrier1_rgr"];

// A training casualty spawned by a non-host client can be local to that client even though the
// server owns the training-group watcher. Route armor work to the casualty owner instead of
// silently failing the local-only addVest command.
if (isNil "ACME_acmSpawnerPlateCarrierEventInstalled") then {
    ACME_acmSpawnerPlateCarrierEventInstalled = true;
    ["ACME_acmSpawnerArmorLocal", {
        params [["_patient", objNull, [objNull]]];
        if (!isNull _patient && {local _patient}) then {
            [_patient] call ACME_fnc_acmSpawnerArmor;
        };
    }] call CBA_fnc_addEventHandler;
};

if (isServer && {isNil "ACME_acmSpawnerPlateCarrierPFH"}) then {
    ACME_acmSpawnerPlateCarrierPFH = [{
        if !(missionNamespace getVariable ["ACME_acmSpawnerPlateCarrierEnabled", true]) exitWith {};
        private _grp = missionNamespace getVariable ["ACM_mission_TrainingCasualtyGroup", grpNull];
        if (isNull _grp) exitWith {};
        {
            if !(_x getVariable ["ACME_acmSpawnerPlateCarrierDone", false]) then {
                [_x] call ACME_fnc_acmSpawnerArmor;
            };
        } forEach (units _grp);
    }, 2, []] call CBA_fnc_addPerFrameHandler;
};
