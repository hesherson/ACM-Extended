// SKED litter settings (CBA, server wide).
[
    "acme_sked_bearersRequired", "SLIDER",
    ["Rescuers to lift", "How many rescuers must hold a handle before the SKED can be lifted and carried."],
    ["ACM Extended", "SKED"], [1, 2, 2, 0], 1
] call CBA_fnc_addSetting;
[
    "acme_sked_allowConscious", "CHECKBOX",
    ["Strap in conscious casualties", "Off: only unconscious or dead casualties can be strapped into a SKED."],
    ["ACM Extended", "SKED"], false, 1
] call CBA_fnc_addSetting;
[
    "acme_sked_patientAnim", "EDITBOX",
    ["Casualty pose", "Animation a strapped casualty is held in (lying on the back, arms at the sides)."],
    ["ACM Extended", "SKED"], "unconsciousfaceup", 1
] call CBA_fnc_addSetting;
[
    "acme_sked_liftHeight", "SLIDER",
    ["Carry height (m)", "Height of the SKED above the ground while a team carries it."],
    ["ACM Extended", "SKED"], [0.3, 1.0, 0.55, 2], 1
] call CBA_fnc_addSetting;
[
    "acme_sked_hpmkSqueeze", "CHECKBOX",
    ["Squeeze the HPMK-I shell", "A casualty in the HPMK-I gets the squeezed shell while strapped into a SKED."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
// Calibration: move the casualty in the SKED (SKED axes: X right, Y toward the head, Z up), metres.
{
    [
        format ["acme_sked_offset%1", _x], "SLIDER",
        [format ["Casualty offset %1 (m)", _x], "Fine adjustment of where the casualty lies in the SKED."],
        ["ACM Extended", "SKED"], [-0.3, 0.3, 0, 3], 1
    ] call CBA_fnc_addSetting;
} forEach ["X", "Y", "Z"];
// The carry bag shown slung from the shoulder of whoever has a SKED in their inventory (fn_slungUpdate.sqf).
[
    "acme_sked_slungShow", "CHECKBOX",
    ["Show the slung bag", "Whoever carries a SKED in their inventory wears its bag slung from the right shoulder."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_sked_slungRange", "SLIDER",
    ["Slung bag range (m)", "The slung bag is shown on units within this distance of the camera."],
    ["ACM Extended", "SKED"], [50, 1000, 300, 0], 1
] call CBA_fnc_addSetting;
{
    [
        format ["acme_sked_slung%1", _x], "SLIDER",
        [format ["Slung bag offset %1 (m)", _x], "Fine adjustment of where the bag hangs (X right, Y forward, Z up)."],
        ["ACM Extended", "SKED"], [-0.3, 0.3, 0, 3], 1
    ] call CBA_fnc_addSetting;
} forEach ["X", "Y", "Z"];

[
    "acme_sked_debug", "CHECKBOX",
    ["Medical transport diagnostics", "Log transport handoffs to RPT and show the read-only audit in ACE Self Interaction."],
    ["ACM Extended", "SKED"], false, 1
] call CBA_fnc_addSetting;
