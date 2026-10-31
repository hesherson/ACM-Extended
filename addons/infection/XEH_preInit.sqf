#include "script_component.hpp"

ADDON = false;

PREP_RECOMPILE_START;
#include "XEH_PREP.hpp"
PREP_RECOMPILE_END;

#define ACM_SETTINGS_CATEGORY LLSTRING(Category)

// Basic

[
    QGVAR(infectionEnabled),
    "CHECKBOX",
    [LLSTRING(SETTING_Enable), LLSTRING(SETTING_Enable_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [true],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(infectionStageTime),
    "SLIDER",
    [LLSTRING(SETTING_StageTime), LLSTRING(SETTING_StageTime_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [5, 60, 30, 0],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(infectionRiskMultiplier),
    "SLIDER",
    [LLSTRING(SETTING_RiskMultiplier), LLSTRING(SETTING_RiskMultiplier_Desc)],
    [ACM_SETTINGS_CATEGORY, ""],
    [0.1, 3, 1, 1],
    true
] call CBA_fnc_addSetting;
[
    QGVAR(hardcoreSepsisEvacMinutes),
    "SLIDER",
    ["[HARDCORE] Sepsis evacuation threshold", "Minutes continuously in septic shock before persistent organ dysfunction is latched. Has no effect unless Persistent Sepsis is enabled."],
    [ACM_SETTINGS_CATEGORY, "Hardcore"],
    [5, 30, 10, 0],
    true
] call CBA_fnc_addSetting;

[
    QGVAR(feverWarmPerMin),
    "SLIDER",
    ["Fever rise rate", "Maximum core-temperature rise in degrees C per minute from infection thermogenesis. Shock can blunt this response; hemorrhage and burn cooling still compete with it."],
    [ACM_SETTINGS_CATEGORY, "Physiology"],
    [0.05, 0.40, 0.18, 2],
    true
] call CBA_fnc_addSetting;

ADDON = true;
