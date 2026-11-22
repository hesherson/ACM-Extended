#include "script_component.hpp"
#include "..\main\script_build.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        requiredVersion = REQUIRED_VERSION;
        units[] = {};
        weapons[] = {
            "ACME_EyeCover_Right",
            "ACME_EyeCover_Left",
            "ACME_EyeCover"
        };
        magazines[] = {
            "ACME_Eyewasher"
        };
        requiredAddons[] = {
            "cba_main",
            "ace_main",
            "ace_goggles",
            "ace_medical_gui",
            "ace_medical_treatment",
            "cba_settings",
            "ACM_main",
            "ACM_core",
            "ACM_gui",
            "ACM_cbrn",
            "ACM_Extended"
        };
        author = AUTHOR;
        authors[] = {"Katalam", "MiszczuZPolski", "Mazinski", "Inferno"};
        VERSION_CONFIG;
        ACME_BUILD_CONFIG("ophthalmology");
    };
};

#include "CfgEventHandlers.hpp"
#include "CfgWeapons.hpp"
#include "CfgMagazines.hpp"
#include "CfgVehicles.hpp"
#include "ACE_Medical_Treatment_Actions.hpp"
#include "RscTitles.hpp"
