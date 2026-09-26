#include "script_component.hpp"

ADDON = false;

PREP_RECOMPILE_START;
#include "XEH_PREP.hpp"
PREP_RECOMPILE_END;

#define ACM_SETTINGS_CATEGORY LLSTRING(Category)

[
    QGVAR(burnsEnabled),
    "CHECKBOX",
    [LLSTRING(SETTING_Enable), LLSTRING(SETTING_Enable_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [true],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(sourcesEnabled),
    "CHECKBOX",
    [LLSTRING(SETTING_Sources), LLSTRING(SETTING_Sources_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [true],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(igniteChanceMul),
    "SLIDER",
    [LLSTRING(SETTING_IgniteChance), LLSTRING(SETTING_IgniteChance_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [0, 3, 1, 1],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(burn3PainlessChance),
    "SLIDER",
    [LLSTRING(SETTING_Burn3Painless), LLSTRING(SETTING_Burn3Painless_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [0, 1, 0.5, 2],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(headBurnAirwayChance),
    "SLIDER",
    [LLSTRING(SETTING_AirwayChance), LLSTRING(SETTING_AirwayChance_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [0, 1, 0.3, 2],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(fieldRecoveryMinutes),
    "SLIDER",
    ["Systemic burn recovery time", "Minutes for capillary-leak, heat-loss and compensatory burn physiology to resolve after the acute phase in normal mode. Burn wounds themselves do not disappear."],
    [ACM_SETTINGS_CATEGORY, "Physiology"],
    [10, 60, 25, 0],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(hardcorePersistentBurns),
    "CHECKBOX",
    ["[HARDCORE] Persistent Major Burns", "Major adult burns can leave a field-unresolved systemic burden. The casualty can be stabilized, but a residual preload/thermal burden and evacuation requirement remain until full heal or definitive care."],
    [ACM_SETTINGS_CATEGORY, "Hardcore"],
    [false],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(hardcoreEvacBurden),
    "SLIDER",
    ["[HARDCORE] Major burn threshold", "Weighted whole-body burn burden that latches the persistent major-burn state. This is a gameplay severity fraction, not a bedside TBSA calculator."],
    [ACM_SETTINGS_CATEGORY, "Hardcore"],
    [0.25, 0.75, 0.40, 2],
    true
] call CBA_fnc_addSetting;

ADDON = true;
