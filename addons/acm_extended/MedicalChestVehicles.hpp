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
        class ACE_Actions {
            class ACE_MainActions {
                displayName = "Medical Chest";
                distance = 4;
                condition = "private _state = _target getVariable ['ACME_medicalChestState',[]]; count _state == 2 && {!(_state select 1)}";
                selection = "";
                class ACME_OpenMedicalChest {
                    displayName = "Open Medical Chest";
                    distance = 4;
                    condition = "true";
                    statement = "[_target,_player,'open'] call ACME_fnc_medicalChestUse";
                };
            };
        };
    };

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
        supplyRadius = 0;
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
                displayName = "Medical Chest"; \
                distance = 4; \
                selection = ""; \
                condition = "((_target getVariable ['ACME_medicalChestAnchor',objNull]) getVariable ['ACME_medicalChestState',[0,false]]) select 1"; \
                class ACME_MedicalChestSupplies { \
                    displayName = "Open Supplies"; \
                    distance = 4; \
                    condition = "true"; \
                    statement = "[_target,_player,'supplies'] call ACME_fnc_medicalChestUse"; \
                }; \
                class ACME_CloseMedicalChest { \
                    displayName = "Close Medical Chest"; \
                    distance = 4; \
                    condition = "true"; \
                    statement = "[_target,_player,'close'] call ACME_fnc_medicalChestUse"; \
                }; \
            }; \
        }; \
    }
    ACME_MEDICAL_CHEST_OPEN_VARIANT(ACME_MedicalChest4Drawers,Land_PortableCabinet_01_4drawers_olive_F);
    ACME_MEDICAL_CHEST_OPEN_VARIANT(ACME_MedicalChest7Drawers,Land_PortableCabinet_01_7drawers_olive_F);
#undef ACME_MEDICAL_CHEST_OPEN_VARIANT
