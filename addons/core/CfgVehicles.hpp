#define ADDMAGAZINE(classname,num) \
    class DOUBLES(_xx,classname) { \
        magazine = QUOTE(classname); \
        count = num; \
    }

#define ADDITEM(classname,num) \
    class DOUBLES(_xx,classname) { \
        name = QUOTE(classname); \
        count = num; \
    }

#define ACTION_UNLOADANDCARRY \
    class ACM_Action_UnloadAndCarryPatient { \
        displayName = CSTRING(CarryPatient); \
        condition = QUOTE(alive _target); \
        exceptions[] = {"isNotDragging", "isNotCarrying", "isNotInside"}; \
        statement = ""; \
        insertChildren = QUOTE(call FUNC(addVehicleUnloadCarryPatientActions)); \
        icon = QACEPATHTOF(dragging,ui\icons\person_carry.paa); \
    }

#define ACTION_REFILL_OXYGEN_425 \
    class ACM_Action_Refill_PortableOxygenTank_425 { \
        displayName = ECSTRING(breathing,RefillOxygenTank); \
        condition = QUOTE([ARR_2(_player,_target)] call EFUNC(breathing,canRefillOxygenTank)); \
        exceptions[] = {"isNotInside"}; \
        statement = QUOTE([_player] call EFUNC(breathing,refillOxygenTank)); \
        icon = QPATHTOEF(breathing,ui\icon_oxygentank_ca.paa); \
    }

#define ACTION_PATIENTS \
    class ACM_Action_PatientsList { \
        displayName = CSTRING(VehiclePatients); \
        condition = QUOTE(count (fullCrew [ARR_2(_target,'')]) > 0); \
        exceptions[] = {"isNotInside"}; \
        statement = ""; \
        insertChildren = QUOTE(call FUNC(addVehiclePatientActions)); \
        icon = QPATHTOEF(main,logo_empty.paa); \
    }

