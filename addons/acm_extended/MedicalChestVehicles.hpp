#define ACME_MEDICAL_CHEST_ACTIONS(LID_ACTION, LABEL, CONDITION, STATEMENT) \
        class UserActions { \
            class ACME_Inventory { \
                displayName = "Medical Chest Inventory"; \
                position = ""; \
                radius = 4; \
                priority = 2; \
                showWindow = 0; \
                hideOnUse = 1; \
                onlyForPlayer = 1; \
                condition = "([this] call ACME_fnc_medicalChestTarget) isNotEqualTo []"; \
                statement = "[this,ACE_player] call ACME_fnc_medicalChestInventory"; \
            }; \
        }; \
        class ACE_Actions { \
            class ACE_MainActions { \
                displayName = "Medical Chest"; \
                distance = 4; \
                selection = ""; \
                condition = "[_target,_player] call ACME_fnc_medicalChestCanUse"; \
                class ACME_Inventory { \
                    displayName = "Inventory"; \
                    condition = "[_target,_player] call ACME_fnc_medicalChestCanUse"; \
                    statement = "[_target,_player] call ACME_fnc_medicalChestInventory"; \
                }; \
                class LID_ACTION { \
                    displayName = LABEL; \
                    condition = CONDITION; \
                    statement = STATEMENT; \
                }; \
            }; \
        }

    class Land_PortableCabinet_01_closed_olive_F;
    class Land_PortableCabinet_01_4drawers_olive_F;
    class Land_PortableCabinet_01_7drawers_olive_F;

    class ACME_MedicalChest: Land_PortableCabinet_01_closed_olive_F {
        scope = 2;
        scopeCurator = 2;
        author = "mavis";
        displayName = "Medical Chest (Full Stock)";
        editorCategory = "EdCat_Supplies";
        editorSubcategory = "ACM_core_EditorCategory";
        ace_dragging_canDrag = 0;
        ace_dragging_canCarry = 0;
        ace_cargo_canLoad = 0;
        class Attributes {
            class ACME_medicalChestStartOpen {
                property = "ACME_medicalChestStartOpen";
                displayName = "Start Open";
                tooltip = "Place the detached lid beside the chest and start with the drawers accessible.";
                control = "Checkbox";
                typeName = "BOOL";
                defaultValue = "false";
                expression = "if (!is3DEN && {isServer}) then {_this setVariable ['ACME_medicalChestStartOpen', _value];};";
            };
        };
        ACME_MEDICAL_CHEST_ACTIONS(ACME_OpenMedicalChest,"Open Medical Chest","[_target,_player,true] call ACME_fnc_medicalChestCanUse","[_target,_player,true] call ACME_fnc_medicalChestUse");
    };

#define ACME_MEDICAL_CHEST_RETEXTURE(CLASS,NUMBER,LABEL,STOCK) \
    class CLASS: ACME_MedicalChest { \
        scope = 2; \
        scopeCurator = 2; \
        displayName = LABEL; \
        acmeChestVariant = NUMBER; \
        acmeChestStock = STOCK; \
    }
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_01,1,"Medical Chest 01 (MED CHEST 1)","");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_02,2,"Medical Chest 02 (Field Markings)","");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_03,3,"Medical Chest 03 (OR)","surgery");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_04,4,"Medical Chest 04 (MED)","");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_05,5,"Medical Chest 05 (PAD)","dressings");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_06,6,"Medical Chest 06 (IV FLUIDS)","fluids");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_07,7,"Medical Chest 07 (AIRWAY)","airway");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_08,8,"Medical Chest 08 (BLOOD)","blood");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_09,9,"Medical Chest 09 (Black Cross)","");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_10,10,"Medical Chest 10 (Red Cross)","");
#undef ACME_MEDICAL_CHEST_RETEXTURE

    // An invisible model provides a live native Gear container inside the chest.
    class ACME_MedicalChestCargo: Box_NATO_Ammo_F {
        scope = 1;
        scopeCurator = 0;
        displayName = "Medical Chest";
        model = "\core\empty\empty.p3d";
        maximumLoad = 2000000;
        transportMaxWeapons = 2000;
        transportMaxMagazines = 2000;
        transportMaxBackpacks = 100;
        supplyRadius = 2.5;
        forceSupply = 1;
        showWeaponCargo = 0;
        ace_cargo_canLoad = 0;
        class ACE_Actions {class ACE_MainActions {condition = "false";};};
        ace_dragging_canDrag = 0;
        ace_dragging_canCarry = 0;
        class TransportWeapons {};
        class TransportMagazines {};
        class TransportItems {};
        class TransportBackpacks {};
    };
    class ACME_MedicalChestSpecialtyCargo: ACME_MedicalChestCargo {
        maximumLoad = 20000;
    };

#define ACME_MEDICAL_CHEST_OPEN_VARIANT(NAME, BASE) \
    class NAME: BASE { \
        scope = 1; \
        scopeCurator = 0; \
        displayName = "Medical Chest"; \
        ace_cargo_canLoad = 0; \
        ace_dragging_canDrag = 0; \
        ace_dragging_canCarry = 0; \
        ACME_MEDICAL_CHEST_ACTIONS(ACME_CloseMedicalChest,"Close Medical Chest","[_target,_player,false] call ACME_fnc_medicalChestCanUse","[_target,_player,false] call ACME_fnc_medicalChestUse"); \
    }
    ACME_MEDICAL_CHEST_OPEN_VARIANT(ACME_MedicalChest4Drawers,Land_PortableCabinet_01_4drawers_olive_F);
    ACME_MEDICAL_CHEST_OPEN_VARIANT(ACME_MedicalChest7Drawers,Land_PortableCabinet_01_7drawers_olive_F);
#undef ACME_MEDICAL_CHEST_OPEN_VARIANT
#undef ACME_MEDICAL_CHEST_ACTIONS
