// Enable Dust Injury
[
    QGVAR(enable),
    "CHECKBOX",
    LLSTRING(setting_enable),
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_injury)],
    [false],
    true
] call CBA_fnc_addSetting;

// Count goggles-named eyewear (no ACE_Resistance) as full eye protection
[
    QGVAR(goggles_name_fallback),
    "CHECKBOX",
    LLSTRING(setting_goggles_name_fallback),
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_injury)],
    [true],
    true
] call CBA_fnc_addSetting;

// Probability to get dust in the eyes
[
    QGVAR(probability_dust),
    "SLIDER",
    [LLSTRING(setting_probability_dust)],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_injury)],
    [1, 100, 5, 0],
    true
] call CBA_fnc_addSetting;

// Probability to get dust in the eyes which is not treated by blink
[
    QGVAR(probability_dust_heavy),
    "SLIDER",
    [LLSTRING(setting_probability_dust_heavy)],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_injury)],
    [1, 100, 1, 0],
    true
] call CBA_fnc_addSetting;

// Probability to treat the dust in the eyes with blinking
[
    QGVAR(probability_treatment_dust),
    "SLIDER",
    [LLSTRING(setting_probability_treatment_dust)],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_injury)],
    [1, 100, 20, 0],
    true
] call CBA_fnc_addSetting;

// Eye Wash treatment time
[
    QGVAR(eyewash_treatment_time),
    "SLIDER",
    [LLSTRING(setting_eyewash_treatment_time)],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_manual_blink)],
    [1, 10, 2, 0],
    true
] call CBA_fnc_addSetting;

// Eye Wash medic required
[
    QGVAR(eyewash_medic_required),
    "LIST",
    [LLSTRING(setting_eyewash_medic_required)],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_manual_blink)],
    [[0, 1, 2], ["STR_ACE_Medical_Treatment_Anyone", "STR_ACE_Medical_Treatment_Medics", "STR_ACE_Medical_Treatment_Doctors"], 0],
    true
] call CBA_fnc_addSetting;

// Eye Shield treatment time
[
    QGVAR(eyeshield_treatment_time),
    "SLIDER",
    [LLSTRING(setting_eyeShield_treatment_time)],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_manual_blink)],
    [1, 10, 2, 0],
    true
] call CBA_fnc_addSetting;


// Eye Shield medic required
[
    QGVAR(eyeshield_medic_required),
    "LIST",
    [LLSTRING(setting_eyeShield_medic_required)],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_manual_blink)],
    [[0, 1, 2], ["STR_ACE_Medical_Treatment_Anyone", "STR_ACE_Medical_Treatment_Medics", "STR_ACE_Medical_Treatment_Doctors"], 0],
    true
] call CBA_fnc_addSetting;


// ACME 1.3.0 structural ocular-trauma behavior.
// Ordinary mode is game-compressed: structural injury can resolve over a useful mission timescale,
// especially when protected. Hardcore converts structural trauma into a stabilization/evacuation problem.
[
    QGVAR(structuralRecoveryMinutes),
    "SLIDER",
    ["Structural eye recovery time", "Minutes for structural eye trauma to recover in normal mode while protected by an eye shield. Unshielded recovery is slower. Has no field-healing effect when Persistent Ocular Trauma is enabled."],
    [CBA_SETTINGS_CAT, LSTRING(setting_subcategory_injury)],
    [5, 30, 12, 0],
    true
] call CBA_fnc_addSetting;

