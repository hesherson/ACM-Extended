// over-resuscitation crackle rate split, used by the stethoscope override. heavy edema gives fast crackles and
// milder edema gives normal crackles, so both crackle variants have a real trigger.
ACME_edema_crackleFastVol = 1.0;  // the ACM Overload_Volume at or above which the crackles read Fast. it was bumped from 0.5 to 1.0 to
                                            // track the gentler curve, at the same severity point near 0.5, so "Fast" still means moderate to severe edema
                                            // rather than firing at what is now only mild overload.

// direct pressure over a fractured limb. it is a severe pain stimulus, and it wakes the patient from a light
// ko or obtundation only.
ACME_DP_fracturePainEnabled = true;
ACME_DP_fracturePainAmount = 1.0;
ACME_DP_fracturePainCooldown = 8;
ACME_DP_fractureWakeMinSpO2 = 85;
ACME_DP_fractureWakeMinMAP = 60;
ACME_DP_fractureWakeGrace = 8;

// direct-pressure free-movement pose tuning, for the limb and the head.
ACME_DP_idleToPose = 0.8;  // idle seconds before adopting the holding pose
ACME_DP_lookDot    = 0.4;  // minimum horizontal facing dot toward the patient to hold the pose, about a 66 deg cone.
// B128: give every other-casualty Direct Pressure hold one additional metre of working leash. Movement input
// still releases the hold immediately; this distance is only for leaning/repositioning around a stationary casualty.
ACME_DP_leashDist = 2.7;
ACME_DP_torsoLeashDist = 3.2;
ACME_DP_treatTimeMult = 1.6;  // while a medic holds limb, head or self direct pressure, every timed action takes this much longer, because one hand is occupied.
ACME_DP_limbBleedMult = 0.72;  // normal: modest immediate reduction of ordinary external limb bleeding while pressure is physically maintained.
ACME_DP_limbBleedMultHardcore = 0.80;  // hardcore: still improved, but less forgiving than normal. Head/torso are never multiplied.

// Recalculate ACE/ACM wound bleeding on the casualty owner whenever limb pressure begins, yields, resumes or ends.
// This keeps the limb-only multiplier immediate in multiplayer instead of waiting for the next bandage/clot update.
if (isNil "ACME_DP_BleedRecalcEH") then {
    ACME_DP_BleedRecalcEH = ["ACME_DP_recalcBleed", {
        params ["_patient"];
        if (!isNull _patient && {local _patient}) then {
            [_patient] call ace_medical_status_fnc_updateWoundBloodLoss;
        };
    }] call CBA_fnc_addEventHandler;
};

// Dedicated-server cleanup for providers that vanish before their local DP PFH can run teardown. The casualty
// owner clears only this provider's exact marker, so disconnect/death cannot erase a replacement hold.
if (isServer && {isNil "ACME_DP_ServerCleanupInstalled"}) then {
    ACME_DP_ServerCleanupInstalled = true;
    ACME_DP_ServerReleaseProvider = {
        params ["_unit"];
        if (isNull _unit) exitWith {};
        private _patient = _unit getVariable ["ACME_DP_Patient", objNull];
        private _part = _unit getVariable ["ACME_DP_Part", ""];
        private _token = _unit getVariable ["ACME_DP_ClaimToken", ""];
        private _epoch = _unit getVariable ["ACME_DP_ClaimEpoch", -1];
        if (!isNull _patient && {_part != ""}) then {
            if (_token != "") then {
                [_patient, "directPressureClaim", ["release", [_unit, _part, _token, _epoch, owner _unit]]] call ACME_fnc_ownerDispatch;
            } else {
                [_patient, "directPressureMarker", [_unit, _part, false]] call ACME_fnc_ownerDispatch;
            };
        };
        _unit setVariable ["ACME_DP_Active", false, true];
        _unit setVariable ["ACME_DP_Patient", objNull, true];
        _unit setVariable ["ACME_DP_ClaimToken", "", true];
        _unit setVariable ["ACME_DP_ClaimEpoch", -1, true];
    };
    addMissionEventHandler ["HandleDisconnect", {
        params ["_unit"];
        [_unit] call ACME_DP_ServerReleaseProvider;
        false
    }];
    addMissionEventHandler ["EntityKilled", {
        params ["_unit"];
        [_unit] call ACME_DP_ServerReleaseProvider;
    }];
};
