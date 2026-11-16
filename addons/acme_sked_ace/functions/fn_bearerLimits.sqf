// [minimum to lift, maximum handle claims] for a deployed litter.
params ["_litter"];
if (getNumber (configOf _litter >> "acmeLitterExtraCrew") > 0) exitWith {[3, 4]};
[((missionNamespace getVariable ["acme_sked_bearersRequired", 2]) max 1) min 2, 2]
