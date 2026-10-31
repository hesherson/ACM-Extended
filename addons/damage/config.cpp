#include "../main/script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("damage");
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {
            "ACM_PressureBandage",
            "ACM_EmergencyTraumaDressing",
            "ACM_ElasticWrap"
        };
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "cba_main",
            "ace_main",
            "ace_medical_treatment"
        };
        author = AUTHOR;
        VERSION_CONFIG;
    };
};

#include "ACE_Medical_Injuries.hpp"
#include "CfgEventHandlers.hpp"
#include "CfgWeapons.hpp"
