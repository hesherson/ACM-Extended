#include "..\main\script_build.hpp"
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        ACME_BUILD_CONFIG("circulation");
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {
            "ACME_AED",
            "ACME_PressureCuff",
            "ACME_IV_16g",
            "ACME_IV_14g",
            "ACME_IO_FAST",
            "ACME_IO_EZ",
            "ACME_Syringe_10",
            "ACME_Syringe_5",
            "ACME_Syringe_3",
            "ACME_Syringe_1",
            "ACME_Vial_Epinephrine",
            "ACME_Vial_Adenosine",
            "ACME_Vial_Morphine",
            "ACME_Vial_Ketamine",
            "ACME_Vial_Lidocaine",
            "ACME_Vial_TXA",
            "ACME_Vial_Amiodarone",
            "ACME_Vial_Atropine",
            "ACME_Vial_Fentanyl",
            "ACME_Vial_Ondansetron",
            "ACME_Vial_CalciumChloride",
            "ACME_Vial_Ertapenem",
            "ACME_Vial_Esmolol",
            "ACME_Spray_Naloxone",
            "ACME_Lozenge_Fentanyl",
            "ACME_FieldBloodTransfusionKit_500",
            "ACME_FieldBloodTransfusionKit_250",
            "ACME_BloodBag_O_1000",
            "ACME_BloodBag_ON_1000",
            "ACME_BloodBag_A_1000",
            "ACME_BloodBag_AN_1000",
            "ACME_BloodBag_B_1000",
            "ACME_BloodBag_BN_1000",
            "ACME_BloodBag_AB_1000",
            "ACME_BloodBag_ABN_1000",
            "ACME_BloodBag_O_500",
            "ACME_BloodBag_ON_500",
            "ACME_BloodBag_A_500",
            "ACME_BloodBag_AN_500",
            "ACME_BloodBag_B_500",
            "ACME_BloodBag_BN_500",
            "ACME_BloodBag_AB_500",
            "ACME_BloodBag_ABN_500",
            "ACME_BloodBag_O_250",
            "ACME_BloodBag_ON_250",
            "ACME_BloodBag_A_250",
            "ACME_BloodBag_AN_250",
            "ACME_BloodBag_B_250",
            "ACME_BloodBag_BN_250",
            "ACME_BloodBag_AB_250",
            "ACME_BloodBag_ABN_250"
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
