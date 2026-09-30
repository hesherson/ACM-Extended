#include "../main/script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("circulation");
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {
            "ACM_AED",
            "ACM_PressureCuff",
            "ACM_IV_16g",
            "ACM_IV_14g",
            "ACM_IO_FAST",
            "ACM_IO_EZ",
            "ACM_Syringe_10",
            "ACM_Syringe_5",
            "ACM_Syringe_3",
            "ACM_Syringe_1",
            "ACM_Vial_Epinephrine",
            "ACM_Vial_Adenosine",
            "ACM_Vial_Morphine",
            "ACM_Vial_Ketamine",
            "ACM_Vial_Lidocaine",
            "ACM_Vial_TXA",
            "ACM_Vial_Amiodarone",
            "ACM_Vial_Atropine",
            "ACM_Vial_Fentanyl",
            "ACM_Vial_Ondansetron",
            "ACM_Vial_CalciumChloride",
            "ACM_Vial_Ertapenem",
            "ACM_Vial_Esmolol",
            "ACM_Spray_Naloxone",
            "ACM_Lozenge_Fentanyl",
            "ACM_FieldBloodTransfusionKit_500",
            "ACM_FieldBloodTransfusionKit_250",
            "ACM_BloodBag_O_1000",
            "ACM_BloodBag_ON_1000",
            "ACM_BloodBag_A_1000",
            "ACM_BloodBag_AN_1000",
            "ACM_BloodBag_B_1000",
            "ACM_BloodBag_BN_1000",
            "ACM_BloodBag_AB_1000",
            "ACM_BloodBag_ABN_1000",
            "ACM_BloodBag_O_500",
            "ACM_BloodBag_ON_500",
            "ACM_BloodBag_A_500",
            "ACM_BloodBag_AN_500",
            "ACM_BloodBag_B_500",
            "ACM_BloodBag_BN_500",
            "ACM_BloodBag_AB_500",
            "ACM_BloodBag_ABN_500",
            "ACM_BloodBag_O_250",
            "ACM_BloodBag_ON_250",
            "ACM_BloodBag_A_250",
            "ACM_BloodBag_AN_250",
            "ACM_BloodBag_B_250",
            "ACM_BloodBag_BN_250",
            "ACM_BloodBag_AB_250",
            "ACM_BloodBag_ABN_250"
        };
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "cba_main",
            "ace_main",
            "ace_medical_treatment",
            "ACM_core"
        };
        author = AUTHOR;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"
#include "CfgMagazines.hpp"
#include "CfgMoves.hpp"
#include "CfgWeapons.hpp"
#include "ACE_Medical_Treatment_Actions.hpp"

class RscText;
class RscLine;
class RscStructuredText;
class RscButton;
class RscButtonMenu;
class RscPicture;
class RscPictureKeepAspect;
class RscListBox;

#include "\x\ACM\addons\core\UI_defines.hpp"
#include "Defibrillator_Monitor_Dialog.hpp"
#include "RscFeelPulse.hpp"
#include "MeasureBP_Dialog.hpp"
#include "SyringeDraw_Dialog.hpp"
#include "TransfusionMenu_Dialog.hpp"
