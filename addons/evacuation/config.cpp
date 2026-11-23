#include "..\main\script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("evacuation");
        name = COMPONENT_NAME;
        units[] = {
            "ACME_ModuleEvacuationPoint",
            "ACME_ModuleReinforcePoint"
        };
        weapons[] = {};
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
#include "CfgVehicles.hpp"
#include "CfgFactionClasses.hpp"
