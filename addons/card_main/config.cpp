#include "../main/script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class DD1380_main {
        ACME_BUILD_CONFIG("card_main");
        author = "Lynx";
        name = "DD1380 - Main";
        requiredVersion = 2.20;
        requiredAddons[] = {"ACM_main", "cba_main", "ace_common"};
        units[] = {};
        weapons[] = {};
        VERSION_CONFIG;
    };
};
#include "CfgFontFamilies.hpp"
#include "CfgEventHandlers.hpp"
