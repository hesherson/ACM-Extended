#include "../main/script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("disability");
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {
            "ACM_SAMSplint"
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

#include "CfgEventHandlers.hpp"
#include "CfgWeapons.hpp"