class CfgVehicles {
    class ACE_medicalSupplyCrate;
    class ACME_MedicalSupplyCrate_Basic: ACE_medicalSupplyCrate {
        dlc = "ACM_Extended";
        displayName = CSTRING(MedicalSupplyCrate_Basic_Display);
        author = "mavis";
        editorCategory = "EdCat_Supplies";
        editorSubcategory = QGVAR(EditorCategory);
        /*hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {QPATHTOF(data\supplyBox.paa)};*/
        class TransportMagazines {
            ADDMAGAZINE(ACME_Paracetamol,4);
            ADDMAGAZINE(ACME_AmmoniaInhalant,4);
            ADDMAGAZINE(ACME_Inhaler_Penthrox,5);
        };
        class TransportItems {
            // Catastrophic Bleeding
            ADDITEM(ACME_PressureBandage,50);
            ADDITEM(ACME_EmergencyTraumaDressing,20);
            ADDITEM(ACME_ElasticWrap,40);
            ADDITEM(ACE_tourniquet,24);
            // Airway
            ADDITEM(ACME_OPA,10);
            ADDITEM(ACME_NPA,10);
            ADDITEM(ACME_SuctionBag,5);
            // Breathing
            ADDITEM(ACME_ChestSeal,10);
            ADDITEM(ACME_PocketBVM,2);
            ADDITEM(ACME_NCDKit,5);
            // Disability
            ADDITEM(ACE_morphine,10);
            ADDITEM(ACME_SAMSplint,10);
            // Other
            ADDITEM(ACME_Spray_Naloxone,10);
        };
    };
    ACME_ITEM_ALIAS(ACM_MedicalSupplyCrate_Basic,ACME_MedicalSupplyCrate_Basic);
    class ACME_MedicalSupplyCrate_Advanced: ACME_MedicalSupplyCrate_Basic {
        displayName = CSTRING(MedicalSupplyCrate_Advanced_Display);
        class TransportMagazines {
            ADDMAGAZINE(ACME_Paracetamol,8);
            ADDMAGAZINE(ACME_AmmoniaInhalant,8);
            ADDMAGAZINE(ACME_Inhaler_Penthrox,8);
            ADDMAGAZINE(ACME_OxygenTank_425,2);
        };
        class TransportItems {
            // Catastrophic Bleeding
            ADDITEM(ACME_PressureBandage,60);
            ADDITEM(ACME_EmergencyTraumaDressing,30);
            ADDITEM(ACME_ElasticWrap,60);
            ADDITEM(ACE_tourniquet,16);
            // Airway
            ADDITEM(ACME_IGel,20);
            ADDITEM(ACME_ACCUVAC,5);
            ADDITEM(ACME_OPA,10);
            ADDITEM(ACME_NPA,10);
            ADDITEM(ACME_SuctionBag,10);
            ADDITEM(ACME_CricKit,10);
            // Breathing
            ADDITEM(ACME_Stethoscope,4);
            ADDITEM(ACME_ChestSeal,20);
            ADDITEM(ACME_BVM,4);
            ADDITEM(ACME_NCDKit,10);
            ADDITEM(ACME_PulseOximeter,5);
            ADDITEM(ACME_ThoracostomyKit,5);
            ADDITEM(ACME_ChestTubeKit,5);
            // Circulation
            ADDITEM(ACME_AED,3);
            ADDITEM(ACME_PressureCuff,3);
            ADDITEM(ACME_IV_16g,25);
            ADDITEM(ACME_IV_14g,15);
            ADDITEM(ACME_Syringe_1,5);
            ADDITEM(ACME_Syringe_3,5);
            ADDITEM(ACME_Syringe_5,5);
            ADDITEM(ACME_Syringe_10,2);
            ADDITEM(ACME_IO_FAST,15);
            ADDITEM(ACME_IO_EZ,15);
            ADDITEM(ACME_Vial_Epinephrine,10);
            ADDITEM(ACME_Vial_Esmolol,10);
            ADDITEM(ACME_Vial_TXA,10);
            ADDITEM(ACME_Vial_Amiodarone,10);
            ADDITEM(ACME_Vial_Atropine,10);
            ADDITEM(ACME_BloodBag_ON_1000,10);
            ADDITEM(ACME_BloodBag_ON_500,10);
            ADDITEM(ACME_BloodBag_ON_250,10);
            ADDITEM(ACE_plasmaIV,10);
            ADDITEM(ACE_plasmaIV_500,10);
            ADDITEM(ACE_plasmaIV_250,10);
            ADDITEM(ACE_salineIV,10);
            ADDITEM(ACE_salineIV_500,10);
            ADDITEM(ACE_salineIV_250,10);
            ADDITEM(ACME_FieldBloodTransfusionKit_250,5);
            ADDITEM(ACME_FieldBloodTransfusionKit_500,5);
            ADDITEM(ACME_Vial_CalciumChloride,10);
            // Disability
            ADDITEM(ACE_morphine,5);
            ADDITEM(ACME_Vial_Morphine,10);
            ADDITEM(ACME_Vial_Ketamine,10);
            ADDITEM(ACME_Vial_Fentanyl,10);
            ADDITEM(ACME_Vial_Lidocaine,10);
            ADDITEM(ACME_Vial_Ondansetron,10);
            ADDITEM(ACME_Lozenge_Fentanyl,10);
            ADDITEM(ACME_SAMSplint,10);
            // Other
            ADDITEM(ACME_Spray_Naloxone,10);
            ADDITEM(ACE_personalAidKit,1);
            ADDITEM(ACE_surgicalKit,2);
            ADDITEM(ACE_bodyBag,5);
            ADDITEM(ACE_suture,60);
            ADDITEM(ACME_Vial_Ertapenem,10);
        };
    };
    ACME_ITEM_ALIAS(ACM_MedicalSupplyCrate_Advanced,ACME_MedicalSupplyCrate_Advanced);
    class ACME_CBRN_SupplyCrate: ACE_medicalSupplyCrate {
        dlc = "ACM_Extended";
        displayName = ECSTRING(CBRN,SupplyCrate_Display);
        author = "mavis";
        editorCategory = "EdCat_Supplies";
        editorSubcategory = QGVAR(EditorCategory);
        /*hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {QPATHTOF(data\supplyBox.paa)};*/
        class TransportMagazines {};
        class TransportItems {
            // Treatment
            ADDITEM(ACME_Autoinjector_ATNA,30);
            ADDITEM(ACME_Autoinjector_Midazolam,10);
            //ADDITEM(ACME_Ampule_Dimercaprol,10);
            // Other
            ADDITEM(ACME_GasMaskFilter,30);
        };
    };
    ACME_ITEM_ALIAS(ACM_CBRN_SupplyCrate,ACME_CBRN_SupplyCrate);
    class ACME_CBRN_PPE_SupplyCrate: ACME_CBRN_SupplyCrate {
        displayName = ECSTRING(CBRN,SupplyCrate_PPE_Display);
        class TransportItems {
            ADDITEM(U_C_CBRN_Suit_01_Blue_F,10);
            ADDITEM(G_AirPurifyingRespirator_02_black_F,10);
            ADDITEM(ChemicalDetector_01_watch_F,2);
            ADDITEM(ACME_GasMaskFilter,10);
        };
    };
    ACME_ITEM_ALIAS(ACM_CBRN_PPE_SupplyCrate,ACME_CBRN_PPE_SupplyCrate);

