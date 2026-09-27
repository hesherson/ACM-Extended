class CfgVehicles {
    class B_Survivor_F;
    // Engine initial loadout: both patient spawners create this class directly.
    // A scripted addVest after createUnit leaves an observable unarmored interval.
    class GVAR(TrainingPatient): B_Survivor_F {
        scope = 1;
        scopeCurator = 0;
        scopeArsenal = 0;
        linkedItems[] = {"V_PlateCarrier1_rgr"};
        respawnLinkedItems[] = {"V_PlateCarrier1_rgr"};
    };

    class Logic;
    class Module_F: Logic {
        class AttributesBase {
            class Default;
            class Combo;
            class Edit;
            class Checkbox;
            class ModuleDescription;
        };
    };

    class GVAR(Eden_FullHealFacility): Module_F {
        scope = 2;
        displayName = CSTRING(FullHealFacility_Module);
        icon = QPATHTOF(ui\Icon_Module_FullHealFacility_ca.paa);
        portrait = QPATHTOF(ui\Icon_Module_FullHealFacility_ca.paa);
        category = QGVAR(Category_Mission);
        function = QFUNC(moduleInitFullHealFacility_Eden);
        functionPriority = 1;
        isGlobal = 1;
        isTriggerActivated = 0;
        author = AUTHOR;
        class Attributes: AttributesBase {
            class InteractionDistance: Edit {
                property = QGVAR(Eden_FullHealFacility_InteractionDistance);
                displayName = ECSTRING(core,Common_Module_InteractionDistance);
                typeName = "NUMBER";
                defaultValue = 5;
            };
            class InteractionPosition: Edit {
                property = QGVAR(Eden_FullHealFacility_InteractionPosition);
                displayName = ECSTRING(core,Common_Module_InteractionPosition);
                tooltip = ECSTRING(core,Common_Module_InteractionPosition_Tooltip);
                typeName = "STRING";
                defaultValue = "[0,0,0]";
            };
        };
    };

    class GVAR(Eden_ElevationOverride): Module_F {
        scope = 2;
        displayName = "ACME Elevation Override";
        category = QGVAR(Category_Mission);
        function = QFUNC(moduleInitElevationOverride_Eden);
        functionPriority = 1;
        isGlobal = 1;
        isTriggerActivated = 0;
        isDisposable = 0;
        author = AUTHOR;

        class Attributes: AttributesBase {
            class DetectedBaseElevation: Edit {
                property = QGVAR(Eden_ElevationOverride_DetectedBaseElevation);
                displayName = "Detected ACE Base Elevation (m)";
                tooltip = "Informational. Prefilled from ACE's resolved map altitude when available, otherwise the terrain elevationOffset. The runtime report shows the value ACME actually replaced.";
                typeName = "NUMBER";
                defaultValue = "missionNamespace getVariable ['ace_common_mapAltitude', getNumber (configFile >> 'CfgWorlds' >> worldName >> 'elevationOffset')]";
            };

            class Mode: Combo {
                property = QGVAR(Eden_ElevationOverride_Mode);
                displayName = "Override Mode";
                tooltip = "Calibration is recommended: place this module at a location with a known real elevation and enter that elevation below. Manual mode sets ACE's base map elevation directly.";
                typeName = "NUMBER";
                defaultValue = 0;
                class values {
                    class CalibrateAtModule {
                        name = "Calibrate at module position (recommended)";
                        value = 0;
                    };
                    class ManualBase {
                        name = "Set ACE base elevation manually";
                        value = 1;
                    };
                };
            };

            class ElevationUnits: Combo {
                property = QGVAR(Eden_ElevationOverride_Units);
                displayName = "Elevation Units";
                tooltip = "Units used by Desired Elevation below.";
                typeName = "NUMBER";
                defaultValue = 1;
                class values {
                    class Meters {
                        name = "Meters";
                        value = 0;
                    };
                    class Feet {
                        name = "Feet";
                        value = 1;
                    };
                };
            };

            class DesiredElevation: Edit {
                property = QGVAR(Eden_ElevationOverride_DesiredElevation);
                displayName = "Desired Elevation";
                tooltip = "Calibration mode: the real elevation at this module's position. Manual mode: the desired ACE map base elevation. Relative hills and valleys are preserved.";
                typeName = "NUMBER";
                defaultValue = 0;
            };

            class ShowStartupReport: Checkbox {
                property = QGVAR(Eden_ElevationOverride_ShowStartupReport);
                displayName = "Show Startup Report";
                tooltip = "Shows the original ACE base, corrected base, and effective elevation at this module once when the mission starts. The same information is always written to the RPT.";
                typeName = "BOOL";
                defaultValue = 1;
            };
        };
    };
};
