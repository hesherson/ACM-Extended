#include "..\main\script_build.hpp"
// SKED rescue stretcher (28 in x 8 ft, OD green): rolled in its pack, laid out open, and wrapped round a
// casualty. The litter behaviour (strap in, drag, team carry, vehicles) is in acme_sked_ace.
// All paths use single backslashes.
// Adapted from the supplied SKED model package.

class CfgPatches {
    class acme_sked {
        ACME_BUILD_CONFIG("acme_sked");
        name = "ACM Extended SKED";
        author = "mavis";
        requiredVersion = 2.0;
        requiredAddons[] = {"A3_Data_F_AoW_Loadorder"};
        units[] = {"ACME_SKED_Item_Ground", "ACME_SKED_Pack", "ACME_SKED_Rolled", "ACME_SKED_Open", "ACME_SKED_Wrapped"};
        weapons[] = {"ACME_SKED_Item"};
    };
};

class CfgEditorCategories {
    class ACME_EdCat_Medical {
        displayName = "ACM Extended";
    };
};

class CfgEditorSubcategories {
    class ACME_EdSubcat_Litters {
        displayName = "Litters";
    };
};

class CfgWeapons {
    class ItemCore;
    class InventoryItem_Base_F;
    class ACME_SKED_Item: ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "SKED Rescue Stretcher";
        descriptionShort = "Roll-up rescue stretcher, 28 in x 8 ft, in its pack. Carried in your inventory, the pack hangs from your right shoulder and leaves your backpack free. Lay it out, strap a casualty in, drag or carry them.";
        model = "\acme_sked\sked_pack.p3d";
        picture = "\acme_sked\data\ui\icon_sked_ca.paa";
        class ItemInfo: InventoryItem_Base_F {
            mass = 160;
        };
    };
};

class CfgVehicles {
    class Item_Base_F;
    class ThingX;

    class ACME_SKED_Item_Ground: Item_Base_F {
        scope = 2;
        scopeCurator = 2;
        author = "mavis";
        displayName = "SKED Rescue Stretcher [Item]";
        editorCategory = "ACME_EdCat_Medical";
        editorSubcategory = "ACME_EdSubcat_Litters";
        vehicleClass = "Items";
        class TransportItems {
            class _xx_ACME_SKED_Item {
                name = "ACME_SKED_Item";
                count = 1;
            };
        };
    };

    // Some curator and mission item spawners pass the inventory classname to createVehicle.
    class ACME_SKED_Item: ACME_SKED_Item_Ground {
        scope = 1;
        scopeCurator = 0;
    };

    // Base for the three SKED objects. The ACE properties are read only when ACE is loaded.
    class ACME_SKED_Base: ThingX {
        scope = 0;
        author = "mavis";
        icon = "iconObject_1x1";
        editorCategory = "ACME_EdCat_Medical";
        editorSubcategory = "ACME_EdSubcat_Litters";
        destrType = "DestructNo";
        mapSize = 2.4;
        acmeLitterOpen = "ACME_SKED_Open";
        acmeLitterOccupied = "ACME_SKED_Wrapped";
        acmeLitterChestPoint = "pt_spine3";
        acmeLitterHandles[] = {"handle_lh", "handle_rh", "handle_lf", "handle_rf"};
    };
    class ACME_SKED_Pack: ACME_SKED_Base {
        scope = 2;
        scopeCurator = 2;
        displayName = "SKED (in its bag)";
        model = "\acme_sked\sked_pack.p3d";
        mapSize = 0.9;
        ace_dragging_canCarry = 1;
        ace_dragging_carryPosition[] = {0, 0.7, 1.0};
        ace_dragging_carryDirection = 90;
        ace_cargo_size = 1;
        ace_cargo_canLoad = 1;
    };
    class ACME_SKED_Rolled: ACME_SKED_Pack {
        displayName = "SKED (rolled)";
        model = "\acme_sked\sked_rolled.p3d";
    };
    class ACME_SKED_Open: ACME_SKED_Base {
        scope = 2;
        scopeCurator = 2;
        displayName = "SKED (laid out)";
        model = "\acme_sked\sked_open.p3d";
        ace_dragging_canDrag = 1;
        ace_dragging_dragPosition[] = {0, 1.55, 0};
        ace_dragging_dragDirection = 180;
        ace_dragging_canCarry = 1;
        ace_dragging_carryPosition[] = {0, 0.6, 0.9};
        ace_dragging_carryDirection = 90;
        ace_cargo_size = 1;
        ace_cargo_canLoad = 1;
    };
    // With a casualty strapped in. Created and removed by acme_sked_ace; placed by hand it is an empty prop.
    // One rescuer drags it head first by the tow strap (ACE drag); a team carries it by the handles.
    class ACME_SKED_Wrapped: ACME_SKED_Base {
        scope = 2;
        scopeCurator = 0;
        displayName = "SKED (casualty strapped in)";
        model = "\acme_sked\sked_wrapped.p3d";
        ace_dragging_canDrag = 1;
        ace_dragging_dragPosition[] = {0, 1.55, 0};
        ace_dragging_dragDirection = 180;
        ace_dragging_canCarry = 0;
    };
};
