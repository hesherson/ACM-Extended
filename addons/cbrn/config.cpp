#include "../main/script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("cbrn");
        name = COMPONENT_NAME;
        units[] = {
            "ACM_HazardObject",
            QGVAR(moduleCreateHazardZone),
            QGVAR(moduleCreateChemicalDevice),
            QGVAR(Eden_HazardZone),
            QGVAR(Eden_ChemicalDevice)
        };
        weapons[] = {
            "ACM_GasMaskFilter",
            "ACM_Autoinjector_ATNA",
            "ACM_Autoinjector_Midazolam"
        };
        magazines[] = {
            "ACM_Mortar_Shell_8Rnd_CS",
            "ACM_Mortar_Shell_8Rnd_Chlorine"
        };
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

#include "CfgSounds.hpp"
#include "CfgCloudlets.hpp"
#include "CfgAmmo.hpp"
#include "CfgWeapons.hpp"
#include "CfgMagazines.hpp"
#include "CfgMagazineWells.hpp"
#include "CfgVehicles.hpp"
#include "CfgFactionClasses.hpp"
#include "CfgEventHandlers.hpp"
#include "ACM_CBRN_Hazards.hpp"
#include "RscAttributes.hpp"
