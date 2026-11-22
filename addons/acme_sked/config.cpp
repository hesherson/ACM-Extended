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
        dlc = "ACM_Extended";
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
        dlc = "ACM_Extended";
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
        dlc = "ACM_Extended";
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
        // Where the casualty lies, in the axes of the litter (the laid out and the occupied model stand at the same
        // place): the middle of the chest, the height of the bed, and the pose (fn_patientPose.sqf).
        acmeLitterChest[] = {0, 0.479};
        acmeLitterBedHeight = 0.006;
        acmeLitterPose = "ACME_Litter_Side";
        // where the casualty's pack lies while they are on the litter: on their shins, at this height
        acmeLitterBag[] = {0, -0.42, 0.0};
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
        // the HPMK laid out ready on it ("Stage HPMK": acme_sked_fnc_stageHpmk, tools/build_hpmk_staged.py)
        acmeHpmkStaged = "\acme_hpmk\hpmk_staged_sked.p3d";
        // Dragged with ACME's drag (fn_dragLocal.sqf): by the tow strap, the foot end trailing.
        acmeDragPoint = "tow";
        acmeDragRear = "foot_end";
        // While it is dragged its strap runs up to the rescuer's left hip (fn_dragStrapAim.sqf, model.cfg):
        // the strap is this long, it turns about this point of the SKED, and the rescuer walks this far in front
        // of that point.
        acmeDragStrap = 1.45;
        acmeDragStrapFrom = "head_end";
        acmeDragStrapReach = 1.2;
        class AnimationSources {
            class strap_pitch {
                source = "user";
                animPeriod = 0.3;
                initPhase = 0;
            };
            class strap_yaw: strap_pitch {};
        };
        ace_dragging_canDrag = 0;
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
        acmeDragPoint = "tow";
        acmeDragRear = "foot_end";
        acmeDragStrap = 1.45;
        acmeDragStrapFrom = "head_end";
        acmeDragStrapReach = 1.2;
        class AnimationSources {
            class strap_pitch {
                source = "user";
                animPeriod = 0.3;
                initPhase = 0;
            };
            class strap_yaw: strap_pitch {};
            // the five straps over the casualty, each up and down (model.cfg; fn_strapFit.sqf)
            class fit_feet {
                source = "user";
                animPeriod = 0.4;
                initPhase = 0;
            };
            class fit_knee: fit_feet {};
            class fit_pelvis: fit_feet {};
            class fit_belly: fit_feet {};
            class fit_chest: fit_feet {};
            // 1: the SKED's own strap is taken out (a model of it hangs there instead, fn_strapArcs.sqf)
            class own_pelvis {
                source = "user";
                animPeriod = 0.001;
                initPhase = 0;
            };
            class own_belly: own_pelvis {};
            class own_chest: own_pelvis {};
            class own_knee: own_pelvis {};
            class own_feet: own_pelvis {};
        };
        // Straps pulled tight over the casualty, as models of their own (tools/build_sked_strap_arcs.py), and the
        // source that takes the SKED's own strap out for each. Bare: the three that cross his arms and hands
        // (the leg straps go round each thigh). In the HPMK: all five, over the shell he wears.
        acmeStrapArcBare[] = {"\acme_sked\sked_strap_pelvis_bare.p3d", "\acme_sked\sked_strap_belly_bare.p3d", "\acme_sked\sked_strap_chest_bare.p3d"};
        acmeStrapArcHpmk[] = {"\acme_sked\sked_strap_pelvis_hpmk.p3d", "\acme_sked\sked_strap_belly_hpmk.p3d", "\acme_sked\sked_strap_chest_hpmk.p3d", "\acme_sked\sked_strap_knee_hpmk.p3d", "\acme_sked\sked_strap_feet_hpmk.p3d"};
        // With the HPMK opened over his chest: the straps over belly and chest are undone (no model: nothing can be
        // folded back from under a closed strap). The one over the pelvis stays closed, and the folded cover lies
        // over it (tools/hpmk_opened.py).
        acmeStrapArcHpmkOpen[] = {"\acme_sked\sked_strap_pelvis_hpmk.p3d", "\A3\Weapons_F\empty.p3d", "\A3\Weapons_F\empty.p3d", "\acme_sked\sked_strap_knee_hpmk.p3d", "\acme_sked\sked_strap_feet_hpmk.p3d"};
        acmeStrapArcSources[] = {"own_pelvis", "own_belly", "own_chest", "own_knee", "own_feet"};
        // How far each strap is moved from where it is modelled (m; feet, knee, pelvis, belly, chest), for a bare
        // casualty and for one in the HPMK. As modelled the straps stand 8 to 15 cm over a bare casualty.
        acmeStrapFitSources[] = {"fit_feet", "fit_knee", "fit_pelvis", "fit_belly", "fit_chest"};
        acmeStrapFitBare[] = {-0.05, -0.12, -0.105, -0.105, -0.10};
        acmeStrapFitHpmk[] = {0.04, -0.04, -0.05, -0.06, -0.10};
        ace_dragging_canDrag = 0;
        ace_dragging_dragPosition[] = {0, 1.55, 0};
        ace_dragging_dragDirection = 180;
        ace_dragging_canCarry = 0;
    };
};
