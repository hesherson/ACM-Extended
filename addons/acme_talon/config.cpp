#include "..\main\script_build.hpp"

class CfgPatches {
    class acme_talon {
        ACME_BUILD_CONFIG("acme_talon");
        name = "ACM Extended Talon II models";
        author = "mavis";
        requiredVersion = 2.10;
        requiredAddons[] = {"A3_Data_F"};
        units[] = {};
        weapons[] = {};
    };
};
