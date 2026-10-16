#include "../main/script_build.hpp"
// Late-loaded, low-risk config corrections owned by ACM Extended.
// Requiring ACM_Extended guarantees the base item and treatment-action classes already exist before these patches.
class CfgPatches {
    class ACM_itemtext {
        ACME_BUILD_CONFIG("itemtext");
        version = "1.2.4.1";
        name = "ACM Extended Late Config Patches";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.18;
        requiredAddons[] = {"ACM_Extended"};
        author = "mavis";
    };
};

// Direct Pressure owns its provider pose in the ACME runtime. Do not let the CheckPulse parent inject an ACE
// treatment animation first, because that inherited animation can perform a weapon draw/holster transition before
// callbackSuccess starts ACME_DirectPressureHold. Emptying all four animation properties makes the button go
// directly from the current provider state into the ACME-owned hold without a scripted weapon-selection prelude.
class ace_medical_treatment_actions {
    class ACME_DirectPressure {
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
    };
};
