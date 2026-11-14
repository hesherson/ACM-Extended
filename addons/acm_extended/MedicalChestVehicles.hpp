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
        class ACE_Actions {
            class ACE_MainActions {
                displayName = "Open Medical Chest";
                distance = 4;
                condition = "private _state = _target getVariable ['ACME_medicalChestState',[]]; count _state == 2 && {!(_state select 1)} && {[_player,_target,[]] call ace_common_fnc_canInteractWith}";
                selection = "";
                statement = "[_target,_player,true] call ACME_fnc_medicalChestUse";
            };
        };
    };

#define ACME_MEDICAL_CHEST_RETEXTURE(CLASS,NUMBER,LABEL) \
    class CLASS: ACME_MedicalChest { \
        scope = 2; \
        scopeCurator = 2; \
        displayName = LABEL; \
        acmeChestVariant = NUMBER; \
    }
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_01,1,"Medical Chest 01 (MED CHEST 1)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_02,2,"Medical Chest 02 (Field Markings)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_03,3,"Medical Chest 03 (OR)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_04,4,"Medical Chest 04 (MED)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_05,5,"Medical Chest 05 (PAD)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_06,6,"Medical Chest 06 (IV FLUIDS)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_07,7,"Medical Chest 07 (AIRWAY)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_08,8,"Medical Chest 08 (BLOOD)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_09,9,"Medical Chest 09 (Black Cross)");
    ACME_MEDICAL_CHEST_RETEXTURE(ACME_MedicalChest_10,10,"Medical Chest 10 (Red Cross)");
#undef ACME_MEDICAL_CHEST_RETEXTURE

    // An invisible model provides a live native Gear container inside the chest.
    class ACME_MedicalChestCargo: Box_NATO_Ammo_F {
        scope = 1;
        scopeCurator = 0;
        displayName = "Medical Chest";
        model = "\core\empty\empty.p3d";
        maximumLoad = 20000;
        transportMaxWeapons = 2000;
        transportMaxMagazines = 2000;
        transportMaxBackpacks = 100;
        supplyRadius = 2.5;
        forceSupply = 1;
        showWeaponCargo = 0;
        ace_cargo_canLoad = 0;
        ace_dragging_canDrag = 0;
        ace_dragging_canCarry = 0;
        class TransportWeapons {};
        class TransportMagazines {};
        class TransportItems {};
        class TransportBackpacks {};
    };

#define ACME_MEDICAL_CHEST_OPEN_VARIANT(NAME, BASE) \
    class NAME: BASE { \
        scope = 1; \
        scopeCurator = 0; \
        displayName = "Medical Chest"; \
        ace_cargo_canLoad = 0; \
        ace_dragging_canDrag = 0; \
        ace_dragging_canCarry = 0; \
        class UserActions {}; \
        class ACE_Actions { \
            class ACE_MainActions { \
                displayName = "Close Medical Chest"; \
                distance = 4; \
                selection = ""; \
                condition = "(((_target getVariable ['ACME_medicalChestAnchor',objNull]) getVariable ['ACME_medicalChestState',[0,false]]) select 1) && {[_player,_target,[]] call ace_common_fnc_canInteractWith}"; \
                statement = "[_target,_player,false] call ACME_fnc_medicalChestUse"; \
            }; \
        }; \
    }
    ACME_MEDICAL_CHEST_OPEN_VARIANT(ACME_MedicalChest4Drawers,Land_PortableCabinet_01_4drawers_olive_F);
    ACME_MEDICAL_CHEST_OPEN_VARIANT(ACME_MedicalChest7Drawers,Land_PortableCabinet_01_7drawers_olive_F);
#undef ACME_MEDICAL_CHEST_OPEN_VARIANT