    class Man;
    class CAManBase: Man {
        class ACE_Actions {
            class ACE_MainActions {
                class ACM_LyingState_GetUp {
                    displayName = CSTRING(LyingState_GetUp);
                    icon = "";
                    condition = QUOTE(!(isPlayer _target) && {(_target getVariable [ARR_2(QQGVAR(Lying_State),false)]) && alive _target && !(_target getVariable [ARR_2('ACE_isUnconscious',false)]) && !(_target getVariable [ARR_2(QQEGVAR(evacuation,casualtyTicketClaimed),false)])});
                    statement = QUOTE([_target] call FUNC(getUp));
                    exceptions[] = {"isNotInside"};
                    showDisabled = 0;
                };
            };
        };
        class ACE_SelfActions {
            class ACM_Action_GetUp {
                displayName = CSTRING(LyingState_GetUp);
                icon = "";
                condition = QUOTE(_player getVariable [ARR_2(QQGVAR(Lying_State),false)]);
                statement = QUOTE([_player] call FUNC(getUp));
                exceptions[] = {"isNotInside","isNotInLyingState"};
                showDisabled = 0;
            };
            class ACM_Equipment {
                displayName = CSTRING(MedicalEquipment);
                icon = QPATHTOEF(main,logo_empty.paa);
                exceptions[] = {"isNotInside", "isNotSitting"};
                class ACM_AED_Interactions {
                    displayName = ECSTRING(circulation,AED_Short);
                    condition = QUOTE(([ARR_2(_player,'ACME_AED')] call ACME_fnc_itemCount) > 0);
                    statement = "";
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    showDisabled = 0;
                    //icon = QPATHTOF(ui\icon_aed_ca.paa);
                    class ACM_AED_ViewMonitor {
                        displayName = ECSTRING(circulation,ViewMonitor);
                        condition = "true";
                        statement = QUOTE([ARR_2(_player,_player)] call EFUNC(circulation,displayAEDMonitor));
                        exceptions[] = {"isNotInside", "isNotSitting"};
                        showDisabled = 0;
                    };
                };
                                class ACM_Action_SplitMedicationPack {
                    displayName = CSTRING(SplitMedicationPack);
                    condition = "true";
                    statement = "";
                    showDisabled = 0;
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    icon = "";
                    insertChildren = QUOTE([_player] call FUNC(splitMedicationPack_childActions));
                };
            };
        };
    };

    class LandVehicle;
    class Car: LandVehicle {
        class ACE_Actions {
            class ACE_MainActions {
                ACTION_UNLOADANDCARRY;
                ACTION_REFILL_OXYGEN_425;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };

    class Car_F: Car {};
    class Quadbike_01_base_F: Car_F {
        class ACE_Actions: ACE_Actions {
            class ACE_MainActions: ACE_MainActions {
                ACTION_UNLOADANDCARRY;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };

    class Kart_01_Base_F: Car_F {
        class ACE_Actions: ACE_Actions {
            class ACE_MainActions: ACE_MainActions {
                ACTION_UNLOADANDCARRY;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };

    class Tank: LandVehicle {
        class ACE_Actions {
            class ACE_MainActions {
                ACTION_UNLOADANDCARRY;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };

    class Motorcycle: LandVehicle {
        class ACE_Actions {
            class ACE_MainActions {
                ACTION_UNLOADANDCARRY;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };

    class Air;
    class Helicopter: Air {
        class ACE_Actions {
            class ACE_MainActions {
                ACTION_UNLOADANDCARRY;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };

    class Plane: Air {
        class ACE_Actions {
            class ACE_MainActions {
                ACTION_UNLOADANDCARRY;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };

    class Ship;
    class Ship_F: Ship {
        class ACE_Actions {
            class ACE_MainActions {
                ACTION_UNLOADANDCARRY;
            };
        };
        class ACE_SelfActions {
            ACTION_PATIENTS;
        };
    };
};
