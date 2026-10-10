#include "../main/script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("breathing");
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {
            "ACM_ChestSeal",
            "ACM_PulseOximeter",
            "ACM_Stethoscope",
            "ACM_NCDKit",
            "ACM_ChestTubeKit",
            "ACM_ThoracostomyKit",
            "ACM_PocketBVM",
            "ACM_BVM"
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
#include "CfgMagazines.hpp"
#include "CfgWeapons.hpp"
#include "CfgSounds.hpp"
#include "ACE_Medical_Treatment_Actions.hpp"

class RscText;
class RscLine;
class RscStructuredText;
class RscButtonMenu;
class RscButton;
class RscPicture;

#include "\x\ACM\addons\core\UI_defines.hpp"
#include "Stethoscope_Dialog.hpp"
#include "RscUseBVM.hpp"
