class CfgFunctions {
    class overwrite_medical_gui {
        tag = "ace_medical_gui";
        class ace_medical_gui {
            class collectActions {
                file = QPATHTOF(overrides\fnc_collectActions.sqf); //ace/addons/medical_gui/functions/fnc_collectActions.sqf
            };
            class canOpenMenu {
                file = QPATHTOF(overrides\fnc_canOpenMenu.sqf); //ace/addons/medical_gui/functions/fnc_canOpenMenu.sqf
            };
            class onMenuOpen {
                file = QPATHTOF(overrides\fnc_onMenuOpen.sqf); //ace/addons/medical_gui/functions/fnc_onMenuOpen.sqf
            };
            class onMenuClose {
                file = QPATHTOF(overrides\fnc_onMenuClose.sqf); //ace/addons/medical_gui/functions/fnc_onMenuClose.sqf
            };
            class updateActions {
                file = QPATHTOF(overrides\fnc_updateActions.sqf); //ace/addons/medical_gui/functions/fnc_updateActions.sqf
            };
            class updateBodyImage {
                file = QPATHTOF(overrides\fnc_updateBodyImage.sqf); //ace/addons/medical_gui/functions/fnc_updateBodyImage.sqf
            };
            class updateInjuryList {
                file = QPATHTOF(overrides\fnc_updateInjuryList.sqf); //ace/addons/medical_gui/functions/fnc_updateInjuryList.sqf
            };
        };
    };
};
