#include "..\main\script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("zeus");
        name = COMPONENT_NAME;
        units[] = {
            "ACME_ModuleForceWakeUp",
            "ACME_ModuleInflictCardiacArrest",
            "ACME_ModuleInflictChestInjury",
            "ACME_ModuleSetBloodVolume",
            "ACME_ModuleUnCardiacArrest",
            "ACME_ModuleGivePain",
            "ACME_ModuleSetOxygen",
            "ACME_ModuleSetBloodType",
            "ACME_ModuleTogglePlotArmor",
            "ACME_ModuleAssignFullHealFacility"
        };
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "cba_main",
            "ace_main",
            "ace_medical_treatment",
            "ACM_main"
        };
        author = AUTHOR;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"
#include "CfgFactionClasses.hpp"
#include "CfgVehicles.hpp"
#include "RscAttributes.hpp"
