#define ACME_MEDICAL_CHEST_ACTIONS(LID_ACTION, LABEL, CONDITION, STATEMENT) \
        class UserActions { \
            class ACME_Inventory { \
                displayName = "Medical Chest Inventory"; \
                position = "chest_actions"; \
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
                selection = "chest_actions"; \
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

#define ACME_CHEST_TEXTURE_PATH(PATH) #PATH
#define ACME_CHEST_TEXTURE(NUMBER) ACME_CHEST_TEXTURE_PATH(\acm_extended\data\medical_chest\hardigg\case_##NUMBER##_co.paa)
#define ACME_CHEST_ARTWORK(NUMBER) ACME_CHEST_TEXTURE_PATH(\acm_extended\data\medical_chest\hardigg\lid_artwork_##NUMBER##_ca.paa)
#define ACME_CHEST_CLOSED_MODEL(NUMBER) ACME_CHEST_TEXTURE_PATH(\acm_extended\data\medical_chest\hardigg\medchest_##NUMBER##.p3d)
#define ACME_CHEST_LID_MODEL(NUMBER) ACME_CHEST_TEXTURE_PATH(\acm_extended\data\medical_chest\hardigg\hardigg_lid_##NUMBER##.p3d)
#define ACME_CHEST_LID_CLASS(NUMBER) ACME_CHEST_TEXTURE_PATH(ACME_MedicalChestLid_##NUMBER)
#define ACME_CHEST_DRAWER(NUMBER) class drawer_##NUMBER {source = "user"; animPeriod = 0.9; initPhase = 0;}
#define ACME_CHEST_LATCH(NUMBER,PHASE) class latch_##NUMBER {source = "user"; animPeriod = 1.4; initPhase = PHASE;}
#define ACME_CHEST_ANIMATIONS(PHASE) \
        class AnimationSources { \
            class lid {source = "user"; animPeriod = 1; initPhase = 0;}; \
            class insert {source = "user"; animPeriod = 1; initPhase = 0;}; \
            ACME_CHEST_DRAWER(1); ACME_CHEST_DRAWER(2); ACME_CHEST_DRAWER(3); ACME_CHEST_DRAWER(4); \
            ACME_CHEST_DRAWER(5); ACME_CHEST_DRAWER(6); ACME_CHEST_DRAWER(7); ACME_CHEST_DRAWER(8); \
            ACME_CHEST_LATCH(1,PHASE); ACME_CHEST_LATCH(2,PHASE); ACME_CHEST_LATCH(3,PHASE); ACME_CHEST_LATCH(4,PHASE); \
            ACME_CHEST_LATCH(5,PHASE); ACME_CHEST_LATCH(6,PHASE); ACME_CHEST_LATCH(7,PHASE); ACME_CHEST_LATCH(8,PHASE); \
            ACME_CHEST_LATCH(9,PHASE); ACME_CHEST_LATCH(10,PHASE); \
        }
// The four drawer insert has the same sources, without drawers 5 to 8.
#define ACME_CHEST_ANIMATIONS_4(PHASE) \
        class AnimationSources { \
            class lid {source = "user"; animPeriod = 1; initPhase = 0;}; \
            class insert {source = "user"; animPeriod = 1; initPhase = 0;}; \
            ACME_CHEST_DRAWER(1); ACME_CHEST_DRAWER(2); ACME_CHEST_DRAWER(3); ACME_CHEST_DRAWER(4); \
            ACME_CHEST_LATCH(1,PHASE); ACME_CHEST_LATCH(2,PHASE); ACME_CHEST_LATCH(3,PHASE); ACME_CHEST_LATCH(4,PHASE); \
            ACME_CHEST_LATCH(5,PHASE); ACME_CHEST_LATCH(6,PHASE); ACME_CHEST_LATCH(7,PHASE); ACME_CHEST_LATCH(8,PHASE); \
            ACME_CHEST_LATCH(9,PHASE); ACME_CHEST_LATCH(10,PHASE); \
        }

    class ACME_MedicalChestVisual: Box_NATO_Ammo_F {
        scope = 0;
        scopeCurator = 0;
        maximumLoad = 0;
        transportMaxWeapons = 0;
        transportMaxMagazines = 0;
        transportMaxBackpacks = 0;
        forceSupply = 0;
        showWeaponCargo = 0;
        supplyRadius = 0;
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {ACME_CHEST_TEXTURE(0)};
        ace_dragging_canDrag = 0;
        ace_dragging_canCarry = 0;
        ace_cargo_canLoad = 0;
        class TransportWeapons {};
        class TransportMagazines {};
        class TransportItems {};
        class TransportBackpacks {};
    };

    class ACME_MedicalChest: ACME_MedicalChestVisual {
        model = "\acm_extended\data\medical_chest\hardigg\medchest.p3d";
        scope = 2;
        scopeCurator = 2;
        author = "mavis";
        displayName = "Medical Chest (Full Stock)";
        hiddenSelections[] = {"camo", "lid_artwork"};
        hiddenSelectionsTextures[] = {ACME_CHEST_TEXTURE(0), ACME_CHEST_ARTWORK(0)};
        acmeChestLidClass = "ACME_MedicalChestLid";
        // The drawer unit shown while the chest is open. A mission can override it on one chest with the
        // variable ACME_medicalChestCabinetClass.
        acmeChestCabinetClass = "ACME_MedicalChest8Drawers";
        editorCategory = "EdCat_Supplies";
        editorSubcategory = "ACM_core_EditorCategory";
        ace_dragging_canDrag = 0;
        ace_dragging_canCarry = 0;
        ace_cargo_canLoad = 0;
        ACME_CHEST_ANIMATIONS(0);
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

#define ACME_MEDICAL_CHEST_RETEXTURE(CLASS,NUMBER,LABEL,STOCK,CABINET) \
    class CLASS: ACME_MedicalChest { \
        scope = 2; \
        scopeCurator = 2; \
        displayName = LABEL; \
        model = ACME_CHEST_CLOSED_MODEL(NUMBER); \
        acmeChestLidClass = ACME_CHEST_LID_CLASS(NUMBER); \
        acmeChestVariant = NUMBER; \
        hiddenSelectionsTextures[] = {ACME_CHEST_TEXTURE(NUMBER), ACME_CHEST_ARTWORK(NUMBER)}; \
        acmeChestStock = STOCK; \
        acmeChestCabinetClass = CABINET; \
    }
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_01,1,"Medical Chest 01 (MED CHEST 1)","","ACME_MedicalChest8Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_02,2,"Medical Chest 02 (Field Markings)","","ACME_MedicalChest8Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_03,3,"Medical Chest 03 (OR)","surgery","ACME_MedicalChest8Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_04,4,"Medical Chest 04 (MED)","","ACME_MedicalChest8Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_05,5,"Medical Chest 05 (PAD)","dressings","ACME_MedicalChest4Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_06,6,"Medical Chest 06 (IV FLUIDS)","fluids","ACME_MedicalChest4Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_07,7,"Medical Chest 07 (AIRWAY)","airway","ACME_MedicalChest8Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_08,8,"Medical Chest 08 (BLOOD)","blood","ACME_MedicalChest4Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_09,9,"Medical Chest 09 (Black Cross)","","ACME_MedicalChest8Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_10,10,"Medical Chest 10 (Red Cross)","","ACME_MedicalChest8Drawers");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_11,11,"Medical Chest 11 (Black Lid)","","ACME_MedicalChest8Drawers");
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

    class ACME_MedicalChest8Drawers: ACME_MedicalChestVisual {
        scope = 1;
        displayName = "Medical Chest";
        model = "\acm_extended\data\medical_chest\hardigg\medchest_open.p3d";
        // Drawer 8 is padlocked to the cabinet: it stays shut while the others slide out.
        acmeChestLockedDrawers[] = {"drawer_8"};
        ACME_CHEST_ANIMATIONS(1);
        ACME_MEDICAL_CHEST_ACTIONS(ACME_CloseMedicalChest,"Close Medical Chest","[_target,_player,false] call ACME_fnc_medicalChestCanUse","[_target,_player,false] call ACME_fnc_medicalChestUse");
    };

    class ACME_MedicalChest4Drawers: ACME_MedicalChest8Drawers {
        model = "\acm_extended\data\medical_chest\hardigg\medchest_open_4.p3d";
        acmeChestLockedDrawers[] = {};
        ACME_CHEST_ANIMATIONS_4(1);
    };
    class ACME_MedicalChest7Drawers: ACME_MedicalChest8Drawers {};

    class ACME_MedicalChestLid: ACME_MedicalChestVisual {
        scope = 1;
        model = "\acm_extended\data\medical_chest\hardigg\hardigg_lid.p3d";
        hiddenSelections[] = {"camo", "lid_artwork"};
        hiddenSelectionsTextures[] = {ACME_CHEST_TEXTURE(0), ACME_CHEST_ARTWORK(0)};
    };

#define ACME_CHEST_LID_VARIANT(NUMBER) \
    class ACME_MedicalChestLid_##NUMBER: ACME_MedicalChestLid { \
        model = ACME_CHEST_LID_MODEL(NUMBER); \
        hiddenSelectionsTextures[] = {ACME_CHEST_TEXTURE(NUMBER), ACME_CHEST_ARTWORK(NUMBER)}; \
    }
    ACME_CHEST_LID_VARIANT(1); ACME_CHEST_LID_VARIANT(2); ACME_CHEST_LID_VARIANT(3);
    ACME_CHEST_LID_VARIANT(4); ACME_CHEST_LID_VARIANT(5); ACME_CHEST_LID_VARIANT(6);
    ACME_CHEST_LID_VARIANT(7); ACME_CHEST_LID_VARIANT(8); ACME_CHEST_LID_VARIANT(9);
    ACME_CHEST_LID_VARIANT(10); ACME_CHEST_LID_VARIANT(11);
#undef ACME_CHEST_LID_VARIANT
#undef ACME_CHEST_LID_CLASS
#undef ACME_CHEST_LID_MODEL
#undef ACME_CHEST_CLOSED_MODEL
#undef ACME_CHEST_ANIMATIONS_4
#undef ACME_CHEST_ANIMATIONS
#undef ACME_CHEST_LATCH
#undef ACME_CHEST_DRAWER
#undef ACME_CHEST_ARTWORK
#undef ACME_CHEST_TEXTURE
#undef ACME_CHEST_TEXTURE_PATH
#undef ACME_MEDICAL_CHEST_ACTIONS
