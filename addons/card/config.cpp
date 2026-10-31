#include "../main/script_build.hpp"
#include "script_component.hpp"

// Lynx's DD1380 classes and virtual paths remain compatible with existing cards.
class CfgPatches {
    class DD1380_card {
        ACME_BUILD_CONFIG("card");
        author = "Lynx";
        name = "DD1380 - Card";
        requiredVersion = 2.20;
        requiredAddons[] = {"DD1380_main", "ACM_gui", "ACM_Extended", "ace_medical_treatment", "ace_dogtags"};
        units[] = {};
        weapons[] = {};
        VERSION_CONFIG;
    };
};
#include "CfgEventHandlers.hpp"
#include "ACE_Medical_Treatment_Actions.hpp"
#include "ui/DD1380_dlg.hpp"
