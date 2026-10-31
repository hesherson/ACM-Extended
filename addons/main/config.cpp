#include "script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("main");
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "cba_main",
            "ace_main"
        };
        author = AUTHOR;
		url="https://discord.gg/5MNPpBpsEr/";
        VERSION_CONFIG;
    };
};

#include "CfgSettings.hpp"
