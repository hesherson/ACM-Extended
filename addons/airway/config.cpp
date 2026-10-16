#include "../main/script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("airway");
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {
            "ACM_OPA",
            "ACM_IGel",
            "ACM_NPA",
            "ACM_SuctionBag",
            "ACM_ACCUVAC",
            "ACM_CricKit"
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
#include "CfgMoves.hpp"
#include "CfgWeapons.hpp"
#include "ACE_Medical_Treatment_Actions.hpp"

class RscText;
class RscPicture;
class RscButton;
class RscButtonMenu;
class RscControlsGroupNoScrollbars;

#include "\x\ACM\addons\core\UI_defines.hpp"
#include "RscHeadTilt.hpp"
#include "SurgicalAirway_Dialog.hpp"
